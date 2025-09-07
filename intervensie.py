import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
import base64
import requests

# ---------------- GitHub Upload Function ---------------- #
def upload_file_to_github(file_path, repo, path_in_repo, token, branch="master"):
    """Upload or update a file in a GitHub repository."""
    url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
    headers = {"Authorization": f"token {token}"}

    # Check if file exists on GitHub
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json()["sha"]
    else:
        sha = None

    with open(file_path, "rb") as f:
        content = f.read()

    data = {
        "message": f"Update {path_in_repo}",
        "content": base64.b64encode(content).decode("utf-8"),
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    r = requests.put(url, headers=headers, json=data)
    if r.status_code not in [200, 201]:
        st.error(f"GitHub upload failed: {r.json()}")
    else:
        st.success("📤 Data successfully synced to GitHub!")

# ---------------- Config ---------------- #
st.set_page_config(page_title="HOËRSKOOL SAUL DAMON: INTERVENSIE KLASSE", layout="wide")

csv_file = "intervensie_database.csv"
foto_dir = "fotos"
pres_dir = "presensies"
os.makedirs(foto_dir, exist_ok=True)
os.makedirs(pres_dir, exist_ok=True)

# Ensure CSV exists
if not os.path.exists(csv_file):
    df = pd.DataFrame(columns=[
        "Datum", "Vak", "Tema", "Totaal Genooi", "Totaal Opgedaag",
        "Opvoeder", "Foto", "Presensielys"
    ])
    df.to_csv(csv_file, index=False)

# ---------------- UI ---------------- #
st.title("HOËRSKOOL SAUL DAMON")
st.subheader("📘 Intervensie Klasse")

with st.form("data_form", clear_on_submit=True):
    datum = st.date_input("📅 Datum", value=datetime.today())
    vak = st.text_input("📚 Vak")
    tema = st.text_input("🎯 Tema")
    totaal_genooi = st.number_input("👥 Totaal Genooi", min_value=1, step=1)
    totaal_opgedaag = st.number_input("✅ Totaal Opgedaag", min_value=0, step=1)
    opvoeder = st.text_input("👨‍🏫 Opvoeder")

    foto = st.file_uploader("Laai Foto op", type=["jpg", "jpeg", "png"])
    presensie_l = st.file_uploader(
        "Laai Presensielys op (CSV, Excel, PDF of Foto)",
        type=["csv", "xlsx", "pdf", "jpg", "jpeg", "png"]
    )

    submitted = st.form_submit_button("➕ Stoor Data")

    if submitted:
        # Validation - all fields required
        if not (vak and tema and opvoeder and foto and presensie_l and totaal_genooi > 0):
            st.error("⚠️ Alle velde is verpligtend! Vul asseblief alles in.")
        else:
            # Save files
            foto_path = os.path.join(foto_dir, foto.name)
            with open(foto_path, "wb") as f:
                f.write(foto.getbuffer())

            pres_path = os.path.join(pres_dir, presensie_l.name)
            with open(pres_path, "wb") as f:
                f.write(presensie_l.getbuffer())

            # Save to CSV
            new_entry = {
                "Datum": datum.strftime("%Y-%m-%d"),
                "Vak": vak,
                "Tema": tema,
                "Totaal Genooi": totaal_genooi,
                "Totaal Opgedaag": totaal_opgedaag,
                "Opvoeder": opvoeder,
                "Foto": foto_path,
                "Presensielys": pres_path
            }
            df = pd.read_csv(csv_file)
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(csv_file, index=False)

            # Upload CSV to GitHub automatically
            token = st.secrets["GITHUB_TOKEN"]
            repo = st.secrets["GITHUB_REPO"]  # bv. "arnoldtRealph/intervensie"
            upload_file_to_github(csv_file, repo, "intervensie_database.csv", token)

            st.success("✅ Data gestoor en gesinkroniseer met GitHub!")

# ---------------- Reporting ---------------- #
st.subheader("📊 Verslag")

df = pd.read_csv(csv_file)
if not df.empty:
    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
    df["Aanwesigheid %"] = (df["Totaal Opgedaag"] / df["Totaal Genooi"]) * 100

    # Filters
    filter_type = st.selectbox("🔎 Kies filter", ["Alles", "Weekliks", "Maandeliks", "Kwartaalliks"])
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

    if df.empty:
        st.warning("⚠️ Geen data vir hierdie periode nie.")
    else:
        st.dataframe(df)

        # Word verslag
        doc = Document()
        doc.add_heading("Saul Damon High School - Intervensie Verslag", level=1)
        doc.add_paragraph(f"Filter: {filter_type}")
        doc.add_paragraph(f"Gegenereer op: {today.strftime('%Y-%m-%d %H:%M')}")
        doc.add_paragraph("")

        for _, row in df.iterrows():
            doc.add_paragraph(f"📅 Datum: {row['Datum'].strftime('%Y-%m-%d')}")
            doc.add_paragraph(f"📚 Vak: {row['Vak']}")
            doc.add_paragraph(f"🎯 Tema: {row['Tema']}")
            doc.add_paragraph(f"👥 Totaal Genooi: {row['Totaal Genooi']}")
            doc.add_paragraph(f"✅ Totaal Opgedaag: {row['Totaal Opgedaag']}")
            doc.add_paragraph(f"👨‍🏫 Opvoeder: {row['Opvoeder']}")
            doc.add_paragraph(f"📈 Aanwesigheid: {row['Aanwesigheid %']:.2f}%")

            if pd.notna(row["Foto"]) and os.path.exists(row["Foto"]):
                doc.add_picture(row["Foto"], width=Inches(2))

            doc.add_paragraph("📑 Presensielys:")
            if pd.notna(row["Presensielys"]) and os.path.exists(row["Presensielys"]):
                ext = row["Presensielys"].split(".")[-1].lower()
                if ext in ["jpg", "jpeg", "png"]:
                    doc.add_picture(row["Presensielys"], width=Inches(2))
                else:
                    doc.add_paragraph(f"  → {os.path.basename(row['Presensielys'])}")
            else:
                doc.add_paragraph("Geen presensielys opgelaai")

            doc.add_paragraph("---------------------------")

        word_path = "intervensie_report.docx"
        doc.save(word_path)

        with open(word_path, "rb") as f:
            st.download_button("⬇️ Laai Verslag af (Word)", f, file_name="intervensie_report.docx")
else:
    st.info("Nog geen data beskikbaar nie.")
