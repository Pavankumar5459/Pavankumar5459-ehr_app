# Hanvion Health – EHR + ICD-10 Apps

This repository contains two Streamlit applications:

1. **Premium EHR App (`ehr_app.py`)**
   - Demographics
   - Admission details with ICD-10 search
   - Vitals, history, exam
   - Assessment & plan
   - Hanvion Health Assistant (rule-based helper)

2. **ICD-10 Code Explorer (`icd10_dashboard_app.py`)**
   - Searches CMS Section 111 valid ICD-10 file (Jan 2026)
   - Filters by Included / Excluded / All codes
   - Displays results in an interactive table

## Folder Structure

- `ehr_app.py` – main EHR application
- `icd10_dashboard_app.py` – ICD-10 explorer app
- `icd10_utils.py` – shared utilities to load and search ICD-10 dataset
- `requirements.txt` – Python dependencies
- `data/section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx` – **you must upload this manually**

## How to Use

1. Create a new GitHub repository.
2. Upload all files from this project (including the `data` folder).
3. Manually upload the ICD-10 Excel file into the `data` folder with the exact name:
   `section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx`
4. Deploy on Streamlit Cloud:
   - For EHR app: set main file to `ehr_app.py`
   - For ICD-10 explorer: set main file to `icd10_dashboard_app.py`

These apps are for educational and demo purposes only and do not replace any official clinical or billing systems.
