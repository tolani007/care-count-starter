# -------- HF Spaces env fixes --------
import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# -------- Std / libs --------
import re
import time
from uuid import uuid4
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client, Client
import torch
from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    BlipForQuestionAnswering,
    TrOCRProcessor,
    VisionEncoderDecoderModel,
)

# -------- App header --------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("BLIP-assisted inventory logging with Supabase")

# -------- Config / secrets --------
def get_secret(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Space → Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Your existing tables
TABLE_VOLUNTEERS = "volunteers"
TABLE_VISIT_ITEMS = "visit_items"
TABLE_MASTER = "inventory_master"  # reserved for future enrichment

# -------- Models (captioning + VQA + OCR) --------
@st.cache_resource
def load_device():
    return "cuda" if torch.cuda.is_available() else "cpu"

device = load_device()

@st.cache_resource
def load_captioner():
    proc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    mdl = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float32,
    )
    mdl.to(device).eval()
    return proc, mdl

@st.cache_resource
def load_vqa():
    proc = BlipProcessor.from_pretrained("Salesforce/blip-vqa-base")
    mdl = BlipForQuestionAnswering.from_pretrained(
        "Salesforce/blip-vqa-base",
        use_safetensors=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float32,
    )
    mdl.to(device).eval()
    return proc, mdl

@st.cache_resource
def load_trocr():
    proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
    mdl = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
    mdl.to(device).eval()
    return proc, mdl

cap_processor, cap_model = load_captioner()
vqa_processor, vqa_model = load_vqa()
trocr_processor, trocr_model = load_trocr()

def blip_caption(img: Image.Image, max_new_tokens: int = 20) -> str:
    inputs = cap_processor(images=img, return_tensors="pt").to(device)
    with torch.inference_mode():
        out = cap_model.generate(**inputs, max_new_tokens=max_new_tokens)
    return cap_processor.decode(out[0], skip_special_tokens=True).strip()

def blip_vqa_name(img: Image.Image) -> str:
    q = "What is the product name on the label? Answer with brand and product only."
    inputs = vqa_processor(images=img, text=q, return_tensors="pt").to(device)
    with torch.inference_mode():
        out = vqa_model.generate(**inputs, max_new_tokens=15)
    ans = vqa_processor.decode(out[0], skip_special_tokens=True).strip()
    return ans

def trocr_text(img: Image.Image) -> str:
    pixel_values = trocr_processor(images=img, return_tensors="pt").pixel_values.to(device)
    with torch.inference_mode():
        out = trocr_model.generate(pixel_values, max_length=64)
    text = trocr_processor.batch_decode(out, skip_special_tokens=True)[0]
    return text

BAD_LABEL_WORDS = [
    r"nutrition\s+facts", r"calories?", r"serving", r"ingredients?",
    r"net\s+wt", r"fl\.?\s*oz", r"best\s+by", r"barcode", r"scan",
    r"organic\s+certified", r"gluten[-\s]*free", r"non[-\s]*gmo",
]

def clean_product_name(s: str) -> str:
    if not s:
        return ""
    s = re.sub("|".join(BAD_LABEL_WORDS), " ", s, flags=re.I)
    s = re.sub(r"[^A-Za-z0-9&'’\-\s]", " ", s)     # keep letters, digits, &, apostrophes, hyphens
    s = re.sub(r"\s+", " ", s).strip()
    # Heuristic: pick a short, title-cased phrase (2–5 words)
    words = s.split()
    if len(words) >= 2:
        words = words[:5]
    s = " ".join(words).strip()
    # normalize spaces and casing
    return s.title()

def suggest_item_name(img: Image.Image) -> str:
    # 1) OCR first
    try:
        t = trocr_text(img)
        name = clean_product_name(t)
        if len(name) >= 3:
            return name
    except Exception:
        pass

    # 2) BLIP VQA fallback
    try:
        ans = blip_vqa_name(img)
        name = clean_product_name(ans)
        if len(name) >= 3:
            return name
    except Exception:
        pass

    # 3) Caption last-resort
    try:
        cap = blip_caption(img)
        name = clean_product_name(cap)
        return name or cap
    except Exception:
        return ""

# -------- Session bootstrap --------
if "visit_id" not in st.session_state:
    st.session_state.visit_id = str(uuid4())

# -------- Volunteer onboarding --------
st.subheader("👤 Volunteer")
with st.form("vol_form", clear_on_submit=True):
    username = st.text_input("Username")
    full_name = st.text_input("Full name")
    if st.form_submit_button("Add / Continue"):
        if not (username and full_name):
            st.error("Please fill both fields.")
        else:
            res = sb.table(TABLE_VOLUNTEERS).select("full_name").execute()
            existing = [v["full_name"].lower() for v in (res.data or [])]
            if full_name.lower() not in existing:
                sb.table(TABLE_VOLUNTEERS).insert({"username": username, "full_name": full_name}).execute()
            st.session_state.volunteer = username
            st.success(f"Welcome, {full_name}!")

if "volunteer" not in st.session_state:
    st.info("Add yourself above to start logging.")
    st.stop()

# -------- Image capture / upload + product-name suggestion --------
st.subheader("📸 Scan label to auto-fill item")
c1, c2 = st.columns(2)
with c1:
    cam = st.camera_input("Use your webcam")
with c2:
    up = st.file_uploader("…or upload an image", type=["png", "jpg", "jpeg"])

suggested = ""
img_file = cam or up
if img_file:
    img = Image.open(img_file).convert("RGB")
    st.image(img, use_container_width=True)
    with st.spinner("Reading label…"):
        t0 = time.time()
        try:
            suggested = suggest_item_name(img)
            if suggested:
                st.success(f"🧠 Suggested name: **{suggested}**")
            else:
                st.warning("Couldn’t confidently read the product name. Please type it below.")
            st.caption(f"⏱️ {time.time() - t0:.2f}s")
        except Exception as e:
            st.error(f"Label read failed: {e}")

# -------- Log item to visit_items --------
st.subheader("📥 Add inventory item (this visit)")
with st.form("inventory_form"):
    barcode = st.text_input("Barcode (optional)")
    item_name = st.text_input("Item name", value=suggested)
    category = st.text_input("Category (optional)")
    unit     = st.text_input("Unit (e.g., can, box, lb)")
    qty      = st.number_input("Quantity", min_value=1, step=1, value=1)
    submit_log = st.form_submit_button("✅ Log item")

    if submit_log:
        if item_name.strip():
            payload = {
                "visit_id":  st.session_state.visit_id,
                "timestamp": datetime.utcnow().isoformat(),
                "volunteer": st.session_state.volunteer,
                "barcode":   barcode or None,
                "item_name": item_name.strip(),
                "category":  category or None,
                "unit":      unit or None,
                "qty":       int(qty),
            }
            sb.table(TABLE_VISIT_ITEMS).insert(payload).execute()
            st.success("Logged to visit_items!")
        else:
            st.warning("Enter an item name.")

c3, c4 = st.columns(2)
with c3:
    if st.button("🔄 New visit ID"):
        st.session_state.visit_id = str(uuid4())
        st.success(f"New visit: {st.session_state.visit_id[:8]}…")
with c4:
    st.info(f"Current visit: `{st.session_state.visit_id[:8]}…`")

# -------- Live log & totals from visit_items --------
st.subheader("📊 Recent logs & totals")
try:
    res = sb.table(TABLE_VISIT_ITEMS).select("*").order("timestamp", desc=True).limit(200).execute()
    data = res.data or []
    if data:
        df = pd.DataFrame(data)
        tab1, tab2 = st.tabs(["Latest logs", "Totals"])
        with tab1:
            st.dataframe(df, use_container_width=True, height=360)
            st.download_button(
                "⬇️ Export logs CSV",
                df.to_csv(index=False).encode("utf-8"),
                "care_count_visit_items.csv",
                "text/csv",
            )
        with tab2:
            totals = (
                df.groupby(["item_name", "unit"], dropna=False)["qty"]
                  .sum()
                  .reset_index()
                  .sort_values("qty", ascending=False)
            )
            st.dataframe(totals, use_container_width=True, height=360)
    else:
        st.caption("No items yet.")
except Exception as e:
    st.warning(f"Fetch failed: {e}")
