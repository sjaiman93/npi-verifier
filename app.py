import os
# Force Streamlit Cloud to install the Chromium browser binary on boot
os.system("playwright install chromium")

import streamlit as st
import requests
import pandas as pd
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

def safe_str(val, default=""):
    if val is None:
        return default
    return str(val).strip()

def fetch_npi_data(npi_number):
    url = "https://npiregistry.cms.hhs.gov/api/?version=2.1"
    params = {"number": npi_number}
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
    basic = raw_data.get("basic", {})
    first_name = safe_str(basic.get("first_name"))
    last_name = safe_str(basic.get("last_name"))
    credential = safe_str(basic.get("credential"))
    full_name = f"{first_name} {last_name} {credential}".strip()
    
    state_licenses = []
    
    for tax in raw_data.get("taxonomies", []):
        state = safe_str(tax.get("state"))
        license_num = safe_str(tax.get("license"), default="Not Listed in NPI")
        desc = safe_str(tax.get("desc"), default="None")
        if state:
            state_licenses.append({
                "State": state,
                "License Number": license_num if license_num else "Not Listed in NPI",
                "Source": "NPI Taxonomy",
                "Specialty": desc if desc else "None"
            })

    for ident in raw_data.get("identifiers", []):
        state = safe_str(ident.get("state"))
        license_num = safe_str(ident.get("identifier"))
        desc = safe_str(ident.get("desc"), default="Other Identifier")
        if state and license_num:
            state_licenses.append({
                "State": state,
                "License Number": license_num,
                "Source": "NPI Identifier",
                "Specialty": desc if desc else "Other Identifier"
            })
             
    seen = set()
    unique_licenses = []
    for lic in state_licenses:
        key = (lic["State"], lic["License Number"], lic["Specialty"])
        if key not in seen:
            seen.add(key)
            unique_licenses.append(lic)
             
    return first_name, last_name, full_name, unique_licenses

async def scrape_docinfo_states(first_name, last_name):
    """
    Automates a headless browser to search DocInfo and extract licensed states.
    """
    discovered_states = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await stealth_async(page)
        
        try:
            await page.goto("https://www.docinfo.org/search/", timeout=15000)
            await page.fill("input[name='firstName']", first_name)
            await page.fill("input[name='lastName']", last_name)
            await page.click("button[type='submit']")
            
            # Wait for the table to populate
            await page.wait_for_selector(".results-table", timeout=10000)
            
            # Extract state abbreviations or names from the results column
            state_elements = await page.query_selector_all(".license-state-column")
            for element in state_elements:
                state_text = await element.inner_text()
                if state_text:
                    discovered_states.add(state_text.strip())
        except Exception as e:
            pass # Fails gracefully if timeout occurs or no records exist
        finally:
            await browser.close()
            
    return list(discovered_states)

def main():
    st.set_page_config(page_title="Automated Discovery Layer", page_icon="⚕️", layout="centered")
    st.title("⚕️ MVP Phase 2: NPI & DocInfo Discovery")
    st.markdown("Enter an NPI. The tool will pull NPI data and trigger a headless scraper to sweep DocInfo for missing states.")
    
    npi_input = st.text_input("Enter 10-Digit NPI Number:", max_chars=10)
    
    if st.button("Run Automated Discovery", type="primary"):
        if npi_input.isdigit() and len(npi_input) == 10:
            
            # Step 1: NPI Database
            with st.spinner("1/2: Querying federal CMS database..."):
                raw_data = fetch_npi_data(npi_input)
                
            if raw_data:
                first_name, last_name, full_name, npi_licenses = parse_provider_data(raw_data)
                st.success(f"✅ NPI Record Found: {full_name}")
                
                # Step 2: DocInfo Scraper
                with st.spinner(f"2/2: Launching Playwright to scrape DocInfo for {first_name} {last_name}..."):
                    try:
                        docinfo_states = asyncio.run(scrape_docinfo_states(first_name, last_name))
                    except Exception as e:
                        docinfo_states = []
                        st.error("DocInfo scraper encountered an execution loop error.")

                # Consolidation and UI Render
                st.markdown("### 📋 NPI Reported Licenses")
                if npi_licenses:
                    st.dataframe(pd.DataFrame(npi_licenses), use_container_width=True, hide_index=True)
                else:
                    st.warning("No licenses self-reported in NPI.")

                st.markdown("### 🔍 DocInfo Discovered States")
                if docinfo_states:
                    st.info(f"Additional states found via DocInfo sweep: **{', '.join(docinfo_states)}**")
                else:
                    st.warning("No additional state data extracted from DocInfo.")
            else:
                st.error("⚠️ No records found for this NPI. Please check the number.")
        else:
            st.warning("Please enter a valid 10-digit numeric NPI.")

if __name__ == "__main__":
    main()
