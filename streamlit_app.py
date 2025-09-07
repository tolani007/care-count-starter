# --- Care Count Inventory (Universal HF Vision: VQA→OCR→Caption→Labels) ---

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
from typing import Any, Dict, List, Tuple, Optional
from PIL import Image, ImageOps, ImageEnhance
from supabase import create_client, Client

# ------------------------ Page ------------------------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("Universal HF Vision (VQA with OCR/caption/labels fallback) + Supabase")

# ------------------------ Secrets & Supabase client ------------------------
def get_secret(name: str, default: str | None = None) -> str | None:
    # Reads from env/variables first, then from st.secrets
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===================== Universal HF Vision integration (drop-in) =====================
HF_TOKEN = get_secret("HF_TOKEN")  # optional but helps avoid cold-start throttling

# Defaults for common tasks; can be overridden via Space → Settings → Variables
VQA_MODEL     = os.getenv("VQA_MODEL",     "Salesforce/blip-vqa-capfilt-large")
OCR_MODEL     = os.getenv("OCR_MODEL",     "microsoft/trocr-large-printed")
CAPTION_MODEL = os.getenv("CAPTION_MODEL", "Salesforce/blip-image-captioning-base")
LABELS_MODEL  = os.getenv("LABELS_MODEL",  "microsoft/resnet-50")

# Suggestion chain order; override with SUGGESTION_CHAIN env/variable (e.g., "vqa>ocr>labels")
SUGGESTION_CHAIN = [
    m.strip() for m in os.getenv("SUGGESTION_CHAIN", "vqa>ocr>caption>labels").split(">")
    if m.strip()
]

def _to_png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

def _hf_url(model_id: str) -> str:
    model_id = model_id.strip().strip('"').strip("'")
    return f"https://api-inference.huggingface.co/models/{model_id}"

def _headers() -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if HF_TOKEN:
        h["Authorization"] = f"Bearer {HF_TOKEN}"
    return h

def _post_json(model_id: str, payload: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    try:
        r = requests.post(_hf_url(model_id), headers=_headers(), json=payload, timeout=60)
        if r.status_code in (503, 524):
            return None, f"loading ({r.status_code})"
        if r.status_code == 404:
            return None, "not found (404)"
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:180]}"
        return r.json(), None
    except Exception as e:
        return None, f"error: {e}"

def _post_multipart(model_id: str, files: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Any], Optional[str]]:
    try:
        r = requests.post(_hf_url(model_id), headers=_headers(), files=files, data=(data or {}), timeout=60)
        if r.status_code in (503, 524):
            return None, f"loading ({r.status_code})"
        if r.status_code == 404:
            return None, "not found (404)"
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:180]}"
        return r.json(), None
    except Exception as e:
        return None, f"error: {e}"

# ----- Task wrappers -----
def call_vqa(img: Image.Image, question: str, models: List[str] | None = None) -> Tuple[str, Optional[str], List[str]]:
    """
    Visual Question Answering (e.g., BLIP-VQA).
    Returns (answer, model_used, errors[]).
    """
    models = models or [VQA_MODEL, "Salesforce/blip-vqa-base", "dandelin/vilt-b32-finetuned-vqa"]
    img_bytes = _to_png_bytes(img)
    errs: List[str] = []
    for mid in models:
        files = {"image": ("image.png", img_bytes, "image/png")}
        data = {"inputs": json.dumps({"question": question})}  # multipart with inputs JSON-string
        out, err = _post_multipart(mid, files=files, data=data)
        if err:
            errs.append(f"{mid.split('/')[-1]} {err}")
            if "loading" in err:
                time.sleep(1.0)
            continue
        ans = ""
        if isinstance(out, list) and out:
            ans = out[0].get("answer") or out[0].get("generated_text") or ""
        elif isinstance(out, dict):
            ans = out.get("answer") or out.get("generated_text") or ""
        if ans:
            return ans.strip(), mid, errs
    return "", None, errs

def call_ocr(img: Image.Image, models: List[str] | None = None) -> Tuple[str, Optional[str], List[str]]:
    """
    OCR via TrOCR (image-to-text).
    Returns (text, model_used, errors[]).
    """
    models = models or [OCR_MODEL, "microsoft/trocr-base-printed"]
    img_b64 = base64.b64encode(_to_png_bytes(img)).decode("utf-8")
    errs: List[str] = []
    for mid in models:
        out, err = _post_json(mid, {"inputs": img_b64})
        if err:
            errs.append(f"{mid.split('/')[-1]} {err}")
            if "loading" in err:
                time.sleep(1.0)
            continue
        txt = ""
        if isinstance(out, list) and out:
            txt = out[0].get("generated_text") or ""
        elif isinstance(out, dict):
            txt = out.get("generated_text") or ""
        if txt:
            return txt.strip(), mid, errs
    return "", None, errs

def call_caption(img: Image.Image, models: List[str] | None = None) -> Tuple[str, Optional[str], List[str]]:
    """
    Captioning via BLIP image-captioning.
    Returns (caption, model_used, errors[]).
    """
    models = models or [CAPTION_MODEL, "Salesforce/blip-image-captioning-large"]
    img_b64 = base64.b64encode(_to_png_bytes(img)).decode("utf-8")
    errs: List[str] = []
    for mid in models:
        out, err = _post_json(mid, {"inputs": img_b64})
        if err:
            errs.append(f"{mid.split('/')[-1]} {err}")
            if "loading" in err:
                time.sleep(1.0)
            continue
        cap = ""
        if isinstance(out, list) and out:
            cap = out[0].get("generated_text") or ""
        elif isinstance(out, dict):
            cap = out.get("generated_text") or ""
        if cap:
            return cap.strip(), mid, errs
    return "", None, errs

def call_labels(img: Image.Image, models: List[str] | None = None) -> Tuple[List[Dict[str, Any]], Optional[str], List[str]]:
    """
    Image classification (returns list of {label, score}).
    Good for general tags if everything else fails.
    """
    models = models or [LABELS_MODEL]
    img_bytes = _to_png_bytes(img)
    errs: List[str] = []
    for mid in models:
        files = {"image": ("image.png", img_bytes, "image/png")}
        out, err = _post_multipart(mid, files=files)
        if err:
            errs.append(f"{mid.split('/')[-1]} {err}")
            if "loading" in err:
                time.sleep(1.0)
            continue
        if isinstance(out, list) and out and isinstance(out[0], dict) and "label" in out[0]:
            return out, mid, errs
    return [], None, errs

# ----- Normalizers -----
BRAND_ALIASES = {
    "degree": "Degree", "dove": "Dove", "vaseline": "Vaseline",
    "campbell's": "Campbell's", "heinz": "Heinz", "kellogg's": "Kellogg's",
    "quaker": "Quaker", "pepsi": "Pepsi", "coke": "Coca-Cola",
}
TYPE_ALIASES = {
    "antiperspirant": "Antiperspirant", "deodorant": "Deodorant",
    "toothpaste": "Toothpaste", "tooth brush": "Toothbrush",
    "cereal": "Cereal", "soup": "Soup", "beans": "Beans",
    "rice": "Rice", "pasta": "Pasta", "sauce": "Sauce", "soda": "Soda",
    "lotion": "Lotion", "body lotion": "Body lotion", "hand sanitizer": "Hand sanitizer",
    "shampoo": "Shampoo", "conditioner": "Conditioner",
}

def _clean(s: str) -> str:
    return (s or "").strip().lower()

def normalize_item(brand: str, ptype: str, fallback_text: str = "") -> str:
    b = BRAND_ALIASES.get(_clean(brand), (brand or "").strip())
    t = TYPE_ALIASES.get(_clean(ptype), (ptype or "").strip())
    parts = [p for p in (b, t) if p]
    if parts:
        return " ".join(parts)
    if fallback_text:
        return " ".join(fallback_text.strip().split()[:5])
    return "Unknown"

# ----- Suggestion pipeline (configurable chain) -----
def suggest_name_universal(img: Image.Image) -> Dict[str, Any]:
    """
    Runs SUGGESTION_CHAIN in order. Returns dict with name + debug.
    Chain tokens: 'vqa', 'ocr', 'caption', 'labels'
    """
    debug: Dict[str, Any] = {"path": None, "steps": [], "errors": []}
    brand = ptype = pname = ""
    name = "Unknown"

    for step in SUGGESTION_CHAIN:
        if step == "vqa":
            q_brand = "What is the brand name on the product label? Answer with one or two words."
            q_type  = "What type of product is this? Answer briefly, like 'Soup', 'Pasta', 'Antiperspirant', 'Lotion'."
            q_name  = "What is the product name or variant on the label? Answer in a few words."
            b, m_b, e_b = call_vqa(img, q_brand); debug["errors"] += e_b; debug["steps"].append({"step":"vqa_brand","model":m_b,"answer":b})
            t, m_t, e_t = call_vqa(img, q_type ); debug["errors"] += e_t; debug["steps"].append({"step":"vqa_type","model":m_t,"answer":t})
            n, m_n, e_n = call_vqa(img, q_name ); debug["errors"] += e_n; debug["steps"].append({"step":"vqa_name","model":m_n,"answer":n})
            brand, ptype, pname = b or brand, t or ptype, n or pname
            name = normalize_item(brand, ptype, pname)
            if name != "Unknown":
                debug["path"] = "vqa"
                return {"name": name, "brand": brand, "type": ptype, "raw": pname, "debug": debug}

        elif step == "ocr":
            txt, m_o, e_o = call_ocr(img); debug["errors"] += e_o; debug["steps"].append({"step":"ocr","model":m_o,"text":txt})
            if txt:
                brand = brand or next((BRAND_ALIASES[k] for k in BRAND_ALIASES if k in _clean(txt)), "")
                ptype = ptype or next((TYPE_ALIASES[k] for k in TYPE_ALIASES if k in _clean(txt)), "")
                name = normalize_item(brand, ptype, txt)
                if name != "Unknown":
                    debug["path"] = "ocr"
                    return {"name": name, "brand": brand, "type": ptype, "raw": txt, "debug": debug}

        elif step == "caption":
            cap, m_c, e_c = call_caption(img); debug["errors"] += e_c; debug["steps"].append({"step":"caption","model":m_c,"text":cap})
            if cap:
                name = normalize_item(brand, ptype, cap)
                if name != "Unknown":
                    debug["path"] = "caption"
                    return {"name": name, "brand": brand, "type": ptype, "raw": cap, "debug": debug}

        elif step == "labels":
            labels, m_l, e_l = call_labels(img); debug["errors"] += e_l; debug["steps"].append({"step":"labels","model":m_l,"labels":labels[:5]})
            if labels:
                top = ", ".join([d.get("label","") for d in labels[:3] if d.get("label")])
                name = normalize_item(brand, ptype, top)
                if name != "Unknown":
                    debug["path"] = "labels"
                    return {"name": name, "brand": brand, "type": ptype, "raw": top, "debug": debug}

    return {"name": "Unknown", "brand": brand, "type": ptype, "raw": "", "debug": debug}
# ================== end Universal HF Vision integration ==================

# ------------------------ Image preprocessor (helps phone pics) ------------------------
def preprocess_for_label(img: Image.Image) -> Image.Image:
    """Lighten/contrast + gentle resize for mobile, improves label legibility."""
    img = img.convert("RGB")
    w, h = img.size
    scale = 768 / max(w, h) if max(w, h) > 768 else 1.0
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Brightness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    return img

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
    img_raw = Image.open(img_file).convert("RGB")
    st.image(img_raw, use_container_width=True)

    if st.button("🔍 Suggest name"):
        t0 = time.time()
        img = preprocess_for_label(img_raw)
        result = suggest_name_universal(img)
        st.success(f"🧠 Suggested: **{result['name']}** · ⏱️ {time.time()-t0:.2f}s")
        with st.expander("🔎 Debug (VQA/OCR/Caption/Labels)"):
            st.json(result.get("debug", {}))
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
        return sb.table(table).select("*").order("created_ts", desc=True).execute().data
    except Exception:
        try:
            return sb.table(table).select("*").order("created_at", desc=True).execute().data
        except Exception:
            try:
                return sb.table(table).select("*").limit(1000).execute().data
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
    st.caption("No items yet or tables not found. (Tried: inventory, visit_items, inventory_master)")
