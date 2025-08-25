import os
os.environ.setdefault("HOME", "/tmp")  # avoid '/.streamlit' permission issue
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import time
import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client, Client
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

st.set_page_config(page_title="Care Count Inventory", layout="centered")
st.title("📦 Care Count Inventory")
st.caption("BLIP-assisted inventory logging with Supabase")

def get_secret(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or st.secrets.get(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY in Space → Settings → Secrets.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def load_blip():
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True,
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

# ---- Volunteer ----
st.subheader("👤 Volunteer")
with st.form("vol_form", clear_on_submit=True):
    username = st.text_input("Username")
    full_name = st.text_input("Full name")
    if st.form_submit_button("Add / Continue"):
        if not (username and full_name):
            st.error("Please fill both fields.")
        else:
            res = sb.table("volunteers").select("full_name").execute()
            existing = [v["full_name"].lower() for v in (res.data or [])]
            if full_name.lower() not in existing:
                sb.table("volunteers").insert({"username": username, "full_name": full_name}).execute()
            st.session_state.volunteer = username
            st.success(f"Welcome, {full_name}!")

if "volunteer" not in st.session_state:
    st.info("Add yourself above to start logging.")
    st.stop()

# ---- Capture/Upload ----
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
            st.caption(f"⏱️ {time.time()-t0:.2f}s")
        except Exception as e:
            st.error(f"Captioning failed: {e}")

# ---- Log item ----
st.subheader("📥 Add inventory item")
item_name = st.text_input("Item name", value=suggested)
quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
category = st.text_input("Category (optional)")
expiry = st.date_input("Expiry date (optional)")

if st.button("✅ Log item"):
    if item_name.strip():
        sb.table("inventory").insert({
            "item_name": item_name.strip(),
            "quantity": int(quantity),
            "category": category.strip(),
            "expiry_date": str(expiry) if expiry else None,
            "added_by": st.session_state.volunteer,
        }).execute()
        st.success("Logged!")
    else:
        st.warning("Enter an item name.")

# ---- Live inventory ----
st.subheader("📊 Live inventory")
try:
    data = sb.table("inventory").select("*").order("created_at", desc=True).execute().data
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
        st.caption("No items yet.")
except Exception as e:
    st.warning(f"Fetch failed: {e}")
