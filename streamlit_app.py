# --- Care Count (Volunteers → Visits → Items) ---
# Modern UI/UX with industry-standard design patterns
# Enhanced version with improved user experience

from __future__ import annotations

import os, io, time, base64, re, uuid, json
from datetime import datetime, timedelta
from typing import Optional
import logging

import pytz
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
from supabase import create_client, Client

# Import our modern UI components
from ui_improvements import ModernUIComponents, apply_modern_ui, create_modern_layout

# ------------------------ Enhanced Logging ------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('care_count.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------ App config ------------------------
os.environ.setdefault("HOME", "/tmp")
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

TZ             = os.getenv("APP_TZ", "America/Toronto")
CUTOFF_HOUR    = int(os.getenv("CUTOFF_HOUR", "-1"))   # -1 disables daily cutoff
INACTIVITY_MIN = int(os.getenv("INACTIVITY_MIN", "30"))

def local_now() -> datetime:
    return datetime.now(pytz.timezone(TZ))

# Enhanced page config with modern settings
st.set_page_config(
    page_title="Care Count - Volunteer Management",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/care-count',
        'Report a bug': "https://github.com/your-repo/care-count/issues",
        'About': "# Care Count\nVolunteer management system for community impact tracking"
    }
)

# Apply modern UI styling
apply_modern_ui()

# ------------------------ Enhanced Secrets Management ------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    _SECRETS = getattr(st, "secrets", {})
except Exception:
    _SECRETS = {}

def _is_useful(val: Optional[str]) -> bool:
    return val is not None and str(val).strip() != ""

def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Enhanced secret management with logging"""
    v = os.getenv(name)
    if _is_useful(v):
        logger.info(f"Secret {name} loaded from environment")
        return v

    try:
        if hasattr(_SECRETS, "get"):
            v = _SECRETS.get(name, default)
            if _is_useful(v):
                logger.info(f"Secret {name} loaded from Streamlit secrets")
                return v
    except Exception as e:
        logger.warning(f"Failed to load secret {name} from Streamlit secrets: {e}")

    return default

def require_secret(name: str) -> str:
    """Enhanced secret requirement with better error handling"""
    v = get_secret(name, None)
    if not _is_useful(v):
        st.error(
            f"🔐 **Configuration Error**\n\n"
            f"Missing required configuration: `{name}`\n\n"
            f"Please ensure this is set in your environment variables or `.streamlit/secrets.toml` file.\n\n"
            f"For help, check the [documentation](https://github.com/your-repo/care-count#configuration)."
        )
        st.stop()
    return str(v)

# Required Supabase credentials
SUPABASE_URL = require_secret("SUPABASE_URL")
SUPABASE_KEY = require_secret("SUPABASE_KEY")

# Initialize Supabase client with error handling
try:
    sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    logger.error(f"Supabase connection failed: {e}")
    st.stop()

# Optional provider/config
PROVIDER         = (get_secret("PROVIDER", "nebius") or "nebius").strip().lower()
GEMMA_MODEL      = (get_secret("GEMMA_MODEL", "google/gemma-3-27b-it") or "google/gemma-3-27b-it").strip()
NEBIUS_API_KEY   = get_secret("NEBIUS_API_KEY")
NEBIUS_BASE_URL  = get_secret("NEBIUS_BASE_URL", "https://api.nebius.ai/v1")
FEATH_API_KEY    = get_secret("FEATHERLESS_API_KEY")
FEATH_BASE_URL   = get_secret("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")

# ------------------------ Enhanced Event Logging ------------------------
def log_event(action: str, actor: Optional[str], details: dict, level: str = "info"):
    """Enhanced event logging with multiple levels"""
    log_data = {
        "happened_at": datetime.utcnow().isoformat(),
        "action": action,
        "actor_email": actor,
        "details": json.dumps(details) if isinstance(details, dict) else str(details)
    }
    
    # Log to file
    if level == "error":
        logger.error(f"Event: {action} by {actor} - {details}")
    elif level == "warning":
        logger.warning(f"Event: {action} by {actor} - {details}")
    else:
        logger.info(f"Event: {action} by {actor} - {details}")
    
    # Log to database (without level field to avoid schema issues)
    try:
        sb.table("events").insert(log_data).execute()
    except Exception as e:
        logger.warning(f"Failed to log event to database (continuing): {e}")

# ------------------------ Modern Authentication UI ------------------------
def auth_block() -> tuple[bool, Optional[str]]:
    """Enhanced authentication with modern UI"""
    if "auth_email" not in st.session_state:
        st.session_state["auth_email"] = None
    if "user_email" in st.session_state:
        return True, st.session_state["user_email"]

    # Modern hero section for login
    st.markdown(ModernUIComponents.create_hero_section(
        "Care Count",
        "Snap items, track visits, and make an impact."
    ), unsafe_allow_html=True)

    # Modern login form
    with st.container():
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.subheader("🔐 Sign In")
        st.markdown("Enter your email to receive a secure login code.")
        
        with st.form("otp_request", clear_on_submit=False):
            email = st.text_input(
                "Email Address", 
                value=st.session_state.get("auth_email") or "", 
                placeholder="your.email@example.com",
                help="We'll send you a secure 6-digit code"
            )
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                send = st.form_submit_button("📧 Send Login Code", use_container_width=True)
            
            if send:
                if not email or "@" not in email:
                    st.error("Please enter a valid email address.")
                else:
                    try:
                        with st.spinner("Sending login code..."):
                            sb.auth.sign_in_with_otp({"email": email, "shouldCreateUser": True})
                            st.session_state["auth_email"] = email
                            st.success("✅ Login code sent! Check your email.")
                            log_event("otp_requested", email, {"method": "email"})
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Too Many Requests" in error_msg:
                            st.warning("⏳ Please wait a moment before requesting another code. For security, there's a brief delay between requests.")
                        elif "Invalid email" in error_msg:
                            st.error("❌ Please enter a valid email address.")
                        else:
                            st.error(f"❌ Could not send code: {error_msg}")
                        log_event("otp_failed", email, {"error": error_msg}, "error")

        st.markdown('</div>', unsafe_allow_html=True)

    # OTP verification form
    if st.session_state.get("auth_email"):
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.subheader("🔢 Verify Code")
            st.markdown(f"Enter the 6-digit code sent to **{st.session_state['auth_email']}**")
            
            with st.form("otp_verify", clear_on_submit=True):
                code = st.text_input(
                    "Verification Code", 
                    max_chars=6,
                    placeholder="123456",
                    help="Enter the 6-digit code from your email"
                )
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    ok = st.form_submit_button("✅ Verify & Start Shift", use_container_width=True)
                
                if ok:
                    if len(code) != 6 or not code.isdigit():
                        st.error("Please enter a valid 6-digit code.")
                    else:
                        try:
                            with st.spinner("Verifying code..."):
                                res = sb.auth.verify_otp({"email": st.session_state["auth_email"], "token": code, "type": "email"})
                                if res and res.user:
                                    # Ensure subsequent PostgREST requests carry the user's JWT for RLS
                                    try:
                                        token = getattr(getattr(res, "session", None), "access_token", None)
                                        if token:
                                            sb.postgrest.auth(token)
                                    except Exception:
                                        pass
                                    email = st.session_state["auth_email"]
                                    
                                    # Enhanced volunteer upsert
                                    volunteer_data = {
                                        "email": email,
                                        "last_login_at": datetime.utcnow().isoformat(),
                                        "shift_started_at": datetime.utcnow().isoformat(),
                                        "shift_ended_at": None
                                    }
                                    
                                    sb.table("volunteers").upsert(volunteer_data, on_conflict="email").execute()
                                    
                                    st.session_state["user_email"] = email
                                    st.session_state["shift_started"] = True
                                    st.session_state["last_activity_at"] = local_now()
                                    
                                    log_event("login_success", email, {"method": "otp"})
                                    st.success("🎉 Welcome back! Your shift has started.")
                                    st.balloons()
                                    return True, email
                        except Exception as e:
                            error_msg = str(e)
                            if "expired" in error_msg.lower() or "invalid" in error_msg.lower():
                                st.error("❌ This code has expired or is invalid. Please request a new code.")
                                # Clear the auth_email to allow new code request
                                if "auth_email" in st.session_state:
                                    del st.session_state["auth_email"]
                                st.rerun()
                            else:
                                st.error(f"❌ Verification failed: {error_msg}")
                            log_event("otp_verification_failed", st.session_state["auth_email"], {"error": error_msg}, "error")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    return False, None

def end_shift(email: str, reason: str):
    """Enhanced shift ending with better logging"""
    try:
        end_time = datetime.utcnow().isoformat()
        sb.table("volunteers").update({"shift_ended_at": end_time}).eq("email", email).execute()
        log_event("shift_end", email, {"reason": reason, "end_time": end_time})
    except Exception as e:
        logger.error(f"Failed to end shift for {email}: {e}")

def guard_cutoff_and_idle(email: str):
    """Enhanced session management with better UX"""
    now = local_now()
    # Enforce daily cutoff only when configured
    if CUTOFF_HOUR >= 0:
        cutoff = now.replace(hour=CUTOFF_HOUR, minute=0, second=0, microsecond=0)
        if now >= cutoff:
            end_shift(email, "cutoff_8pm")
    # Inactivity guard remains unchanged
    last = st.session_state.get("last_activity_at")
    
    if last and (now - last).total_seconds() > INACTIVITY_MIN * 60:
        end_shift(email, "inactivity")
        st.session_state.clear()
        st.warning("⏰ You were logged out due to inactivity. Thank you for volunteering today!")
        st.stop()
    
    st.session_state["last_activity_at"] = now

# ------------------------ Main App Flow ------------------------
def main():
    """Main application flow with modern UI"""
    
    # Authentication
    signed_in, user_email = auth_block()
    if not signed_in:
        st.stop()
    
    guard_cutoff_and_idle(user_email)

    # Modern welcome section
    st.markdown(ModernUIComponents.create_hero_section(
        "Care Count Dashboard",
        "Manage visits, track items, and make a difference in your community.",
        user_email
    ), unsafe_allow_html=True)

    # Enhanced status cards
    vrow = fetch_volunteer_row(user_email) or {}
    shift_started_at = vrow.get("shift_started_at")
    lifetime_hours = vrow.get("total_hours", 0)
    
    mins_active = 0
    try:
        if shift_started_at:
            t0 = datetime.fromisoformat(str(shift_started_at).replace("Z","+00:00"))
            mins_active = max(0, int((datetime.utcnow() - t0).total_seconds() // 60))
    except Exception:
        pass

    status_data = {
        "shift_active": f"{mins_active} min",
        "items_today": items_today(user_email),
        "lifetime_hours": f"{round(float(lifetime_hours), 1)} hrs" if isinstance(lifetime_hours, (int, float)) else "0.0 hrs"
    }
    
    st.markdown(ModernUIComponents.create_status_cards(status_data), unsafe_allow_html=True)

    # Modern sign-out button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔒 Sign Out", use_container_width=True, type="secondary"):
            end_shift(user_email, "manual")
            st.session_state.clear()
            st.success("✅ Signed out successfully. See you next time!")
            st.rerun()

    # Enhanced visit management section
    st.markdown(ModernUIComponents.create_modern_form_section(
        "🪪 Visit Management",
        "Start and manage student visits with unique tracking codes"
    ), unsafe_allow_html=True)
    
    active_visit = st.session_state.get("active_visit")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if not active_visit and st.button("🚀 Start New Visit", use_container_width=True, type="primary"):
            try:
                with st.spinner("Creating visit..."):
                    payload = {
                        "visit_code": fallback_visit_code(),
                        "started_at": datetime.utcnow().isoformat(),
                        "ended_at": None,
                        "created_by": user_email
                    }
                    v = sb.table("visits").insert(payload).execute().data[0]
                    if not v.get("visit_code"):
                        v["visit_code"] = payload["visit_code"]
                    st.session_state["active_visit"] = v
                    st.success(f"✅ Visit #{v['id']} started")
                    st.info(f"**Visit Code:** `{v['visit_code']}`")
                    log_event("visit_start", user_email, {"visit_id": v["id"], "visit_code": v["visit_code"]})
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Could not start visit: {e}")
                log_event("visit_start_failed", user_email, {"error": str(e)}, "error")

    with col2:
        if active_visit and st.button("🏁 End Visit", use_container_width=True, type="secondary"):
            try:
                with st.spinner("Ending visit..."):
                    sb.table("visits").update({"ended_at": datetime.utcnow().isoformat()}) \
                      .eq("id", active_visit["id"]).execute()
                    st.success("✅ Visit completed successfully")
                    log_event("visit_end", user_email, {"visit_id": active_visit["id"]})
                    st.session_state.pop("active_visit", None)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Could not end visit: {e}")
                log_event("visit_end_failed", user_email, {"error": str(e)}, "error")

    with col3:
        if st.session_state.get("active_visit"):
            v = st.session_state["active_visit"]
            st.info(f"**Active Visit:** #{v['id']}\n**Code:** {v.get('visit_code','')}")
        else:
            st.info("No active visit")

    st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced item identification section
    st.markdown(ModernUIComponents.create_modern_form_section(
        "📸 Item Identification",
        "Use AI-powered image recognition to identify items quickly and accurately"
    ), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📷 Camera Capture")
        cam = st.camera_input("Take a photo of the item", help="Position the item clearly in the frame")
    
    with col2:
        st.subheader("📁 File Upload")
        up = st.file_uploader(
            "Upload an image", 
            type=["png","jpg","jpeg"],
            help="Supported formats: PNG, JPG, JPEG"
        )

    img_file = cam or up
    if img_file:
        try:
            img = Image.open(img_file).convert("RGB")
            st.image(img, use_container_width=True, caption="Captured Image")
            
            if st.button("🔍 Identify Item with AI", use_container_width=True, type="primary"):
                with st.spinner("Analyzing image with AI..."):
                    t0 = time.time()
                    try:
                        pre = preprocess_for_label(img)
                        raw = gemma_item_name(_to_png_bytes(pre))
                        processing_time = time.time() - t0
                        
                        norm = normalize_item_name(raw)
                        
                        if raw:
                            st.success(f"🤖 **AI Detection:** {raw}")
                        st.info(f"✨ **Normalized:** {norm or '(unknown)'} · ⏱️ {processing_time:.2f}s")
                        
                        st.session_state["scanned_item_name"] = norm or raw or ""
                        st.session_state["last_activity_at"] = local_now()
                        
                        log_event("item_identified", user_email, {
                            "raw_name": raw,
                            "normalized_name": norm,
                            "processing_time": processing_time
                        })
                        
                    except Exception as e:
                        st.error(f"❌ AI identification failed: {e}")
                        log_event("ai_identification_failed", user_email, {"error": str(e)}, "error")
        except Exception as e:
            st.error(f"❌ Failed to process image: {e}")
            log_event("image_processing_failed", user_email, {"error": str(e)}, "error")

    st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced item logging section
    st.markdown(ModernUIComponents.create_modern_form_section(
        "📬 Item Logging",
        "Log items to the current visit with detailed information"
    ), unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        item_name = st.text_input(
            "Item Name", 
            value=st.session_state.get("scanned_item_name",""),
            placeholder="Enter item name or use AI detection above",
            help="Required field - item name for tracking"
        )
    
    with col2:
        quantity = st.number_input(
            "Quantity", 
            min_value=1, 
            max_value=9999, 
            step=1, 
            value=1,
            help="Number of items"
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        category = st.text_input(
            "Category (optional)", 
            placeholder="e.g., Food, Hygiene, Clothing",
            help="Item category for better organization"
        )
    
    with col4:
        unit = st.text_input(
            "Unit (optional)", 
            placeholder="e.g., 500 mL, 1 L, 250 g",
            help="Unit of measurement"
        )
    
    barcode = st.text_input(
        "Barcode (optional)", 
        placeholder="Scan or enter barcode",
        help="Product barcode for inventory tracking"
    )

    save_disabled = not st.session_state.get("active_visit")
    if st.button("✅ Save Item to Visit", disabled=save_disabled, use_container_width=True, type="primary"):
        v = st.session_state.get("active_visit")
        if not v:
            st.warning("⚠️ Please start a visit first before logging items.")
        else:
            name_clean = clean_text(item_name, 120)
            if not name_clean:
                st.warning("⚠️ Item name is required.")
            else:
                with st.spinner("Saving item..."):
                    ts_iso = datetime.utcnow().isoformat()
                    ingest_id = deterministic_ingest_id(int(v["id"]), user_email, name_clean, int(quantity), ts_iso)
                    
                    try:
                        ok, msg = try_rpc_ingest(
                            email=user_email, v_id=int(v["id"]), name=name_clean, qty=int(quantity),
                            category=clean_text(category, 80), unit=clean_text(unit, 40),
                            barcode=clean_text(barcode, 64), ts_iso=ts_iso, ingest_id=ingest_id
                        )
                        
                        if ok:
                            st.success("✅ Item logged successfully!")
                            log_event("item_logged", user_email, {
                                "visit_id": v["id"],
                                "item_name": name_clean,
                                "quantity": quantity
                            })
                        else:
                            st.warning(f"⚠️ {msg}. Trying fallback method...")
                            fallback_direct_insert(user_email, int(v["id"]), name_clean, int(quantity),
                                                   clean_text(category,80), clean_text(unit,40),
                                                   clean_text(barcode,64), ts_iso, ingest_id)
                            st.success("✅ Item logged successfully (fallback method)!")
                            log_event("item_logged_fallback", user_email, {
                                "visit_id": v["id"],
                                "item_name": name_clean,
                                "quantity": quantity
                            })
                    except Exception as e:
                        try:
                            fallback_direct_insert(user_email, int(v["id"]), name_clean, int(quantity),
                                                   clean_text(category,80), clean_text(unit,40),
                                                   clean_text(barcode,64), ts_iso, ingest_id)
                            st.success("✅ Item logged successfully (fallback method)!")
                            log_event("item_logged_fallback", user_email, {
                                "visit_id": v["id"],
                                "item_name": name_clean,
                                "quantity": quantity
                            })
                        except Exception as e2:
                            st.error(f"❌ Failed to log item: {e2}")
                            log_event("item_log_failed", user_email, {"error": str(e2)}, "error")
                    
                    st.session_state["last_activity_at"] = local_now()
                    st.session_state["scanned_item_name"] = name_clean
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced visit items view
    if st.session_state.get("active_visit"):
        st.markdown(ModernUIComponents.create_modern_form_section(
            "🧾 Current Visit Items",
            "Review and manage items in the current visit"
        ), unsafe_allow_html=True)
        
        rows = load_items_for_visit(int(st.session_state["active_visit"]["id"]))
        if rows:
            df = pd.DataFrame(rows)
            
            # Enhanced dataframe display
            st.dataframe(
                df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Time", format="MM/DD/YY HH:mm"),
                    "item_name": st.column_config.TextColumn("Item Name", width="medium"),
                    "qty": st.column_config.NumberColumn("Quantity", width="small"),
                    "category": st.column_config.TextColumn("Category", width="small"),
                    "unit": st.column_config.TextColumn("Unit", width="small")
                }
            )
            
            # Enhanced delete functionality
            with st.expander("🗑️ Delete Item (if mis-logged)"):
                if rows:
                    item_options = {f"{r['item_name']} (Qty: {r['qty']})": r["id"] for r in rows if "id" in r}
                    selected_item = st.selectbox("Select item to delete", list(item_options.keys()))
                    
                    if st.button("🗑️ Delete Selected Item", type="secondary"):
                        item_id = item_options[selected_item]
                        try:
                            # Try both tables safely
                            try:
                                delete_item("visit_items_p", int(item_id))
                            except Exception:
                                delete_item("visit_items", int(item_id))
                            
                            st.success("✅ Item deleted successfully")
                            log_event("item_deleted", user_email, {"item_id": item_id})
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to delete item: {e}")
                            log_event("item_delete_failed", user_email, {"error": str(e)}, "error")
                else:
                    st.info("No items to delete")
        else:
            st.info("📝 No items logged for this visit yet.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced analytics section
    st.markdown(ModernUIComponents.create_modern_form_section(
        "📈 Today's Analytics",
        "Real-time insights into today's volunteer activity"
    ), unsafe_allow_html=True)
    
    try:
        daily = sb.table("v_daily_activity").select("*").execute().data
        today_str = local_now().strftime("%Y-%m-%d")
        today = next((r for r in daily if str(r.get("day",""))[:10]==today_str), None)
        
        if today:
            visits = int(today.get("visits", 0))
            items = int(today.get("items", 0))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Visits Today", visits, delta=None)
            with col2:
                st.metric("Total Items Processed", items, delta=None)
            
            # Progress indicator
            if visits > 0:
                st.markdown(ModernUIComponents.create_progress_indicator(
                    items, visits * 10, "Items per Visit Target"
                ), unsafe_allow_html=True)
        else:
            st.info("📊 Analytics data will appear here as activity increases.")
            
    except Exception as e:
        st.info("📊 Analytics view will be available once the database view is set up.")
        logger.warning(f"Analytics view not available: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced footer with helpful information
    st.markdown("""
    <div class="modern-card" style="margin-top: var(--space-8); text-align: center;">
        <h4>💡 Quick Tips</h4>
        <p style="color: var(--gray-400); margin: 0;">
            When you're done, please <strong>End Visit</strong> and <strong>Sign out</strong>.<br>
            We'll auto-sign you out after inactivity or at 8pm local time. 💜
        </p>
    </div>
    """, unsafe_allow_html=True)

# ------------------------ Helper Functions (Enhanced) ------------------------
def fetch_volunteer_row(email: str) -> dict | None:
    """Enhanced volunteer data fetching with error handling"""
    try:
        return sb.table("volunteers").select("*").eq("email", email).single().execute().data
    except Exception as e:
        logger.warning(f"Failed to fetch volunteer data for {email}: {e}")
        return None

def items_today(email: str) -> int:
    """Enhanced item counting with better error handling"""
    try:
        day = local_now().strftime("%Y-%m-%d")
        # Try partitioned table first
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
        except Exception as e:
            logger.warning(f"Failed to count items for {email}: {e}")
            return 0

def fallback_visit_code() -> str:
    """Enhanced visit code generation with better uniqueness"""
    try:
        day = local_now().strftime("%Y-%m-%d")
        todays = sb.table("visits").select("id,started_at").gte("started_at", f"{day} 00:00:00") \
                 .lte("started_at", f"{day} 23:59:59").execute().data or []
        seq = len(todays) + 1
    except Exception:
        seq = int(time.time()) % 1000
    return f"V-{seq}-{local_now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"

def _to_png_bytes(img: Image.Image) -> bytes:
    """Convert image to PNG bytes"""
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

def preprocess_for_label(img: Image.Image) -> Image.Image:
    """Enhanced image preprocessing for better AI recognition"""
    img = img.convert("RGB")
    w, h = img.size
    scale = 1024 / max(w, h) if max(w, h) > 1024 else 1.0
    if scale < 1.0: 
        img = img.resize((int(w * scale), int(h * scale)))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Brightness(img).enhance(1.06)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img

def gemma_item_name(img_bytes: bytes) -> str:
    """Enhanced AI item identification with better error handling and fallback"""
    try:
        primary_err = None
        if PROVIDER == "nebius":
            try:
                if not NEBIUS_API_KEY:
                    raise RuntimeError("NEBIUS_API_KEY missing")
                return _openai_style_chat(NEBIUS_BASE_URL, NEBIUS_API_KEY, GEMMA_MODEL, img_bytes)
            except Exception as e:
                primary_err = e
        if PROVIDER == "featherless":
            try:
                if not FEATH_API_KEY:
                    raise RuntimeError("FEATHERLESS_API_KEY missing")
                return _openai_style_chat(FEATH_BASE_URL, FEATH_API_KEY, GEMMA_MODEL, img_bytes)
            except Exception as e:
                primary_err = e
        # Fallback chain if primary failed or unknown provider
        if FEATH_API_KEY:
            return _openai_style_chat(FEATH_BASE_URL, FEATH_API_KEY, GEMMA_MODEL, img_bytes)
        raise primary_err or RuntimeError(f"Unknown PROVIDER: {PROVIDER}")
    except Exception as e:
        logger.error(f"AI identification failed: {e}")
        raise

def _openai_style_chat(base_url: str, api_key: str, model_id: str, img_bytes: bytes) -> str:
    """Enhanced API communication with better error handling"""
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You label item being held in the image for a food bank. Return ONLY the item name."},
            {"role": "user", "content": [
                {"type": "text", "text": "What is the name of the item in the picture? Return only the item name."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]}
        ]
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=90)
        if r.status_code != 200:
            raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
    except requests.exceptions.Timeout:
        raise RuntimeError("AI service timeout - please try again")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"AI service error: {e}")

def normalize_item_name(s: str) -> str:
    """Enhanced item name normalization"""
    s = (s or "").strip()
    if not s: 
        return ""
    
    # Enhanced brand and type recognition
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
    
    low = re.sub(r"[®™]", "", s.lower())
    for b in BRANDS: 
        low = low.replace(b, "")
    
    chosen = None
    for t in GENERIC_TYPES:
        if t in low: 
            chosen = t
            break
    
    cleaned = " ".join(low.split())
    return (chosen or cleaned.title())[:120]

def clean_text(v: Optional[str], maxlen: int = 120) -> Optional[str]:
    """Enhanced text cleaning"""
    if not v: 
        return None
    v = re.sub(r"\s+", " ", v).strip()
    return v[:maxlen] if v else None

def deterministic_ingest_id(v_id: int, email: str, name: str, qty: int, ts_iso: str) -> str:
    """Enhanced ID generation for data integrity"""
    key = f"visit_items::{v_id}::{email}::{name}::{qty}::{ts_iso}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

def try_rpc_ingest(email: str, v_id: int, name: str, qty: int,
                   category: Optional[str], unit: Optional[str],
                   barcode: Optional[str], ts_iso: str, ingest_id: str) -> tuple[bool,str]:
    """Enhanced RPC ingestion with better error handling"""
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
        
        rows = res.data if isinstance(res.data, list) else []
        if rows:
            r0 = rows[0]
            ok = bool(r0.get("ok", False))
            msg = str(r0.get("msg", ""))
            return ok, msg or ("ok" if ok else "failed")
        return True, "ok"
    except Exception as e:
        logger.warning(f"RPC ingest failed, using fallback: {e}")
        raise e

def fallback_direct_insert(email: str, v_id: int, name: str, qty: int,
                           category: Optional[str], unit: Optional[str],
                           barcode: Optional[str], ts_iso: str, ingest_id: str) -> None:
    """Enhanced fallback insertion with better error handling"""
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
        # Legacy table fallback
        payload.pop("ingest_id", None)
        sb.table("visit_items").insert(payload).execute()

def load_items_for_visit(visit_id: int) -> list[dict]:
    """Enhanced item loading with better error handling"""
    try:
        return sb.table("visit_items_p").select("*").eq("visit_id", visit_id) \
            .order("timestamp", desc=True).limit(500).execute().data or []
    except Exception:
        try:
            return sb.table("visit_items").select("*").eq("visit_id", visit_id) \
                .order("timestamp", desc=True).limit(500).execute().data or []
        except Exception as e:
            logger.warning(f"Failed to load items for visit {visit_id}: {e}")
            return []

def delete_item(table: str, item_id: int):
    """Enhanced item deletion with better error handling"""
    try:
        sb.table(table).delete().eq("id", item_id).execute()
    except Exception as e:
        logger.error(f"Failed to delete item {item_id} from {table}: {e}")
        raise e

# ------------------------ App Configuration Display ------------------------
st.sidebar.markdown("### ⚙️ Configuration")
st.sidebar.info(f"""
**Provider:** `{PROVIDER}`  
**Model:** `{GEMMA_MODEL}`  
**Timezone:** `{TZ}`  
**Cutoff:** {CUTOFF_HOUR}:00 PM  
**Inactivity:** {INACTIVITY_MIN} min
""")

# ------------------------ Main App Execution ------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"❌ Application error: {e}")
        st.info("Please refresh the page or contact support if the issue persists.")
