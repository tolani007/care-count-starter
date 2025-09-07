# --- Care Count Inventory (VQA-only suggestion, free HF API) ---

import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue on Spaces
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import io
import time
import json
import base64
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
from supabase import create_client, Client

# ------------------------ Page ------------------------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("BLIP-VQA–assisted inventory logging with Supabase (free Hugging Face Inference API)")

# ------------------------ Secrets & clients ------------------------
def get_secret(name: str, default: str | None = None) -> str | None:
    # Reads from env/Variables first, then from st.secrets (Secrets)
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================================================
#                 UNIVERSAL HF VISION (VQA ONLY)
# ================================================================
def _clean(s: str | None) -> str:
    return (s or "").strip().strip('"').strip("'")

def _qualify_repo(repo: str | None) -> str:
    """If a model id is provided without owner, add the most likely owner."""
    rid = _clean(repo)
    if not rid:
        return rid
    if '/' in rid:
        return rid
    # guess common owners
    if rid.startswith("blip-vqa"):
        return f"Salesforce/{rid}"
    if rid.startswith("blip-image"):
        return f"Salesforce/{rid}"
    if rid.startswith("trocr"):
        return f"microsoft/{rid}"
    if rid.startswith("vit-") or rid.startswith("deit-"):
        return f"google/{rid}"
    return rid

HF_TOKEN = get_secret("HF_TOKEN")  # HF access token (read scope recommended)

# Preferred model from Variables/Secrets; else defaults.
VQA_MODELS = [
    _qualify_repo(get_secret("VQA_MODEL")) or "Salesforce/blip-vqa-capfilt-large",
    "Salesforce/blip-vqa-base",
    "dandelin/vilt-b32-finetuned-vqa",
]
# Dedup while preserving order
_seen = set()
VQA_MODELS = [m for m in VQA_MODELS if m and not (m in _seen or _seen.add(m))]

def preprocess_for_label(img: Image.Image) -> Image.Image:
    """Lighten/contrast + gentle resize for mobile, improves label legibility."""
    img = img.convert("RGB")
    w, h = img.size
    scale = 768 / max(w, h) if max(w, h) > 768 else 1.0
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Brightness(img).enhance(1.12)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    return img

def _hf_vqa_call(model_id: str, img: Image.Image, question: str) -> tuple[str, str | None]:
    """
    Call HF Inference API for image-question-answering with base64 JSON.
    Returns (answer, error).
    """
    try:
        b = io.BytesIO()
        img.save(b, format="PNG")
        img_b64 = base64.b64encode(b.getvalue()).decode("utf-8")

        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {"Accept": "application/json"}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        payload = {"inputs": {"question": question, "image": img_b64}}
        r = requests.post(url, headers=headers, json=payload, timeout=60)

        if r.status_code in (503, 524):  # model loading / gateway timeout
            return "", f"{model_id} loading ({r.status_code})"
        if r.status_code == 404:
            return "", f"{model_id} not found (404)"
        if r.status_code != 200:
            return "", f"{model_id} HTTP {r.status_code}: {r.text[:200]}"

        out = r.json()
        ans = ""
        if isinstance(out, list) and out:
            ans = out[0].get("answer") or out[0].get("generated_text") or ""
        elif isinstance(out, dict):
            ans = out.get("answer") or out.get("generated_text") or ""
        return (ans or "").strip(), None
    except Exception as e:
        return "", f"{model_id} error: {e}"

def ask_vqa(img: Image.Image, question: str) -> tuple[str, str | None, list[str]]:
    """
    Try each model id until one returns a non-empty answer.
    Returns (answer, model_used, errors[]).
    """
    errors: list[str] = []
    for mid in VQA_MODELS:
        ans, err = _hf_vqa_call(mid, img, question)
        if err:
            errors.append(err)
            if "loading" in err:
                time.sleep(1.0)
            continue
        if ans:
            return ans, mid, errors
    return "", None, errors

# ------------------------ Normalizer ------------------------
BRAND_ALIASES = {
    "degree": "Degree",
    "campbell's": "Campbell's",
    "heinz": "Heinz",
    "kellogg's": "Kellogg's",
    "quaker": "Quaker",
    "pepsi": "Pepsi",
    "coke": "Coca-Cola",
    "vaseline": "Vaseline",
    "compliments": "Compliments",
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
    "lotion": "Lotion",
    "body lotion": "Body lotion",
    "hand sanitizer": "Hand sanitizer",
    "mayonnaise": "Mayonnaise",
    "condiment": "Condiment",
}

def _clean_name(s: str) -> str:
    return (s or "").strip().lower()

def normalize_item(brand: str, ptype: str, fallback_text: str = "") -> str:
    b = BRAND_ALIASES.get(_clean_name(brand), (brand or "").strip())
    t = TYPE_ALIASES.get(_clean_name(ptype), (ptype or "").strip())
    parts = [p for p in [b, t] if p]
    if parts:
        return " ".join(parts)
    if fallback_text:
        return " ".join(fallback_text.strip().split()[:5])
    return "Unknown"

# ------------------------ VQA-only suggestion pipeline ------------------------
def suggest_name_vqa_only(img_original: Image.Image) -> dict:
    img = preprocess_for_label(img_original)

    q_brand = "What is the brand name on the product label? Answer with one or two words."
    q_type  = "What type of product is this? Answer briefly, like 'Soup', 'Pasta', 'Antiperspirant', 'Lotion', 'Mayonnaise'."
    q_name  = "What is the product name or variant on the label? Answer in a few words."

    brand, model_b, err_b = ask_vqa(img, q_brand)
    ptype, model_t, err_t  = ask_vqa(img, q_type)
    pname, model_n, err_n  = ask_vqa(img, q_name)

    name = normalize_item(brand, ptype, pname)

    return {
        "name": name if name else "Unknown",
        "vqa_brand": brand,
        "vqa_type": ptype,
        "vqa_pname": pname,
        "models": {"brand": model_b, "type": model_t, "pname": model_n},
        "errors": [*err_b, *err_t, *err_n],
    }

# ================================================================
#                          APP UI
# ================================================================

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

    # Show current vision config + quick connectivity check
    with st.expander("⚙️ Vision config / API status", expanded=False):
        st.write({"VQA_MODELS": VQA_MODELS})
        try:
            ping = requests.get("https://api-inference.huggingface.co/status", timeout=10)
            st.caption(f"HF API status: {ping.status_code}")
        except Exception as e:
            st.warning(f"Network check failed: {e}")

    if st.button("🔍 Suggest name"):
        t0 = time.time()
        result = suggest_name_vqa_only(img)
        st.success(f"🧠 Suggested: **{result['name']}** · ⏱️ {time.time()-t0:.2f}s")
        with st.expander("🔎 Debug (VQA)"):
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
        # some tables use created_ts, others created_at; try both, else limit
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
