def parse_provider_data(raw_data):
    """
    Extracts the Provider's Name and State Licenses from taxonomies AND identifiers.
    """
    basic = raw_data.get("basic", {})
    first_name = basic.get("first_name", "")
    last_name = basic.get("last_name", "")
    credential = basic.get("credential", "")
    full_name = f"{first_name} {last_name} {credential}".strip()
    
    state_licenses = []
    
    # 1. Check Taxonomies (and DON'T drop if license number is blank)
    taxonomies = raw_data.get("taxonomies", [])
    for tax in taxonomies:
        state = tax.get("state", "")
        license_num = tax.get("license", "Not Provided") # Keep state even if license is blank
        desc = tax.get("desc", "None")
        is_primary = tax.get("primary", False)
        
        if state:  # As long as there is a state, we want to know about it
             state_licenses.append({
                 "State": state,
                 "License Number": license_num,
                 "Source": "Taxonomy",
                 "Specialty": desc,
                 "Primary": "Yes" if is_primary else "No"
             })

    # 2. Check Other Identifiers (Doctors often hide state licenses here)
    identifiers = raw_data.get("identifiers", [])
    for ident in identifiers:
        state = ident.get("state", "")
        license_num = ident.get("identifier", "")
        desc = ident.get("desc", "Other ID")
        
        # Only pull it if it's tied to a state
        if state and license_num:
             state_licenses.append({
                 "State": state,
                 "License Number": license_num,
                 "Source": "Other Identifier",
                 "Specialty": desc,
                 "Primary": "N/A"
             })
             
    # 3. Remove exact duplicates (sometimes they list the same license in both places)
    unique_licenses = [dict(t) for t in {tuple(d.items()) for d in state_licenses}]
             
    return full_name, unique_licenses
