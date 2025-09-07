```python
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
import base64
import requests
from io import BytesIO

# ---------------- Config ---------------- #
st.set_page_config(
    page_title="HOËRSKOOL SAUL DAMON: INTERVENSIE KLASSE",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
CSV_FILE = "intervensie_database.csv"
LOG_FILE = "app_log.csv"
FOTO_DIR = "fotos"
PRES_DIR = "presensies"
GITHUB_API_URL = "https://api.github.com/repos/{repo}/contents/{path}"
GRADE_OPTIONS = ["8", "9", "10", "11", "12"]

# Initialize directories and CSV
for directory in [FOTO_DIR, PRES_DIR]:
    os.makedirs(directory, exist_ok=True)

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=[
        "Datum", "Graad", "Vak", "Tema", "Totaal Genooi", 
        "Totaal Opgedaag", "Opvoeder", "Foto", "Presensielys"
    ]).to_csv(CSV_FILE, index=False)

# Initialize log file
if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["Timestamp", "Action", "Details", "Status"]).to_csv(LOG_FILE, index=False)

def log_action(action, details="", status="INFO"):
    """Log actions to CSV file."""
    log_entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action": action,
        "Details": details,
        "Status": status
    }
    try:
        df_log = pd.read_csv(LOG_FILE)
        df_log = pd.concat([df_log, pd.DataFrame([log_entry])], ignore_index=True)
        df_log.to_csv(LOG_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Fout met log stoor: {str(e)}")
        return False

# ---------------- GitHub Upload Function ---------------- #
@st.cache_data(show_spinner=False, ttl=300)  # Cache for 5 minutes
def upload_file_to_github(file_path, repo, path_in_repo, token, branch="master"):
    """Upload or update a file in a GitHub repository."""
    try:
        log_action("GitHub Upload Attempt", f"File: {path_in_repo}, Repo: {repo}", "INFO")
        
        # Validate token
        if not token or token.strip() == "":
            log_action("GitHub Upload Failed", "Empty or missing token", "ERROR")
            st.error("⚠️ GitHub token is leeg of ontbreek! Gaan na GitHub → Settings → Developer settings → Personal access tokens en genereer 'n nuwe token met 'repo' scope.")
            return False
        
        url = GITHUB_API_URL.format(repo=repo, path=path_in_repo)
        headers = {
            "Authorization": f"token {token}", 
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

        # Test token validity
        test_url = "https://api.github.com/user"
        test_response = requests.get(test_url, headers=headers, timeout=10)
        if test_response.status_code != 200:
            error_msg = test_response.json().get('message', 'Unknown authentication error')
            if test_response.status_code == 401:
                error_msg += " - Kontroleer of die token korrek is en 'repo' scope het. Gaan na GitHub → Settings → Developer settings → Personal access tokens."
            log_action("GitHub Upload Failed", f"Token validation failed: {error_msg}", "ERROR")
            st.error(f"⚠️ GitHub Token is ongeldig: {error_msg}")
            return False

        # Read file content
        if not os.path.exists(file_path):
            log_action("GitHub Upload Failed", f"Local file not found: {file_path}", "ERROR")
            st.error(f"⚠️ Lokale lêer nie gevind nie: {file_path}")
            return False
            
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        # Check if file exists on GitHub
        r = requests.get(url, headers=headers, timeout=10)
        data = {
            "message": f"Update {path_in_repo} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content,
            "branch": branch
        }
        if r.status_code == 200:
            data["sha"] = r.json()["sha"]
            log_action("GitHub File Exists", f"Found existing file: {path_in_repo}", "INFO")

        # Upload file
        r = requests.put(url, headers=headers, json=data, timeout=10)
        if r.status_code not in [200, 201]:
            error_detail = r.json().get('message', f'HTTP {r.status_code}') if r.content else f'HTTP {r.status_code}'
            log_action("GitHub Upload Failed", f"Upload error: {error_detail}", "ERROR")
            st.error(f"⚠️ GitHub upload misluk: {error_detail}")
            return False
        
        log_action("GitHub Upload Success", f"Successfully uploaded: {path_in_repo}", "SUCCESS")
        return True
        
    except requests.exceptions.Timeout:
        log_action("GitHub Upload Failed", "Request timeout", "ERROR")
        st.error("⚠️ GitHub verbinding het uitgetime-out. Probeer weer.")
        return False
    except requests.exceptions.ConnectionError:
        log_action("GitHub Upload Failed", "Connection error", "ERROR")
        st.error("⚠️ Geen verbinding met GitHub nie. Kontroleer jou internetverbinding.")
        return False
    except Exception as e:
        log_action("GitHub Upload Failed", f"Unexpected error: {str(e)}", "ERROR")
        st.error(f"⚠️ Onverwagte fout: {str(e)}")
        return False

# ---------------- UI ---------------- #
st.title("HOËRSKOOL SAUL DAMON")
st.subheader("📘 Intervensie Klasse")

# Log display in sidebar
st.sidebar.title("📋 Logs")
if os.path.exists(LOG_FILE):
    log_df = pd.read_csv(LOG_FILE)
    if not log_df.empty:
        # Show recent logs (last 20 entries)
        recent_logs = log_df.tail(20).sort_values("Timestamp", ascending=False)
        st.sidebar.dataframe(
            recent_logs,
            column_config={
                "Timestamp": st.column_config.DatimeColumn(format="YYYY-MM-DD HH:mm:ss"),
                "Status": st.column_config.SelectboxColumn(options=["INFO", "SUCCESS", "ERROR", "WARNING"])
            },
            width="stretch",
            height=400
        )
        
        # Log statistics
        status_counts = log_df["Status"].value_counts()
        col1, col2, col3 = st.sidebar.columns(3)
        with col1:
            st.metric("Totaal Logs", len(log_df))
        with col2:
            st.metric("Sukses", status_counts.get("SUCCESS", 0))
        with col3:
            st.metric("Foute", status_counts.get("ERROR", 0))
    else:
        st.sidebar.info("Geen log items nog nie.")
else:
    st.sidebar.info("Log lêer nie gevind nie.")

# Form
with st.form("data_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        datum = st.date_input("📅 Datum", value=datetime.today(), format="YYYY/MM/DD")
        graad = st.selectbox("🎓 Graad", GRADE_OPTIONS)
        vak = st.text_input("📚 Vak")
        tema = st.text_input("🎯 Tema")
    with col2:
        totaal_genooi = st.number_input("👥 Totaal Genooi", min_value=1, step=1, format="%d")
        totaal_opgedaag = st.number_input("✅ Totaal Opgedaag", min_value=0, step=1, format="%d")
        opvoeder = st.text_input("👨‍🏫 Opvoeder")
    
    foto = st.file_uploader("📸 Laai Foto op", type=["jpg", "jpeg", "png"])
    presensie_l = st.file_uploader(
        "📑 Laai Presensielys op", 
        type=["csv", "xlsx", "pdf", "jpg", "jpeg", "png"]
    )

    submitted = st.form_submit_button("➕ Stoor Data")

    if submitted:
        log_action("Form Submission", f"Submitted by: {opvoeder}", "INFO")
        
        if not all([datum, graad, vak, tema, opvoeder, foto, presensie_l, totaal_genooi]):
            log_action("Form Validation Failed", "Missing required fields", "WARNING")
            st.error("⚠️ Alle velde is verpligtend!")
        elif totaal_opgedaag > totaal_genooi:
            log_action("Form Validation Failed", f"Attendance ({totaal_opgedaag}) > Total ({totaal_genooi})", "WARNING")
            st.error("⚠️ Totaal Opgedaag kan nie meer as Totaal Genooi wees nie!")
        else:
            log_action("File Processing", f"Saving files for {vak} - {tema}", "INFO")
            
            # Save files with unique names to prevent overwrites
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            foto_ext = os.path.splitext(foto.name)[1]
            pres_ext = os.path.splitext(presensie_l.name)[1]
            foto_path = os.path.join(FOTO_DIR, f"foto_{timestamp}{foto_ext}")
            pres_path = os.path.join(PRES_DIR, f"presensie_{timestamp}{pres_ext}")

            try:
                with open(foto_path, "wb") as f:
                    f.write(foto.getbuffer())
                log_action("File Save Success", f"Photo saved: {foto_path}", "SUCCESS")
            except Exception as e:
                log_action("File Save Failed", f"Photo save error: {str(e)}", "ERROR")
                st.error(f"⚠️ Fout met foto stoor: {str(e)}")

            try:
                with open(pres_path, "wb") as f:
                    f.write(presensie_l.getbuffer())
                log_action("File Save Success", f"Attendance sheet saved: {pres_path}", "SUCCESS")
            except Exception as e:
                log_action("File Save Failed", f"Attendance sheet save error: {str(e)}", "ERROR")
                st.error(f"⚠️ Fout met presensielys stoor: {str(e)}")

            # Save to CSV
            try:
                new_entry = {
                    "Datum": datum.strftime("%Y-%m-%d"),
                    "Graad": graad,
                    "Vak": vak,
                    "Tema": tema,
                    "Totaal Genooi": totaal_genooi,
                    "Totaal Opgedaag": totaal_opgedaag,
                    "Opvoeder": opvoeder,
                    "Foto": foto_path,
                    "Presensielys": pres_path
                }
                df = pd.read_csv(CSV_FILE)
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                log_action("Database Update Success", f"Added entry for {datum.strftime('%Y-%m-%d')} - {vak}", "SUCCESS")
            except Exception as e:
                log_action("Database Update Failed", f"CSV error: {str(e)}", "ERROR")
                st.error(f"⚠️ Fout met databasis stoor: {str(e)}")
                st.stop()  # Stop execution if database save fails

            # Upload to GitHub
            try:
                token = st.secrets.get("GITHUB_TOKEN")
                repo = st.secrets.get("GITHUB_REPO")
                
                if not token or not repo:
                    log_action("GitHub Config Missing", f"Token: {bool(token)}, Repo: {bool(repo)}", "WARNING")
                    st.warning("⚠️ GitHub konfigurasie ontbreek in secrets. Data is lokaal gestoor. Gaan na .streamlit/secrets.toml en voeg GITHUB_TOKEN en GITHUB_REPO by.")
                elif upload_file_to_github(CSV_FILE, repo, "intervensie_database.csv", token, branch="master"):
                    log_action("Sync Complete", "All operations successful", "SUCCESS")
                    st.success("✅ Data gestoor en gesinkroniseer met GitHub!")
                else:
                    log_action("Sync Incomplete", "GitHub sync failed but data saved locally", "WARNING")
                    st.warning("⚠️ Data lokaal gestoor, maar GitHub sinkronisasie misluk.")
                    
            except KeyError as e:
                log_action("GitHub Secrets Error", f"Missing secret: {str(e)}", "ERROR")
                st.error("⚠️ GitHub konfigurasie ontbreek in secrets! Gaan na .streamlit/secrets.toml en voeg GITHUB_TOKEN en GITHUB_REPO by.")
            except Exception as e:
                log_action("GitHub Unexpected Error", f"Sync error: {str(e)}", "ERROR")
                st.error(f"⚠️ Onverwagte GitHub fout: {str(e)}")

# ---------------- Reporting ---------------- #
st.subheader("📊 Verslag")

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_and_filter_data(filter_type):
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
    
    df = pd.read_csv(CSV_FILE)
    if df.empty:
        return df
    
    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
    df["Aanwesigheid %"] = (df["Totaal Opgedaag"] / df["Totaal Genooi"] * 100).round(2)
    
    today = datetime.today()
    if filter_type == "Weekliks":
        start = today - timedelta(days=7)
        df = df[df["Datum"] >= start]
    elif filter_type == "Maandeliks":
        start = today - timedelta(days=30)
        df = df[df["Datum"] >= start]
    elif filter_type == "Kwartaalliks":
        start = today - timedelta(days=90)
        df = df[df["Datum"] >= start]
    return df

# Filters
filter_type = st.selectbox("🔎 Kies filter", ["Alles", "Weekliks", "Maandeliks", "Kwartaalliks"])
df = load_and_filter_data(filter_type)

if df.empty:
    st.info("ℹ️ Nog geen data beskikbaar nie.")
else:
    log_action("Report Generated", f"Filter: {filter_type}, Records: {len(df)}", "INFO")
    
    # Display data with sorting and styling
    st.dataframe(
        df.sort_values("Datum", ascending=False),
        column_config={
            "Datum": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Aanwesigheid %": st.column_config.NumberColumn(format="%.2f%%"),
            "Graad": st.column_config.SelectboxColumn(options=GRADE_OPTIONS)
        },
        width="stretch"
    )

    # Generate Word report
    def generate_word_report(df):
        doc = Document()
        doc.add_heading("Saul Damon High School - Intervensie Verslag", level=1)
        doc.add_paragraph(f"Filter: {filter_type}")
        doc.add_paragraph(f"Gegenereer op: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        for _, row in df.iterrows():
            doc.add_paragraph(f"📅 Datum: {row['Datum'].strftime('%Y-%m-%d')}")
            doc.add_paragraph(f"🎓 Graad: {row['Graad']}")
            doc.add_paragraph(f"📚 Vak: {row['Vak']}")
            doc.add_paragraph(f"🎯 Tema: {row['Tema']}")
            doc.add_paragraph(f"👥 Totaal Genooi: {row['Totaal Genooi']}")
            doc.add_paragraph(f"✅ Totaal Opgedaag: {row['Totaal Opgedaag']}")
            doc.add_paragraph(f"👨‍🏫 Opvoeder: {row['Opvoeder']}")
            doc.add_paragraph(f"📈 Aanwesigheid: {row['Aanwesigheid %']:.2f}%")
            
            if pd.notna(row["Foto"]) and os.path.exists(row["Foto"]):
                try:
                    doc.add_picture(row["Foto"], width=Inches(2))
                except Exception as e:
                    doc.add_paragraph(f"⚠️ Kon nie foto laai nie: {str(e)}")
            
            doc.add_paragraph("📑 Presensielys:")
            if pd.notna(row["Presensielys"]) and os.path.exists(row["Presensielys"]):
                ext = row["Presensielys"].split(".")[-1].lower()
                if ext in ["jpg", "jpeg", "png"]:
                    try:
                        doc.add_picture(row["Presensielys"], width=Inches(2))
                    except Exception as e:
                        doc.add_paragraph(f"⚠️ Kon nie presensielys beeld laai nie: {str(e)}")
                else:
                    doc.add_paragraph(f"  → {os.path.basename(row['Presensielys'])}")
            else:
                doc.add_paragraph("Geen presensielys opgelaai")
            
            doc.add_paragraph("-" * 30)
        
        # Save to BytesIO for download
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    # Download button
    buffer = generate_word_report(df)
    st.download_button(
        "⬇️ Laai Verslag af (Word)",
        buffer,
        file_name=f"intervensie_report_{datetime.now().strftime('%Y%m%d')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
```
