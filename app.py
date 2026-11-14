import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ==========================================
# 0. PAGE CONFIG & CUSTOM UI STYLING
# ==========================================

st.set_page_config(page_title="Patient Health Management System", page_icon="🏥", layout="wide")

def apply_custom_ui():
    st.markdown(
        """
        <style>
        /* 1. Background Graphic: Soft Clinical Gradient + Subtle Medical Cross SVG */
        .stApp {
            background-color: #f0f4f8;
            background-image: 
                radial-gradient(at 0% 0%, rgba(23, 185, 120, 0.14) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(30, 61, 89, 0.14) 0px, transparent 50%),
                url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://w3.org fill='none' fill-rule='evenodd'%3E%3Cg fill='%231e3d59' fill-opacity='0.045'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            background-attachment: fixed;
        }

        /* 2. Frosted Glass Card Containers */
        [data-testid="stForm"], [data-testid="stDataFrame"], [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.90);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 18px;
            border: 1px solid rgba(30, 61, 89, 0.12);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        }

        /* 3. Sidebar Styling & Alert Readability Fix */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3d59 0%, #162e44 100%);
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] input {
            color: #1e3d59 !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] * {
            color: #162e44 !important;
        }

        /* 4. Custom Hero Banner */
        .hero-banner {
            background: linear-gradient(135deg, #1e3d59 0%, #17b978 100%);
            padding: 24px 30px;
            border-radius: 14px;
            color: white;
            margin-bottom: 24px;
            box-shadow: 0 8px 20px rgba(30, 61, 89, 0.15);
        }
        .hero-banner h1 {
            color: white !important;
            margin: 0;
            font-size: 1.9rem;
        }
        .hero-banner p {
            color: rgba(255, 255, 255, 0.92);
            margin: 6px 0 0 0;
            font-size: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_hero(title, subtitle):
    st.markdown(
        f"""
        <div class="hero-banner">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

apply_custom_ui()
# ==========================================
# 1. CORE DATA STRUCTURE ENGINE MAPS
# ==========================================

SPECIALTY_CARDS = [
    {"dept": "Pediatrics", "doctor": "Dr. Pradip (Pediatrics)", "icon": "🧸", "desc": "Child & adolescent healthcare (Ages 0–15)"},
    {"dept": "General Medicine", "doctor": "Dr. Sharma (General Medicine)", "icon": "🩺", "desc": "Fever, infections, respiratory & primary care"},
    {"dept": "ENT", "doctor": "Dr. Rao (ENT)", "icon": "👂", "desc": "Ear, nose, throat & sinus treatments"},
    {"dept": "Neurology", "doctor": "Dr. Sen (Neurology)", "icon": "🧠", "desc": "Migraines, seizures & nervous system care"},
    {"dept": "Ophthalmology", "doctor": "Dr. Manish (Ophthalmology)", "icon": "👁️", "desc": "Vision testing, eye infections & glaucoma"},
    {"dept": "Psychology", "doctor": "Dr. Meera (Psychology)", "icon": "💬", "desc": "Counseling, behavioral therapy & stress management"},
    {"dept": "Psychiatry", "doctor": "Dr. Radha (Psychiatry)", "icon": "🌿", "desc": "Clinical mental health & medication management"},
    {"dept": "Gynecology", "doctor": "Dr. Anjali (Gynecology)", "icon": "🌸", "desc": "Women's reproductive health & maternity care"}
]

SPECIALTY_DOCTORS = [item["doctor"] for item in SPECIALTY_CARDS]

ALL_TIME_SLOTS = (
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM"
)

SYMPTOM_VARIANTS = [
    "High Fever & Chills",
    "Chronic Cough & Shortness of Breath",
    "Severe Abdominal Pain & Acid Reflux",
    "Acute Joint Pain & Swelling",
    "Earache, Sinus Congestion & Sore Throat",
    "Hearing Loss, Tinnitus & Vertigo",
    "Severe Throbbing Headache & Aura",
    "Sudden Dizziness, Numbness & Seizure Episodes",
    "Blurred Vision, Eye Redness & Irritation",
    "Gradual Vision Loss & Eye Pressure",
    "Work Burnout, Relationship Stress & Grief",
    "Persistent Low Mood, Fatigue & Loss of Interest",
    "Excessive Worry, Panic Attacks & Insomnia",
    "Irregular Menstrual Cycles & Pelvic Pain",
    "Prenatal Checkup & Hormonal Imbalance"
]

SYMPTOM_TO_DOCTOR_MAP = {
    "High Fever & Chills": "Dr. Sharma (General Medicine)",
    "Chronic Cough & Shortness of Breath": "Dr. Sharma (General Medicine)",
    "Severe Abdominal Pain & Acid Reflux": "Dr. Sharma (General Medicine)",
    "Acute Joint Pain & Swelling": "Dr. Sharma (General Medicine)",
    "Earache, Sinus Congestion & Sore Throat": "Dr. Rao (ENT)",
    "Hearing Loss, Tinnitus & Vertigo": "Dr. Rao (ENT)",
    "Severe Throbbing Headache & Aura": "Dr. Sen (Neurology)",
    "Sudden Dizziness, Numbness & Seizure Episodes": "Dr. Sen (Neurology)",
    "Blurred Vision, Eye Redness & Irritation": "Dr. Manish (Ophthalmology)",
    "Gradual Vision Loss & Eye Pressure": "Dr. Manish (Ophthalmology)",
    "Work Burnout, Relationship Stress & Grief": "Dr. Meera (Psychology)",
    "Persistent Low Mood, Fatigue & Loss of Interest": "Dr. Radha (Psychiatry)",
    "Excessive Worry, Panic Attacks & Insomnia": "Dr. Radha (Psychiatry)",
    "Irregular Menstrual Cycles & Pelvic Pain": "Dr. Anjali (Gynecology)",
    "Prenatal Checkup & Hormonal Imbalance": "Dr. Anjali (Gynecology)"
}

DISEASE_ENGINE = {
    "High Fever & Chills": ["Viral Influenza", "Malaria Parasitism"],
    "Chronic Cough & Shortness of Breath": ["Acute Bronchitis", "Bronchial Asthma"],
    "Severe Abdominal Pain & Acid Reflux": ["Acute Gastritis", "Gastroesophageal Reflux Disease (GERD)"],
    "Acute Joint Pain & Swelling": ["Rheumatoid Arthritis", "Acute Gouty Arthritis"],
    "Earache, Sinus Congestion & Sore Throat": ["Acute Sinusitis", "Acute Tonsillitis"],
    "Hearing Loss, Tinnitus & Vertigo": ["Benign Paroxysmal Positional Vertigo (BPPV)", "Otitis Media"],
    "Severe Throbbing Headache & Aura": ["Chronic Migraine", "Tension Headache"],
    "Sudden Dizziness, Numbness & Seizure Episodes": ["Focal Epilepsy", "Peripheral Neuropathy"],
    "Blurred Vision, Eye Redness & Irritation": ["Bacterial Conjunctivitis", "Dry Eye Syndrome"],
    "Gradual Vision Loss & Eye Pressure": ["Open-Angle Glaucoma", "Age-Related Cataract"],
    "Work Burnout, Relationship Stress & Grief": ["Acute Stress Reaction", "Adjustment Disorder"],
    "Persistent Low Mood, Fatigue & Loss of Interest": ["Major Depressive Disorder", "Persistent Depressive Disorder"],
    "Excessive Worry, Panic Attacks & Insomnia": ["Generalized Anxiety Disorder (GAD)", "Primary Insomnia"],
    "Irregular Menstrual Cycles & Pelvic Pain": ["Polycystic Ovary Syndrome (PCOS)", "Primary Dysmenorrhea"],
    "Prenatal Checkup & Hormonal Imbalance": ["Routine Antenatal Care", "Perimenopausal Syndrome"]
}

PRESCRIPTION_SUGGESTIONS = {
    "Viral Influenza": "Symptomatic relief: Tab. Paracetamol 650mg TDS, Hydration therapy, Rest.",
    "Malaria Parasitism": "Antimalarial course: Tab. Artemether-Lumefantrine regimen as directed.",
    "Acute Bronchitis": "Cough suppressant: Syr. Dextromethorphan 10ml TDS & Warm saline gargles.",
    "Bronchial Asthma": "Maintenance Inhaler: Budesonide + Formoterol puffs twice daily as needed.",
    "Acute Gastritis": "Antacid control: Cap. Pantoprazole 40mg OD before breakfast for 7 days.",
    "Gastroesophageal Reflux Disease (GERD)": "H2 Blocker combo: Cap. Rabeprazole 20mg + Domperidone 30mg SR before meals.",
    "Rheumatoid Arthritis": "NSAID Management: Tab. Naproxen 500mg BD after meals, Tab. Leflunomide 20mg.",
    "Acute Gouty Arthritis": "Uric Acid Lowering: Tab. Febuxostat 40mg OD, Tab. Colchicine 0.5mg SOS for pain.",
    "Acute Sinusitis": "Decongestant & Steam: Fluticasone Nasal Spray 2 puffs BD + Steam inhalation.",
    "Acute Tonsillitis": "Antibiotic & Gargle: Tab. Amoxicillin-Clavulanate 625mg BD for 5 days + Betadine gargles.",
    "Benign Paroxysmal Positional Vertigo (BPPV)": "Vestibular Suppressant: Tab. Betahistine 16mg BD + Epley maneuver exercises.",
    "Otitis Media": "Otic Drops & Analgesic: Ciprofloxacin Ear Drops 3 drops TDS + Tab. Ibuprofen 400mg SOS.",
    "Chronic Migraine": "Acute relief: Tab. Sumatriptan 50mg SOS at onset; Prophylaxis: Tab. Propranolol 40mg OD.",
    "Tension Headache": "Analgesic: Tab. Paracetamol 650mg + Caffeine combination SOS, stress & posture therapy.",
    "Focal Epilepsy": "Anticonvulsant: Tab. Levetiracetam 500mg BD, avoid sleep deprivation and driving.",
    "Peripheral Neuropathy": "Neuro-support: Cap. Pregabalin 75mg + Methylcobalamin 1500mcg OD at bedtime.",
    "Bacterial Conjunctivitis": "Topical Antibiotic: Moxifloxacin 0.5% Eye Drops, 1 drop QID for 5 days.",
    "Dry Eye Syndrome": "Ocular Lubricant: Carboxymethylcellulose 0.5% Eye Drops, 1-2 drops QID.",
    "Open-Angle Glaucoma": "IOP Lowering: Timolol Maleate 0.5% Eye Drops, 1 drop BD in affected eye(s).",
    "Age-Related Cataract": "Pre-op prep & anti-glare glasses; schedule phacoemulsification surgery evaluation.",
    "Acute Stress Reaction": "Psychotherapy: 4 weekly Cognitive Behavioral Counseling sessions + guided relaxation.",
    "Adjustment Disorder": "Supportive Therapy: Bi-weekly psychotherapy + structured sleep and mindfulness routine.",
    "Major Depressive Disorder": "SSRI Therapy: Tab. Sertraline 50mg OD after breakfast + Cognitive Behavioral Therapy (CBT).",
    "Persistent Depressive Disorder": "SSRI Maintenance: Tab. Escitalopram 10mg OD mornings + weekly psychotherapy.",
    "Generalized Anxiety Disorder (GAD)": "Anxiolytic / SSRI: Tab. Escitalopram 10mg OD + breathing & mindfulness exercises.",
    "Primary Insomnia": "Sleep Hygiene protocol + Tab. Melatonin 5mg 30 mins before bedtime for 14 days.",
    "Polycystic Ovary Syndrome (PCOS)": "Metabolic & Cycle Support: Tab. Myo-Inositol + Folic Acid OD + lifestyle & diet plan.",
    "Primary Dysmenorrhea": "Antispasmodic relief: Tab. Mefenamic Acid 250mg + Dicyclomine 10mg SOS during pain.",
    "Routine Antenatal Care": "Prenatal Supplements: Tab. Folic Acid 5mg OD + Iron & Calcium supplements daily.",
    "Perimenopausal Syndrome": "Hormonal & Bone Support: Calcium + Vitamin D3 OD + gynecological follow-up."
}

DOCTOR_FEE_SCHEDULE = {
    "Dr. Pradip (Pediatrics)": 600.00,
    "Dr. Sharma (General Medicine)": 500.00,
    "Dr. Rao (ENT)": 750.00,
    "Dr. Sen (Neurology)": 1500.00,
    "Dr. Manish (Ophthalmology)": 700.00,
    "Dr. Meera (Psychology)": 900.00,
    "Dr. Radha (Psychiatry)": 1000.00,
    "Dr. Anjali (Gynecology)": 850.00
}

DISEASE_TO_MEDICINE_MAP = {
    "Viral Influenza": "Paracetamol 650mg",
    "Malaria Parasitism": "Artemether-Lumefantrine",
    "Acute Bronchitis": "Dextromethorphan Syr.",
    "Bronchial Asthma": "Budesonide Inhaler",
    "Acute Gastritis": "Pantoprazole 40mg",
    "Gastroesophageal Reflux Disease (GERD)": "Rabeprazole Combo",
    "Rheumatoid Arthritis": "Naproxen 500mg",
    "Acute Gouty Arthritis": "Febuxostat 40mg",
    "Acute Sinusitis": "Fluticasone Nasal Spray",
    "Acute Tonsillitis": "Amoxicillin-Clavulanate 625mg",
    "Benign Paroxysmal Positional Vertigo (BPPV)": "Betahistine 16mg",
    "Otitis Media": "Ciprofloxacin Ear Drops",
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
    "Primary Insomnia": "Melatonin 5mg",
    "Polycystic Ovary Syndrome (PCOS)": "Myo-Inositol + Folic Acid",
    "Primary Dysmenorrhea": "Mefenamic Acid 250mg",
    "Routine Antenatal Care": "Folic Acid 5mg",
    "Perimenopausal Syndrome": "Calcium + Vitamin D3"
}
# ==========================================
# 2. DATABASE INITIALIZATION ENGINE
# ==========================================

def init_db():
    conn = sqlite3.connect("hospital_v2.db")
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT NOT NULL,
        patient_age INTEGER,
        patient_gender TEXT,
        patient_contact TEXT,
        patient_problem TEXT,
        doctor TEXT NOT NULL,
        appt_date TEXT NOT NULL DEFAULT '',
        appt_time TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL
    )
    ''')

    cursor.execute("PRAGMA table_info(appointments)")
    appt_cols = [col_name for _, col_name, _, _, _, _ in cursor.fetchall()]
    if "appt_date" not in appt_cols:
        cursor.execute("ALTER TABLE appointments ADD COLUMN appt_date TEXT NOT NULL DEFAULT ''")
    if "appt_time" not in appt_cols:
        cursor.execute("ALTER TABLE appointments ADD COLUMN appt_time TEXT NOT NULL DEFAULT ''")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            patient_age INTEGER,
            doctor TEXT NOT NULL DEFAULT 'Attending Specialist',
            symptoms TEXT NOT NULL,
            diagnosed_disease TEXT NOT NULL,
            prescription TEXT NOT NULL,
            medicine_dispensed TEXT NOT NULL DEFAULT 'None',
            medicine_cost REAL NOT NULL DEFAULT 0.0,
            notes TEXT,
            consultation_date TEXT NOT NULL
        )
    ''')

    cursor.execute("PRAGMA table_info(consultations)")
    cons_cols = [col_name for _, col_name, _, _, _, _ in cursor.fetchall()]
    if "doctor" not in cons_cols:
        cursor.execute("ALTER TABLE consultations ADD COLUMN doctor TEXT NOT NULL DEFAULT 'Attending Specialist'")
    if "medicine_dispensed" not in cons_cols:
        cursor.execute("ALTER TABLE consultations ADD COLUMN medicine_dispensed TEXT NOT NULL DEFAULT 'None'")
    if "medicine_cost" not in cons_cols:
        cursor.execute("ALTER TABLE consultations ADD COLUMN medicine_cost REAL NOT NULL DEFAULT 0.0")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            stock_qty INTEGER NOT NULL,
            min_required INTEGER NOT NULL,
            unit_price REAL NOT NULL DEFAULT 150.0
        )
    ''')

    cursor.execute("PRAGMA table_info(inventory)")
    inv_cols = [col_name for _, col_name, _, _, _, _ in cursor.fetchall()]
    if "unit_price" not in inv_cols:
        cursor.execute("ALTER TABLE inventory ADD COLUMN unit_price REAL NOT NULL DEFAULT 150.0")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            doctor_assigned TEXT NOT NULL,
            consultation_fee REAL NOT NULL,
            medicine_fee REAL NOT NULL DEFAULT 0.0,
            tax_amount REAL NOT NULL,
            grand_total REAL NOT NULL,
            payment_status TEXT NOT NULL,
            billing_date TEXT NOT NULL
        )
    ''')

    cursor.execute("PRAGMA table_info(billing)")
    bill_cols = [col_name for _, col_name, _, _, _, _ in cursor.fetchall()]
    if "medicine_fee" not in bill_cols:
        cursor.execute("ALTER TABLE billing ADD COLUMN medicine_fee REAL NOT NULL DEFAULT 0.0")
    
    cursor.execute("SELECT COUNT(*) FROM appointments")
    if cursor.fetchone() == (0,):
        cursor.execute("INSERT INTO appointments (patient_name, patient_age, patient_contact, patient_problem, doctor, appt_date, appt_time, status) VALUES ('Rama', 34, '9876543210', '[Severity: Moderate | Duration: 1 - 3 days | Age: 34] Symptoms: Earache, Sinus Congestion & Sore Throat.', 'Dr. Rao (ENT)', '2026-11-15', '10:00 AM', 'Confirmed')")
        cursor.execute("INSERT INTO appointments (patient_name, patient_age, patient_contact, patient_problem, doctor, appt_date, appt_time, status) VALUES ('Priya Patel', 10, '9123456780', '[Severity: Mild | Duration: Less than 24 hours | Age: 10] Symptoms: High Fever & Chills.', 'Dr. Pradip (Pediatrics)', '2026-11-15', '02:30 PM', 'Pending')")

    medicines = [
        ('Paracetamol 650mg', 'Analgesic / Antipyretic', 120, 30, 45.0),
        ('Artemether-Lumefantrine', 'Antimalarial', 15, 10, 240.0),
        ('Dextromethorphan Syr.', 'Antitussive Cough Syrup', 45, 15, 110.0),
        ('Budesonide Inhaler', 'Bronchodilator', 8, 10, 380.0),
        ('Pantoprazole 40mg', 'Antacid / PPI', 350, 100, 95.0),
        ('Rabeprazole Combo', 'Antacid / GERD Support', 180, 40, 140.0),
        ('Naproxen 500mg', 'NSAID / Anti-inflammatory', 90, 30, 125.0),
        ('Febuxostat 40mg', 'Uric Acid Lowering Therapy', 60, 20, 190.0),
        ('Fluticasone Nasal Spray', 'ENT Nasal Corticosteroid', 55, 15, 310.0),
        ('Amoxicillin-Clavulanate 625mg', 'Broad-Spectrum Antibiotic', 85, 25, 220.0),
        ('Betahistine 16mg', 'Antivertigo Agent', 70, 20, 165.0),
        ('Ciprofloxacin Ear Drops', 'Otic Antibiotic', 40, 15, 85.0),
        ('Sumatriptan 50mg', 'Antimigraine / Triptan', 75, 20, 260.0),
        ('Levetiracetam 500mg', 'Anticonvulsant', 110, 30, 290.0),
        ('Pregabalin 75mg', 'Neuropathic Pain Agent', 95, 25, 210.0),
        ('Moxifloxacin Eye Drops', 'Ophthalmic Antibiotic', 40, 15, 145.0),
        ('Carboxymethylcellulose Drops', 'Ocular Lubricant', 65, 20, 130.0),
        ('Timolol 0.5% Eye Drops', 'Antiglaucoma Agent', 30, 10, 175.0),
        ('Sertraline 50mg', 'SSRI Antidepressant', 140, 40, 185.0),
        ('Escitalopram 10mg', 'SSRI Anxiolytic', 160, 40, 195.0),
        ('Melatonin 5mg', 'Sleep Regulator', 85, 25, 150.0),
        ('Myo-Inositol + Folic Acid', 'PCOS Metabolic Support', 90, 25, 340.0),
        ('Mefenamic Acid 250mg', 'Antispasmodic Analgesic', 110, 30, 75.0),
        ('Folic Acid 5mg', 'Prenatal Supplement', 200, 50, 60.0),
        ('Calcium + Vitamin D3', 'Bone & Hormonal Support', 150, 40, 180.0)
    ]    
    cursor.executemany(
        "INSERT OR IGNORE INTO inventory (medicine_name, category, stock_qty, min_required, unit_price) VALUES (?, ?, ?, ?, ?)",
        medicines
    )
    
    conn.commit()
    conn.close()

init_db()
# ==========================================
# 3. PDF GENERATION UTILITIES
# ==========================================

def build_prescription_pdf(name, doctor, disease, symptoms, Rx, notes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], alignment=TA_CENTER, textColor='#1e3d59', fontSize=24, spaceAfter=6)
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], alignment=TA_CENTER, textColor='#17b978', fontSize=10, spaceAfter=20)
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=11, leading=16, spaceAfter=8)
    section_title = ParagraphStyle('SecTitle', parent=styles['Heading3'], textColor='#1e3d59', fontSize=14, spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=11, leading=16, leftIndent=10)
    
    story = []
    story.append(Paragraph("🏥 PATIENT HEALTH MANAGEMENT SYSTEM", title_style))
    story.append(Paragraph("E-Health Portal Automated Prescription Record System", sub_style))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
    story.append(Paragraph(f"<b>Patient Name:</b> {name}", meta_style))
    story.append(Paragraph(f"<b>Attending Doctor:</b> {doctor}", meta_style)) 
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Clinical Diagnostics Summary", section_title))
    story.append(Paragraph(f"<b>Presenting Symptoms:</b> {symptoms}", body_style))
    story.append(Paragraph(f"<b>Inferred Final Diagnosis:</b> {disease}", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("💊 Prescribed Medications (Rx Options)", section_title))
    story.append(Paragraph(Rx.replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("📝 Lifestyle Advice & Clinical Notes", section_title))
    story.append(Paragraph(notes if notes else "No additional restrictions specified.", body_style))
    story.append(Spacer(1, 40))
    
    story.append(Paragraph(f"Authorized Signature: <b>{doctor}</b> (Digitally Validated)", ParagraphStyle('Sign', parent=styles['Normal'], alignment=TA_LEFT, fontSize=9)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def build_invoice_pdf(invoice_id, name, doctor, base_fee, med_fee, med_name, tax, total, status, date_str):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    brand_title = ParagraphStyle('InvBrand', parent=styles['Heading1'], alignment=TA_CENTER, textColor='#1e3d59', fontSize=22, spaceAfter=4)
    brand_sub = ParagraphStyle('InvSub', parent=styles['Normal'], alignment=TA_CENTER, textColor='#777777', fontSize=9, spaceAfter=25)
    inv_title = ParagraphStyle('InvTitle', parent=styles['Heading2'], textColor='#1e3d59', fontSize=14, spaceAfter=15)
    meta_style = ParagraphStyle('InvMeta', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    table_label = ParagraphStyle('TblLabel', parent=styles['Normal'], fontSize=11, leading=16)
    total_style = ParagraphStyle('TblTotal', parent=styles['Heading3'], textColor='#17b978', fontSize=12, leading=16)
    footer_style = ParagraphStyle('InvFoot', parent=styles['Normal'], alignment=TA_CENTER, textColor='#888888', fontSize=8, spaceBefore=40)
    
    story = []
    story.append(Paragraph("🏥 PATIENT HEALTH MANAGEMENT SYSTEM", brand_title))
    story.append(Paragraph("123 Health Boulevard, Wellness District | Support: +91 99999 88888", brand_sub))
    
    story.append(Paragraph("<b>PATIENT INVOICE RECEIPT</b>", inv_title))
    story.append(Paragraph(f"<b>Invoice ID:</b> #LL-2026-{invoice_id}", meta_style))
    story.append(Paragraph(f"<b>Date/Time:</b> {date_str}", meta_style))
    story.append(Paragraph(f"<b>Patient Name:</b> {name}", meta_style))
    story.append(Paragraph(f"<b>Attending Clinician:</b> {doctor}", meta_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<hr/>", meta_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Itemised Description Charges:</b>", meta_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"• Clinical Consultation Services Base Fee: <b>₹{base_fee:,.2f}</b>", table_label))
    story.append(Paragraph(f"• Pharmacy Dispensed Medication ({med_name}): <b>₹{med_fee:,.2f}</b>", table_label))
    story.append(Paragraph(f"• Central Medical Tax Services (18% GST): <b>₹{tax:,.2f}</b>", table_label))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Grand Total Amount Settled: ₹{total:,.2f}</b>", total_style))
    story.append(Paragraph(f"<b>Transaction Status:</b> <font color='#17b978'><b>{status}</b></font>", table_label))
    
    story.append(Spacer(1, 30))
    story.append(Paragraph("<i>This is a computer-generated transaction record voucher. No physical signature is required.</i>", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
# ==========================================
# 4. SECURE SIDEBAR NAVIGATION ENGINE
# ==========================================

st.sidebar.title("🏥 Patient Health Management System")
st.sidebar.markdown("---")

user_role = st.sidebar.selectbox(
    "Switch User View:",
    ["Patient Portal", "Doctor Dashboard", "Pharmacy Inventory", "Billing Dashboard", "Admin Analytics"],
    key="main_role_selector"
)

if user_role in ["Doctor Dashboard", "Pharmacy Inventory", "Billing Dashboard", "Admin Analytics"]:
    authenticated = False
    st.sidebar.markdown(f"#### 🔐 Secure {user_role} Login")
    password_input = st.sidebar.text_input("Enter Access Password:", type="password", key=f"pwd_{user_role}")
    
    role_passwords = {
        "Doctor Dashboard": "doctor123",
        "Pharmacy Inventory": "pharma123",
        "Billing Dashboard": "billing123",
        "Admin Analytics": "admin123"
    }
    
    if password_input == role_passwords[user_role]:
        authenticated = True
        st.sidebar.success("🔒 Access Granted")
    elif password_input != "":
        st.sidebar.error("❌ Invalid Access Token")
else:
    authenticated = True
# ==========================================
# 5. SECURE VIEW LOGIC RUNTIME
# ==========================================

if not authenticated:
    render_hero("🔒 Restricted Clinical Access Area", "Authorized medical personnel only. Enter your access token in the sidebar.")
    st.warning("Please provide the correct credentials in the sidebar to unlock this dashboard view.")
    st.info("💡 Hint: Use doctor123, pharma123, billing123, or admin123 based on selection.")
else:
    # --- PAGE 1: PATIENT PORTAL ---
    if user_role == "Patient Portal":
        render_hero("🏥 Patient Health Management System", "Select a medical specialty below, complete a symptom check, or download your prescriptions.")
        
        # FRONT PAGE: 8 CLINICAL SPECIALTIES GRID
        st.subheader("🏥 Available Clinical Specialties")
        if "selected_specialty_doc" not in st.session_state:
            st.session_state["selected_specialty_doc"] = None

        row1_cols = st.columns(4, gap="medium")
        row2_cols = st.columns(4, gap="medium")
        all_cols = row1_cols + row2_cols

        for idx, spec in enumerate(SPECIALTY_CARDS):
            with all_cols[idx]:
                with st.container(border=True):
                    st.markdown(f"#### {spec['icon']} {spec['dept']}")
                    st.caption(f"**{spec['doctor']}**")
                    st.write(f"<small>{spec['desc']}</small>", unsafe_allow_html=True)
                    if st.button(f"Select {spec['dept']}", key=f"btn_spec_{idx}", use_container_width=True):
                        st.session_state["selected_specialty_doc"] = spec["doctor"]

        st.markdown("---")
        col_left, col_right = st.columns((1.15, 1), gap="large")
        
        with col_left:
            # STEP 1: SYMPTOM ENQUIRY MODULE
            st.subheader("🩺 Step 1: Pre-Appointment Symptom Enquiry")
            with st.container(border=True):
                col_age_check, col_sym_check = st.columns((1, 2))
                with col_age_check:
                    p_age = st.number_input("Patient Age", min_value=0, max_value=120, value=25)
                with col_sym_check:
                    selected_symptoms = st.multiselect(
                        "Current Symptoms",
                        options=SYMPTOM_VARIANTS,
                        placeholder="Select one or more symptoms..."
                    )
                
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    duration = st.selectbox("Symptom Duration", ["Less than 24 hours", "1 - 3 days", "4 - 7 days", "More than a week"])
                with col_s2:
                    severity = st.select_slider("Pain / Discomfort Severity", options=["Mild", "Moderate", "Severe"])
                
                additional_details = st.text_input("Additional Notes or Allergies (Optional)", placeholder="e.g., Fever spiked at night, allergic to penicillin...")

                default_specialist = next(iter(SPECIALTY_DOCTORS))
                if p_age < 16:
                    recommended_doc = "Dr. Pradip (Pediatrics)"
                    if severity == "Severe":
                        st.error(f"🚨 **Pediatric Priority Alert:** Since the patient is under 16 and has severe symptoms, we strongly recommend consulting **{recommended_doc}** immediately.")
                    else:
                        st.info(f"🧸 **Pediatric Routing:** Patients under 16 are automatically routed to **{recommended_doc}**.")
                elif st.session_state["selected_specialty_doc"]:
                    recommended_doc = st.session_state["selected_specialty_doc"]
                    st.success(f"✅ **Selected Department:** You chose **{recommended_doc}** from the specialties menu above.")
                elif selected_symptoms:
                    primary_symptom = next(iter(selected_symptoms))
                    recommended_doc = SYMPTOM_TO_DOCTOR_MAP.get(primary_symptom, default_specialist)
                    if severity == "Severe":
                        st.error(f"🚨 **High Priority Triage:** Based on severe symptoms, we strongly recommend consulting **{recommended_doc}** immediately.")
                    else:
                        st.info(f"💡 **Recommended Specialist:** Based on your symptoms, we suggest booking with **{recommended_doc}**.")
                else:
                    recommended_doc = default_specialist
                    st.caption("Click a specialty card above or select symptoms to auto-assign your doctor.")

            st.markdown("---")

            # STEP 2: APPOINTMENT BOOKING FORM (WITH DOUBLE-BOOKING PREVENTION)
            st.subheader("🗓️ Step 2: Confirm Appointment Details")
            default_doc_index = SPECIALTY_DOCTORS.index(recommended_doc) if recommended_doc in SPECIALTY_DOCTORS else 0
            doctor_choice = st.selectbox("Assigned Department Specialist", SPECIALTY_DOCTORS, index=default_doc_index)
            
            col_date, col_time = st.columns(2)
            with col_date:
                appointment_date = st.date_input("Select Appointment Date", min_value=datetime.today().date())
            
            conn = sqlite3.connect("hospital_v2.db")
            booked_slots_df = pd.read_sql_query(
                "SELECT appt_time FROM appointments WHERE doctor = ? AND appt_date = ? AND status != 'Cancelled'",
                conn,
                params=(doctor_choice, str(appointment_date))
            )
            conn.close()
            booked_slots = set(booked_slots_df["appt_time"].tolist())
            available_slots = [slot for slot in ALL_TIME_SLOTS if slot not in booked_slots]

            with col_time:
                if available_slots:
                    appointment_time = st.selectbox("Select Available Time Slot", available_slots)
                else:
                    appointment_time = None
                    st.warning("No slots left on this date.")

            with st.form("appointment_form", clear_on_submit=True):
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    patient_name = st.text_input("Full Patient Name", placeholder="e.g. Rahul Sharma")
                with col_n2:
                    p_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                
                p_contact = st.text_input("Registered Contact Number (Used to unlock your Rx later)", placeholder="e.g. 9876543210")
                
                submit_button = st.form_submit_button("Confirm Appointment Slot", type="primary")
                 if submit_button:
                    if patient_name.strip() == "":
                        st.error("Please enter a valid patient name.")
                    elif p_contact.strip() == "":
                        st.error("Please enter your contact number so you can access your prescription later.")
                    elif not selected_symptoms:
                        st.warning("Please complete Step 1 by selecting at least one symptom before booking.")
                    elif not appointment_time:
                        st.error("Please select another date with available time slots.")
                    else:
                        triage_summary = (
                            f"[Severity: {severity} | Duration: {duration} | Age: {p_age}] "
                            f"Symptoms: {', '.join(selected_symptoms)}. "
                            f"Notes: {additional_details if additional_details else 'None'}"
                        )
                        
                        conn = sqlite3.connect("hospital_v2.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO appointments (patient_name, patient_age, patient_gender, patient_contact, patient_problem, doctor, appt_date, appt_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (patient_name.strip(), p_age, p_gender, p_contact.strip(), triage_summary, doctor_choice, str(appointment_date), appointment_time, "Pending")
                        )
                        conn.commit()
                        conn.close()
                        st.session_state["selected_specialty_doc"] = None
                        st.success(f"🎉 Appointment booked with **{doctor_choice}** on {appointment_date} at {appointment_time}! Your symptom report has been sent to the doctor.")
                        st.rerun()

        with col_right:
            tab_req, tab_rx = st.tabs(["📋 Active Requests", "📄 Download Prescriptions & Notes"])
            
            with tab_req:
                st.subheader("Active Registered Requests")
                conn = sqlite3.connect("hospital_v2.db")
                df = pd.read_sql_query("SELECT id AS ID, patient_name AS [Patient Name], doctor AS Doctor, appt_date AS [Scheduled Date], appt_time AS [Time Slot], status AS Status FROM appointments ORDER BY id DESC", conn)
                conn.close()
                st.dataframe(df, use_container_width=True, hide_index=True)

            with tab_rx:
                st.subheader("Verified E-Health Prescription Portal")
                st.caption("Enter your full name and registered phone number to view and download your doctor's prescription and notes.")
                
                verify_name = st.text_input("Patient Full Name:", placeholder="e.g. Rahul Sharma", key="rx_verify_name")
                verify_contact = st.text_input("Registered Contact Number:", placeholder="e.g. 9876543210", key="rx_verify_phone")

                if verify_name.strip() and verify_contact.strip():
                    conn = sqlite3.connect("hospital_v2.db")
                    appt_check = pd.read_sql_query(
                        "SELECT patient_contact FROM appointments WHERE LOWER(TRIM(patient_name)) = LOWER(TRIM(?))",
                        conn,
                        params=(verify_name,)
                    )
                    clean_input_digits = "".join(ch for ch in verify_contact if ch.isdigit())
                    registered_digits = {
                        "".join(ch for ch in str(c) if ch.isdigit())
                        for c in appt_check["patient_contact"].dropna().tolist()
                    }
                    # Allow '0000' fallback for older records created without a contact number
                    is_verified = (clean_input_digits in registered_digits and clean_input_digits != "") or (
                        not appt_check.empty and registered_digits == {""} and verify_contact.strip() == "0000"
                    )

                    if is_verified:
                        rx_df = pd.read_sql_query(
                            "SELECT id, patient_name, doctor, symptoms, diagnosed_disease, prescription, notes, consultation_date FROM consultations WHERE LOWER(TRIM(patient_name)) = LOWER(TRIM(?)) ORDER BY id DESC",
                            conn,
                            params=(verify_name,)
                        )
                        conn.close()

                        if not rx_df.empty:
                            st.success(f"🔓 Identity Verified! Found {len(rx_df)} prescription record(s):")
                            for rec in rx_df.to_dict("records"):
                                with st.container(border=True):
                                    st.markdown(f"**🗓️ Visit Date:** {rec['consultation_date']} | **🩺 Doctor:** {rec['doctor']}")
                                    st.markdown(f"**Diagnosis:** {rec['diagnosed_disease']} *(Symptoms: {rec['symptoms']})*")
                                    st.info(f"💊 **Prescription:** {rec['prescription']}")
                                    st.caption(f"📝 **Doctor Notes:** {rec['notes'] if rec['notes'] else 'No additional notes.'}")

                                    pdf_data = build_prescription_pdf(
                                        rec["patient_name"],
                                        rec["doctor"],
                                        rec["diagnosed_disease"],
                                        rec["symptoms"],
                                        rec["prescription"],
                                        rec["notes"]
                                    )
                                    st.download_button(
                                        label="📥 Download Prescription & Notes (PDF)",
                                        data=pdf_data,
                                        file_name=f"Prescription_{rec['patient_name'].replace(' ', '_')}_{rec['id']}.pdf",
                                        mime="application/pdf",
                                        key=f"patient_dl_rx_{rec['id']}"
                                    )
                        else:
                            st.info("Identity verified, but your doctor has not finalized a prescription yet.")
                    else:
                        conn.close()
                        st.error("❌ Verification Failed: Patient name and contact number do not match our records. (Tip: Use '0000' if booked before phone tracking was added.)")
### Block 7 — Section 5B: Page 2 (Doctor Dashboard with Medicine Cost Logging & Past PDF Downloads)

```python
    # --- PAGE 2: DOCTOR DASHBOARD ---
    elif user_role == "Doctor Dashboard":
        render_hero("🩺 Medical Practitioner Workspace", "Manage daily patient schedules, review E-health logs, and issue digital prescriptions.")
        
        selected_dept = st.selectbox("Filter Schedule by Specialist / Department:", ["All Departments"] + SPECIALTY_DOCTORS)
        
        conn = sqlite3.connect("hospital_v2.db")
        df = pd.read_sql_query("SELECT id AS ID, patient_name AS [Patient Name], patient_age AS [Age], doctor AS Doctor, patient_problem AS [Triage Report], appt_date AS [Date], appt_time AS [Slot], status AS Status FROM appointments", conn)
        conn.close()
        
        if selected_dept != "All Departments":
            df = df[df["Doctor"] == selected_dept]
            
        if not df.empty:
            tab1, tab2 = st.tabs(["📅 Operational Schedule", "🩺 Patient Diagnostics & Rx"])
            
            with tab1:
                st.subheader("Active Operational Schedule")
                edited_df = st.data_editor(
                    df,
                    column_config={"Status": st.column_config.SelectboxColumn("Appointment Status", options=["Pending", "Confirmed", "Completed", "Cancelled"], required=True)},
                    disabled=["ID", "Patient Name", "Age", "Doctor", "Triage Report", "Date", "Slot"],
                    use_container_width=True,
                    key="doctor_grid",
                    hide_index=True
                )
                
                if st.button("💾 Save Schedule Status Updates", type="primary"):
                    conn = sqlite3.connect("hospital_v2.db")
                    cursor = conn.cursor()
                    for index, row in edited_df.iterrows():
                        cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (row["Status"], int(row["ID"])))
                    conn.commit()
                    conn.close()
                    st.success("Patient schedules synchronized!")
                    st.rerun()
                    
            with tab2:
                st.subheader("Real-time Patient Diagnostics & Prescription Module")
                patient_list = df["Patient Name"].unique().tolist()
                selected_patient = st.selectbox("Select Patient to Diagnose:", patient_list)
                
                conn = sqlite3.connect("hospital_v2.db")
                cursor = conn.cursor()
                patient_info = cursor.execute("SELECT patient_age, doctor, patient_problem FROM appointments WHERE patient_name = ? ORDER BY id DESC LIMIT 1", (selected_patient,)).fetchone()
                
                if patient_info:
                    raw_age, raw_doc, raw_note = patient_info
                    p_age_val = raw_age if raw_age is not None else 25
                    assigned_doc = raw_doc if raw_doc else selected_dept
                    triage_note = raw_note if raw_note else "No pre-appointment triage recorded."
                else:
                    p_age_val = 25
                    assigned_doc = selected_dept
                    triage_note = "No pre-appointment triage recorded."
                
                history_df = pd.read_sql_query(
                    "SELECT id AS ID, consultation_date AS [Date], doctor AS [Doctor], symptoms AS [Symptoms], diagnosed_disease AS [Diagnosis], prescription AS [Prescription Summary], notes AS [Doctor Notes] FROM consultations WHERE patient_name = ? ORDER BY id DESC",
                    conn,
                    params=(selected_patient,)
                )
                conn.close()

                st.info(f"📋 **Pre-Appointment Symptom Enquiry Report (Age: {p_age_val}):** {triage_note}")
              
                st.markdown("##### 📜 Previous E-Health Consultation Logs")
                if not history_df.empty:
                    st.warning(f"🔄 Revisit Detected! Found {len(history_df)} record(s) for {selected_patient}:")
                    st.dataframe(history_df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

                    past_records = history_df.to_dict("records")
                    record_labels = [f"{r['Date']} — {r['Diagnosis']}" for r in past_records]
                    chosen_past_label = st.selectbox("Select a Past Record to Download PDF:", record_labels, key="doc_past_rx_select")
                    chosen_past_rec = past_records[record_labels.index(chosen_past_label)]

                    past_pdf_bytes = build_prescription_pdf(
                        selected_patient,
                        chosen_past_rec["Doctor"],
                        chosen_past_rec["Diagnosis"],
                        chosen_past_rec["Symptoms"],
                        chosen_past_rec["Prescription Summary"],
                        chosen_past_rec["Doctor Notes"]
                    )
                    st.download_button(
                        label="📥 Download Selected Past Prescription & Notes (PDF)",
                        data=past_pdf_bytes,
                        file_name=f"Prescription_{selected_patient.replace(' ', '_')}_{chosen_past_rec['ID']}.pdf",
                        mime="application/pdf",
                        key="doc_past_rx_dl_btn"
                    )
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
                    st.info(suggested_rx)
                    final_prescription = st.text_area("Finalized Pharmacy Prescription:", value=suggested_rx, height=70)
                    clinical_notes = st.text_input("Additional Case Notes:", placeholder="e.g. Bedrest for 3 days")
                    
                log_submitted = st.button("🚀 Log & Finalize Case", type="primary")
                    
                if log_submitted:
                    conn = sqlite3.connect("hospital_v2.db")
                    cursor = conn.cursor()
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

                    target_medicine = DISEASE_TO_MEDICINE_MAP.get(chosen_disease, "None")
                    med_price = 0.0
                    if target_medicine != "None":
                        price_row = cursor.execute("SELECT unit_price FROM inventory WHERE medicine_name = ?", (target_medicine,)).fetchone()
                        med_price = float(price_row) if price_row else 150.0
                        cursor.execute("UPDATE inventory SET stock_qty = MAX(0, stock_qty - 1) WHERE medicine_name = ?", (target_medicine,))
                    
                    cursor.execute(
                        'INSERT INTO consultations (patient_name, patient_age, doctor, symptoms, diagnosed_disease, prescription, medicine_dispensed, medicine_cost, notes, consultation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (selected_patient, p_age_val, assigned_doc, chosen_symptom, chosen_disease, final_prescription, target_medicine, med_price, clinical_notes, current_time)
                    )
                    cursor.execute("UPDATE appointments SET status = 'Completed' WHERE patient_name = ?", (selected_patient,))

                    conn.commit()
                    conn.close()
                    st.session_state["pdf_ready_patient"] = selected_patient
                    st.session_state["pdf_data"] = (selected_patient, assigned_doc, chosen_disease, chosen_symptom, final_prescription, clinical_notes)
                    st.rerun()

                if "pdf_ready_patient" in st.session_state and st.session_state["pdf_ready_patient"] == selected_patient:
                    p_name, d_name, p_dis, p_sym, p_rx, p_note = st.session_state["pdf_data"]
                    pdf_bytes = build_prescription_pdf(p_name, d_name, p_dis, p_sym, p_rx, p_note)
                    st.markdown("---")
                    st.success("📄 Medical Prescription Document Compiled Successfully!")
                    st.download_button(
                        label="📥 Download Newly Logged PDF Prescription",
                        data=pdf_bytes,
                        file_name=f"Prescription_{p_name.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("No active appointments registered for this selection.")
    # --- PAGE 3: PHARMACY INVENTORY ---
    elif user_role == "Pharmacy Inventory":
        render_hero("📦 Medical Dispensary & Pharmacy Stock", "Monitor formulation stock levels, unit pricing, reorder alerts, and live inventory updates.")
        
        conn = sqlite3.connect("hospital_v2.db")
        df_inv = pd.read_sql_query("SELECT id AS ID, medicine_name AS [Medicine Name], category AS [Therapeutic Class], stock_qty AS [Current Stock Units], min_required AS [Safety Threshold Limit], unit_price AS [Unit Price (₹)] FROM inventory", conn)
        conn.close()

        low_stock_items = df_inv[df_inv["Current Stock Units"] <= df_inv["Safety Threshold Limit"]]

        col_stat1, col_stat2 = st.columns(2)
        col_stat1.metric("Total Maintained Formulas", len(df_inv))
        col_stat2.metric("Critical Low Reorder Alerts", len(low_stock_items), delta=-len(low_stock_items) if len(low_stock_items) > 0 else 0, delta_color="inverse")
        
        if not low_stock_items.empty:
            st.error("⚠️ Critical Shortage Warning: The following formulas have fallen below safety limits!")
            st.dataframe(low_stock_items, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Live Inventory & Pricing Editor")
        edited_inv = st.data_editor(df_inv, disabled=["ID", "Medicine Name", "Therapeutic Class"], use_container_width=True, hide_index=True, key="inventory_editor")

        if st.button("💾 Apply & Update Inventory Balances", type="primary"):
            conn = sqlite3.connect("hospital_v2.db")
            cursor = conn.cursor()
            for index, row in edited_inv.iterrows():
                cursor.execute(
                    "UPDATE inventory SET stock_qty = ?, min_required = ?, unit_price = ? WHERE id = ?",
                    (int(row["Current Stock Units"]), int(row["Safety Threshold Limit"]), float(row["Unit Price (₹)"]), int(row["ID"]))
                )
            conn.commit()
            conn.close()
            st.success("Pharmacy inventory & pricing updates successfully committed!")
            st.rerun()

    # --- PAGE 4: BILLING DASHBOARD ---
    elif user_role == "Billing Dashboard":
        render_hero("💰 Patient Checkouts & Invoice Generator", "Process completed consultations with itemized pharmacy charges, GST, and downloadable PDF receipts.")
        
        conn = sqlite3.connect("hospital_v2.db")
        query = """
            SELECT DISTINCT a.patient_name, a.doctor 
            FROM appointments a
            WHERE a.status = 'Completed' 
            AND a.patient_name NOT IN (SELECT patient_name FROM billing)
        """
        unbilled_df = pd.read_sql_query(query, conn)
        conn.close()

        col_bill_form, col_bill_log = st.columns(2, gap="large")

        with col_bill_form:
            st.subheader("💳 Process Pending Checkout")
            if not unbilled_df.empty:
                unbilled_df["display_select"] = unbilled_df["patient_name"] + " — " + unbilled_df["doctor"]
                selected_record = st.selectbox("Select Pending Patient:", unbilled_df["display_select"].tolist())
                
                chosen_patient, chosen_doctor = selected_record.split(" — ", 1)

                # Fetch dispensed medicine and cost from latest consultation
                conn = sqlite3.connect("hospital_v2.db")
                med_row = conn.execute(
                    "SELECT medicine_dispensed, medicine_cost FROM consultations WHERE patient_name = ? ORDER BY id DESC LIMIT 1",
                    (chosen_patient,)
                ).fetchone()
                conn.close()

                dispensed_med_name = med_row if (med_row and med_row) else "No Medication Dispensed"
                med_fee = float(med_row) if (med_row and med_row is not None) else 0.0
                
                base_fee = DOCTOR_FEE_SCHEDULE.get(chosen_doctor, 500.00)
                subtotal = base_fee + med_fee
                tax_calc = round(subtotal * 0.18, 2)
                total_bill = round(subtotal + tax_calc, 2)
                
                st.info(f"📋 **Itemized Billing Summary for {chosen_patient}:**\n\n* **Dispensed Medicine:** {dispensed_med_name}")
                m1, m2 = st.columns(2)
                m1.metric("Consultation Fee", f"₹{base_fee:,.2f}")
                m2.metric("Medicine Charges", f"₹{med_fee:,.2f}")

                m3, m4 = st.columns(2)
                m3.metric("18% GST", f"₹{tax_calc:,.2f}")
                m4.metric("Grand Total", f"₹{total_bill:,.2f}")
                
                pay_method = st.selectbox("Payment Method:", ["Cash", "UPI / QR Scanner", "Credit/Debit Card", "Insurance Claim"])
                
                if st.button("🚀 Process Payment & Issue Invoice", type="primary"):
                    conn = sqlite3.connect("hospital_v2.db")
                    cursor = conn.cursor()
                    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    cursor.execute(
                        "INSERT INTO billing (patient_name, doctor_assigned, consultation_fee, medicine_fee, tax_amount, grand_total, payment_status, billing_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (chosen_patient, chosen_doctor, base_fee, med_fee, tax_calc, total_bill, f"Paid via {pay_method}", current_date)
                    )
                    last_id = cursor.lastrowid
                    conn.commit()
                    conn.close()
                    
                    st.session_state["invoice_ready_id"] = last_id
                    st.session_state["invoice_pdf_data"] = (last_id, chosen_patient, chosen_doctor, base_fee, med_fee, dispensed_med_name, tax_calc, total_bill, f"Paid via {pay_method}", current_date)
                    st.success(f"🎉 Receipt generated for {chosen_patient}.")
                    st.rerun()
            else:
                st.info("✨ Clean Slate: No pending unbilled patient checkouts found.")

            if "invoice_ready_id" in st.session_state:
                i_id, p_name, d_name, b_fee, m_fee, m_name, t_amt, g_tot, p_stat, d_str = st.session_state["invoice_pdf_data"]
                inv_bytes = build_invoice_pdf(i_id, p_name, d_name, b_fee, m_fee, m_name, t_amt, g_tot, p_stat, d_str)
                st.markdown("---")
                st.success("📄 Invoice Receipt PDF Compiled Successfully!")
                st.download_button(
                    label="📥 Download Printed Billing Receipt",
                    data=inv_bytes,
                    file_name=f"Invoice_{i_id}_{p_name.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

        with col_bill_log:
            st.subheader("📜 Historical Financial Transaction Logs")
            conn = sqlite3.connect("hospital_v2.db")
            billing_history_df = pd.read_sql_query("SELECT id AS [Inv ID], patient_name AS [Patient Name], consultation_fee AS [Consult (₹)], medicine_fee AS [Medicine (₹)], grand_total AS [Total Paid (₹)], payment_status AS [Status], billing_date AS [Date] FROM billing ORDER BY id DESC", conn)
            conn.close()
            if not billing_history_df.empty:
                st.dataframe(billing_history_df, use_container_width=True, hide_index=True)
            else:
                st.caption("No invoices issued yet today.")

    # --- PAGE 5: ADMIN ANALYTICS ---
    elif user_role == "Admin Analytics":
        render_hero("📊 Hospital Operational Control Panel", "Real-time clinical metrics, booking pipeline status, and disease incidence analytics.")
        
        conn = sqlite3.connect("hospital_v2.db")
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
                color="Total Incidences",
                color_continuous_scale="Tealgrn",
                title="Epidemiological Workload Distribution Map", 
                text_auto=True
            )
            
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(255,255,255,0.85)",
                plot_bgcolor="rgba(255,255,255,0.85)",
                xaxis_title="Diagnosed Disease Pathway",
                yaxis_title="Patient Record Count",
                font=dict(family="Arial", size=12),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No disease data logged out via the Doctor Workspace yet.")

