import requests
import streamlit as st

def get_reps(address):
    """
    DEBUG MODE: Queries Geocodio and prints raw diagnostics to the screen.
    """
    st.divider()
    st.markdown("### 🛠️ Civic Engine Debugger")

    # 1. CHECK API KEY
    try:
        api_key = st.secrets["geocodio"]["api_key"]
        # Show last 4 chars to verify it's reading the right key
        st.success(f"✅ API Key Loaded (Ends in: ...{api_key[-4:]})")
    except:
        st.error("❌ CRITICAL: 'geocodio' section or 'api_key' missing from secrets.toml")
        return []

    # 2. CONSTRUCT REQUEST
    # We use 'congressional_districts' which contains federal legislator data
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        'q': address,
        'fields': 'congressional_districts', 
        'api_key': api_key
    }

    st.info(f"📡 Sending Request for: **{address}**")

    try:
        # 3. EXECUTE REQUEST
        r = requests.get(url, params=params)
        
        # 4. CHECK HTTP STATUS
        if r.status_code != 200:
            st.error(f"❌ API Request Failed. Status Code: {r.status_code}")
            st.json(r.json()) # Print the error message from Geocodio
            return []
        
        data = r.json()
        
        # 5. INSPECT RAW DATA (The most important part)
        with st.expander("🔍 Click to view Raw JSON Response", expanded=True):
            st.json(data)

        # 6. ATTEMPT PARSING (Step-by-Step with Logs)
        if not data.get('results'):
            st.warning("⚠️ API returned 200 OK, but 'results' list is empty.")
            return []

        result = data['results'][0]
        fields = result.get('fields', {})
        
        # Check for the district field
        districts = fields.get('congressional_districts', [])
        if not districts:
            st.error("❌ 'congressional_districts' field is missing in response.")
            return []
        
        # Check for legislators
        current_legislators = districts[0].get('current_legislators', [])
        if not current_legislators:
            st.error("❌ 'current_legislators' list is empty for this district.")
            return []

        st.success(f"✅ Parsing {len(current_legislators)} raw legislators...")

        targets = []
        
        for leg in current_legislators:
            role = leg.get('type')
            
            # Only keep Federal
            if role in ['senator', 'representative']:
                bio = leg.get('bio', {})
                contact = leg.get('contact', {})
                
                full_name = f"{bio.get('first_name')} {bio.get('last_name')}"
                title = "U.S. Senator" if role == 'senator' else "U.S. Representative"
                
                # Address Parsing
                addr_raw = contact.get('address') or "United States Capitol, Washington DC"
                
                targets.append({
                    'name': full_name,
                    'title': title,
                    'address_obj': {
                        'name': full_name, 
                        'street': addr_raw, 
                        'city': "Washington", 
                        'state': "DC", 
                        'zip': "20510"
                    }
                })

        return targets

    except Exception as e:
        st.error(f"🔥 Python Exception during processing: {e}")
        return []