import streamlit as st
import requests
import pandas as pd

def fetch_npi_data(npi_number):
    """
    Queries the free CMS NPPES v2.1 API.
    """
    url = "https://npiregistry.cms.hhs.gov/api/?version=2.1"
    params = {
        "number": npi_number
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check if results exist in the JSON payload
        if "results" in data and len(data["results"]) > 0:
            return data["results"][0]
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to NPPES API: {e}")
        return None

def parse_provider_data(raw_data):
    """
    Extracts the Provider's Name and State Licenses from the JSON.
    """
    # 1. Extract Name & Credentials
    basic = raw_data.get("basic", {})
    first_name = basic.get("first_name", "")
    last_name = basic.get("last_name", "")
    credential = basic.get("credential", "")
    
    # Clean up spacing if credential is blank
    full_name = f"{first_name} {last_name} {credential}".strip()
    
    # 2. Extract State Licenses from the Taxonomy array
    taxonomies = raw_data.get("taxonomies", [])
    state_licenses = []
    
    for tax in taxonomies:
        state = tax.get("state", "")
        license_num = tax.get("license", "")
        desc = tax.get("desc", "")
        is_primary = tax.get("primary", False)
        
        # Only append if both state and license number are reported
        if state and license_num:
             state_licenses.append({
                 "State": state,
                 "License Number": license_num,
                 "Specialty / Taxonomy": desc,
                 "Primary License": "Yes" if is_primary else "No"
             })
             
    return full_name, state_licenses

def main():
    st.set_page_config(page_title="NPPES Verifier", page_icon="⚕️", layout="centered")
    
    st.title("⚕️ MVP Phase 1: NPI Lookup Engine")
    st.markdown("Enter a 10-digit NPI number to retrieve the candidate's exact state licenses from the federal registry.")
    
    # Streamlit Input UI
    npi_input = st.text_input("Enter 10-Digit NPI Number:", max_chars=10)
    
    if st.button("Fetch Provider Data", type="primary"):
        if npi_input.isdigit() and len(npi_input) == 10:
            with st.spinner("Querying federal CMS database..."):
                raw_data = fetch_npi_data(npi_input)
                
                if raw_data:
                    full_name, state_licenses = parse_provider_data(raw_data)
                    
                    st.success("✅ Provider Record Found!")
                    st.subheader(f"Provider: {full_name}")
                    
                    if state_licenses:
                        st.markdown("### 📋 Reported State Licenses")
                        # Display extracted licenses cleanly in a dataframe
                        df = pd.DataFrame(state_licenses)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.warning("No state license records found in the provider's taxonomy data.")
                        
                    # Let developers see the raw JSON for debugging
                    with st.expander("View Raw NPPES JSON Payload"):
                        st.json(raw_data)
                else:
                    st.error("⚠️ No records found for this NPI. Please check the number.")
        else:
            st.warning("Please enter a valid 10-digit numeric NPI.")

if __name__ == "__main__":
    main()
