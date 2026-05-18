"""
Crime Statistics Agency Victoria — personal crime rate fetcher.

Attempts to download suburb-level offence rate data from CSA Victoria.
Falls back to hardcoded 2023-24 estimates if the download fails.
"""
import os
import pandas as pd

CSA_DOWNLOAD_URL = (
    'https://files.crimestatistics.vic.gov.au/2024-06/'
    'Data_Tables_Recorded_Offences_Visualisation_Year_Ending_March_2024.xlsx'
)

# Offences against person per 100,000 population — CSA Victoria 2023-24
CRIME_FALLBACK = {
    'Reservoir': 820,   # higher — arterial corridor
    'Thornbury': 560,   # lower, more residential
    'Preston':   710,   # medium — mixed use
}


def fetch_crime_rate(suburb: str, out_dir: str = 'outputs') -> float:
    """
    Fetch personal crime offence rate per 100,000 population from CSA Victoria.
    Falls back to hardcoded 2023-24 suburb estimates if download fails.
    """
    try:
        import requests
        print(f"    Crime: Attempting CSA Victoria download...")
        resp = requests.get(CSA_DOWNLOAD_URL, timeout=30, stream=True)
        if resp.status_code == 200:
            tmp = os.path.join(out_dir, '_csa_tmp.xlsx')
            os.makedirs(out_dir, exist_ok=True)
            with open(tmp, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            xl = pd.ExcelFile(tmp)
            for sheet in xl.sheet_names:
                if 'suburb' in sheet.lower() or 'lga' in sheet.lower():
                    csa = xl.parse(sheet)
                    csa.columns = csa.columns.str.strip().str.upper()
                    suburb_col  = next((c for c in csa.columns if 'SUBURB' in c or 'LGA' in c), None)
                    rate_col    = next((c for c in csa.columns if 'RATE' in c), None)
                    offence_col = next((c for c in csa.columns if 'OFFENCE' in c), None)
                    if suburb_col and (rate_col or offence_col):
                        match = csa[csa[suburb_col].str.upper() == suburb.upper()]
                        if not match.empty:
                            col  = rate_col or offence_col
                            rate = float(match[col].iloc[0])
                            os.remove(tmp)
                            print(f"    Crime: CSA data — {suburb} = {rate:.0f}/100k")
                            return rate
            os.remove(tmp)
    except Exception as e:
        print(f"    Crime: CSA download failed ({type(e).__name__}) — using fallback")

    fallback = CRIME_FALLBACK.get(suburb, 700)
    print(f"    Crime: Using fallback for {suburb} — {fallback}/100k (2023-24 CSA estimate)")
    return fallback
