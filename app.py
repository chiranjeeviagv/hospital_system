import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def init_db():
    """Initializes the database structure and safely syncs new specialty medicines."""
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    
    # 1. Appointments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            doctor TEXT NOT NULL,
            appt_date TEXT NOT NULL DEFAULT '',
            appt_time TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL
        )
    ''')
    
    cursor.execute("PRAGMA table_info(appointments)")
    columns = [info[1] for info in cursor.fetchall()]
    if "appt_date" not in columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN appt_date TEXT NOT NULL DEFAULT ''")
    if "appt_time" not in columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN appt_time TEXT NOT NULL DEFAULT ''")
    
    # 2. Consultations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            symptoms TEXT NOT NULL,
            diagnosed_disease TEXT NOT NULL,
            prescription TEXT NOT NULL,
            notes TEXT,
            consultation_date TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM appointments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO appointments (patient_name, doctor, appt_date, appt_time, status) VALUES ('Rahul Sharma', 'Dr. Verma (Cardiology)', '2026-11-08', '10:00 AM', 'Confirmed')")
        cursor.execute("INSERT INTO appointments (patient_name, doctor, appt_date, appt_time, status) VALUES ('Priya Patel', 'Dr. Reddy (Pediatrics)', '2026-11-08', '02:30 PM', 'Pending')")

    # 3. Pharmacy Stock Inventory Table (INSERT OR IGNORE safely updates live DBs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            stock_qty INTEGER NOT NULL,
            min_required INTEGER NOT NULL
        )
    ''')
    
    medicines = [
        ('Paracetamol 650mg', 'Analgesic / Antipyretic', 120, 30),
        ('Artemether-Lumefantrine', 'Antimalarial', 15, 10),
        ('Dextromethorphan Syr.', 'Antitussive Cough Syrup', 45, 15),
        ('Budesonide Inhaler', 'Bronchodilator', 8, 10),
        ('Telmisartan 40mg', 'Antihypertensive', 200, 50),
        ('Nitroglycerin 0.5mg', 'Antianginal Vasodilator', 25, 20),
        ('Pantoprazole 40mg', 'Antacid / PPI', 350, 100),
        ('Rabeprazole Combo', 'Antacid / GERD Support', 180, 40),
        ('Naproxen 500mg', 'NSAID / Anti-inflammatory', 90, 30),
        ('Febuxostat 40mg', 'Uric Acid Lowering Therapy', 60, 20),
        ('Sumatriptan 50mg', 'Antimigraine / Triptan', 75, 20),
        ('Levetiracetam 500mg', 'Anticonvulsant', 110, 30),
        ('Pregabalin 75mg', 'Neuropathic Pain Agent', 95, 25),
        ('Moxifloxacin Eye Drops', 'Ophthalmic Antibiotic', 40, 15),
        ('Carboxymethylcellulose Drops', 'Ocular Lubricant', 65, 20),
        ('Timolol 0.5% Eye Drops', 'Antiglaucoma Agent', 30, 10),
        ('Sertraline 50mg', 'SSRI Antidepressant', 140, 40),
        ('Escitalopram 10mg', 'SSRI Anxiolytic', 160, 40),
        ('Melatonin 3mg', 'Sleep Regulator', 85, 25)
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO inventory (medicine_name, category, stock_qty, min_required) VALUES (?, ?, ?, ?)",
        medicines
    )
    
    conn.commit()
    conn.close()

init_db()

# --- 2. ENGINE MAPS ---
SPECIALTY_DOCTORS = [
    "Dr. Sharma (General Medicine)",
    "Dr. Verma (Cardiology)",
    "Dr. Reddy (Pediatrics)",
    "Dr. Sen (Neurology)",
    "Dr. Nair (Ophthalmology)",
    "Dr. Rao (Psychiatry)"
]

SYMPTOM_VARIANTS = [
    "High Fever & Chills",
    "Chronic Cough & Shortness of Breath",
    "Severe Abdominal Pain & Acid Reflux",
    "Acute Joint Pain & Swelling",
    "Chest Pain & Palpitations",
    "Severe Throbbing Headache & Aura",
    "Sudden Dizziness, Numbness & Seizure Episodes",
    "Blurred Vision, Eye Redness & Irritation",
    "Gradual Vision Loss & Eye Pressure",
    "Persistent Low Mood, Fatigue & Loss of Interest",
    "Excessive Worry, Panic Attacks & Insomnia"
]

DISEASE_ENGINE = {
    "High Fever & Chills": ["Viral Influenza", "Malaria Parasitism"],
    "Chronic Cough & Shortness of Breath": ["Acute Bronchitis", "Bronchial Asthma"],
    "Severe Abdominal Pain & Acid Reflux": ["Acute Gastritis", "Gastroesophageal Reflux Disease (GERD)"],
    "Acute Joint Pain & Swelling": ["Rheumatoid Arthritis", "Acute Gouty Arthritis"],
    "Chest Pain & Palpitations": ["Essential Hypertension", "Angina Pectoris"],
    "Severe Throbbing Headache & Aura": ["Chronic Migraine", "Tension Headache"],
    "Sudden Dizziness, Numbness & Seizure Episodes": ["Focal Epilepsy", "Peripheral Neuropathy"],
    "Blurred Vision, Eye Redness & Irritation": ["Bacterial Conjunctivitis", "Dry Eye Syndrome"],
    "Gradual Vision Loss & Eye Pressure": ["Open-Angle Glaucoma", "Age-Related Cataract"],
    "Persistent Low Mood, Fatigue & Loss of Interest": ["Major Depressive Disorder", "Persistent Depressive Disorder"],
    "Excessive Worry, Panic Attacks & Insomnia": ["Generalized Anxiety Disorder (GAD)", "Primary Insomnia"]
}

PRESCRIPTION_SUGGESTIONS = {
    "Viral Influenza": "Symptomatic relief: Tab. Paracetamol 650mg TDS, Hydration therapy, Rest.",
    "Malaria Parasitism": "Antimalarial course: Tab. Artemether-Lumefantrine regimen as directed.",
    "Acute Bronchitis": "Cough suppressant: Syr. Dextromethorphan 10ml TDS & Warm saline gargles.",
    "Bronchial Asthma": "Maintenance Inhaler: Budesonide + Formoterol puffs twice daily as needed.",
    "Essential Hypertension": "Antihypertensive: Tab. Telmisartan 40mg OD mornings, monitor BP daily.",
    "Angina Pectoris": "Cardioprotective: Tab. Nitroglycerin 0.5mg sublingual SOS, Tab. Aspirin 75mg OD.",
    "Acute Gastritis": "Antacid control: Cap. Pantoprazole 40mg OD before breakfast for 7 days.",
    "Gastroesophageal Reflux Disease (GERD)": "H2 Blocker combo: Cap. Rabeprazole 20mg + Domperidone 30mg SR before meals.",
    "Rheumatoid Arthritis": "NSAID Management: Tab. Naproxen 500mg BD after meals, Tab. Leflunomide 20mg.",
    "Acute Gouty Arthritis": "Uric Acid Lowering: Tab. Febuxostat 40mg OD, Tab. Colchicine 0.5mg SOS for pain.",
    "Chronic Migraine": "Acute relief: Tab. Sumatriptan 50mg SOS at onset; Prophylaxis: Tab. Propranolol 40mg OD.",
    "Tension Headache": "Analgesic: Tab. Paracetamol 650mg + Caffeine combination SOS, stress & posture therapy.",
    "Focal Epilepsy": "Anticonvulsant: Tab. Levetiracetam 500mg BD, avoid sleep deprivation and driving.",
    "Peripheral Neuropathy": "Neuro-support: Cap. Pregabalin 75mg + Methylcobalamin 1500mcg OD at bedtime.",
    "Bacterial Conjunctivitis": "Topical Antibiotic: Moxifloxacin 0.5% Eye Drops, 1 drop QID for 5 days.",
    "Dry Eye Syndrome": "Ocular Lubricant: Carboxymethylcellulose 0.5% Eye Drops, 1-2 drops QID.",
    "Open-Angle Glaucoma": "IOP Lowering: Timolol Maleate 0.5% Eye Drops, 1 drop BD in affected eye(s).",
    "Age-Related Cataract": "Pre-op prep & anti-glare glasses; schedule phacoemulsification surgery evaluation.",
    "Major Depressive Disorder": "SSRI Therapy: Tab. Sertraline 50mg OD after breakfast + Cognitive Behavioral Therapy (CBT).",
    "Persistent Depressive Disorder": "SSRI Maintenance: Tab. Escitalopram 10mg OD mornings + weekly psychotherapy.",
    "Generalized Anxiety Disorder (GAD)": "Anxiolytic / SSRI: Tab. Escitalopram 10mg OD + breathing & mindfulness exercises.",
    "Primary Insomnia": "Sleep Hygiene protocol + Tab. Melatonin 3mg 30 mins before bedtime for 14 days."
}

# --- 3. PDF GENERATION UTILITY ---
def build_prescription_pdf(name, disease, symptoms, Rx, notes):
    """Generates a professional medical layout in-memory and returns bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Corporate Clinical Palette Layout Styles
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], alignment=TA_CENTER, textColor='#1e3d59', fontSize=24, spaceAfter=6)
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], alignment=TA_CENTER, textColor='#17b978', fontSize=10, spaceAfter=20)
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=11, leading=16, spaceAfter=8)
    section_title = ParagraphStyle('SecTitle', parent=styles['Heading3'], textColor='#1e3d59', fontSize=14, spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=11, leading=16, leftIndent=10)
    
    story = []
    
    # Clinic Banner Heading
    story.append(Paragraph("🏥 LIFELINE HEALTHCARE MEDICAL CENTER", title_style))
    story.append(Paragraph("E-Health Portal Automated Prescription Record System", sub_style))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
    story.append(Paragraph(f"<b>Patient Name:</b> {name}", meta_style))
    story.append(Paragraph("<hr/>", meta_style))
    
    # Clinical Analysis Parameters
    story.append(Paragraph("Clinical Diagnostics Summary", section_title))
    story.append(Paragraph(f"<b>Presenting Symptoms:</b> {symptoms}", body_style))
    story.append(Paragraph(f"<b>Inferred Final Diagnosis:</b> {disease}", body_style))
    story.append(Spacer(1, 10))
    
    # Pharmacy Orders
    story.append(Paragraph("💊 Prescribed Medications (Rx Options)", section_title))
    story.append(Paragraph(Rx.replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 10))
    
    # Professional Advice
    story.append(Paragraph("📝 Lifestyle Advice & Clinical Notes", section_title))
    story.append(Paragraph(notes if notes else "No additional restrictions specified.", body_style))
    
    # Sign off placeholder
    story.append(Spacer(1, 40))
    story.append(Paragraph("<i>Authorized Signature (Digitally Validated Record)</i>", ParagraphStyle('Sign', parent=styles['Normal'], alignment=TA_LEFT, fontSize=9)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 4. SECURE SIDEBAR NAVIGATION ENGINE ---
st.set_page_config(page_title="Lifeline HMS Pro", page_icon="🏥", layout="wide")

st.sidebar.title("🏥 Lifeline HMS Pro")
st.sidebar.markdown("---")

user_role = st.sidebar.selectbox(
    "Switch User View:", 
    ["Patient Portal", "Doctor Dashboard", "Pharmacy Inventory", "Admin Analytics"],
    key="main_role_selector"
)

if user_role in ["Doctor Dashboard", "Pharmacy Inventory", "Admin Analytics"]:
    authenticated = False
    st.sidebar.markdown(f"#### 🔐 Secure {user_role} Login")
    password_input = st.sidebar.text_input("Enter Access Password:", type="password", key=f"pwd_{user_role}")
    
    role_passwords = {
        "Doctor Dashboard": "doctor123",
        "Pharmacy Inventory": "pharma123",
        "Admin Analytics": "admin123"
    }
    
    if password_input == role_passwords[user_role]:
        authenticated = True
        st.sidebar.success("🔒 Access Granted")
    elif password_input != "":
        st.sidebar.error("❌ Invalid Access Token")
else:
    authenticated = True

# --- 5. SECURE VIEW LOGIC RUNTIME ---
if not authenticated:
    st.title("🔒 Restricted Clinical Access Area")
    st.warning("Please provide the correct authorization credentials in the left sidebar to unlock this terminal page dashboard view.")
    st.info("💡 Hint for testing: Use **doctor123**, **pharma123**, or **admin123** based on your selection.")

else:
    # PAGE 1: PATIENT PORTAL
    if user_role == "Patient Portal":
        st.title("🗓️ Patient Appointment Booking")
        st.write("Fill out the interactive form below to book a clinical slot.")
        
        with st.form("appointment_form", clear_on_submit=True):
            st.subheader("Enter Booking Details")
            patient_name = st.text_input("Full Patient Name", placeholder="e.g. Rahul Sharma")
            doctor_choice = st.selectbox("Select Department Specialist", SPECIALTY_DOCTORS)
            
            col_date, col_time = st.columns(2)
            with col_date:
                appointment_date = st.date_input("Select Appointment Date", min_value=datetime.today().date())
            with col_time:
                appointment_time = st.selectbox("Select Available Time Slot", ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM"])
                
            submit_button = st.form_submit_button("Confirm Appointment Slot")
            
            if submit_button:
                if patient_name.strip() == "":
                    st.error("Please enter a valid patient name to book an appointment.")
                else:
                    conn = sqlite3.connect("hospital.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO appointments (patient_name, doctor, appt_date, appt_time, status) VALUES (?, ?, ?, ?, ?)",
                        (patient_name, doctor_choice, str(appointment_date), appointment_time, "Pending")
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 Success! Appointment requested with {doctor_choice} on {appointment_date} at {appointment_time}.")

        st.markdown("---")
        st.subheader("📋 Active Registered Requests")
        conn = sqlite3.connect("hospital.db")
        df = pd.read_sql_query("SELECT id AS ID, patient_name AS [Patient Name], doctor AS Doctor, appt_date AS [Scheduled Date], appt_time AS [Time Slot], status AS Status FROM appointments", conn)
        conn.close()
        st.dataframe(df, use_container_width=True, hide_index=True)

    # PAGE 2: DOCTOR DASHBOARD
    elif user_role == "Doctor Dashboard":
        st.title("🩺 Medical Practitioner Workspace")
        
        st.subheader("1. Active Operational Schedule")
        selected_dept = st.selectbox("Filter Schedule by Specialist / Department:", ["All Departments"] + SPECIALTY_DOCTORS)
        
        conn = sqlite3.connect("hospital.db")
        df = pd.read_sql_query("SELECT id AS ID, patient_name AS [Patient Name], doctor AS Doctor, appt_date AS [Date], appt_time AS [Slot], status AS Status FROM appointments", conn)
        conn.close()
        
        if selected_dept != "All Departments":
            df = df[df["Doctor"] == selected_dept]
        
        if not df.empty:
            edited_df = st.data_editor(
                df,
                column_config={"Status": st.column_config.SelectboxColumn("Appointment Status", options=["Pending", "Confirmed", "Completed", "Cancelled"], required=True)},
                disabled=["ID", "Patient Name", "Doctor", "Date", "Slot"],
                use_container_width=True,
                key="doctor_grid",
                hide_index=True
            )
            
            if st.button("💾 Save Schedule Status Updates", type="secondary"):
                conn = sqlite3.connect("hospital.db")
                cursor = conn.cursor()
                for index, row in edited_df.iterrows():
                    cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (row["Status"], int(row["ID"])))
                conn.commit()
                conn.close()
                st.success("Patient schedules synchronized!")
                st.rerun()

            st.markdown("---")
            st.subheader("2. Real-time Patient Diagnostics & Prescription Module")
            
            patient_list = df["Patient Name"].unique().tolist()
            selected_patient = st.selectbox("Select Patient to Diagnose / View EHR History:", patient_list)
            
            conn = sqlite3.connect("hospital.db")
            history_df = pd.read_sql_query("SELECT consultation_date AS [Date], symptoms AS [Symptoms], diagnosed_disease AS [Diagnosis], prescription AS [Prescription Summary], notes AS [Doctor Notes] FROM consultations WHERE patient_name = ?", conn, params=(selected_patient,))
            conn.close()
            
            st.markdown("##### 📜 Previous E-Health Consultation Logs")
            if not history_df.empty:
                st.warning(f"🔄 Revisit Detected! Found {len(history_df)} record(s) for {selected_patient}:")
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else:
                st.info("🆕 Fresh Registration: No historical entries found.")
                
            st.markdown("---")
            st.markdown(f"##### ✍️ Create New Clinical Entry for {selected_patient}")
            
            col_diag, col_presc = st.columns(2)
            with col_diag:
                st.info("🧪 Step A: Choose Presenting Symptoms")
                chosen_symptom = st.selectbox("Observed Variant Pathway:", SYMPTOM_VARIANTS)
                available_diseases = DISEASE_ENGINE[chosen_symptom]
                chosen_disease = st.selectbox("Inferred Medical Condition Variant:", available_diseases)
                
            with col_presc:
                st.success("💊 Step B: Smart Prescriptive Suggestions Engine")
                suggested_rx = PRESCRIPTION_SUGGESTIONS[chosen_disease]
                st.caption("AI Clinical Decision Support Recommendation:")
                st.code(suggested_rx, language="markdown")
                final_prescription = st.text_area("Finalized Pharmacy Prescription:", value=suggested_rx, height=70)
                clinical_notes = st.text_input("Additional Case Notes / Lifestyle advice:", placeholder="e.g. Bedrest for 3 days")
                
            col_btn1, _ = st.columns(2)
            with col_btn1:
                log_submitted = st.button("🚀 Log & Finalize Case", type="primary")
                
            if log_submitted:
                conn = sqlite3.connect("hospital.db")
                cursor = conn.cursor()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute(
                    'INSERT INTO consultations (patient_name, symptoms, diagnosed_disease, prescription, notes, consultation_date) VALUES (?, ?, ?, ?, ?, ?)',
                    (selected_patient, chosen_symptom, chosen_disease, final_prescription, clinical_notes, current_time)
                )
                cursor.execute("UPDATE appointments SET status = 'Completed' WHERE patient_name = ?", (selected_patient,))
                medicine_keywords = {
                    "Viral Influenza": "Paracetamol 650mg",
                    "Malaria Parasitism": "Artemether-Lumefantrine",
                    "Acute Bronchitis": "Dextromethorphan Syr.",
                    "Bronchial Asthma": "Budesonide Inhaler",
                    "Essential Hypertension": "Telmisartan 40mg",
                    "Angina Pectoris": "Nitroglycerin 0.5mg",
                    "Acute Gastritis": "Pantoprazole 40mg",
                    "Gastroesophageal Reflux Disease (GERD)": "Rabeprazole Combo",
                    "Rheumatoid Arthritis": "Naproxen 500mg",
                    "Acute Gouty Arthritis": "Febuxostat 40mg",
                    "Chronic Migraine": "Sumatriptan 50mg",
                    "Tension Headache": "Paracetamol 650mg",
                    "Focal Epilepsy": "Levetiracetam 500mg",
                    "Peripheral Neuropathy": "Pregabalin 75mg",
                    "Bacterial Conjunctivitis": "Moxifloxacin Eye Drops",
                    "Dry Eye Syndrome": "Carboxymethylcellulose Drops",
                    "Open-Angle Glaucoma": "Timolol 0.5% Eye Drops",
                    "Major Depressive Disorder": "Sertraline 50mg",
                    "Persistent Depressive Disorder": "Escitalopram 10mg",
                    "Generalized Anxiety Disorder (GAD)": "Escitalopram 10mg",
                    "Primary Insomnia": "Melatonin 3mg"
                }

                target_medicine = medicine_keywords.get(chosen_disease)
                if target_medicine:
                    cursor.execute(
                        "UPDATE inventory SET stock_qty = MAX(0, stock_qty - 1) WHERE medicine_name = ?",
                        (target_medicine,)
                    )

                conn.commit()
                conn.close()

                st.session_state["pdf_ready"] = (selected_patient, chosen_disease, chosen_symptom, final_prescription, clinical_notes)
                st.toast("Case logged into medical database charts!")
                st.rerun()
 
            # Fixed tuple index check so PDF button renders reliably
        if "pdf_ready" in st.session_state and st.session_state["pdf_ready"][0] == selected_patient:
                p_name, p_dis, p_sym, p_rx, p_note = st.session_state["pdf_ready"]
                pdf_bytes = build_prescription_pdf(p_name, p_dis, p_sym, p_rx, p_note)
                st.markdown("---")
                st.success("📄 Professional Medical Prescription Document Compiled Successfully!")
                st.download_button(
                    label="📥 Download Official Printed PDF Prescription",
                    data=pdf_bytes,
                    file_name=f"Prescription_{p_name.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("No active appointments registered for this selection.")

    # PAGE 3: PHARMACY INVENTORY
    elif user_role == "Pharmacy Inventory":
        st.title("📦 Medical Dispensary & Pharmacy Stock Management")
        st.write("Track available medicine reserves, check alerts for low stock levels, and update inventories.")
        
        conn = sqlite3.connect("hospital.db")
        df_inv = pd.read_sql_query("SELECT id AS ID, medicine_name AS [Medicine Name], category AS [Therapeutic Class], stock_qty AS [Current Stock Units], min_required AS [Safety Threshold Limit] FROM inventory", conn)
        conn.close()
        
        low_stock_items = df_inv[df_inv["Current Stock Units"] <= df_inv["Safety Threshold Limit"]]
        
        col_stat1, col_stat2 = st.columns(2)
        col_stat1.metric("Total Maintained Formulas", len(df_inv))
        col_stat2.metric("Critical Low Reorder Alerts", len(low_stock_items), delta=-len(low_stock_items) if len(low_stock_items) > 0 else 0, delta_color="inverse")
        
        if not low_stock_items.empty:
            st.error("⚠️ Critical Shortage Warning: The following formulas have fallen below safety limits!")
            st.dataframe(low_stock_items, use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.subheader("Live Inventory Editor")
        
        edited_inv = st.data_editor(
            df_inv,
            disabled=["ID", "Medicine Name", "Therapeutic Class"],
            use_container_width=True,
            hide_index=True,
            key="inventory_editor"
        )
        
        if st.button("💾 Apply & Update Inventory Balances", type="primary"):
            conn = sqlite3.connect("hospital.db")
            cursor = conn.cursor()
            for index, row in edited_inv.iterrows():
                cursor.execute("UPDATE inventory SET stock_qty = ?, min_required = ? WHERE id = ?", (int(row["Current Stock Units"]), int(row["Safety Threshold Limit"]), int(row["ID"])))
            conn.commit()
            conn.close()
            st.success("Pharmacy inventory tracking log changes successfully committed!")
            st.rerun()

    # PAGE 4: ADMIN ANALYTICS
    elif user_role == "Admin Analytics":
        st.title("📊 Hospital Operational Control Panel")
        conn = sqlite3.connect("hospital.db")
        df_app = pd.read_sql_query("SELECT * FROM appointments", conn)
        df_cons = pd.read_sql_query("SELECT * FROM consultations", conn)
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Patient Bookings", len(df_app))
        col2.metric("Awaiting Approval", len(df_app[df_app["status"] == "Pending"]))
        col3.metric("Completed Treatments", len(df_app[df_app["status"] == "Completed"]))
        st.markdown("---")
        if not df_cons.empty:
            st.subheader("📈 Case Allocation by Diagnosed Conditions")
            chart_data = df_cons["diagnosed_disease"].value_counts().reset_index()
            chart_data.columns = ["Disease Variant", "Total Incidences"]
            fig = px.bar(
                chart_data, 
                x="Disease Variant", 
                y="Total Incidences", 
                color="Disease Variant", 
                title="Epidemiological Variant Workload Distribution Map", 
                text_auto=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No disease data logged out via the Doctor Workspace yet to graph out distribution metrics.")

        