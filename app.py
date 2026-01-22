import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import pydeck as pdk
from google.oauth2 import service_account
import gspread

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="FMN Order Tracking Assistant",
    layout="wide",
    page_icon="🚚"
)

# FMN Brand Colors
FMN_COLORS = {
    "primary_green": "#076401",
    "primary_orange": "#FD7601",
    "primary_red": "#D22622",
    "accent_green": "#92BC0C",
    "accent_blue": "#599BD4",
    "navy_blue": "#19365E",
}

# Custom CSS for FMN branding
st.markdown(f"""
    <style>
    .stButton > button[kind="primary"] {{
        background-color: {FMN_COLORS['primary_orange']} !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: #E56A01 !important;
    }}
    
    .stButton > button {{
        border: 2px solid {FMN_COLORS['primary_green']} !important;
        color: {FMN_COLORS['primary_green']} !important;
        font-weight: 600 !important;
    }}
    
    .stButton > button:hover {{
        background-color: {FMN_COLORS['primary_green']} !important;
        color: white !important;
    }}
    
    [data-testid="stMetricValue"] {{
        color: {FMN_COLORS['primary_green']} !important;
        font-weight: 700 !important;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {FMN_COLORS['primary_green']} !important;
        box-shadow: 0 0 0 0.2rem rgba(7, 100, 1, 0.25) !important;
    }}
    
    h1, h2, h3 {{
        color: {FMN_COLORS['navy_blue']} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CONFIGURATION & SESSION INIT
# -------------------------------------------------
MAX_ATTEMPTS = 3
SESSION_TIMEOUT = 15  # minutes

def init_session():
    """Initialize session state variables"""
    if "stage" not in st.session_state:
        st.session_state.stage = "name"
        st.session_state.customer_name = ""
        st.session_state.order_id = ""
        st.session_state.attempts = 0
        st.session_state.blocked_until = None
        st.session_state.last_activity = datetime.now()

def check_timeout():
    """Check if session has timed out"""
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=SESSION_TIMEOUT):
        st.session_state.stage = "name"
        st.session_state.customer_name = ""
        st.session_state.order_id = ""
        st.warning(f"⏰ Session timed out after {SESSION_TIMEOUT} minutes of inactivity.")
        return True
    st.session_state.last_activity = datetime.now()
    return False

# -------------------------------------------------
# DATA LOADING
# -------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    """Load data from Google Sheets"""
    try:
        # Authenticate using the service account credentials from Streamlit secrets
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        st.write("✅ Credentials loaded successfully.")
        
        # Authenticate and access Google Sheets
        gc = gspread.authorize(creds)
        st.write("✅ Google Sheets authentication successful.")
        
        sheet = gc.open("Saleschatbotdb").sheet1  # Replace with your actual Google Sheet name
        st.write("✅ Connected to Google Sheet.")
        
        data = sheet.get_all_records()

        # Convert the data into a DataFrame
        df = pd.DataFrame(data)
        st.success("✅ Connected to live Google Sheets data")

    except Exception as e:
        # Fallback: Show error and use sample data
        st.warning(f"⚠️ Google Sheets connection unavailable. Error: {str(e)}. Using sample data for demonstration.")
        
        # Sample data based on your actual data structure
        sample_data = {
            'Sales Order Creation Date': ['1/20/26 0:00'],
            'Invoice account': ['C32064-B0'],
            'Delivery address Name': ['GOODNESS BAKERIES COMPANY LIMITED'],
            'Item number': ['FG23065'],
            'Net amount': [45990000],
            'Product name': ['GP-Confectionery Flour 50Kg- FM'],
            'Quantity Order': [900],
            'Payment receipt date': ['1/20/26 0:00'],
            'Sales order': ['SFM0079952'],
            'Unit price': [51100.0],
            'Quantity': [900],
            'Unit': ['Bag'],
            'vehicle_type': ['shac man'],
            'transporter': ['GTD'],
            'transaction_type': ['FG DELIVERY'],
            'vehicle_tonnage_capacity': [45],
            'driver_name': ['BASSEY SUNDAY'],
            'truck_no': ['T28333LA'],
            'trip_type': ['two-way'],
            'trip_route': ['APAPA-SITE-FLOUR-PORTHARCOURT-GOODNESS BAKERIES COMPANY LIMITED'],
            'phone_number': ['8065964813'],
            'customer_location': ['GOODNESS BAKERIES COMPANY LIMITED'],
            'delivery_geotag_lat': [4.831032175],
            'delivery_geotag_lng': [7.00228428],
            'created_trip_date': ['1/20/26 19:30'],
            'arrival_at_source Date': ['1/20/26 20:00'],
            'trip_started_date': [''],
            'arrival_at_delivery_location Date': [''],
            'Delivery Expected Date': ['Your order is expected to arrive between 1/23/2026 8:30:18 AM and 1/25/2026 8:30:18 AM'],
            'Order Dispatch Status': ['Order Dispatch is On Time'],
            'Vehicle Arrival Status at Warehouse Status': ['Vehicle arrived at Warehouse'],
            'Trip Status': ['Driver still Waiting at the Loading Warehouse'],
            'Delivery Arrival Status': ['Order Arrival at Customer Location Pending'],
            'distance_covered_inMeters': ['']
        }
        df = pd.DataFrame(sample_data)

    # Clean and standardize data
    df = df.fillna('N/A')
    
    if 'Sales order' in df.columns:
        df['Sales order'] = df['Sales order'].astype(str).str.strip().str.upper()
    
    if 'Invoice account' in df.columns:
        df['Invoice account'] = df['Invoice account'].astype(str).str.strip().str.upper()
    
    return df

# -------------------------------------------------
# ORDER LOOKUP LOGIC
# -------------------------------------------------
def find_order_details(order_id, invoice_account, df):
    """Find order with two-factor verification"""
    order_clean = order_id.strip().upper()
    invoice_clean = invoice_account.strip().upper()
    
    rows = df[(df["Sales order"] == order_clean) & (df["Invoice account"] == invoice_clean)]
    
    if rows.empty:
        order_exists = df[df["Sales order"] == order_clean]
        if not order_exists.empty:
            return "invalid_invoice"
        return None
    
    return rows

# -------------------------------------------------
# MAIN APP
# -------------------------------------------------
def main():
    st.title("🚚 FMN Order Tracking Assistant")
    st.write("Real-time order verification and delivery tracking system")
    
    # Initialize session
    init_session()
    
    # Check for timeout
    if check_timeout():
        return
    
    df = load_data()
    
    if df.empty:
        st.error("❌ Unable to load order data. Please contact support.")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        if st.button("🔄 Refresh Data"):
            load_data.clear()
            st.rerun()
        
        if st.session_state.customer_name:
            st.success(f"👤 **Logged in as:**\n\n{st.session_state.customer_name}")
        
        st.caption(f"⏱️ Session timeout: {SESSION_TIMEOUT} minutes")
        
        if st.button("🔴 End Session"):
            st.session_state.stage = "name"
            st.session_state.customer_name = ""
            st.session_state.order_id = ""
            st.session_state.attempts = 0
            st.rerun()
        
        st.markdown("---")
        st.caption("🏢 Flour Mills of Nigeria PLC")
        st.caption("© 2026 FMN - All Rights Reserved")
    
    # Stage 1: Name Input
    if st.session_state.stage == "name":
        st.header("👋 Welcome to FMN Order Tracking")
        st.write("Let's get started by identifying yourself.")
        
        name = st.text_input(
            "Enter your full name:",
            max_chars=100,
            placeholder="e.g., John Doe"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Continue →", type="primary", use_container_width=True):
                if name.strip() == "":
                    st.error("❌ Please enter a valid name.")
                else:
                    st.session_state.customer_name = name.strip()
                    st.session_state.stage = "order"
                    st.rerun()
    
    # Stage 2: Order ID Input
    elif st.session_state.stage == "order":
        st.header(f"Hello, {st.session_state.customer_name}! 👋")
        st.write("Please provide your Sales Order ID to track your delivery.")
        
        order_id = st.text_input(
            "Sales Order ID:",
            max_chars=50,
            placeholder="e.g., SFM0079952"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back"):
                st.session_state.stage = "name"
                st.rerun()
        with col2:
            if st.button("Continue →", type="primary"):
                if order_id.strip() == "":
                    st.error("❌ Please enter a valid order ID.")
                else:
                    st.session_state.order_id = order_id.strip()
                    st.session_state.stage = "validate"
                    st.rerun()
    
    # Stage 3: Invoice Verification
    elif st.session_state.stage == "validate":
        # Check if blocked
        if st.session_state.blocked_until:
            if datetime.now() < st.session_state.blocked_until:
                remaining = int((st.session_state.blocked_until - datetime.now()).total_seconds())
                st.error(f"🚫 Too many failed attempts. Please wait {remaining} seconds.")
                
                if st.button("← Back to Start"):
                    st.session_state.stage = "name"
                    st.session_state.blocked_until = None
                    st.session_state.attempts = 0
                    st.rerun()
                return
            else:
                st.session_state.blocked_until = None
                st.session_state.attempts = 0
        
        st.header("🔒 Security Verification")
        st.info(f"**Order ID:** {st.session_state.order_id}")
        st.write("Please confirm your Invoice Account ID for security verification.")
        
        if st.session_state.attempts > 0:
            st.warning(f"⚠️ Failed attempts: {st.session_state.attempts}/{MAX_ATTEMPTS}")
        
        invoice_account = st.text_input(
            "Invoice Account ID:",
            max_chars=50,
            placeholder="e.g., C32064-B0"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("← Back"):
                st.session_state.stage = "order"
                st.session_state.attempts = 0
                st.rerun()
        
        with col2:
            if st.button("Verify & Track Order 🔍", type="primary"):
                if invoice_account.strip() == "":
                    st.error("❌ Please enter your Invoice Account ID.")
                else:
                    invoice_clean = invoice_account.strip().upper()
                    
                    with st.spinner("🔍 Verifying credentials..."):
                        time.sleep(1)
                        result = find_order_details(st.session_state.order_id, invoice_clean, df)
                    
                    if isinstance(result, pd.DataFrame):
                        # SUCCESS - Display all sections
                        st.session_state.attempts = 0
                        
                        st.success(f"### ✅ Order Found for {st.session_state.customer_name}!")
                        st.write(f"**Sales Order:** {st.session_state.order_id}")
                        
                        st.markdown("---")
                        
                        # Display all sections
                        display_customer_details(result)
                        st.markdown("---")
                        
                        display_product_details(result)
                        st.markdown("---")
                        
                        display_order_details(result)
                        st.markdown("---")
                        
                        display_delivery_timeline(result)
                        st.markdown("---")
                        
                        display_delivery_map(result)
                        st.markdown("---")
                        
                        display_vehicle_details(result)
                        st.markdown("---")
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🔍 Track Another Order", use_container_width=True):
                                st.session_state.stage = "order"
                                st.session_state.order_id = ""
                                st.rerun()
                        with col2:
                            if st.button("🏠 Start New Session", use_container_width=True):
                                st.session_state.stage = "name"
                                st.session_state.customer_name = ""
                                st.session_state.order_id = ""
                                st.rerun()
                    
                    elif result == "invalid_invoice":
                        st.session_state.attempts += 1
                        
                        if st.session_state.attempts >= MAX_ATTEMPTS:
                            st.session_state.blocked_until = datetime.now() + timedelta(minutes=5)
                            st.error(f"🚫 Maximum attempts exceeded. Locked for 5 minutes.")
                        else:
                            st.error("❌ Invoice Account mismatch! Please verify and try again.")
                    
                    else:
                        st.session_state.attempts += 1
                        
                        if st.session_state.attempts >= MAX_ATTEMPTS:
                            st.session_state.blocked_until = datetime.now() + timedelta(minutes=5)
                            st.error(f"🚫 Maximum attempts exceeded. Locked for 5 minutes.")
                        else:
                            st.error(f"❌ Order not found: {st.session_state.order_id}")

if __name__ == "__main__":
    main()
