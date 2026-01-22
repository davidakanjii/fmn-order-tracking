import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import pydeck as pdk

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
        # Try to load from Google Colab/Sheets if available
        from google.colab import auth
        import gspread
        from google.auth import default
        
        auth.authenticate_user()
        creds, _ = default()
        gc = gspread.authorize(creds)
        
        SHEET_NAME = "Saleschatbotdb"
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        st.success("✅ Connected to live Google Sheets data")
        
    except:
        # Fallback: Show error and use sample data
        st.warning("⚠️ Google Sheets connection unavailable. Using sample data for demonstration.")
        
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
# DISPLAY FUNCTIONS
# -------------------------------------------------
def display_customer_details(order_df):
    """Section 1: Customer Details"""
    st.markdown("### 👤 Customer Details")
    first_row = order_df.iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**📅 Order Date**\n\n{first_row['Sales Order Creation Date']}")
    with col2:
        st.info(f"**🆔 Invoice Account**\n\n{first_row['Invoice account']}")
    with col3:
        st.info(f"**📍 Delivery Address**\n\n{first_row['Delivery address Name']}")

def display_product_details(order_df):
    """Section 2: Product Details"""
    st.markdown("### 📦 Product Details")
    
    # Create a clean table view
    product_cols = ['Product name', 'Item number', 'Quantity Order', 'Unit', 'Unit price', 'Net amount']
    available_cols = [col for col in product_cols if col in order_df.columns]
    
    if available_cols:
        display_df = order_df[available_cols].copy()
        
        # Format pricing columns
        if 'Unit price' in display_df.columns:
            display_df['Unit price'] = display_df['Unit price'].apply(
                lambda x: f"₦{float(x):,.2f}" if pd.notna(x) and str(x).strip() != '' else 'N/A'
            )
        if 'Net amount' in display_df.columns:
            display_df['Net amount'] = display_df['Net amount'].apply(
                lambda x: f"₦{float(x):,.2f}" if pd.notna(x) and str(x).strip() != '' else 'N/A'
            )
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Total Amount
        try:
            total = order_df['Net amount'].astype(float).sum()
            st.metric("**Total Order Value**", f"₦{total:,.2f}")
        except:
            st.metric("**Total Order Value**", "N/A")

def display_order_details(order_df):
    """Section 3: Order Details"""
    st.markdown("### 📋 Order Summary")
    first_row = order_df.iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**🆔 Sales Order:** {first_row['Sales order']}")
        st.write(f"**💳 Payment Date:** {first_row.get('Payment receipt date', 'N/A')}")
    with col2:
        st.write(f"**📦 Quantity Ordered:** {first_row['Quantity Order']} {first_row['Unit']}")
        try:
            st.write(f"**💵 Unit Price:** ₦{float(first_row['Unit price']):,.2f}")
        except:
            st.write(f"**💵 Unit Price:** N/A")
    with col3:
        st.write(f"**📊 Total Items:** {len(order_df)}")
        try:
            st.write(f"**💰 Net Amount:** ₦{float(first_row['Net amount']):,.2f}")
        except:
            st.write(f"**💰 Net Amount:** N/A")

def display_delivery_timeline(order_df):
    """Section 4 & 5: Expected Delivery Timeline and Order Status"""
    st.markdown("### 🚚 Delivery Timeline & Status")
    first_row = order_df.iloc[0]
    
    # Expected delivery date
    expected_date = first_row.get('Delivery Expected Date', 'N/A')
    st.info(f"**📅 Expected Delivery Date:** {expected_date}")
    
    # Order Status Information with visual indicators
    st.markdown("#### 📍 Order Tracking Status")
    
    status_items = [
        ("Order Dispatched", first_row.get('created_trip_date', 'N/A'), first_row.get('Order Dispatch Status', 'N/A')),
        ("Arrived at Warehouse", first_row.get('arrival_at_source Date', 'N/A'), first_row.get('Vehicle Arrival Status at Warehouse Status', 'N/A')),
        ("Trip Started", first_row.get('trip_started_date', 'N/A'), first_row.get('Trip Status', 'N/A')),
        ("Arrived at Delivery", first_row.get('arrival_at_delivery_location Date', 'N/A'), first_row.get('Delivery Arrival Status', 'N/A'))
    ]
    
    for status_label, date_time, status_desc in status_items:
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            if date_time != 'N/A' and str(date_time).strip() != '':
                st.success(f"✅ **{status_label}**")
            else:
                st.warning(f"⏳ **{status_label}**")
        
        with col2:
            if date_time != 'N/A' and str(date_time).strip() != '':
                st.write(f"🕐 {date_time}")
            else:
                st.write("*Pending*")
        
        with col3:
            if status_desc != 'N/A':
                st.caption(f"_{status_desc}_")

def display_delivery_map(order_df):
    """Section 6: Delivery Location Map"""
    st.markdown("### 🗺️ Delivery Location")
    first_row = order_df.iloc[0]
    
    # Check if geolocation data exists
    lat = first_row.get('delivery_geotag_lat', None)
    lng = first_row.get('delivery_geotag_lng', None)
    customer_loc = first_row.get('customer_location', 'N/A')
    
    if pd.notna(lat) and pd.notna(lng) and str(lat).strip() != '' and str(lng).strip() != '':
        try:
            lat_float = float(lat)
            lng_float = float(lng)
            
            # Create map with PyDeck
            view_state = pdk.ViewState(
                latitude=lat_float,
                longitude=lng_float,
                zoom=13,
                pitch=0
            )
            
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=[{"lat": lat_float, "lon": lng_float}],
                get_position=["lon", "lat"],
                get_color=[7, 100, 1, 200],
                get_radius=200,
            )
            
            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_style="mapbox://styles/mapbox/streets-v11"
            ))
            
            st.caption(f"📍 Customer Location: {customer_loc}")
            st.caption(f"🌐 Coordinates: {lat_float}, {lng_float}")
            
            # Google Maps link
            maps_url = f"https://www.google.com/maps?q={lat_float},{lng_float}"
            st.markdown(f"[🔗 Open in Google Maps]({maps_url})")
            
        except (ValueError, TypeError):
            st.warning("⚠️ Unable to display map - invalid coordinates")
            st.write(f"**📍 Customer Location:** {customer_loc}")
    else:
        st.warning("⚠️ Geolocation data not available")
        st.write(f"**📍 Customer Location:** {customer_loc}")

def display_vehicle_details(order_df):
    """Section 7: Vehicle Details"""
    st.markdown("### 🚛 Vehicle & Driver Information")
    first_row = order_df.iloc[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🚗 VEHICLE INFORMATION**")
        st.write(f"• **Vehicle Type:** {first_row.get('vehicle_type', 'N/A')}")
        st.write(f"• **Truck Number:** {first_row.get('truck_no', 'N/A')}")
        st.write(f"• **Tonnage Capacity:** {first_row.get('vehicle_tonnage_capacity', 'N/A')} tons")
        st.write(f"• **Transporter:** {first_row.get('transporter', 'N/A')}")
        st.write(f"• **Transaction Type:** {first_row.get('transaction_type', 'N/A')}")
    
    with col2:
        st.markdown("**👨‍✈️ DRIVER & TRIP INFORMATION**")
        st.write(f"• **Driver Name:** {first_row.get('driver_name', 'N/A')}")
        st.write(f"• **Phone Number:** {first_row.get('phone_number', 'N/A')}")
        st.write(f"• **Trip Type:** {first_row.get('trip_type', 'N/A')}")
        
        distance = first_row.get('distance_covered_inMeters', 'N/A')
        if distance != 'N/A' and pd.notna(distance) and str(distance).strip() != '':
            try:
                distance_km = float(distance) / 1000
                st.metric("🛣️ Distance Covered", f"{distance_km:.2f} km")
            except (ValueError, TypeError):
                st.write(f"• **Distance Covered:** Not available")
        else:
            st.write(f"• **Distance Covered:** Not available")
    
    # Full route in expandable section
    trip_route = first_row.get('trip_route', 'N/A')
    if trip_route != 'N/A':
        with st.expander("🗺️ View Full Trip Route"):
            st.write(trip_route)

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
