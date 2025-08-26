# --- streamlit_app.py (Care Count Inventory via HF Inference API) ---

import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import io
import time
import re
from typing import List, Dict, Any, Tuple

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from supabase import create_client, Client
from huggingface_hub import InferenceClient

# ------------------------ Page ------------------------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("Label reading with TrOCR + BLIP-VQA (HF Inference API) • Supabase-backed")

# ------------------------ Secrets / Clients ------------------------
def get_secret(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
HF_TOKEN     = get_secret("HF_TOKEN", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Space → Settings → Secrets.")
    st.stop()

if not HF_TOKEN:
    st.error("❌ Missing HF_TOKEN. Create a **Read** token at https://huggingface.co/settings/tokens "
             "and add it in Space → Settings → Secrets → HF_TOKEN. Then restart the Space.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
hf = InferenceClient(token=HF_TOKEN)

# Remote model ids (kept small & free-tier friendly)
TROCR_MODEL = "microsoft/trocr-base-printed"          # OCR
VQA_MODEL   = "Salesforce/blip-vqa-base"              # VQA
CAP_MODEL   = "Salesforce/blip-image-captioning-base" # Caption fallback

# ------------------------ Image utilities ------------------------
def _to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

def resize_short(img: Image.Image, short=640) -> Image.Image:
    w, h = img.size
    s = min(w, h)
    if s <= short:
        return img
    scale = short / s
    return img.resize((int(w * scale), int(h * scale)))

def autoprocess(img: Image.Image) -> Image.Image:
    # Light preprocessing for better OCR on phone shots
    img = resize_short(img, 640)
    img = ImageOps.autocontrast(img)
    return img

def center_crops(img: Image.Image, n=2, frac=0.80) -> List[Image.Image]:
    """Few center crops to keep API usage low."""
    crops = []
    w, h = img.size
    for i in range(n):
        f = frac + i * 0.1
        cw, ch = int(w * f), int(h * f)
        x0 = (w - cw) // 2
        y0 = (h - ch) // 2
        crops.append(img.crop((x0, y0, x0 + cw, y0 + ch)))
    return crops

# ------------------------ Remote calls with surfaced errors ------------------------
def remote_trocr(img: Image.Image) -> Tuple[str, str | None]:
    try:
        out = hf.image_to_text(image=_to_png_bytes(img), model=TROCR_MODEL, timeout=60)
        if isinstance(out, list) and out:
            out = out[0].get("generated_text", "")
        return (out or "").strip(), None
    except Exception as e:
        return "", f"TROCR error: {e}"

def remote_vqa(img: Image.Image, question: str) -> Tuple[str, str | None]:
    try:
        out = hf.visual_question_answering(
            image=_to_png_bytes(img),
            question=question,
            model=VQA_MODEL,
            timeout=60,
        )
        if isinstance(out, list) and out:
            ans = (out[0].get("answer") or "").strip()
            return ans, None
        return (out or "").strip(), None
    except Exception as e:
        return "", f"VQA error: {e}"

def remote_caption(img: Image.Image) -> Tuple[str, str | None]:
    try:
        out = hf.image_to_text(image=_to_png_bytes(img), model=CAP_MODEL, timeout=60)
        if isinstance(out, list) and out:
            out = out[0].get("generated_text", "")
        return (out or "").strip(), None
    except Exception as e:
        return "", f"Caption error: {e}"

# ------------------------ Catalog normalizer (extend anytime) ------------------------
BRANDS: Dict[str, str] = {
    "Degree": r"\bdegree\b",
    "Dove": r"\bdove\b",
    "Heinz": r"\bheinz\b",
    "Kellogg's": r"\bkellogg'?s\b",
    "Barilla": r"\bbarilla\b",
    "Campbell": r"\bcampbell'?s?\b",
    "Unilever": r"\bunilever\b",
    # Add food-bank brands as you encounter them…
}

TYPES: Dict[str, str] = {
    "Antiperspirant Spray": r"\b(antiperspirant|dry\s*spray)\b",
    "Deodorant": r"\bdeodorant\b",
    "Cereal": r"\bcereal\b",
    "Pasta": r"\bpasta\b",
    "Soup": r"\bsoup\b",
    "Rice": r"\brice\b",
    "Beans": r"\bbeans?\b",
    "Pasta Sauce": r"\b(pasta|tomato)\s*sauce\b",
    "Toothpaste": r"\btoothpaste\b",
    # Extend freely…
}

BAD    = r"nutrition facts|ingredients?|net wt|barcode|best by|serving size|calories"
VARIANT = r"\b\d{2,3}H\b|\b(advanced|max|sport|original|unscented|lemonade|spicy|low\s*sodium)\b"

def clean(s: str) -> str:
    s = re.sub(BAD, " ", s, flags=re.I)
    s = re.sub(r"[^A-Za-z0-9&'’\- ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _match(table: Dict[str, str], text: str) -> str | None:
    for k, pat in table.items():
        if re.search(pat, text, flags=re.I):
            return k
    return None

# ------------------------ Suggestion pipeline ------------------------
def suggest_item_name(img: Image.Image, economy: bool = True) -> Dict[str, Any]:
    """
    Returns dict with:
      name, ocr_text, vqa_brand, vqa_type, caption, errors[], latency_s, calls{ocr,vqa,cap}
    """
    t0 = time.time()
    err_list: List[str] = []

    img = autoprocess(img)

    # OCR over a couple of crops
    crops = center_crops(img, n=2 if economy else 4, frac=0.8)
    ocr_texts = []
    for c in crops:
        txt, e = remote_trocr(autoprocess(c))
        if e: err_list.append(e)
        if txt: ocr_texts.append(txt)
    ocr = clean(" ".join(ocr_texts))

    # VQA
    vqa_brand, e1 = remote_vqa(img, "What brand name is printed on the product label? One or two words only.")
    if e1: err_list.append(e1)
    vqa_type, e2  = remote_vqa(img, "What kind of product is this? Use a short noun phrase (e.g., Cereal, Pasta, Soup, Antiperspirant Spray).")
    if e2: err_list.append(e2)

    # Caption fallback
    cap, e3 = remote_caption(img)
    if e3: err_list.append(e3)

    # Normalize
    fused = " ".join(filter(None, [ocr, vqa_brand, vqa_type, cap]))
    brand = _match(BRANDS, fused)
    ptype = _match(TYPES, fused)
    var_m = re.search(VARIANT, fused, flags=re.I)
    parts = [brand, ptype, var_m.group(0).upper() if var_m else None]
    name = " ".join([p for p in parts if p]).strip() or (vqa_brand or ocr or cap or "Unknown").title()

    return {
        "name": name,
        "ocr_text": ocr,
        "vqa_brand": vqa_brand,
        "vqa_type": vqa_type,
        "caption": cap,
        "errors": err_list,
        "latency_s": round(time.time() - t0, 2),
        "calls": {"ocr": len(crops), "vqa": 2, "cap": 1},
    }

# ------------------------ Volunteer auth ------------------------
st.subheader("👤 Volunteer")
with st.form("vol_form", clear_on_submit=True):
    username = st.text_input("Username")
    full_name = st.text_input("Full name")
    if st.form_submit_button("Add / Continue"):
        if not (username and full_name):
            st.error("Please fill both fields.")
        else:
            existing = sb.table("volunteers").select("full_name").execute().data or []
            names = {row["full_name"].strip().lower() for row in existing}
            if full_name.strip().lower() not in names:
                sb.table("volunteers").insert({"username": username, "full_name": full_name}).execute()
            st.session_state["volunteer"] = username
            st.success(f"Welcome, {full_name}!")

if "volunteer" not in st.session_state:
    st.info("Add yourself above to start logging.")
    st.stop()

# ------------------------ Scan / Upload & Suggest ------------------------
st.subheader("📸 Scan label to auto-fill item")
c1, c2 = st.columns(2)
with c1:
    cam = st.camera_input("Use your camera (works on phones)")
with c2:
    up = st.file_uploader("…or upload a photo", type=["png", "jpg", "jpeg"])

economy = st.toggle("Economy mode (fewer API calls)", value=True)

suggested_name = st.session_state.get("suggested_name", "")
img_file = cam or up

if img_file:
    img = Image.open(img_file).convert("RGB")
    st.image(img, caption="Captured", use_container_width=True)

    if st.button("🔎 Suggest name"):
        with st.spinner("Reading label…"):
            res = suggest_item_name(img, economy=economy)
        st.success(f"🧠 Suggested: **{res['name']}**  ·  ⏱ {res['latency_s']}s")
        with st.expander("Debug (OCR / VQA / Caption)"):
            st.json(res)
        suggested_name = res["name"]
        st.session_state["suggested_name"] = suggested_name

# ------------------------ Log item (visit_items) ------------------------
st.subheader("📥 Add inventory item (this visit)")
item_name = st.text_input("Item name", value=suggested_name or "")
quantity  = st.number_input("Quantity", min_value=1, step=1, value=1)
category  = st.text_input("Category (optional)")
unit      = st.text_input("Unit (optional, e.g., 'can', 'box', 'spray')")

if st.button("✅ Log item"):
    if item_name.strip():
        try:
            sb.table("visit_items").insert({
                "volunteer": st.session_state.get("volunteer", "unknown"),
                "barcode": None,
                "item_name": item_name.strip(),
                "category": category.strip() or None,
                "unit": unit.strip() or None,
                "qty": int(quantity),
                # "timestamp": database default (now())
            }).execute()
            st.success("Logged!")
            st.session_state.pop("suggested_name", None)
        except Exception as e:
            st.error(f"Supabase insert failed: {e}")
    else:
        st.warning("Enter an item name.")

# ------------------------ Live table (visit_items) ------------------------
st.subheader("📊 Live inventory (recent visit items)")
try:
    # Your schema shows column 'timestamp' on visit_items
    data = sb.table("visit_items").select("*").order("timestamp", desc=True).limit(200).execute().data
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "⬇️ Export CSV",
            df.to_csv(index=False).encode("utf-8"),
            "care_count_visit_items.csv",
            "text/csv",
        )
    else:
        st.caption("No items yet.")
except Exception as e:
    st.warning(f"Fetch failed: {e}")
