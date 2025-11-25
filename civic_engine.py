import requests
import streamlit as st

def get_reps(address):
    """
    DEBUG MODE: Queries Geocodio and prints raw JSON diagnostics.
    """
    st.divider()
    st.markdown("### 🛠️ Civic Engine Debugger")

    # 1. Load Key
    try:
        api_key = st.secrets["geocodio"]["api_key"]
    except:
        st.error("❌ Missing API Key in secrets.")
        return []

    # 2. Request
    # We ask for 'cd' (Congressional Districts) which includes legislators
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        'q': address,
        'fields': 'cd', 
        'api_key': api_key
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        # 3. DISPLAY RAW LOGS (This is what you need)
        with st.expander("🔍 Click here to see Raw Geocodio Response", expanded=True):
            st.write(f"**Status Code:** {r.status_code}")
            st.json(data)

        # 4. Standard Error Checks
        if r.status_code != 200:
            st.error(f"❌ API Error: {data.get('error')}")
            return []

        if not data.get('results'):
            st.warning("⚠️ Address not found.")
            return []

        result = data['results'][0]
        fields = result.get('fields', {})
        
        # 5. PARSING ATTEMPT
        # Geocodio usually puts data under 'congressional_districts' even if you request 'cd'
        districts = fields.get('congressional_districts', [])
        
        if not districts:
            st.error("❌ 'congressional_districts' key is missing from fields.")
            st.write("Available keys:", list(fields.keys()))
            return []

        # Get Legislators
        # We take the first district found (usually the correct one)
        current_legislators = districts[0].get('current_legislators', [])
        
        if not current_legislators:
            st.warning("⚠️ 'current_legislators' list is empty/missing.")
            st.write("District Data found:", districts[0])
            return []

        targets = []
        
        for leg in current_legislators:
            role = leg.get('type')
            # Debug: Print every role found
            # st.write(f"Found Official: {leg.get('bio', {}).get('first_name')} - Role: {role}")
            
            if role in ['Senator', 'Representative']:
                bio = leg.get('bio', {})
                contact = leg.get('contact', {})
                
                full_name = f"{bio.get('first_name')} {bio.get('last_name')}"
                title = "U.S. Senator" if role == 'Senator' else "U.S. Representative"
                
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

        if targets:
            st.success(f"✅ Successfully parsed {len(targets)} legislators!")
            return targets
        else:
            st.warning("Found legislators, but none matched 'Senator' or 'Representative'.")
            return []

    except Exception as e:
        st.error(f"🔥 Python Error: {e}")
        return []