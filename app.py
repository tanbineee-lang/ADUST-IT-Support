import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="ADUST IT Support Desk",
    page_icon="💻",
    layout="wide"
)

# ---------------------------------------------------------
# DATABASE CONNECTION HANDLING (Supabase Cloud or SQLite Local)
# ---------------------------------------------------------
# Check if Supabase connection settings exist in Streamlit secrets (.streamlit/secrets.toml)
USE_SUPABASE = "supabase" in st.secrets if hasattr(st, "secrets") else False

if USE_SUPABASE:
    from supabase import create_client
    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]
    supabase = create_client(supabase_url, supabase_key)

LOCAL_DB_FILE = "it_tickets.db"

def init_db():
    """Initialize local SQLite database if not using Supabase."""
    if not USE_SUPABASE:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                category TEXT NOT NULL,
                issue_title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'Open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

def create_ticket(name, email, role, dept, category, title, desc):
    """Insert a new support ticket into the database."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if USE_SUPABASE:
        data = {
            "user_name": name,
            "user_email": email,
            "role": role,
            "department": dept,
            "category": category,
            "issue_title": title,
            "description": desc,
            "status": "Open",
            "created_at": now,
            "updated_at": now
        }
        res = supabase.table("tickets").insert(data).execute()
        ticket_id = res.data[0]["ticket_id"]
        return ticket_id
    else:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO tickets (user_name, user_email, role, department, category, issue_title, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?)
        ''', (name, email, role, dept, category, title, desc, now, now))
        conn.commit()
        ticket_id = c.lastrowid
        conn.close()
        return ticket_id

def fetch_ticket_by_id(ticket_id):
    """Fetch details of a specific ticket."""
    if USE_SUPABASE:
        res = supabase.table("tickets").select("*").eq("ticket_id", ticket_id).execute()
        if res.data:
            return res.data[0]
        return None
    else:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        record = c.fetchone()
        conn.close()
        if record:
            return {
                "ticket_id": record[0],
                "user_name": record[1],
                "user_email": record[2],
                "role": record[3],
                "department": record[4],
                "category": record[5],
                "issue_title": record[6],
                "description": record[7],
                "status": record[8],
                "created_at": record[9],
                "updated_at": record[10]
            }
        return None

def get_all_tickets_df():
    """Retrieve all tickets as a Pandas DataFrame for the admin dashboard."""
    if USE_SUPABASE:
        res = supabase.table("tickets").select("*").order("ticket_id", desc=True).execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame()
    else:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        df = pd.read_sql_query("SELECT * FROM tickets ORDER BY ticket_id DESC", conn)
        conn.close()
        return df

def update_ticket_status(ticket_id, new_status):
    """Update the status of a specific ticket."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if USE_SUPABASE:
        supabase.table("tickets").update({"status": new_status, "updated_at": now}).eq("ticket_id", ticket_id).execute()
    else:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?", (new_status, now, ticket_id))
        conn.commit()
        conn.close()

# Initialize Local Database
init_db()

# ---------------------------------------------------------
# INTERFACE & LAYOUT
# ---------------------------------------------------------
st.title("💻 ADUST IT Support Ticket Portal")

if USE_SUPABASE:
    st.caption("🟢 Database Mode: **Supabase Cloud Database**")
else:
    st.caption("🟡 Database Mode: **Local SQLite Database**")

tab1, tab2, tab3 = st.tabs(["📌 Submit Support Request", "🔍 Track Ticket Status", "⚙️ IT Admin Dashboard"])

# ---------------------------------------------------------
# TAB 1: TICKET SUBMISSION FORM
# ---------------------------------------------------------
with tab1:
    st.subheader("Submit a New IT Support Request")
    st.write("Fill out the form below to register an IT support issue. You will receive a unique Ticket ID to track progress.")
    
    with st.form("ticket_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name *")
            email = st.text_input("University Email *")
            role = st.selectbox("Your Role *", ["Faculty", "Management", "Staff", "Student"])
            
        with col2:
            department = st.text_input("Department / Office Location *")
            category = st.selectbox("Issue Category *", [
                "Hardware (PC, Laptop, Printer)",
                "Network / Wi-Fi / LAN",
                "Software & OS Installation",
                "Email & User Account",
                "Classroom Multimedia / Projector",
                "Other"
            ])
            
        title = st.text_input("Issue Summary / Short Title *")
        description = st.text_area("Detailed Description of the Problem *")
        
        submitted = st.form_submit_button("Submit Ticket")
        
        if submitted:
            if not name.strip() or not email.strip() or not title.strip() or not description.strip():
                st.error("Please fill in all required fields marked with *.")
            else:
                ticket_id = create_ticket(name, email, role, department, category, title, description)
                st.success(f"🎉 Support request submitted! Your Ticket ID is: **#{ticket_id}**")
                st.info("Please save this Ticket ID to check status updates in the 'Track Ticket Status' tab.")

# ---------------------------------------------------------
# TAB 2: TICKET STATUS SEARCH
# ---------------------------------------------------------
with tab2:
    st.subheader("Check Status of Your Request")
    search_id = st.number_input("Enter your Ticket ID:", min_value=1, step=1)
    
    if st.button("Search Ticket"):
        ticket = fetch_ticket_by_id(search_id)
        
        if ticket:
            st.markdown(f"### Ticket #{ticket['ticket_id']}: {ticket['issue_title']}")
            
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Submitted By:** {ticket['user_name']}")
            c2.write(f"**Role/Dept:** {ticket['role']} ({ticket['department']})")
            c3.write(f"**Category:** {ticket['category']}")
            
            st.write("---")
            
            # Display status banner
            status = ticket['status']
            if status == "Open":
                st.warning(f"Current Status: **{status}** (Awaiting)")
            elif status == "In Progress":
                st.info(f"Current Status: **{status}** (IT Staff is working on this)")
            elif status == "Resolved":
                st.success(f"Current Status: **{status}** (Issue has been resolved)")
            else:
                st.error(f"Current Status: **{status}**")
                
            st.write(f"**Issue Description:**")
            st.info(ticket['description'])
            
            st.caption(f"Created on: {ticket['created_at']} | Last Updated: {ticket['updated_at']}")
        else:
            st.error(f"No ticket found matching ID #{search_id}.")

# ---------------------------------------------------------
# TAB 3: IT ADMIN DASHBOARD
# ---------------------------------------------------------
with tab3:
    st.subheader("IT Department Operations Center")
    
    # Password Access Control
    admin_passcode = st.text_input("Enter Admin Passcode to Access Management Panel:", type="password")
    
    # You can change this admin password to whatever you like
    if admin_passcode == "admin123":
        st.success("Access Granted")
        
        df_tickets = get_all_tickets_df()
        
        if df_tickets.empty:
            st.info("No tickets currently registered in the database.")
        else:
            # Metric Tiles
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Tickets", len(df_tickets))
            m2.metric("Open Requests", len(df_tickets[df_tickets['status'] == 'Open']))
            m3.metric("In Progress", len(df_tickets[df_tickets['status'] == 'In Progress']))
            m4.metric("Resolved", len(df_tickets[df_tickets['status'] == 'Resolved']))
            
            st.divider()
            
            # Status Update Form
            st.markdown("### ✏️ Update Ticket Status")
            col_sel1, col_sel2, col_btn = st.columns([2, 2, 1])
            
            ticket_options = df_tickets['ticket_id'].tolist()
            
            with col_sel1:
                selected_id = st.selectbox("Select Ticket ID:", ticket_options)
            with col_sel2:
                new_status_val = st.selectbox("Assign New Status:", ["Open", "In Progress", "Resolved", "Closed"])
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Apply Update"):
                    update_ticket_status(selected_id, new_status_val)
                    st.success(f"Updated Ticket #{selected_id} to '{new_status_val}'")
                    st.rerun()
            
            st.divider()
            
            # Comprehensive Table View
            st.markdown("### 📋 All Registered Support Requests")
            st.dataframe(df_tickets, use_container_width=True)

    elif admin_passcode != "":
        st.error("Incorrect passcode. Access denied.")
