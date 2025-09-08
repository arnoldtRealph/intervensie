import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
from github import Github
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
ERROR_LOG_FILE = "error_log.txt"
FOTO_DIR = "fotos"
PRES_DIR = "presensies"
GRADE_OPTIONS = ["8", "9", "10", "11", "12"]

# Initialize directories and CSV
for directory in [FOTO_DIR, PRES_DIR]:
    os.makedirs(directory, exist_ok=True)

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=[
        "Datum", "Graad", "Vak", "Tema", "Totaal Genooi", 
        "Totaal Opgedaag", "Opvoeder", "Foto", "Presensielys"
    ]).to_csv(CSV_FILE, index=False)

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
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(f"Log save failed: {str(e)} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        return False

# ---------------- GitHub Upload Function ---------------- #
def upload_file_to_github(file_path, repo_name, path_in_repo, token):
    """Upload or update a file in a GitHub repository using PyGithub."""
    try:
        log_action("GitHub Upload Attempt", f"File: {path_in_repo}, Repo: {repo_name}", "INFO")
        if not token or token.strip() == "":
            log_action("GitHub Upload Failed", "Empty or missing token", "ERROR")
            st.error("⚠️ GitHub token is leeg of ontbreek!")
            return False

        g = Github(token)
        repo = g.get_repo(repo_name)

        if not os.path.exists(file_path):
            log_action("GitHub Upload Failed", f"Local file not found: {file_path}", "ERROR")
            st.error(f"⚠️ Lokale lêer nie gevind nie: {file_path}")
            return False

        with open(file_path, "rb") as file:
            content = file.read()

        repo_path = path_in_repo
        try:
            contents = repo.get_contents(repo_path, ref="master")
            repo.update_file(
                path=repo_path,
                message=f"Updated {repo_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content=content,
                sha=contents.sha,
                branch="master"
            )
            log_action("GitHub Upload Success", f"Updated existing file: {repo_path}", "SUCCESS")
        except:
            repo.create_file(
                path=repo_path,
                message=f"Created {repo_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content=content,
                branch="master"
            )
            log_action("GitHub Upload Success", f"Created new file: {repo_path}", "SUCCESS")
        return True
    except Exception as e:
        error_msg = str(e)
        log_action("GitHub Upload Failed", f"Error: {error_msg}", "ERROR")
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(f"GitHub push failed: {error_msg} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        st.error(f"⚠️ GitHub upload misluk: {error_msg}")
        return False

# ---------------- UI ---------------- #
st.title("HOËRSKOOL SAUL DAMON")
st.subheader("📘 Intervensie Klasse")

# Log Display on Homepage
st.subheader("📋 Logs")
if os.path.exists(LOG_FILE):
    log_df = pd.read_csv(LOG_FILE)
    if not log_df.empty:
        recent_logs = log_df.tail(20).sort_values("Timestamp", ascending=False)
        st.dataframe(
            recent_logs,
            column_config={
                "Timestamp": st.column_config.DateColumn(format="YYYY-MM-DD HH:mm:ss"),
                "Status": st.column_config.SelectboxColumn(options=["INFO", "SUCCESS", "ERROR", "WARNING"])
            },
            use_container_width=True,
            height=400
        )
        # Log statistics
        status_counts = log_df["Status"].value_counts()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Totaal Logs", len(log_df))
        with col2:
            st.metric("Sukses", status_counts.get("SUCCESS", 0))
        with col3:
            st.metric("Foute", status_counts.get("ERROR", 0))
    else:
        st.info("ℹ️ Nog geen log items nie.")
else:
    st.info("ℹ️ Log lêer nie gevind nie.")

# [Rest of the code remains unchanged: Form, Reporting, and Word document generation]
# For brevity, include only the Word document generation and download section to confirm the fix
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
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# Download button
if not df.empty:
    try:
        doc_bytes = generate_word_report(df)
        st.download_button(
            label="⬇️ Laai Verslag af (Word)",
            data=doc_bytes,
            file_name=f"intervensie_report_{datetime.now().strftime('%Y%m%d')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="download_word_report"
        )
    except Exception as e:
        log_action("Word Report Download Failed", f"Error: {str(e)}", "ERROR")
        st.error(f"⚠️ Fout met verslag aflaai: {str(e)}")
