# --- Care Count (Volunteers → Visits → Items) ---
# Delightful Laurier-themed UX + enterprise data hygiene
# - OTP email login (Supabase)
# - Shift tracking & idle/8pm auto sign-out
# - Human-friendly visit_code (with DB trigger or safe fallback)
# - VLM-assisted item name
# - RPC ingest with validation/quarantine (fallback to direct insert)
# - Volunteer Impact card (today + lifetime)

from __future__ import annotations

import os, io, time, base64, re, uuid, json
from datetime import datetime, timedelta
from typing import Optional

import pytz
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
from supabase import create_client, Client

# ------------------------ App config ------------------------
os.environ.setdefault("HOME", "/tmp")
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

TZ             = os.getenv("APP_TZ", "America/Toronto")
CUTOFF_HOUR    = int(os.getenv("CUTOFF_HOUR", "20"))   # 8pm local
INACTIVITY_MIN = int(os.getenv("INACTIVITY_MIN", "30"))

def local_now() -> datetime:
    return datetime.now(pytz.timezone(TZ))

st.set_page_config(page_title="Care Count", layout="centered")
st.markdown("""
<style>
/* Laurier theme vibes */
:root { --cc-purple:#6d28d9; --cc-gold:#fde047; --cc-bg:#0b1420; --cc-panel:#0f1a2a; --cc-border:#1d2a44; }
.block-container { padding-top: 2rem; }
h1, h2, .stMarkdown h1, .stMarkdown h2 { letter-spacing:.2px }
.cc-pill { display:inline-block; padding:4px 10px; border-radius:999px; background:var(--cc-gold); color:#111827; font-weight:700; font-size:12px; }
.cc-hint { background:#10233b; border:1px solid #1f3b5b; color:#e6e8f0; padding:12px 16px; border-radius:10px; }
.cc-hero { background:#0f1a2a; border:1px solid #1f2a44; padding:16px 18px; border-radius:14px; }
.cc-btn-primary button { background:var(--cc-purple)!important; color:#fff!important; border:0!important; }
.cc-danger button { background:#7f1d1d!important; color:#fff!important; }
.status-card { display:flex; gap:16px; flex-wrap:wrap; }
.card { background:#0f1a2a; border:1px solid #1f2a44; border-radius:14px; padding:14px 16px; min-width:200px; }
.card h4 { margin:0 0 6px 0; font-size:0.95rem; color:#cbd5e1 }
.card .big { font-size:1.6rem; font-weight:700; color:#e5e7eb }
.small { color:#9aa3b2; font-size:12px }
</style>
""", unsafe_allow_html=True)

st.title("💜💛 Care Count")
st.caption("Thanks for showing up for the community today. Snap items, keep visits tidy, and help us understand the impact of your time.")

# ------------------------ Secrets & client ------------------------
def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v: return v
    try: return st.secrets.get(name, default)
    except Exception: return default

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")   # anon key (RLS should be ON)
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase creds. Add SUPABASE_URL & SUPABASE_KEY.")
    st.stop()

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# VLM provider
PROVIDER       = (get_secret("PROVIDER", "nebius") or "nebius").strip().lower()
GEMMA_MODEL    = (get_secret("GEMMA_MODEL", "google/gemma-3-27b-it") or "google/gemma-3-27b-it").strip()
NEBIUS_API_KEY = get_secret("NEBIUS_API_KEY")
NEBIUS_BASE_URL= get_secret("NEBIUS_BASE_URL", "https://api.nebius.ai/v1")
FEATH_API_KEY  = get_secret("FEATHERLESS_API_KEY")
FEATH_BASE_URL = get_secret("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")

st.caption(f"Provider: `{PROVIDER}` · Model: `{GEMMA_MODEL}` · TZ: `{TZ}`")

# ------------------------ Light events/audit (non-blocking) ------------------------
def log_event(action: str, actor: Optional[str], details: dict):
    try:
        sb.table("events").insert({"actor_email": actor, "action": action, "details": details}).execute()
    except Exception:
        pass

# ------------------------ Auth (Email OTP) ------------------------
def auth_block() -> tuple[bool, Optional[str]]:
    if "auth_email" not in st.session_state:
        st.session_state["auth_email"] = None
    if "user_email" in st.session_state:
        return True, st.session_state["user_email"]

    st.subheader("Sign in")
    with st.form("otp_request", clear_on_submit=False, border=False):
        email = st.text_input("Email", value=st.session_state.get("auth_email") or "", autocomplete="email")
        send = st.form_submit_button("Send login code")
        if send:
            if not email or "@" not in email:
                st.error("Please enter a valid email.")
            else:
                try:
                    sb.auth.sign_in_with_otp({"email": email, "shouldCreateUser": True})
                    st.session_state["auth_email"] = email
                    st.success("We emailed you a one-time code. Enter it to continue.")
                except Exception as e:
                    st.error(f"Could not send code: {e}")

    if st.session_state.get("auth_email"):
        with st.form("otp_verify", clear_on_submit=True, border=False):
            code = st.text_input("Enter 6-digit code", max_chars=6)
            ok = st.form_submit_button("Verify & start shift")
            if ok:
                try:
                    res = sb.auth.verify_otp({"email": st.session_state["auth_email"], "token": code, "type": "email"})
                    if res and res.user:
                        email = st.session_state["auth_email"]
                        # Idempotent upsert for volunteer & start shift
                        sb.table("volunteers").upsert({
                            "email": email,
                            "last_login_at": datetime.utcnow().isoformat(),
                            "shift_started_at": datetime.utcnow().isoformat(),
                            "shift_ended_at": None
                        }, on_conflict="email").execute()
                        st.session_state["user_email"] = email
                        st.session_state["shift_started"] = True
                        st.session_state["last_activity_at"] = local_now()
                        log_event("login", email, {"method":"otp"})
                        st.toast("Welcome back! Shift started. 💜", icon="✅")
                        return True, email
                except Exception as e:
                    st.error(f"Verification failed: {e}")
    return False, None

def end_shift(email: str, reason: str):
    try:
        sb.table("volunteers").update({"shift_ended_at": datetime.utcnow().isoformat()}).eq("email", email).execute()
        log_event("shift_end", email, {"reason": reason})
    except Exception:
        pass

def guard_cutoff_and_idle(email: str):
    now = local_now()
    last = st.session_state.get("last_activity_at")
    if last and (now - last).total_seconds() > INACTIVITY_MIN * 60:
        end_shift(email, "inactivity")
        st.session_state.clear()
        st.info("You were logged out due to inactivity. Thank you for volunteering today!")
        st.stop()
    st.session_state["last_activity_at"] = now

    cutoff = now.replace(hour=CUTOFF_HOUR, minute=0, second=0, microsecond=0)
    if now >= cutoff:
        end_shift(email, "cutoff_8pm")
        st.session_state.clear()
        st.info("We close the day at 8pm. Your shift has been ended. Thank you so much!")
        st.stop()

signed_in, user_email = auth_block()
if not signed_in:
    st.stop()
guard_cutoff_and_idle(user_email)

# Welcome banner (visceral, kind)
st.markdown(
    f"""<div class="cc-hero">
    <div class="small">Welcome,</div>
    <div style="font-weight:800;font-size:1.15rem"> {user_email}</div>
    <div class="small">Thank you for showing up for the community today. 💜💛</div>
    </div>""",
    unsafe_allow_html=True
)

# Sign-out button (prominent)
c_signout = st.columns([1,1,6])[1]
with c_signout:
    st.markdown('<div class="cc-btn-primary">', unsafe_allow_html=True)
    if st.button("🔒 Sign out"):
        end_shift(user_email, "manual")
        st.session_state.clear()
        st.success("Signed out. See you next time!")
        st.stop()
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------ Volunteer Impact card ------------------------
def fetch_volunteer_row(email: str) -> dict | None:
    try:
        return sb.table("volunteers").select("*").eq("email", email).single().execute().data
    except Exception:
        return None

def items_today(email: str) -> int:
    try:
        day = local_now().strftime("%Y-%m-%d")
        # try partitioned table first
        data = sb.table("visit_items_p").select("id,timestamp,volunteer") \
                .gte("timestamp", f"{day} 00:00:00").lte("timestamp", f"{day} 23:59:59") \
                .eq("volunteer", email).execute().data
        return len(data or [])
    except Exception:
        try:
            data = sb.table("visit_items").select("id,timestamp,volunteer") \
                    .gte("timestamp", f"{day} 00:00:00").lte("timestamp", f"{day} 23:59:59") \
                    .eq("volunteer", email).execute().data
            return len(data or [])
        except Exception:
            return 0

vrow = fetch_volunteer_row(user_email) or {}
shift_started_at = vrow.get("shift_started_at")
lifetime_hours = vrow.get("total_hours")  # may not exist yet; handled below
mins_active = 0
try:
    if shift_started_at:
        t0 = datetime.fromisoformat(str(shift_started_at).replace("Z","+00:00"))
        mins_active = max(0, int((datetime.utcnow() - t0).total_seconds() // 60))
except Exception:
    pass

st.markdown('<div class="status-card">', unsafe_allow_html=True)
st.markdown(f'<div class="card"><h4>Shift active</h4><div class="big">{mins_active} min</div><div class="small">since you signed in</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="card"><h4>Items you logged today</h4><div class="big">{items_today(user_email)}</div></div>', unsafe_allow_html=True)
if isinstance(lifetime_hours, (int, float)):
    st.markdown(f'<div class="card"><h4>Lifetime hours</h4><div class="big">{round(float(lifetime_hours),1)}</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ------------------------ Image helpers ------------------------
def _to_png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO(); img.save(b, format="PNG"); return b.getvalue()

def preprocess_for_label(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    scale = 1024 / max(w, h) if max(w, h) > 1024 else 1.0
    if scale < 1.0: img = img.resize((int(w * scale), int(h * scale)))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Brightness(img).enhance(1.06)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img

# ------------------------ VLM client ------------------------
SYSTEM_HINT = "You label item being held in the image for a food bank. Return ONLY the item name."

def _openai_style_chat(base_url: str, api_key: str, model_id: str, img_bytes: bytes) -> str:
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_HINT},
            {"role": "user", "content": [
                {"type": "text", "text": "What is the name of the item in the picture? Return only the item name."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]}
        ]
    }
    r = requests.post(url, json=payload, headers=headers, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()

def gemma_item_name(img_bytes: bytes) -> str:
    if PROVIDER == "nebius":
        if not NEBIUS_API_KEY: raise RuntimeError("NEBIUS_API_KEY missing")
        return _openai_style_chat(NEBIUS_BASE_URL, NEBIUS_API_KEY, GEMMA_MODEL, img_bytes)
    elif PROVIDER == "featherless":
        if not FEATH_API_KEY: raise RuntimeError("FEATHERLESS_API_KEY missing")
        return _openai_style_chat(FEATH_BASE_URL, FEATH_API_KEY, GEMMA_MODEL, img_bytes)
    else:
        raise RuntimeError(f"Unknown PROVIDER: {PROVIDER}")

# ------------------------ Normalization ------------------------
BRANDS = {
    "whiskas","tetley","kellogg's","kelloggs","campbell's","campbells","heinz",
    "nestle","kraft","general mills","cheerios","oreo","oreos","pringles","lays","doritos",
    "ice river","green bottle","great value","wheat thins","vegetable thins","raid"
}
GENERIC_TYPES = {
    "water","toothpaste","deodorant","antiperspirant","soap","shampoo","conditioner",
    "lotion","tea","coffee","cereal","pasta","rice","beans","sauce","salsa","cleaner",
    "peanut butter","jam","jelly","tuna","chicken","beef","flour","sugar","salt","oil",
    "crackers","cookies","soup","insect killer","spray"
}
def normalize_item_name(s: str) -> str:
    s = (s or "").strip()
    if not s: return ""
    low = re.sub(r"[®™]", "", s.lower())
    for b in BRANDS: low = low.replace(b, "")
    chosen = None
    for t in GENERIC_TYPES:
        if t in low: chosen = t; break
    cleaned = " ".join(low.split())
    return (chosen or cleaned.title())[:120]

def clean_text(v: Optional[str], maxlen: int = 120) -> Optional[str]:
    if not v: return None
    v = re.sub(r"\s+", " ", v).strip()
    return v[:maxlen] if v else None

# ------------------------ Visit flow ------------------------
st.subheader("🪪 Anonymous Student Visit")

active_visit = st.session_state.get("active_visit")

def fallback_visit_code() -> str:
    """Readable visit_code if DB trigger isn't present."""
    try:
        day = local_now().strftime("%Y-%m-%d")
        todays = sb.table("visits").select("id,started_at").gte("started_at", f"{day} 00:00:00") \
                 .lte("started_at", f"{day} 23:59:59").execute().data or []
        seq = len(todays) + 1
    except Exception:
        seq = int(time.time()) % 1000
    return f"V-{seq}-{local_now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="cc-btn-primary">', unsafe_allow_html=True)
    if not active_visit and st.button("Start Visit"):
        try:
            payload = {
                "visit_code": fallback_visit_code(),  # DB trigger will override if present
                "started_at": datetime.utcnow().isoformat(),
                "ended_at": None,
                "created_by": user_email
            }
            v = sb.table("visits").insert(payload).execute().data[0]
            # If trigger generated code, keep that
            if not v.get("visit_code"):
                v["visit_code"] = payload["visit_code"]
            st.session_state["active_visit"] = v
            st.success(f"Visit #{v['id']} started · code: **{v['visit_code']}**")
            log_event("visit_start", user_email, {"visit_id": v["id"], "visit_code": v["visit_code"]})
        except Exception as e:
            st.error(f"Could not start visit: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    if active_visit and st.button("End Visit (Checkout)"):
        try:
            sb.table("visits").update({"ended_at": datetime.utcnow().isoformat()}) \
              .eq("id", active_visit["id"]).execute()
            st.success("Visit checked out. Ready for the next student.")
            log_event("visit_end", user_email, {"visit_id": active_visit["id"]})
            st.session_state.pop("active_visit", None)
        except Exception as e:
            st.error(f"Could not end visit: {e}")

with c3:
    if st.session_state.get("active_visit"):
        v = st.session_state["active_visit"]
        st.caption(f"Active visit_id: {v['id']} · code: {v.get('visit_code','')}")
    else:
        st.caption("No active visit.")

# ------------------------ Identify item ------------------------
st.subheader("📸 Identify item from image")

c4, c5 = st.columns(2)
with c4: cam = st.camera_input("Use your phone or webcam")
with c5: up  = st.file_uploader("…or upload an image", type=["png","jpg","jpeg"])

img_file = cam or up
if img_file:
    img = Image.open(img_file).convert("RGB")
    st.image(img, use_container_width=True)
    if st.button("🔍 Ask model for item name"):
        t0, raw = time.time(), ""
        try:
            pre = preprocess_for_label(img); raw = gemma_item_name(_to_png_bytes(pre))
        except Exception as e:
            st.error(f"Provider error: {e}"); log_event("vlm_error", user_email, {"error": str(e)})
        norm = normalize_item_name(raw)
        if raw: st.success(f"🧠 Model: **{raw}**")
        st.info(f"✨ Normalized: **{norm or '(unknown)'}** · ⏱️ {time.time()-t0:.2f}s")
        st.session_state["scanned_item_name"] = norm or raw or ""
        st.session_state["last_activity_at"] = local_now()

# ------------------------ Log item ------------------------
st.subheader("📬 Log item to current visit")

item_name = st.text_input("Item name", value=st.session_state.get("scanned_item_name",""))
quantity  = st.number_input("Quantity", min_value=1, max_value=9999, step=1, value=1)
category  = st.text_input("Category (optional)")
unit      = st.text_input("Unit (optional, e.g., 500 mL, 1 L, 250 g)")
barcode   = st.text_input("Barcode (optional)")

def deterministic_ingest_id(v_id: int, email: str, name: str, qty: int, ts_iso: str) -> str:
    key = f"visit_items::{v_id}::{email}::{name}::{qty}::{ts_iso}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

def try_rpc_ingest(email: str, v_id: int, name: str, qty: int,
                   category: Optional[str], unit: Optional[str],
                   barcode: Optional[str], ts_iso: str, ingest_id: str) -> tuple[bool,str]:
    """
    Call the RPC safe_ingest_visit_item if it exists.
    Returns (ok, msg). If function is missing, raises to trigger fallback.
    """
    try:
        res = sb.rpc("safe_ingest_visit_item", {
            "p_email": email,
            "p_visit_id": v_id,
            "p_item_name": name,
            "p_qty": qty,
            "p_category": category,
            "p_unit": unit,
            "p_barcode": barcode,
            "p_ts": ts_iso,
            "p_ingest_id": ingest_id
        }).execute()
        # RPC returns a setof (ok boolean, msg text) — normalize
        rows = res.data if isinstance(res.data, list) else []
        if rows:
            r0 = rows[0]
            ok = bool(r0.get("ok", False))
            msg = str(r0.get("msg", ""))
            return ok, msg or ("ok" if ok else "failed")
        # Some PostgREST setups return {} — treat as ok
        return True, "ok"
    except Exception as e:
        # If function missing (42883) or not exposed, re-raise to use fallback
        raise e

def fallback_direct_insert(email: str, v_id: int, name: str, qty: int,
                           category: Optional[str], unit: Optional[str],
                           barcode: Optional[str], ts_iso: str, ingest_id: str) -> None:
    """Write into visit_items_p if present, else visit_items (keeps app working)."""
    payload = {
        "visit_id": v_id,
        "timestamp": ts_iso,
        "volunteer": email,
        "item_name": name,
        "category": category,
        "unit": unit,
        "qty": qty,
        "barcode": barcode,
        "weather_type": None,
        "temp_c": None,
        "ingest_id": ingest_id
    }
    try:
        sb.table("visit_items_p").insert(payload).execute()
    except Exception:
        # legacy table fallback
        payload.pop("ingest_id", None)
        sb.table("visit_items").insert(payload).execute()

st.markdown('<div class="cc-btn-primary">', unsafe_allow_html=True)
save_disabled = not st.session_state.get("active_visit")
if st.button("✅ Save Item to Visit", disabled=save_disabled):
    v = st.session_state.get("active_visit")
    if not v:
        st.warning("Start a visit first, then save items.")
    else:
        name_clean = clean_text(item_name, 120)
        if not name_clean:
            st.warning("Item name is required.")
        else:
            ts_iso = datetime.utcnow().isoformat()
            ingest_id = deterministic_ingest_id(int(v["id"]), user_email, name_clean, int(quantity), ts_iso)
            try:
                ok, msg = try_rpc_ingest(
                    email=user_email, v_id=int(v["id"]), name=name_clean, qty=int(quantity),
                    category=clean_text(category, 80), unit=clean_text(unit, 40),
                    barcode=clean_text(barcode, 64), ts_iso=ts_iso, ingest_id=ingest_id
                )
                if ok:
                    st.success("Item logged ✅")
                else:
                    st.warning(f"Ingest said: {msg}. (Will try direct insert.)")
                    fallback_direct_insert(user_email, int(v["id"]), name_clean, int(quantity),
                                           clean_text(category,80), clean_text(unit,40),
                                           clean_text(barcode,64), ts_iso, ingest_id)
                    st.success("Item logged ✅ (fallback)")
            except Exception as e:
                # RPC missing or failed → direct insert
                try:
                    fallback_direct_insert(user_email, int(v["id"]), name_clean, int(quantity),
                                           clean_text(category,80), clean_text(unit,40),
                                           clean_text(barcode,64), ts_iso, ingest_id)
                    st.success("Item logged ✅ (fallback)")
                except Exception as e2:
                    st.error(f"Ingest failed: {e2}")
            st.session_state["last_activity_at"] = local_now()
            st.session_state["scanned_item_name"] = name_clean
st.markdown('</div>', unsafe_allow_html=True)

# ------------------------ Visit items view + delete ------------------------
def load_items_for_visit(visit_id: int) -> list[dict]:
    # Prefer partitioned table
    try:
        return sb.table("visit_items_p").select("*").eq("visit_id", visit_id) \
            .order("timestamp", desc=True).limit(500).execute().data or []
    except Exception:
        try:
            return sb.table("visit_items").select("*").eq("visit_id", visit_id) \
                .order("timestamp", desc=True).limit(500).execute().data or []
        except Exception:
            return []

def delete_item(table: str, item_id: int):
    try:
        sb.table(table).delete().eq("id", item_id).execute()
    except Exception as e:
        raise e

if st.session_state.get("active_visit"):
    st.subheader("🧾 Items in this visit")
    rows = load_items_for_visit(int(st.session_state["active_visit"]["id"]))
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        with st.expander("🗑️ Delete an item (if mis-logged)"):
            ids = [r["id"] for r in rows if "id" in r]
            choice = st.selectbox("Choose item id", ids) if ids else None
            st.markdown('<div class="cc-danger">', unsafe_allow_html=True)
            if st.button("Delete selected", disabled=not bool(ids)):
                if choice is None:
                    st.warning("Pick an id.")
                else:
                    # try both tables safely
                    try:
                        delete_item("visit_items_p", int(choice))
                    except Exception:
                        delete_item("visit_items", int(choice))
                    st.success("Deleted.")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.caption("No items logged for this visit yet.")

# ------------------------ Analytics (light) ------------------------
st.subheader("📈 Today")
try:
    daily = sb.table("v_daily_activity").select("*").execute().data
    today_str = local_now().strftime("%Y-%m-%d")
    today = next((r for r in daily if str(r.get("day",""))[:10]==today_str), None)
    visits = int(today["visits"]) if today and "visits" in today else 0
    items  = int(today["items"]) if today and "items" in today else 0
    st.markdown(f"**Visits:** {visits} · **Items:** {items}")
except Exception:
    st.caption("Analytics view unavailable yet.")

# ------------------------ Gentle reminder ------------------------
st.markdown(
    """<div class="cc-hint">
    💡 When you’re done, please <b>End Visit</b> and <b>Sign out</b>.<br>
    We’ll auto-sign you out after inactivity or at 8pm local time. 💜
    </div>""",
    unsafe_allow_html=True
)
