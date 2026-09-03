import streamlit as st
import requests
import pandas as pd

def safe_str(val, default=""):
    """
    Safely handles None, nulls, integers, and strips whitespace.
    """
    if val is None:
        return default
    return str(val).strip()

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
        
        if "results" in data and len(data["results"]) > 0:
            return data["results"][0]
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to NPPES API: {e}")
        return None

def parse_provider_data(raw_data):
    """
    Extracts Provider Name and State Licenses safely from taxonomies AND identifiers.
    """
    basic = raw_data.get("basic", {})
    first_name = safe_str(basic.get("first_name"))
    last_name = safe_str(basic.get("last_name"))
    credential = safe_str(basic.get("credential"))
    full_name = f"{first_name} {last_name} {credential}".strip()
    
    state_licenses = []
    
    # 1. Check Taxonomies
    taxonomies = raw_data.get("taxonomies", [])
    for tax in taxonomies:
        state = safe_str(tax.get("state"))
        license_num = safe_str(tax.get("license"), default="Not Listed in NPI")
        desc = safe_str(tax.get("desc"), default="None")
        is_primary = tax.get("primary", False)
        
        if state:
            state_licenses.append({
                "State": state,
                "License Number": license_num if license_num else "Not Listed in NPI",
                "Source": "Taxonomy",
                "Specialty": desc if desc else "None",
                "Primary": "Yes" if is_primary else "No"
            })

    # 2. Check Other Identifiers section
    identifiers = raw_data.get("identifiers", [])
    for ident in identifiers:
        state = safe_str(ident.get("state"))
        license_num = safe_str(ident.get("identifier"))
        desc = safe_str(ident.get("desc"), default="Other Identifier")
        
        if state and license_num:
            state_licenses.append({
                "State": state,
                "License Number": license_num,
                "Source": "Other Identifier",
                "Specialty": desc if desc else "Other Identifier",
                "Primary": "N/A"
            })
             
    # 3. Deduplicate cleanly
    seen = set()
    unique_licenses = []
    for lic in state_licenses:
        key = (lic["State"], lic["License Number"], lic["Specialty"])
        if key not in seen:
            seen.add(key)
            unique_licenses.append(lic)
             
    return full_name, unique_licenses

def main():
    st.set_page_config(page_title="NPPES Verifier", page_icon="⚕️", layout="centered")
    
    st.title("⚕️ MVP Phase 1: NPI Lookup Engine")
    st.markdown("Enter a 10-digit NPI number to retrieve the candidate's exact state licenses from the federal registry.")
    
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
                        df = pd.DataFrame(state_licenses)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.warning("No state license records found in the provider's data.")
                        
                    with st.expander("View Raw NPPES JSON Payload"):
                        st.json(raw_data)
                else:
                    st.error("⚠️ No records found for this NPI. Please check the number.")
        else:
            st.warning("Please enter a valid 10-digit numeric NPI.")

if __name__ == "__main__":
    main()
