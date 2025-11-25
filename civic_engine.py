import requests
import streamlit as st

def get_reps(address):
    """
    Fixed Version: Uses correct 'cd' field parameter.
    """
    st.divider()
    st.markdown("### 🛠️ Civic Engine Status")

    # 1. Load Key
    try:
        api_key = st.secrets["geocodio"]["api_key"]
    except:
        st.error("❌ Missing API Key in secrets.")
        return []

    # 2. Request (THE FIX IS HERE: 'fields': 'cd')
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        'q': address,
        'fields': 'cd',  # Changed from 'congressional_districts' to 'cd'
        'api_key': api_key
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        # 3. Check for API Errors
        if r.status_code != 200:
            st.error(f"❌ API Error: {data.get('error')}")
            return []

        # 4. Parse Results
        if not data.get('results'):
            st.warning("⚠️ Address not found.")
            return []

        result = data['results'][0]
        
        # Debug: Show what we got back
        # with st.expander("View Raw JSON Data"):
        #     st.json(result)

        # Check for Field Data
        fields = result.get('fields', {})
        districts = fields.get('congressional_districts', [])
        
        if not districts:
            st.error("❌ No district data found for this address.")
            return []

        # Get Legislators
        current_legislators = districts[0].get('current_legislators', [])
        
        targets = []
        
        for leg in current_legislators:
            role = leg.get('type')
            
            # Geocodio returns 'Senator' and 'Representative' (Capitalized)
            if role in ['Senator', 'Representative']:
                bio = leg.get('bio', {})
                contact = leg.get('contact', {})
                
                full_name = f"{bio.get('first_name')} {bio.get('last_name')}"
                title = "U.S. Senator" if role == 'Senator' else "U.S. Representative"
                
                # Address Cleaning
                # Geocodio usually provides the Washington DC address in 'contact'
                addr_raw = contact.get('address') or "United States Capitol, Washington DC"
                
                # Create simplified object
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

        if targets:
            st.success(f"✅ Successfully found {len(targets)} legislators!")
            return targets
        else:
            st.warning("Found district, but no legislators listed.")
            return []

    except Exception as e:
        st.error(f"🔥 Error: {e}")
        return []