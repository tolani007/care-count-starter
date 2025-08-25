# -------- HF Spaces env fixes --------
import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# -------- Std / libs --------
import time
from uuid import uuid4
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client, Client
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

# -------- App header --------
st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("BLIP-assisted inventory logging with Supabase")

# -------- Config / secrets --------
def get_secret(name: str, default: str | None = None) -> str | None:
    # HF Spaces: prefers env vars; Streamlit local: st.secrets
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Space → Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use your existing tables
TABLE_VOLUNTEERS = "volunteers"
TABLE_VISIT_ITEMS = "visit_items"
TABLE_MASTER = "inventory_master"  # not used yet, reserved for future enrichment

# -------- BLIP (captioning) --------
@st.cache_resource
def load_blip():
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True,       # avoids torch.load of .bin files (CVE-safe)
        low_cpu_mem_usage=True,
        torch_dtype=torch.float32,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    return processor, model, device

processor, model, device = load_blip()

def caption_image(img: Image.Image, max_new_tokens: int = 25) -> str:
    inputs = processor(images=img, return_tensors="pt").to(device)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return processor.decode(out[0], skip_special_tokens=True).strip()

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

# -------- Image capture / upload + BLIP --------
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
    with st.spinner("Generating caption…"):
        t0 = time.time()
        try:
            suggested = caption_image(img)
            st.success(f"🧠 Suggested: **{suggested}**")
            st.caption(f"⏱️ {time.time() - t0:.2f}s")
        except Exception as e:
            st.error(f"Captioning failed: {e}")

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
        st.success(f"New visit started: {st.session_state.visit_id[:8]}…")
with c4:
    st.info(f"Current visit: `{st.session_state.visit_id[:8]}…`")

# -------- Live log & totals from visit_items --------
st.subheader("📊 Recent logs & totals")
try:
    res = (
        sb.table(TABLE_VISIT_ITEMS)
        .select("*")
        .order("timestamp", desc=True)
        .limit(200)
        .execute()
    )
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
