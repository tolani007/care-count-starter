# --- Care Count Inventory (VQA-only suggestion, free HF API) ---

import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue on Spaces
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import io
import time
import base64
import requests
import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client, Client

# ------------------------ Page ------------------------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("BLIP-VQA–assisted inventory logging with Supabase (free HF Inference API)")

# ------------------------ Secrets & clients ------------------------
def get_secret(name: str, default: str | None = None) -> str | None:
    # Reads from env first (HF Variables), then from st.secrets (HF Secrets)
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- VQA model config (free serverless endpoint) ----
HF_TOKEN = get_secret("HF_TOKEN")  # “Read” token is fine
VQA_MODEL = os.getenv("VQA_MODEL", "Salesforce/blip-vqa-capfilt-large")  # better than base; still free

# ------------------------ Tiny image util ------------------------
def _to_png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

# ------------------------ HTTP VQA helper ------------------------
def vqa_http(img: Image.Image, question: str) -> tuple[str, str | None]:
    """
    Calls HF Inference API for 'image-question-answering' (BLIP-VQA).
    No huggingface_hub client; pure requests to avoid kwarg/version issues.
    Returns (answer, error).
    """
    try:
        img_b64 = base64.b64encode(_to_png_bytes(img)).decode("utf-8")
        url = f"https://api-inference.huggingface.co/models/{VQA_MODEL}"
        headers = {"Accept": "application/json"}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        payload = {"inputs": {"question": question, "image": img_b64}}

        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code != 200:
            return "", f"VQA HTTP {r.status_code}: {r.text[:200]}"

        out = r.json()
        # API sometimes returns list[dict] or dict
        if isinstance(out, list) and out:
            ans = out[0].get("answer") or out[0].get("generated_text") or ""
        elif isinstance(out, dict):
            ans = out.get("answer") or out.get("generated_text") or ""
        else:
            ans = ""
        return (ans or "").strip(), None
    except Exception as e:
        return "", f"VQA HTTP error: {e}"

# ------------------------ Normalizer ------------------------
BRAND_ALIASES = {
    "degree": "Degree",
    "campbell's": "Campbell's",
    "heinz": "Heinz",
    "kellogg's": "Kellogg's",
    "quaker": "Quaker",
    "pepsi": "Pepsi",
    "coke": "Coca-Cola",
}

TYPE_ALIASES = {
    "antiperspirant": "Antiperspirant",
    "deodorant": "Deodorant",
    "toothpaste": "Toothpaste",
    "tooth brush": "Toothbrush",
    "cereal": "Cereal",
    "soup": "Soup",
    "beans": "Beans",
    "rice": "Rice",
    "pasta": "Pasta",
    "sauce": "Sauce",
    "soda": "Soda",
}

def _clean_name(s: str) -> str:
    return (s or "").strip().lower()

def normalize_item(brand: str, ptype: str, fallback_text: str = "") -> str:
    b = BRAND_ALIASES.get(_clean_name(brand), brand.strip())
    t = TYPE_ALIASES.get(_clean_name(ptype), ptype.strip())
    parts = [p for p in [b, t] if p]
    if parts:
        return " ".join(parts)
    if fallback_text:
        return " ".join(fallback_text.strip().split()[:5])
    return "Unknown"

# ------------------------ VQA-only suggestion pipeline ------------------------
def suggest_name_vqa_only(img: Image.Image) -> dict:
    """
    Ask two concise VQA questions + one fallback, then normalize.
    """
    errors = []
    q_brand = "What is the brand name on the product label? Answer with one or two words."
    q_type  = "What type of product is this? Answer briefly, like 'Soup', 'Pasta', 'Antiperspirant'."
    q_name  = "What is the product name or flavor written on the label? Answer with a few words."

    brand, e1 = vqa_http(img, q_brand);  errors += [e1] if e1 else []
    ptype, e2 = vqa_http(img, q_type);   errors += [e2] if e2 else []
    pname, e3 = vqa_http(img, q_name);   errors += [e3] if e3 else []

    name = normalize_item(brand, ptype, pname)
    return {
        "name": name if name else "Unknown",
        "vqa_brand": brand,
        "vqa_type": ptype,
        "vqa_pname": pname,
        "errors": errors,
    }

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
    cam = st.camera_input("Use your webcam")
with c2:
    up = st.file_uploader("…or upload an image", type=["png", "jpg", "jpeg"])

img_file = cam or up
if img_file:
    img = Image.open(img_file).convert("RGB")
    st.image(img, use_container_width=True)

    if st.button("🔍 Suggest name"):
        t0 = time.time()
        result = suggest_name_vqa_only(img)
        st.success(f"🧠 Suggested: **{result['name']}** · ⏱️ {time.time()-t0:.2f}s")
        with st.expander("🔎 Debug (VQA)"):
            st.json(result)
        st.session_state["scanned_item_name"] = result["name"]

# ------------------------ Add inventory item (form unchanged) ------------------------
st.subheader("📥 Add inventory item")

item_name = st.text_input("Item name", value=st.session_state.get("scanned_item_name", ""))
quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
category = st.text_input("Category (optional)")
expiry = st.date_input("Expiry date (optional)")

if st.button("✅ Log item"):
    if not item_name.strip():
        st.warning("Enter an item name.")
    else:
        # Try 'inventory' table first; if missing, fall back to 'visit_items'
        try:
            sb.table("inventory").insert({
                "item_name": item_name.strip(),
                "quantity": int(quantity),
                "category": category.strip() or None,
                "expiry_date": str(expiry) if expiry else None,
                "added_by": st.session_state.get("volunteer", "Unknown"),
            }).execute()
            st.success("Logged to 'inventory'!")
        except Exception as e1:
            # Fallback: visit_items (id, visit_id, timestamp, volunteer, weather_type, temp_c, barcode, item_name, category, unit, qty)
            try:
                payload_vi = {
                    "item_name": item_name.strip(),
                    "qty": int(quantity),
                    "category": category.strip() or None,
                    "volunteer": st.session_state.get("volunteer_name") or st.session_state.get("volunteer") or "Unknown",
                }
                sb.table("visit_items").insert(payload_vi).execute()
                st.success("Logged to 'visit_items'!")
            except Exception as e2:
                st.error(f"Insert failed: {e1}\nFallback failed: {e2}")

# ------------------------ Live inventory (tries multiple tables) ------------------------
st.subheader("📊 Live inventory")

def _try_fetch(table: str):
    try:
        return sb.table(table).select("*").order("created_at", desc=True).execute().data
    except Exception:
        try:
            # some tables don’t have created_at
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
