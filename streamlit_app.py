# --- Care Count Inventory (VQA-only; free HF Inference API; Supabase logging) ---

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
from PIL import Image
from supabase import create_client, Client

# ------------------------ Page ------------------------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("VQA-assisted inventory logging with Supabase (free Hugging Face Inference API)")

# ------------------------ Secrets & clients ------------------------
def get_secret(name: str, default: str | None = None) -> str | None:
    # Reads from env (Variables) first, then from st.secrets (Secrets)
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Inference API config (free, serverless) ----
HF_TOKEN = get_secret("HF_TOKEN", "")  # optional but recommended; a free read token is enough

# You can set VQA_MODELS Variable (CSV) in Settings → Variables.
# We automatically try each model in order until one answers.
_env_models = os.getenv("VQA_MODELS", "").strip()
VQA_MODELS = (
    [m.strip() for m in _env_models.split(",") if m.strip()]
    or [
        "Salesforce/blip-vqa-capfilt-large",  # best quality (sometimes cold)
        "Salesforce/blip-vqa-base",           # lighter fallback
        "dandelin/vilt-b32-finetuned-vqa",    # different family fallback
    ]
)

# ------------------------ Image utils ------------------------
def _to_png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

def _to_b64(img: Image.Image) -> str:
    return base64.b64encode(_to_png_bytes(img)).decode("utf-8")

# ------------------------ HTTP VQA helper ------------------------
def vqa_http(img: Image.Image, question: str) -> tuple[str, str | None, str | None]:
    """
    Try each model in VQA_MODELS. Returns (answer, error, model_used).
    Uses the generic /models/{id} Inference API with base64 image payload.
    """
    img_b64 = _to_b64(img)
    headers = {"Accept": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {"inputs": {"question": question, "image": img_b64}}

    for model_id in VQA_MODELS:
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
        except Exception as e:
            # network/timeout – keep trying next model
            last_err = f"{model_id} error: {e}"
            continue

        if r.status_code == 200:
            out = r.json()
            # API can return list[dict] or dict
            if isinstance(out, list) and out:
                ans = out[0].get("answer") or out[0].get("generated_text") or ""
            elif isinstance(out, dict):
                ans = out.get("answer") or out.get("generated_text") or ""
            else:
                ans = ""
            ans = (ans or "").strip()
            if ans:
                return ans, None, model_id
            last_err = f"{model_id} empty answer"
        elif r.status_code in (503, 504):
            # Model cold/not ready -> try next
            last_err = f"{model_id} cold/not ready ({r.status_code})"
        elif r.status_code == 404:
            last_err = f"{model_id} not found (404)"
        else:
            # Other API error; capture short body
            last_err = f"{model_id} HTTP {r.status_code}: {r.text[:160]}"

    return "", last_err, None

# ------------------------ Normalizer ------------------------
BRAND_ALIASES = {
    "degree": "Degree", "campbell's": "Campbell's", "heinz": "Heinz",
    "kellogg's": "Kellogg's", "quaker": "Quaker", "pepsi": "Pepsi", "coke": "Coca-Cola",
}

TYPE_ALIASES = {
    "antiperspirant": "Antiperspirant", "deodorant": "Deodorant",
    "toothpaste": "Toothpaste", "tooth brush": "Toothbrush",
    "cereal": "Cereal", "soup": "Soup", "beans": "Beans",
    "rice": "Rice", "pasta": "Pasta", "sauce": "Sauce", "soda": "Soda",
}

def _clean(s: str) -> str:
    return (s or "").strip().lower()

def normalize_item(brand: str, ptype: str, fallback_text: str = "") -> str:
    b = BRAND_ALIASES.get(_clean(brand), (brand or "").strip())
    t = TYPE_ALIASES.get(_clean(ptype), (ptype or "").strip())
    name = " ".join([p for p in [b, t] if p])
    if name:
        return name
    if fallback_text:
        # take a few words to avoid overly long labels
        return " ".join(fallback_text.strip().split()[:5])
    return "Unknown"

# ------------------------ VQA-only suggestion pipeline ------------------------
def suggest_name_vqa_only(img: Image.Image) -> dict:
    """
    Ask a few concise VQA questions. Combine & normalize.
    """
    errors, used_models = [], {}

    q_brand = "What is the brand printed on the product label? Answer with one or two words."
    q_type  = "What type of product is this? Answer briefly like 'Soup', 'Pasta', 'Antiperspirant'."
    q_name  = "What is the exact product name or flavor written on the label? Answer a few words."

    brand, e1, m1 = vqa_http(img, q_brand);  (errors.append(e1) if e1 else None); (used_models.setdefault("brand", m1))
    ptype, e2, m2 = vqa_http(img, q_type);   (errors.append(e2) if e2 else None); (used_models.setdefault("type", m2))
    pname, e3, m3 = vqa_http(img, q_name);   (errors.append(e3) if e3 else None); (used_models.setdefault("pname", m3))

    name = normalize_item(brand, ptype, pname)

    return {
        "name": name or "Unknown",
        "vqa_brand": brand,
        "vqa_type":  ptype,
        "vqa_pname": pname,
        "models": used_models,
        "errors": [e for e in errors if e],
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
    cam = st.camera_input("Use your phone or webcam")
with c2:
    up = st.file_uploader("…or upload an image", type=["png", "jpg", "jpeg"])

img_file = cam or up
if img_file:
    img = Image.open(img_file).convert("RGB")
    st.image(img, use_container_width=True)

    if st.button("🔍 Suggest name"):
        t0 = time.time()
        result = suggest_name_vqa_only(img)
        t1 = time.time() - t0
        st.success(f"🧠 Suggested: **{result['name']}** · ⏱️ {t1:.2f}s")
        with st.expander("🔎 Debug (VQA)"):
            st.json(result)
        st.session_state["scanned_item_name"] = result["name"]

# ------------------------ Add inventory item ------------------------
st.subheader("📥 Add inventory item")

item_name = st.text_input("Item name", value=st.session_state.get("scanned_item_name", ""))
quantity  = st.number_input("Quantity", min_value=1, step=1, value=1)
category  = st.text_input("Category (optional)")
expiry    = st.date_input("Expiry date (optional)")

if st.button("✅ Log item"):
    if not item_name.strip():
        st.warning("Enter an item name.")
    else:
        # Prefer a simple 'inventory' table if you created it; otherwise fall back to your existing 'visit_items'
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
            try:
                # visit_items schema from your screenshot: (id, visit_id, timestamp, volunteer, weather_type, temp_c, barcode, item_name, category, unit, qty)
                payload_vi = {
                    "item_name": item_name.strip(),
                    "qty": int(quantity),
                    "category": category.strip() or None,
                    "volunteer": st.session_state.get("volunteer_name") or st.session_state.get("volunteer") or "Unknown",
                }
                sb.table("visit_items").insert(payload_vi).execute()
                st.success("Logged to 'visit_items'!")
            except Exception as e2:
                st.error(f"Insert failed.\nPrimary: {e1}\nFallback: {e2}")

# ------------------------ Live inventory (tries multiple tables) ------------------------
st.subheader("📊 Live inventory")

def _try_fetch(table: str):
    try:
        return sb.table(table).select("*").order("created_ts", desc=True).execute().data
    except Exception:
        try:
            return sb.table(table).select("*").order("created_at", desc=True).execute().data
        except Exception:
            try:
                return sb.table(table).select("*").limit(500).execute().data
            except Exception:
                return None

data = _try_fetch("inventory") or _try_fetch("visit_items") or _try_fetch("inventory_master")

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
    st.caption("No rows yet or tables not found. Tried: inventory, visit_items, inventory_master.")
