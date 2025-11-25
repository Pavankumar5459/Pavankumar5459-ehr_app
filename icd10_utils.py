import os
import pandas as pd
from functools import lru_cache

# Path to ICD-10 Excel file inside the repo
ICD_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
)

@lru_cache(maxsize=1)
def load_icd10():
    """Load ICD-10 dataset from the Excel file (cached)."""
    df = pd.read_excel(ICD_PATH, engine="openpyxl")
    df.columns = df.columns.str.strip()
    return df

def search_icd10(query: str = "", scope: str = "All"):
    """Search ICD-10 codes by code or text. Scope can be All/Included/Excluded."""
    df = load_icd10()

    # Try to detect NF EXCL column if present
    nf_col = None
    for col in df.columns:
        if col.strip().upper().startswith("NF EXCL"):
            nf_col = col
            break

    if nf_col is not None:
        if scope == "Included":
            df = df[df[nf_col].isna()]
        elif scope == "Excluded":
            df = df[~df[nf_col].isna()]

    if not query:
        return df

    q = query.lower()

    code_col = "CODE" if "CODE" in df.columns else df.columns[0]
    short_col = df.columns[1] if len(df.columns) > 1 else code_col
    long_col = df.columns[2] if len(df.columns) > 2 else short_col

    mask = (
        df[code_col].astype(str).str.lower().str.contains(q)
        | df[short_col].astype(str).str.lower().str.contains(q)
        | df[long_col].astype(str).str.lower().str.contains(q)
    )

    return df[mask]
