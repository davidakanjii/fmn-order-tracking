def display_delivery_map(order_df):
    """Section 6: Delivery Location Map"""
    st.markdown("### 🗺️ Delivery Location")
    first_row = order_df.iloc[0]
    
    # Check if geolocation data exists
    lat = first_row.get('delivery_geotag_lat', None)
    lng = first_row.get('delivery_geotag_lng', None)
    customer_loc = first_row.get('customer_location', 'N/A')
    
    if pd.notna(lat) and pd.notna(lng) and lat != 'N/A' and lng != 'N/A':
        try:
            lat_float = float(lat)
            lng_float = float(lng)
            
            # Map style selector
            map_styles = {
                "Light": "mapbox://styles/mapbox/light-v10",
                "Dark": "mapbox://styles/mapbox/dark-v10",
                "Streets": "mapbox://styles/mapbox/streets-v11",
                "Outdoors": "mapbox://styles/mapbox/outdoors-v11",
                "Satellite": "mapbox://styles/mapbox/satellite-v9",
                "Satellite Streets": "mapbox://styles/mapbox/satellite-streets-v11"
            }
            
            # Add map style selector
            selected_style = st.selectbox(
                "Choose Map Style:",
                options=list(map_styles.keys()),
                index=0,  # Default to Light
                key="map_style_selector"
            )
            
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
                get_color=[253, 118, 1, 220],  # FMN Orange for better visibility
                get_radius=200,
            )
            
            # Use selected map style
            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_style=map_styles[selected_style]
            ))
            
            st.caption(f"📍 Customer Location: {customer_loc}")
        except:
            st.warning("⚠️ Unable to display map - invalid coordinates")
            st.write(f"**Customer Location:** {customer_loc}")
    else:
        st.warning("⚠️ Geolocation data not available")
        st.write(f"**Customer Location:** {customer_loc}")
