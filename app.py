import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3

# --- 1. INITIALIZE DATABASE FUNCTION ---
def init_db():
    """Creates a local database file and setup tables if they don't exist."""
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    # Create the appointments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            doctor TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    # Insert seed data if table is completely empty
    cursor.execute("SELECT COUNT(*) FROM appointments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO appointments (patient_name, doctor, status) VALUES ('Rahul Sharma', 'Dr. Verma (Cardiology)', 'Confirmed')")
        cursor.execute("INSERT INTO appointments (patient_name, doctor, status) VALUES ('Priya Patel', 'Dr. Reddy (Pediatrics)', 'Pending')")
    conn.commit()
    conn.close()

# Start the database engine on run
init_db()

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Lifeline HMS", 
    page_icon="🏥", 
    layout="wide"
)

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("🏥 Lifeline HMS")
st.sidebar.markdown("---")
user_role = st.sidebar.selectbox(
    "Switch User View:",
    ["Patient Portal", "Doctor Dashboard", "Admin Analytics"]
)

# --- 4. VIEW LOGIC RUNTIME ---

# PAGE 1: PATIENT PORTAL
if user_role == "Patient Portal":
    st.title("🗓️ Patient Appointment Booking")
    st.write("Welcome to the patient self-service portal. Fill out the form below to book a slot.")
    
    with st.form("appointment_form", clear_on_submit=True):
        st.subheader("Enter Booking Details")
        patient_name = st.text_input("Full Patient Name", placeholder="e.g. Rahul Sharma")
        doctor_choice = st.selectbox(
            "Select Department Specialist",
            ["Dr. Verma (Cardiology)", "Dr. Reddy (Pediatrics)", "Dr. Sen (Neurology)"]
        )
        submit_button = st.form_submit_button("Confirm Appointment Slot")
        
        if submit_button:
            if patient_name.strip() == "":
                st.error("Please enter a valid patient name to book an appointment.")
            else:
                # INSERT INTO LOCAL SQLITE DB
                conn = sqlite3.connect("hospital.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO appointments (patient_name, doctor, status) VALUES (?, ?, ?)",
                    (patient_name, doctor_choice, "Pending")
                )
                conn.commit()
                conn.close()
                st.success(f"🎉 Success! Your appointment request has been submitted to {doctor_choice}.")

    # Fetch and display current data instantly from SQLite
    st.markdown("---")
    st.subheader("📋 Your Active Requests Summary")
    conn = sqlite3.connect("hospital.db")
    df = pd.read_sql_query("SELECT id AS ID, patient_name AS [Patient Name], doctor AS Doctor, status AS Status FROM appointments", conn)
    conn.close()
    st.dataframe(df, use_container_width=True, hide_index=True)

# PAGE 2: DOCTOR DASHBOARD
elif user_role == "Doctor Dashboard":
    st.title("🩺 Medical Practitioner Dashboard")
    st.write("Review, update, and approve upcoming patient consultations below.")
    st.info("💡 Pro-Tip: Double-click any cell in the **Status** column to update it directly, then press 'Save Updates'.")
    
    # Fetch latest data from SQL file
    conn = sqlite3.connect("hospital.db")
    df = pd.read_sql_query("SELECT id AS ID, patient_name AS [Patient Name], doctor AS Doctor, status AS Status FROM appointments", conn)
    conn.close()
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Appointment Status",
                options=["Pending", "Confirmed", "Completed", "Cancelled"],
                required=True,
            )
        },
        disabled=["ID", "Patient Name", "Doctor"],
        use_container_width=True,
        key="doctor_grid",
        hide_index=True
    )
    
    if st.button("💾 Save Operational Updates", type="primary"):
        # WRITE UPDATED GRID ROWS BACK TO SQLITE FILE
        conn = sqlite3.connect("hospital.db")
        cursor = conn.cursor()
        for index, row in edited_df.iterrows():
            cursor.execute(
                "UPDATE appointments SET status = ? WHERE id = ?",
                (row["Status"], int(row["ID"]))
            )
        conn.commit()
        conn.close()
        st.success("Patient schedules synchronized and saved successfully!")
        st.rerun()

# PAGE 3: ADMIN ANALYTICS
elif user_role == "Admin Analytics":
    st.title("📊 Hospital Operational Control Panel")
    st.write("Real-time clinical capacity metrics and interactive appointment charts.")
    
    # Fetch fresh metrics from SQLite database
    conn = sqlite3.connect("hospital.db")
    df = pd.read_sql_query("SELECT * FROM appointments", conn)
    conn.close()
    
    total_appointments = len(df)
    pending_count = len(df[df["status"] == "Pending"])
    confirmed_count = len(df[df["status"] == "Confirmed"])
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total Patient Registrations", value=total_appointments)
    col2.metric(label="Awaiting Approval (Pending)", value=pending_count, delta=f"{pending_count} Active" if pending_count > 0 else "Clear")
    col3.metric(label="Scheduled Consultations", value=confirmed_count)
    
    st.markdown("---")
    st.subheader("📈 Case Allocation by Medical Department")
    
    if total_appointments > 0:
        chart_data = df["doctor"].value_counts().reset_index()
        chart_data.columns = ["Department Specialist", "Total Consultations"]
        
        fig = px.bar(
            chart_data, 
            x="Department Specialist", 
            y="Total Consultations", 
            color="Department Specialist",
            title="Active Operations Workload Tracker",
            text_auto=True
        )
        st.plotly_chart(fig)
    else:
        st.info("No appointment logs available to calculate visualizations yet.")
