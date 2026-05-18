"""
Data loader — reads school_data.csv and returns a cleaned DataFrame.

All column renaming, short-name mapping, and audit-column creation happens
here so the rest of the pipeline works with consistent internal column names.
"""
from pathlib import Path
from typing import Union

import pandas as pd

from config import COLUMN_RENAME, SCHOOL_SHORT_NAMES


def _normalise_severity(s: str) -> str:
    """Map a free-text severity string to Major / Moderate / Minor / Unknown."""
    s = str(s).lower()
    if 'major'    in s: return 'Major'
    if 'moderate' in s: return 'Moderate'
    if 'minor'    in s: return 'Minor'
    return 'Unknown'


def load_school_data(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load and clean the school safety assessment CSV.

    Args:
        csv_path: path to school_data.csv (string or Path).

    Returns:
        pd.DataFrame with:
          - All columns renamed per COLUMN_RENAME mapping in config.py
          - School_short: abbreviated label used in charts and CSV matching
          - FAS_obs, CSS_obs, EEI_obs: observer-entered scores preserved for
            post-scoring audit (computed scores overwrite FAS/CSS/EEI columns)
          - Sev_obs: normalised observer-entered severity for audit comparison
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df = df.rename(columns=COLUMN_RENAME)

    df['School_short'] = df['School'].map(SCHOOL_SHORT_NAMES).fillna(df['School'])

    # Preserve observer-entered scores before the pipeline overwrites FAS/CSS/EEI
    # with computed values, so the audit section can compare them.
    df['FAS_obs'] = pd.to_numeric(df['FAS'], errors='coerce')
    df['CSS_obs'] = pd.to_numeric(df['CSS'], errors='coerce')
    df['EEI_obs'] = pd.to_numeric(df['EEI'], errors='coerce')

    df['Sev_obs'] = df['Severity'].apply(_normalise_severity)

    return df
