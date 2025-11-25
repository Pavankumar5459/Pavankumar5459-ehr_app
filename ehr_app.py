import streamlit as st
from datetime import datetime, date
import os
from openai import OpenAI
from icd10_utils import search_icd10

# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health – EHR",
    layout="wide"
)

# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------
st.markdown("""
<style>
.main { background-color: #F4F6FA; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
h1, h2, h3 { color: #0B3C5D; }
.ehr-card {
    background: white;
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: 1rem;
    border-left: 4px solid #F5A623;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.ehr-badge {
    display: inline-block;
    background: #0B3C5D;
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
}
.small-text { font-size: 0.85rem; color: #444; }
.adr-low {
    display:inline-block;
    background:#2e7d32;
    color:white;
    padding:4px 10px;
    border-radius:16px;
    font-size:0.8rem;
}
.adr-moderate {
    display:inline-block;
    background:#f9a825;
    color:black;
    padding:4px 10px;
    border-radius:16px;
    font-size:0.8rem;
}
.adr-high {
    display:inline-block;
    background:#c62828;
    color:white;
    padding:4px 10px;
    border-radius:16px;
    font-size:0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR – ENCOUNTER & INSURANCE SUMMARY
# ---------------------------------------------------------
st.sidebar.title("Hanvion Health EHR")

st.sidebar.subheader("Encounter Context")
patient_id = st.sidebar.text_input("Patient ID")
mrn = st.sidebar.text_input("MRN")
encounter_type = st.sidebar.selectbox("Encounter Type", ["ER", "Inpatient", "Outpatient"])
encounter_date = st.sidebar.date_input("Encounter Date", datetime.today())
provider = st.sidebar.text_input("Provider Name")

st.sidebar.subheader("Insurance (Summary)")
ins_payer = st.sidebar.text_input("Payer (summary)")
ins_plan = st.sidebar.text_input("Plan Name (summary)")
ins_member_id = st.sidebar.text_input("Member ID (summary)")

# ---------------------------------------------------------
# BASIC FORM-HELP ASSISTANT (NON-AI)
# ---------------------------------------------------------
FAQ = [
    {"keys": ["allergy", "allergies"], "ans": "Record allergies in C. History → Allergies (type + reaction)."},
    {"keys": ["hpi", "present illness"], "ans": "Document HPI in C. History → History of Present Illness."},
    {"keys": ["medication", "meds", "drug"], "ans": "Use Medication History in C. History for current meds."},
    {"keys": ["vital", "bp", "hr", "spo2", "temperature"], "ans": "Enter vitals in D. Vitals section."},
    {"keys": ["assessment", "plan"], "ans": "Use F. Assessment & Plan for impression and management."},
]

def hanvion_ehr_assistant(question: str) -> str:
    q = question.lower()
    for item in FAQ:
        if any(k in q for k in item["keys"]):
            return item["ans"]
    return (
        "This helper can answer basic questions like:\n"
        "- Where do I enter allergies?\n"
        "- What is HPI?\n"
        "- Where do I enter medications?\n"
        "- Where do I enter vitals?\n"
        "Sections:\n"
        "A. Demographics  B. Admission & ICD-10  C. History\n"
        "D. Vitals  E. Examination  F. Assessment & Plan\n"
        "G. ADR Assistant  H. Insurance  I. Billing & Coding"
    )

st.sidebar.subheader("Form Help")
ehr_q = st.sidebar.text_input("Ask about where to enter something:")
if st.sidebar.button("Ask EHR Helper"):
    if ehr_q.strip():
        st.sidebar.info(hanvion_ehr_assistant(ehr_q))

# ---------------------------------------------------------
# ADR RISK ASSISTANT (AI)
# ---------------------------------------------------------
def get_age_from_dob(dob_value):
    if isinstance(dob_value, date):
        today = date.today()
        return today.year - dob_value.year - ((today.month, today.day) < (dob_value.month, dob_value.day))
    return None

def compute_adr_risk_level(age, num_meds, condition, bp_str, spo2):
    """
    Simple heuristic ADR risk classifier: returns ("Low"/"Moderate"/"High", score_int)
    """
    score = 0

    # Age
    if age is not None and age >= 65:
        score += 1

    # Polypharmacy
    if num_meds is not None and num_meds >= 5:
        score += 1

    # Condition
    if condition in ["Guarded", "Critical"]:
        score += 1

    # Blood pressure (try to parse systolic/diastolic)
    try:
        if bp_str and "/" in bp_str:
            parts = bp_str.replace(" ", "").split("/")
            systolic = int(parts[0])
            diastolic = int(parts[1])
            if systolic < 100 or diastolic < 60:
                score += 1
    except Exception:
        pass

    # SpO2
    try:
        if spo2 is not None and spo2 < 92:
            score += 1
    except Exception:
        pass

    if score <= 0:
        return "Low", score
    elif score <= 2:
        return "Moderate", score
    else:
        return "High", score

def run_adr_assistant(
    age,
    sex,
    meds,
    allergies,
    pmh,
    diagnosis,
    vitals,
    risk_level
):
    """
    Calls OpenAI to generate an ADR risk explanation.
    Requires OPENAI_API_KEY configured in env or Streamlit secrets.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = None

    if not api_key:
        return (
            "ADR Assistant is not configured.\n\n"
            "Please set OPENAI_API_KEY in environment variables or Streamlit secrets."
        )

    client = OpenAI(api_key=api_key)

    vitals_text = (
        f"BP: {vitals.get('bp')} mmHg, "
        f"HR: {vitals.get('hr')} bpm, "
        f"RR: {vitals.get('rr')} breaths/min, "
        f"Temp: {vitals.get('temp')} °C, "
        f"SpO2: {vitals.get('spo2')}%."
    )

    prompt = f"""
You are an AI assistant that helps clinicians reflect on potential adverse drug reactions (ADR).
You are NOT a doctor and must NOT give medical advice, diagnoses, or treatment.
You only highlight general risk patterns and monitoring suggestions in a conservative way.

Patient summary:
- Age: {age}
- Sex: {sex}
- Vitals: {vitals_text}
- Current medications (free text): {meds}
- Allergies: {allergies}
- Past medical history: {pmh}
- Working diagnosis / ICD-10: {diagnosis}
- Simple heuristic ADR risk level (from rules): {risk_level}

Tasks:
1. Briefly describe overall ADR risk level (Low / Moderate / High) with reasoning.
2. Mention possible risk factors (polypharmacy, age, organ impairment, hypotension, hypoxia, drug–allergy or drug–condition conflicts).
3. Mention only general monitoring suggestions (e.g., watch for GI upset, bleeding, CNS changes), not specific treatments.
4. Explicitly add a strong disclaimer at the end that this is NOT medical advice and must not replace clinical judgment.

Respond in under 250 words, use simple Markdown and short bullet points.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a cautious clinical decision-support explainer. You never provide medical advice or prescribe."
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
st.markdown(f"""
<div class="ehr-card">
    <span class="ehr-badge">Patient Encounter</span>
    <p class="small-text">
        <b>Patient ID:</b> {patient_id or "—"} |
        <b>MRN:</b> {mrn or "—"} |
        <b>Encounter Type:</b> {encounter_type} |
        <b>Provider:</b> {provider or "—"}
    </p>
</div>
""", unsafe_allow_html=True)

st.title("Hanvion Health – EHR Template")

# ---------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------
left, right = st.columns(2)

# ---------------- LEFT COLUMN ----------------
with left:
    # A. Demographics
    with st.expander("A. Demographics", expanded=True):
        full_name = st.text_input("Full Name")
        dob = st.date_input(
            "Date of Birth",
            value=date(1990, 1, 1),
            min_value=date(1930, 1, 1),
            max_value=date.today(),
        )
        sex = st.selectbox("Sex", ["", "Male", "Female", "Other"])
        phone = st.text_input("Phone Number")
        address = st.text_area("Address", height=60)

        height_cm = st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=0.0)
        weight_kg = st.number_input("Weight (kg)", min_value=0.0, max_value=300.0, value=0.0)
        bmi = None
        if height_cm > 0 and weight_kg > 0:
            bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
            st.caption(f"Calculated BMI: {bmi}")

    # B. Admission + ICD-10
    with st.expander("B. Admission and ICD-10 Search", expanded=True):
        chief_complaint = st.text_area("Chief Complaint")
        mode_of_arrival = st.selectbox("Mode of Arrival", ["Self", "Ambulance", "Transfer", "Referral"])

        st.markdown("**ICD-10 Search** (from CMS Section 111 file)")
        icd_query = st.text_input("Search ICD-10 (code or diagnosis text)")
        icd_results = search_icd10(icd_query)

        selected_icd = ""
        if icd_query:
            st.caption(f"Top 10 matches for: {icd_query}")
            st.dataframe(icd_results.head(10), use_container_width=True)
            if not icd_results.empty:
                code_col = "CODE" if "CODE" in icd_results.columns else icd_results.columns[0]
                desc_col = icd_results.columns[1]
                options = icd_results.head(50).apply(
                    lambda r: f"{r[code_col]} – {r[desc_col]}", axis=1
                )
                selected_icd = st.selectbox("Select Diagnosis", options)

        admission_dx = selected_icd or st.text_input("Admission Diagnosis (manual entry)")

    # C. History
    with st.expander("C. History and Screening", expanded=False):
        hpi = st.text_area("History of Present Illness")
        pmh = st.text_area("Past Medical History")
        meds = st.text_area("Medication History (name, dose, frequency)")
        allergies = st.text_area("Allergies (agent + reaction)")
        family_history = st.text_area("Family History")
        social_history = st.text_area("Social History (occupation, smoking, alcohol, etc.)")

# ---------------- RIGHT COLUMN ----------------
with right:
    # D. Vitals
    with st.expander("D. Vitals", expanded=True):
        st.caption("Examples: BP ≈120/80 mmHg, HR 60–100 bpm, RR 12–20 breaths/min, SpO₂ ≥ 94%, Temp ≈36.5–37.5°C")
        bp = st.text_input("Blood Pressure (mmHg)", placeholder="e.g. 120/80")
        hr = st.number_input("Heart Rate (bpm)", min_value=0, max_value=300, value=80)
        rr = st.number_input("Respiratory Rate (breaths/min)", min_value=0, max_value=80, value=16)
        temp_c = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, value=37.0)
        spo2 = st.number_input("SpO₂ (%)", min_value=0, max_value=100, value=98)
        pain_score = st.slider("Pain Score (0–10)", 0, 10, 0)

    # E. Physical Examination
    with st.expander("E. Physical Examination", expanded=False):
        pe_general = st.text_area("General Appearance")
        pe_systems = st.text_area("System-wise Exam (HEENT, CVS, RS, Abdomen, Neuro, Skin, etc.)")

    # F. Assessment & Plan
    with st.expander("F. Assessment and Plan", expanded=False):
        assessment = st.text_area("Assessment (working diagnosis, impression)")
        plan = st.text_area("Plan (labs, imaging, treatment, monitoring, consults)")
        patient_condition = st.selectbox("Overall Condition", ["", "Stable", "Guarded", "Critical"])

    # G. ADR Assistant
    adr_text = None
    adr_level = None
    adr_score = None
    with st.expander("G. ADR Risk Assistant (Experimental)", expanded=False):
        st.markdown(
            "This ADR assistant uses AI plus simple rules to highlight **possible** ADR risks "
            "based on age, vitals, medications, allergies, history, and diagnosis.\n\n"
            "**It is for educational and decision-support purposes only and is NOT medical advice.**"
        )
        age = get_age_from_dob(dob)
        med_list = [m.strip() for m in meds.split("\n") if m.strip()]
        num_meds = len(med_list) if meds.strip() else 0

        adr_can_run = True
        if not meds.strip():
            st.warning("Enter Medication History in section C before running ADR assistant.")
            adr_can_run = False

        if adr_can_run and st.button("Run ADR Analysis"):
            vitals_dict = {
                "bp": bp,
                "hr": hr,
                "rr": rr,
                "temp": temp_c,
                "spo2": spo2,
            }
            adr_level, adr_score = compute_adr_risk_level(
                age=age,
                num_meds=num_meds,
                condition=patient_condition,
                bp_str=bp,
                spo2=spo2,
            )
            with st.spinner("Analyzing possible ADR risks..."):
                adr_text = run_adr_assistant(
                    age=age,
                    sex=sex,
                    meds=meds,
                    allergies=allergies,
                    pmh=pmh,
                    diagnosis=admission_dx,
                    vitals=vitals_dict,
                    risk_level=adr_level,
                )

        # Show ADR badge + explanation if available
        if adr_level:
            if adr_level == "Low":
                st.markdown(f"<span class='adr-low'>ADR Risk: {adr_level}</span>", unsafe_allow_html=True)
            elif adr_level == "Moderate":
                st.markdown(f"<span class='adr-moderate'>ADR Risk: {adr_level}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='adr-high'>ADR Risk: {adr_level}</span>", unsafe_allow_html=True)

        if adr_text:
            st.markdown("---")
            st.markdown(adr_text)

    # H. Insurance Details
    with st.expander("H. Insurance and Coverage", expanded=False):
        ins_payer_full = st.text_input("Payer Name", value=ins_payer)
        ins_plan_full = st.text_input("Plan Name (e.g. Gold PPO)", value=ins_plan)
        ins_member_id_full = st.text_input("Member ID", value=ins_member_id)
        ins_group_number = st.text_input("Group Number")
        coverage_start = st.date_input("Coverage Start Date", value=date(2020, 1, 1))
        coverage_end = st.date_input("Coverage End Date", value=date(2100, 1, 1))
        copay_info = st.text_input("Copay / Coinsurance (e.g. $30 per visit)")
        insurance_notes = st.text_area("Insurance Notes (authorization, limitations, etc.)")

    # I. Billing & Coding
    with st.expander("I. Billing and Coding (CPT / HCPCS / ICD-10)", expanded=False):
        st.caption("Document high-level billing codes used for this encounter.")
        primary_cpt = st.text_input("Primary CPT Code (e.g. 99213)")
        secondary_cpt = st.text_input("Secondary CPT Code(s)")
        hcpcs_code = st.text_input("HCPCS Code (if applicable)")
        billing_icd_codes = st.text_area("ICD-10 Codes Used for Billing (one per line)")
        billing_notes = st.text_area("Billing Notes (e.g., modifiers, prior auth, medical necessity)")

# ---------------------------------------------------------
# SAVE ENCOUNTER (DEMO)
# ---------------------------------------------------------
st.markdown("---")
if st.button("Save Encounter (demo only)"):
    age_val = get_age_from_dob(dob)
    med_list = [m.strip() for m in meds.split("\n") if m.strip()]
    num_meds = len(med_list) if meds.strip() else 0
    adr_level_final, adr_score_final = compute_adr_risk_level(
        age=age_val,
        num_meds=num_meds,
        condition=patient_condition,
        bp_str=bp,
        spo2=spo2,
    )

    encounter = {
        "patient_id": patient_id,
        "mrn": mrn,
        "encounter_type": encounter_type,
        "encounter_date": str(encounter_date),
        "provider": provider,
        "full_name": full_name,
        "dob": str(dob),
        "age": age_val,
        "sex": sex,
        "phone": phone,
        "address": address,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "chief_complaint": chief_complaint,
        "mode_of_arrival": mode_of_arrival,
        "admission_dx": admission_dx,
        "hpi": hpi,
        "pmh": pmh,
        "meds": meds,
        "allergies": allergies,
        "family_history": family_history,
        "social_history": social_history,
        "bp": bp,
        "hr": hr,
        "rr": rr,
        "temp_c": temp_c,
        "spo2": spo2,
        "pain_score": pain_score,
        "exam_general": pe_general,
        "exam_systems": pe_systems,
        "assessment": assessment,
        "plan": plan,
        "patient_condition": patient_condition,
        "adr_risk_level": adr_level_final,
        "adr_risk_score": adr_score_final,
        "insurance_payer": ins_payer_full,
        "insurance_plan": ins_plan_full,
        "insurance_member_id": ins_member_id_full,
        "insurance_group_number": ins_group_number,
        "coverage_start": str(coverage_start),
        "coverage_end": str(coverage_end),
        "copay_info": copay_info,
        "insurance_notes": insurance_notes,
        "primary_cpt": primary_cpt,
        "secondary_cpt": secondary_cpt,
        "hcpcs_code": hcpcs_code,
        "billing_icd_codes": billing_icd_codes,
        "billing_notes": billing_notes,
    }

    # Basic insurance validation warnings
    warnings = []
    if not ins_payer_full:
        warnings.append("Payer Name is missing.")
    if not ins_member_id_full:
        warnings.append("Member ID is missing.")
    if coverage_end < coverage_start:
        warnings.append("Coverage End Date is before Coverage Start Date.")

    if warnings:
        st.warning("Insurance validation warnings:\n- " + "\n- ".join(warnings))

    st.success("Encounter captured (demo only, not stored in a database).")
    st.json(encounter)
    st.markdown(
    "[Open full Insurance Eligibility app](https://YOUR-ELIGIBILITY-APP-URL)  "
    "(Hosted separately on Streamlit Cloud)."
)
st.markdown(
    "[Open full RCM Billing Dashboard](https://YOUR-RCM-APP-URL)"
)

