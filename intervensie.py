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

# ---------------- GitHub Upload Function ---------------- #
@st.cache_data(show_spinner=False)
def upload_file_to_github(file_path, repo, path_in_repo, token, branch="main"):
    """Upload or update a file in a GitHub repository."""
    try:
        url = GITHUB_API_URL.format(repo=repo, path=path_in_repo)
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        # Read file content
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        # Check if file exists
        r = requests.get(url, headers=headers, timeout=10)
        data = {
            "message": f"Update {path_in_repo} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content,
            "branch": branch
        }
        if r.status_code == 200:
            data["sha"] = r.json()["sha"]

        # Upload file
        r = requests.put(url, headers=headers, json=data, timeout=10)
        if r.status_code not in [200, 201]:
            st.error(f"GitHub upload failed: {r.json().get('message', 'Unknown error')}")
            return False
        return True
    except Exception as e:
        st.error(f"GitHub upload error: {str(e)}")
        return False

# ---------------- UI ---------------- #
st.title("HOËRSKOOL SAUL DAMON")
st.subheader("📘 Intervensie Klasse")

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
        if not all([datum, graad, vak, tema, opvoeder, foto, presensie_l, totaal_genooi]):
            st.error("⚠️ Alle velde is verpligtend!")
        elif totaal_opgedaag > totaal_genooi:
            st.error("⚠️ Totaal Opgedaag kan nie meer as Totaal Genooi wees nie!")
        else:
            # Save files with unique names to prevent overwrites
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            foto_ext = os.path.splitext(foto.name)[1]
            pres_ext = os.path.splitext(presensie_l.name)[1]
            foto_path = os.path.join(FOTO_DIR, f"foto_{timestamp}{foto_ext}")
            pres_path = os.path.join(PRES_DIR, f"presensie_{timestamp}{pres_ext}")

            with open(foto_path, "wb") as f:
                f.write(foto.getbuffer())
            with open(pres_path, "wb") as f:
                f.write(presensie_l.getbuffer())

            # Save to CSV
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

            # Upload to GitHub
            try:
                token = st.secrets["GITHUB_TOKEN"]
                repo = st.secrets["GITHUB_REPO"]
                if upload_file_to_github(CSV_FILE, repo, "intervensie_database.csv", token):
                    st.success("✅ Data gestoor en gesinkroniseer met GitHub!")
            except KeyError:
                st.error("⚠️ GitHub konfigurasie ontbreek in secrets!")

# ---------------- Reporting ---------------- #
st.subheader("📊 Verslag")

@st.cache_data
def load_and_filter_data(filter_type):
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
    # Display data with sorting and styling
    st.dataframe(
        df.sort_values("Datum", ascending=False),
        column_config={
            "Datum": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Aanwesigheid %": st.column_config.NumberColumn(format="%.2f%%")
        },
        use_container_width=True
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
                except:
                    doc.add_paragraph("⚠️ Kon nie foto laai nie")
            
            doc.add_paragraph("📑 Presensielys:")
            if pd.notna(row["Presensielys"]) and os.path.exists(row["Presensielys"]):
                ext = row["Presensielys"].split(".")[-1].lower()
                if ext in ["jpg", "jpeg", "png"]:
                    try:
                        doc.add_picture(row["Presensielys"], width=Inches(2))
                    except:
                        doc.add_paragraph("⚠️ Kon nie presensielys beeld laai nie")
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
        file_name="intervensie_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
