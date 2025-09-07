# --- Care Count Inventory (OCR-only suggestion via Hugging Face Inference API) ---

import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue on Spaces
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import io
import time
import base64
import json
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
from supabase import create_client, Client

try:
    from huggingface_hub import InferenceClient
except Exception:
    InferenceClient = None  # we'll fall back to raw HTTP

# ------------------------ Page ------------------------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("OCR-assisted inventory logging with Supabase (Hugging Face Inference API)")

# ------------------------ Secrets & clients ------------------------
def get_secret(name: str, default: str | None = None) -> str | None:
    # Reads from env/variables first, then from st.secrets
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HF_TOKEN = get_secret("HF_TOKEN")  # optional but recommended for reliability/rate limits
OCR_MODEL = (os.getenv("OCR_MODEL") or st.secrets.get("OCR_MODEL")
             or "microsoft/trocr-large-printed").strip().strip('"').strip("'")

# ------------------------ Image utilities ------------------------
def _to_png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

def preprocess_for_label(img: Image.Image) -> Image.Image:
    """Lighten/contrast + gentle resize for mobile, improves label legibility."""
    img = img.convert("RGB")
    # Resize longest side to ~1024px (helps OCR without huge payloads)
    w, h = img.size
    scale = 1024 / max(w, h) if max(w, h) > 1024 else 1.0
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Brightness(img).enhance(1.12)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    sharp = ImageEnhance.Sharpness(img).enhance(1.2)
    return sharp

# ------------------------ OCR helpers ------------------------
@st.cache_resource(show_spinner=False)
def _hf_client():
    if InferenceClient is None:
        return None
    try:
        return InferenceClient(token=HF_TOKEN)
    except Exception:
        return None

def _ocr_via_client(img: Image.Image) -> tuple[str, str | None]:
    """
    Preferred path: huggingface_hub.InferenceClient.image_to_text
    Returns (text, error)
    """
    client = _hf_client()
    if client is None:
        return "", "HF client unavailable"
    try:
        text = client.image_to_text(image=_to_png_bytes(img), model=OCR_MODEL)
        if isinstance(text, dict):
            # Some backends return {"generated_text": "..."}
            text = text.get("generated_text", "")
        return (text or "").strip(), None
    except Exception as e:
        return "", f"client error: {e}"

def _ocr_via_http(img: Image.Image) -> tuple[str, str | None]:
    """
    Fallback: raw HTTP to Inference API.
    TrOCR (image-to-text) accepts base64 in JSON for Inference API.
    """
    try:
        url = f"https://api-inference.huggingface.co/models/{OCR_MODEL}"
        headers = {"Accept": "application/json"}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        img_b64 = base64.b64encode(_to_png_bytes(img)).decode("utf-8")
        payload = {"inputs": img_b64}

        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code in (503, 524):
            return "", f"model loading ({r.status_code})"
        if r.status_code == 404:
            return "", "model not found (404)"
        if r.status_code != 200:
            return "", f"HTTP {r.status_code}: {r.text[:200]}"

        out = r.json()
        # TrOCR usually returns {"generated_text": "..."} or plain string
        if isinstance(out, dict):
            text = out.get("generated_text", "")
        elif isinstance(out, list) and out and isinstance(out[0], dict):
            text = out[0].get("generated_text", "")
        else:
            text = out if isinstance(out, str) else ""
        return (text or "").strip(), None
    except Exception as e:
        return "", f"http error: {e}"

def run_ocr(img: Image.Image) -> dict:
    """
    Single OCR pass + simple normalization => an item name.
    """
    errors = []
    pre = preprocess_for_label(img)

    text, err = _ocr_via_client(pre)
    if err or not text:
        errors.append(err or "empty")
        text, err2 = _ocr_via_http(pre)
        if err2:
            errors.append(err2)

    name = normalize_from_text(text)
    return {
        "name": name if name else "Unknown",
        "ocr_text": text,
        "model": OCR_MODEL,
        "errors": [e for e in errors if e],
    }

# ------------------------ Normalizer (simple) ------------------------
# Extend anytime with categories you care about
TYPE_WORDS = [
    "soup", "beans", "rice", "pasta", "sauce", "salsa", "cereal", "oats",
    "toothpaste", "toothbrush", "soap", "shampoo", "conditioner",
    "lotion", "body lotion", "mayonnaise", "ketchup", "mustard",
    "peanut butter", "jam", "jelly", "soda", "juice", "tea", "coffee",
    "tuna", "chicken", "beef", "noodles", "flour", "sugar", "salt",
    "deodorant", "antiperspirant", "detergent", "sanitizer", "oil"
]

def normalize_from_text(text: str) -> str:
    """
    Very lightweight: try to pull a 'brand' (first capitalized word)
    and a 'type' (any known type in the text). Fallback to the first 4-5 words.
    """
    t = (text or "").strip()
    if not t:
        return ""

    # candidate brand: first word that looks like Title Case or ALLCAPS
    tokens = [w.strip(",.:;!|/\\-()[]{}") for w in t.split()]
    brand = ""
    for w in tokens[:8]:  # look near the front
        if len(w) >= 2 and (w.isupper() or (w[0].isupper() and w[1:].islower())):
            brand = w
            break

    # candidate type: first match from TYPE_WORDS
    low = t.lower()
    found_type = ""
    for k in TYPE_WORDS:
        if k in low:
            found_type = k
            break

    parts = [p for p in [brand, found_type] if p]
    if parts:
        return " ".join(parts).strip()

    # Fallback: compress to a few words
    return " ".join(tokens[:5]).strip()

# ------------------------ Volunteer login ------------------------
st.subheader("👤 Volunteer")

with st.form("vol_form", clear_on_submit=True):
    username = st.text_input("Username")
    full_name = st.text_input("Full name")
    submitted = st.form_submit_button("Add / Continue")
    if submitted:
        if not (username and full_name):
            st.error("Please fill both fields.")
        else:
            try:
                existing = sb.table("volunteers").select("full_name").execute().data or []
                names = {v["full_name"].strip().lower() for v in existing}
                if full_name.strip().lower() not in names:
                    sb.table("volunteers").insert({"username": username, "full_name": full_name}).execute()
                st.session_state["volunteer"] = username
                st.session_state["volunteer_name"] = full_name
                st.success(f"Welcome, {full_name}!")
            except Exception as e:
                st.error(f"Volunteer add/check failed: {e}")

if "volunteer" not in st.session_state:
    st.info("Add yourself above to start logging.")
    st.stop()

# ------------------------ Capture / Upload ------------------------
st.subheader("📸 Scan label to auto-fill item")

c1, c2 = st.columns(2)
with c1:
    cam = st.camera_input("Use your phone or webcam")
with c2:
    up = st.file_uploader("…or upload an image", type=["png", "jpg", "jpeg"])

img_file = cam or up
if img_file:
    img = Image.open(img_file).convert("RGB")
    st.image(img, use_container_width=True)

    if st.button("🔍 Suggest name"):
        t0 = time.time()
        result = run_ocr(img)
        st.success(f"🧠 Suggested: **{result['name']}** · ⏱️ {time.time()-t0:.2f}s")
        with st.expander("🔎 Debug (OCR)"):
            st.json(result)
        st.session_state["scanned_item_name"] = result["name"]

# ------------------------ Add inventory item ------------------------
st.subheader("📥 Add inventory item")

item_name = st.text_input("Item name", value=st.session_state.get("scanned_item_name", ""))
quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
category = st.text_input("Category (optional)")
expiry = st.date_input("Expiry date (optional)")

if st.button("✅ Log item"):
    if not item_name.strip():
        st.warning("Enter an item name.")
    else:
        try:
            # Preferred simple table
            sb.table("inventory").insert({
                "item_name": item_name.strip(),
                "quantity": int(quantity),
                "category": (category.strip() or None),
                "expiry_date": str(expiry) if expiry else None,
                "added_by": st.session_state.get("volunteer", "Unknown"),
            }).execute()
            st.success("Logged to 'inventory'!")
        except Exception as e1:
            # Fallback to your existing wide log table
            try:
                payload_vi = {
                    "item_name": item_name.strip(),
                    "qty": int(quantity),
                    "category": (category.strip() or None),
                    "volunteer": st.session_state.get("volunteer_name")
                                 or st.session_state.get("volunteer")
                                 or "Unknown",
                }
                sb.table("visit_items").insert(payload_vi).execute()
                st.success("Logged to 'visit_items'!")
            except Exception as e2:
                st.error(f"Insert failed: {e1}\nFallback failed: {e2}")

# ------------------------ Live inventory (tries multiple tables) ------------------------
st.subheader("📊 Live inventory")

def _try_fetch(table: str):
    try:
        # try common timestamp fields first
        return sb.table(table).select("*").order("created_ts", desc=True).execute().data
    except Exception:
        try:
            return sb.table(table).select("*").order("created_at", desc=True).execute().data
        except Exception:
            try:
                return sb.table(table).select("*").limit(1000).execute().data
            except Exception:
                return None

data = _try_fetch("inventory")
if not data:
    data = _try_fetch("visit_items")
if not data:
    data = _try_fetch("inventory_master")

if data:
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "⬇️ Export CSV",
        df.to_csv(index=False).encode("utf-8"),
        "care_count_inventory.csv",
        "text/csv",
    )
else:
    st.caption("No items yet or tables not found. (Tried: inventory, visit_items, inventory_master)")
