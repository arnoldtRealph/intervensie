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
    initial_sidebar_state="expanded"
)

# Constants
CSV_FILE = "intervensie_database.csv"
LOG_FILE = "app_log.csv"
ERROR_LOG_FILE = "error_log.txt"
FOTO_DIR = "fotos"
PRES_DIR = "presensies"
GRADE_OPTIONS = ["8", "9", "10", "11", "12"]
TIMESLOT_OPTIONS = [
    "08:00 - 10:00",
    "10:00 - 12:00",
    "12:00 - 14:00",
    "14:00 - 16:00",
    "16:00 - 18:00"
]

# Initialize directories and CSV
for directory in [FOTO_DIR, PRES_DIR]:
    os.makedirs(directory, exist_ok=True)

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=[
        "Datum", "Graad", "Vak", "Tema", "Totaal Genooi",
        "Totaal Opgedaag", "Opvoeder", "Tydsgleuf", "Foto", "Presensielys"
    ]).to_csv(CSV_FILE, index=False)

if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["Timestamp", "Action", "Details", "Status"]).to_csv(LOG_FILE, index=False)

# ---------------- Log Functions ---------------- #
def log_action(action, details="", status="INFO"):
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
        except Exception:
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

# ---------------- Helper: safe read attendance file ---------------- #
def read_presensie_to_table(path, max_rows=50):
    try:
        ext = path.split('.')[-1].lower()
        if ext == 'csv':
            df_p = pd.read_csv(path)
        elif ext in ['xls', 'xlsx']:
            df_p = pd.read_excel(path)
        else:
            return None
        if df_p.shape[0] > max_rows:
            return df_p.iloc[:max_rows]
        return df_p
    except Exception as e:
        log_action("Presensie Read Failed", f"{path} - {str(e)}", "WARNING")
        return None

# ---------------- Load Intervention Data ---------------- #
@st.cache_data(ttl=600)
def load_intervention_data():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE)
    if df.empty:
        return df
    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
    df["Aanwesigheid %"] = (df["Totaal Opgedaag"] / df["Totaal Genooi"] * 100).round(2)
    return df.sort_values("Datum", ascending=False)

# ---------------- Load Raw Data ---------------- #
@st.cache_data(ttl=300)
def load_raw():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE)
    if df.empty:
        return df
    df['Datum'] = pd.to_datetime(df['Datum'], errors='coerce')
    return df.sort_values("Datum", ascending=False)

# ---------------- UI ---------------- #
st.title("HOËRSKOOL SAUL DAMON")
st.subheader("📘 Intervensie Klasse")

# Sidebar filters
st.sidebar.header("Filters vir Word Verslag")
filter_type = st.sidebar.selectbox("🔎 Kies tydsfilter", ["Alles", "Weekliks", "Maandeliks", "Kwartaalliks", "Jaarliks"]) 
raw_df = load_raw()

opvoeder_options = ['Alles'] + sorted(raw_df['Opvoeder'].dropna().unique().tolist()) if not raw_df.empty else ['Alles']
vak_options = ['Alles'] + sorted(raw_df['Vak'].dropna().unique().tolist()) if not raw_df.empty else ['Alles']
graad_options = ['Alles'] + GRADE_OPTIONS

selected_opvoeder = st.sidebar.selectbox("Opvoeder", opvoeder_options)
selected_vak = st.sidebar.selectbox("Vak", vak_options)
selected_graad = st.sidebar.selectbox("Graad", graad_options)

# ---------------- Form ---------------- #
with st.form("data_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        datum = st.date_input("📅 Datum", value=datetime.today(), format="YYYY/MM/DD")
        graad = st.selectbox("🎓 Graad", GRADE_OPTIONS, key='form_graad')
        vak = st.text_input("📚 Vak", key='form_vak')
        tema = st.text_input("🎯 Tema", key='form_tema')
        tydsgleuf = st.selectbox("⏰ Kies Tydsgleuf", TIMESLOT_OPTIONS, key="form_tydsgleuf")
    with col2:
        totaal_genooi = st.number_input("👥 Totaal Genooi", min_value=1, step=1, format="%d", key='form_totaal_genooi')
        totaal_opgedaag = st.number_input("✅ Totaal Opgedaag", min_value=0, step=1, format="%d", key='form_totaal_opgedaag')
        opvoeder = st.text_input("👨‍🏫 Opvoeder", key='form_opvoeder')
    
    foto = st.file_uploader("📸 Laai Foto op", type=["jpg", "jpeg", "png"], key='form_foto')
    presensie_l = st.file_uploader("📑 Laai Presensielys op", type=["csv", "xlsx", "pdf", "jpg", "jpeg", "png"], key='form_presensie')

    submitted = st.form_submit_button("➕ Stoor Data")

    if submitted:
        if not all([datum, graad, vak, tema, opvoeder, foto, presensie_l, totaal_genooi, tydsgleuf]):
            st.error("⚠️ Alle velde is verpligtend!")
        elif totaal_opgedaag > totaal_genooi:
            st.error("⚠️ Totaal Opgedaag kan nie meer as Totaal Genooi wees nie!")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            foto_ext = os.path.splitext(foto.name)[1]
            pres_ext = os.path.splitext(presensie_l.name)[1]
            foto_path = os.path.join(FOTO_DIR, f"foto_{timestamp}{foto_ext}")
            pres_path = os.path.join(PRES_DIR, f"presensie_{timestamp}{pres_ext}")

            with open(foto_path, "wb") as f:
                f.write(foto.getbuffer())
            with open(pres_path, "wb") as f:
                f.write(presensie_l.getbuffer())

            new_entry = {
                "Datum": datum.strftime("%Y-%m-%d"),
                "Graad": graad,
                "Vak": vak,
                "Tema": tema,
                "Tydsgleuf": tydsgleuf,
                "Totaal Genooi": int(totaal_genooi),
                "Totaal Opgedaag": int(totaal_opgedaag),
                "Opvoeder": opvoeder,
                "Foto": foto_path,
                "Presensielys": pres_path
            }
            df = pd.read_csv(CSV_FILE)
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)

            token = st.secrets.get("GITHUB_TOKEN")
            repo = st.secrets.get("GITHUB_REPO")
            if token and repo:
                upload_file_to_github(CSV_FILE, repo, "intervensie_database.csv", token)

            st.success("✅ Data gestoor en gesinkroniseer!")
            load_intervention_data.clear()
            load_raw.clear()
            st.rerun()

# ---------------- Log Display ---------------- #
st.subheader("📊 Intervensie Log Inskrywings")
intervention_df = load_intervention_data()

if intervention_df.empty:
    st.info("ℹ️ Geen intervensie inskrywings nie.")
else:
    st.dataframe(
        intervention_df[["Datum", "Graad", "Vak", "Tema", "Tydsgleuf", "Totaal Genooi", "Totaal Opgedaag", "Opvoeder", "Aanwesigheid %"]],
        use_container_width=True
    )

# ---------------- Word Report ---------------- #
st.subheader("📑 Intervensie Verslag Aflaai")

def generate_word_report(df_to_export):
    doc = Document()
    doc.add_heading("Saul Damon High School - Intervensie Verslag", level=1)
    doc.add_paragraph(f"Gegenereer op: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph("")

    if not df_to_export.empty:
        columns = ["Datum", "Graad", "Vak", "Tema", "Tydsgleuf", "Totaal Genooi", "Totaal Opgedaag", "Opvoeder", "Aanwesigheid %"]
        table = doc.add_table(rows=1, cols=len(columns))
        hdr_cells = table.rows[0].cells
        for i, col in enumerate(columns):
            hdr_cells[i].text = col

        for _, row in df_to_export.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = row['Datum'].strftime('%Y-%m-%d')
            row_cells[1].text = str(row['Graad'])
            row_cells[2].text = row['Vak']
            row_cells[3].text = row['Tema']
            row_cells[4].text = row['Tydsgleuf']
            row_cells[5].text = str(row['Totaal Genooi'])
            row_cells[6].text = str(row['Totaal Opgedaag'])
            row_cells[7].text = row['Opvoeder']
            row_cells[8].text = f"{row['Aanwesigheid %']:.2f}%"

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

try:
    doc_bytes = generate_word_report(intervention_df)
    st.download_button(
        label="⬇️ Laai Intervensie Verslag af (Word)",
        data=doc_bytes,
        file_name=f"intervensie_report_{datetime.now().strftime('%Y%m%d')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
except Exception as e:
    st.error(f"⚠️ Fout met verslag aflaai: {str(e)}")
