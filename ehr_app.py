import streamlit as st
from datetime import datetime
from icd10_utils import search_icd10

# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health – Premium EHR",
    page_icon="🏥",
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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR – Encounter Context
# ---------------------------------------------------------
st.sidebar.title("🏥 Hanvion Health EHR")
st.sidebar.markdown("### 🧾 Encounter Context")

patient_id = st.sidebar.text_input("Patient ID")
mrn = st.sidebar.text_input("MRN")
encounter_type = st.sidebar.selectbox("Encounter Type", ["ER", "Inpatient", "Outpatient"])
encounter_date = st.sidebar.date_input("Encounter Date", datetime.today())
provider = st.sidebar.text_input("Provider Name")

# ---------------------------------------------------------
# HANVION HEALTH ASSISTANT
# ---------------------------------------------------------
FAQ = [
    {"keys":["allergy","allergies"], "ans":"Record allergies in **C. History → Allergies (type + reaction)**."},
    {"keys":["hpi","illness"], "ans":"Fill HPI in **C. History → History of Present Illness**."},
    {"keys":["vital","bp","hr","spo2","temperature"], "ans":"Enter vitals in **D. Vitals**."},
    {"keys":["med","medication","drug"], "ans":"Use **Medication History** in section C for current medications."},
    {"keys":["past medical","pmh"], "ans":"Chronic diseases go under **Past Medical History**."},
    {"keys":["family"], "ans":"Document hereditary risks in **Family History**."},
    {"keys":["social"], "ans":"Record lifestyle details in **Social History**."},
    {"keys":["exam","physical"], "ans":"Document findings in **E. Physical Examination**."},
    {"keys":["assessment","plan"], "ans":"Document diagnosis and treatment in **F. Assessment & Plan**."},
]

def hanvion_assistant(question: str) -> str:
    q = question.lower()
    for item in FAQ:
        if any(k in q for k in item["keys"]):
            return item["ans"]

    return (
        "I'm the **Hanvion Health Assistant**. I couldn't find an exact match.\n\n"
        "Try asking things like:\n"
        "- Where do I enter allergies?\n"
        "- What is HPI?\n"
        "- Where do I enter medications?\n"
        "- How do I fill vitals?"
    )

st.sidebar.markdown("### 💬 Hanvion Health Assistant")
user_q = st.sidebar.text_input("Ask something:")

if st.sidebar.button("Ask"):
    if user_q.strip():
        st.sidebar.success(hanvion_assistant(user_q))

# ---------------------------------------------------------
# HEADER CARD
# ---------------------------------------------------------
st.markdown(f"""
<div class="ehr-card">
    <span class="ehr-badge">Patient Encounter Overview</span>
    <p class="small-text">
        <b>Patient ID:</b> {patient_id or "—"} |
        <b>MRN:</b> {mrn or "—"} |
        <b>Encounter Type:</b> {encounter_type} |
        <b>Provider:</b> {provider or "—"}
    </p>
</div>
""", unsafe_allow_html=True)

st.title("Hanvion Health – Premium EHR Template")

# ---------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------
left, right = st.columns(2)

with left:
    with st.expander("🧍 A. Demographics", expanded=True):
        name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth")
        sex = st.selectbox("Sex", ["", "Male", "Female", "Other"])
        phone = st.text_input("Phone")
        address = st.text_area("Address")

    with st.expander("📥 B. Admission + ICD-10 Search", expanded=True):
        chief = st.text_area("Chief Complaint")
        mode = st.selectbox("Mode of Arrival", ["Self", "Ambulance", "Transfer", "Referral"])

        st.markdown("#### 🔍 ICD-10 Search")
        icd_query = st.text_input("Find ICD-10 (code or diagnosis text)")
        icd_results = search_icd10(icd_query)

        selected_icd = ""
        if icd_query:
            st.write(icd_results.head(10))
            if not icd_results.empty:
                selected_icd = st.selectbox(
                    "Select a Diagnosis",
                    icd_results["CODE"] + " – " + icd_results.iloc[:, 1]
                )

        admission_dx = selected_icd or st.text_input("Admission Diagnosis (Manual)")

    with st.expander("📚 C. History & Screening"):
        hpi = st.text_area("History of Present Illness")
        pmh = st.text_area("Past Medical History")
        meds = st.text_area("Medication History")
        allergies = st.text_area("Allergies (type + reaction)")
        family_history = st.text_area("Family History")
        social_history = st.text_area("Social History")

with right:
    with st.expander("❤️ D. Vitals", expanded=True):
        bp = st.text_input("Blood Pressure")
        hr = st.number_input("Heart Rate", 0, 300, value=80)
        rr = st.number_input("Respiratory Rate", 0, 80, value=16)
        temp = st.number_input("Temperature (°C)", 30.0, 45.0, value=37.0)
        spo2 = st.number_input("SpO₂ (%)", 0, 100, value=98)
        pain = st.slider("Pain Score", 0, 10, value=0)

    with st.expander("🩺 E. Physical Examination"):
        pe_general = st.text_area("General Appearance")
        pe_systems = st.text_area("System-wise Exam (HEENT, CVS, RS, Abd, Neuro, Skin, etc.)")

    with st.expander("🧠 F. Assessment & Plan"):
        assessment = st.text_area("Assessment (working diagnosis, overall impression)")
        plan = st.text_area("Plan (labs, imaging, treatment, consults, monitoring, prophylaxis, code status)")
        condition = st.selectbox("Patient Condition", ["Stable", "Guarded", "Critical"])

# ---------------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------------
st.markdown("---")

if st.button("Save Encounter"):
    encounter = {
        "patient_id": patient_id,
        "mrn": mrn,
        "encounter_type": encounter_type,
        "encounter_date": str(encounter_date),
        "provider": provider,
        "name": name,
        "dob": str(dob),
        "sex": sex,
        "chief": chief,
        "mode_of_arrival": mode,
        "admission_dx": admission_dx,
        "bp": bp,
        "hr": hr,
        "rr": rr,
        "temp": temp,
        "spo2": spo2,
        "pain": pain,
        "hpi": hpi,
        "pmh": pmh,
        "meds": meds,
        "allergies": allergies,
        "family_history": family_history,
        "social_history": social_history,
        "exam_general": pe_general,
        "exam_systems": pe_systems,
        "assessment": assessment,
        "plan": plan,
        "condition": condition,
    }

    st.success("Encounter saved (demo only).")
    st.json(encounter)

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("""
---
<p class="small-text">
Developed by <b>Hanvion Health</b> – Smart Clinical Documentation & ICD-10 Assistance.
</p>
""", unsafe_allow_html=True)
