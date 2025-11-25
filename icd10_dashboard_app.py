import streamlit as st
from icd10_utils import search_icd10, load_icd10

st.set_page_config(
    page_title="ICD-10 Code Explorer – Hanvion Health",
    page_icon="💊",
    layout="wide",
)

st.title("ICD-10 Code Explorer")
st.markdown("#### Hanvion Health – CMS Section 111 Valid ICD-10 (Jan 2026)")

st.write(
    "Search and filter valid ICD-10 codes from the CMS Section 111 update file. "
    "Use the filters in the sidebar to explore included and excluded codes."
)

with st.sidebar:
    st.header("Search & Filters")
    query = st.text_input("Search by code or diagnosis text")
    scope = st.radio("Code set", ["All", "Included", "Excluded"], index=0)
    show_rows = st.slider("Max rows to display", 10, 200, 50, step=10)

df = search_icd10(query, scope=scope)

st.caption(f"Showing {min(len(df), show_rows)} of {len(df):,} matching rows.")

st.dataframe(df.head(show_rows), use_container_width=True)

st.markdown("---")
st.markdown(
    "Data source: CMS Section 111 valid ICD-10 file (Jan 2026). "
    "This tool is for educational and internal use only and does not replace official CMS publications."
)
