# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
from docx import Document
from docx.shared import Inches
import base64
import requests

# --------------------
# Page Setup
# --------------------
st.set_page_config(page_title="Intervensie Verslag", layout="wide")
st.title("📘 Saul Damon High School")
st.subheader("Intervensie Klasse")
st.write("Welkom — vul die besonderhede in en stoor. Gebruik die filters om tydperke te kies en laai 'n Word verslag af.")

# --------------------
# Files & CSV Setup
# --------------------
CSV_FILE = "intervensie_database.csv"
PHOTO_DIR = "fotos"
PRES_DIR = "presensies"

os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(PRES_DIR, exist_ok=True)

# Default columns (ensure Presensielys kolom)
DEFAULT_COLUMNS = ["Datum", "Vak", "Tema", "Totaal Genooi", "Totaal Opgedaag", "Opvoeder", "Foto", "Presensielys", "Opkoms %"]

if not os.path.exists(CSV_FILE):
    df_empty = pd.DataFrame(columns=DEFAULT_COLUMNS)
    df_empty.to_csv(CSV_FILE, index=False)

# --------------------
# Helper: GitHub upload (CSV only)
# --------------------
def upload_file_to_github(local_path, repo, path_in_repo, token, branch="main", commit_message="Update intervensie CSV"):
    """
    Upload or update a file in GitHub repo via contents API.
    repo: "https://github.com/arnoldtRealph/intervensie"
    path_in_repo: "folder/filename.csv"
    token: personal access token (store in st.secrets)
    """
    if not token or not repo:
        st.warning("GitHub token of repo nie geset nie — sal nie na GitHub push nie.")
        return False

    url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
    with open(local_path, "rb") as f:
        content = f.read()
    encoded = base64.b64encode(content).decode()

    # Check if file exists to get sha
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    sha = None
    if r.status_code == 200:
        try:
            sha = r.json().get("sha")
        except Exception:
            sha = None

    data = {
        "message": commit_message,
        "content": encoded,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    r = requests.put(url, headers=headers, json=data)
    if r.status_code in (200, 201):
        return True
    else:
        st.error(f"GitHub upload misluk: {r.status_code} — {r.text[:300]}")
        return False

# --------------------
# Helper: create chart (returns BytesIO png)
# --------------------
def create_bar_chart(df):
    fig, ax = plt.subplots(figsize=(8,4))
    # group by date or vak depending on rows count
    if len(df) <= 10:
        x = df["Datum"].dt.strftime("%Y-%m-%d")
        df_plot = df.set_index(x)[["Totaal Genooi", "Totaal Opgedaag"]]
        df_plot.plot(kind="bar", ax=ax)
        ax.set_xlabel("Datum")
    else:
        df_group = df.groupby(df["Datum"].dt.to_period("M")).sum()
        df_group.index = df_group.index.astype(str)
        df_group[["Totaal Genooi", "Totaal Opgedaag"]].plot(kind="bar", ax=ax)
        ax.set_xlabel("Periode")
    ax.set_ylabel("Aantal")
    ax.set_title("Genooi vs Opgedaag")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf

# --------------------
# Load data
# --------------------
df = pd.read_csv(CSV_FILE)
# Ensure columns exist
for col in DEFAULT_COLUMNS:
    if col not in df.columns:
        df[col] = ""

# Convert Datum to datetime where possible
if not df.empty:
    try:
        df["Datum"] = pd.to_datetime(df["Datum"])
    except Exception:
        # keep as string if parse fails
        pass

# --------------------
# Layout: Tabs
# --------------------
tab1, tab2 = st.tabs(["📋 Data Invoer & Verslag", "🛠️ Hulpmiddels / Instellings"])

with tab1:
    st.header("➕ Nuwe Intervensie Invoer")
    with st.form("invoer_form", clear_on_submit=True):
        datum = st.date_input("Datum", datetime.today())
        vak = st.text_input("Vak")
        tema = st.text_input("Tema")
        totaal_genooi = st.number_input("Totaal Genooi", min_value=0, step=1, value=0)
        totaal_opgedaag = st.number_input("Totaal Opgedaag", min_value=0, step=1, value=0)
        opvoeder = st.text_input("Opvoeder")
        foto = st.file_uploader("Laai Foto op (opsioneel)", type=["png","jpg","jpeg"])
        presensie_l = st.file_uploader("Laai Presensielys op (CSV, XLSX, PDF of Foto) (opsioneel)", type=["csv","xlsx","pdf","png","jpg","jpeg"])
        submitted = st.form_submit_button("Stoor Invoer")

        if submitted:
            # Load current df fresh
            df = pd.read_csv(CSV_FILE)
            # Save foto
            foto_path = ""
            if foto is not None:
                foto_path = os.path.join(PHOTO_DIR, foto.name)
                try:
                    with open(foto_path, "wb") as f:
                        f.write(foto.getbuffer())
                except Exception as e:
                    st.error(f"Kon foto nie stoor nie: {e}")
                    foto_path = ""

            # Save presensielys file
            pres_path = ""
            if presensie_l is not None:
                pres_path = os.path.join(PRES_DIR, presensie_l.name)
                try:
                    with open(pres_path, "wb") as f:
                        f.write(presensie_l.getbuffer())
                except Exception as e:
                    st.error(f"Kon presensielys nie stoor nie: {e}")
                    pres_path = ""

            # compute attendance %
            opkoms_persent = (totaal_opgedaag / totaal_genooi * 100) if totaal_genooi and totaal_genooi > 0 else 0.0

            new_entry = {
                "Datum": datum.strftime("%Y-%m-%d"),
                "Vak": vak,
                "Tema": tema,
                "Totaal Genooi": int(totaal_genooi),
                "Totaal Opgedaag": int(totaal_opgedaag),
                "Opvoeder": opvoeder,
                "Foto": foto_path,
                "Presensielys": pres_path,
                "Opkoms %": round(opkoms_persent, 2)
            }

            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            # Save locally
            df.to_csv(CSV_FILE, index=False)
            st.success("Invoer gestoor plaaslik ✅")

            # Optionally push CSV to GitHub if secrets exist
            gh_token = st.secrets.get("GITHUB_TOKEN") if hasattr(st, "secrets") else None
            gh_repo = st.secrets.get("GITHUB_REPO") if hasattr(st, "secrets") else None
            if gh_token and gh_repo:
                ok = upload_file_to_github(CSV_FILE, repo=gh_repo, path_in_repo=os.path.basename(CSV_FILE), token=gh_token)
                if ok:
                    st.success("CSV ook na GitHub gestuur ✅")
            else:
                st.info("GitHub sync: geen token/repo in secrets. Slaan slegs plaaslik op.")

    st.divider()

    st.header("📊 Filters & Data")
    df = pd.read_csv(CSV_FILE)
    if not df.empty:
        df["Datum"] = pd.to_datetime(df["Datum"])
    else:
        st.info("Geen data nog nie. Voeg 'n inskrywing by.")

    # Filter keuse
    filter_type = st.selectbox("Kies tydperk om te filter", ["Alles", "Weekliks", "Maandeliks", "Kwartaalliks"])
    filtered_df = df.copy()
    if not df.empty:
        today = datetime.today()
        if filter_type == "Weekliks":
            start = today - timedelta(days=7)
            filtered_df = df[df["Datum"] >= start]
        elif filter_type == "Maandeliks":
            start = today - timedelta(days=30)
            filtered_df = df[df["Datum"] >= start]
        elif filter_type == "Kwartaalliks":
            start = today - timedelta(days=90)
            filtered_df = df[df["Datum"] >= start]

    st.subheader("Gefilterde Data")
    st.dataframe(filtered_df.reset_index(drop=True))

    # Metrics & chart
    if not filtered_df.empty:
        totaal_sessies = len(filtered_df)
        totaal_genooi = filtered_df["Totaal Genooi"].sum()
        totaal_opgedaag = filtered_df["Totaal Opgedaag"].sum()
        avg_attendance = filtered_df["Opkoms %"].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Totaal Sessies", int(totaal_sessies))
        col2.metric("Totaal Genooi", int(totaalt := totaal_genooi))
        col3.metric("Totaal Opgedaag", int(totaal_op := totaal_opgedaag))
        col4.metric("Gem. Opkoms %", f"{avg_attendance:.2f}%")

        st.subheader("Grafiek: Genooi vs Opgedaag")
        chart_buf = create_bar_chart(filtered_df)
        st.image(chart_buf)

    # Export buttons
    st.divider()
    st.header("⤓ Laai Verslag Af")

    if not filtered_df.empty:
        def create_word_bytes(df_for_doc):
            doc = Document()
            doc.add_heading("Saul Damon High School", level=1)
            doc.add_heading("Intervensie Klasse - Verslag", level=2)
            doc.add_paragraph(f"Datum van genereer: {datetime.today().strftime('%Y-%m-%d %H:%M')}")
            doc.add_paragraph(f"Periode filter: {filter_type}")
            doc.add_paragraph("")

            # Opsommingstabel
            totaal_sessies = len(df_for_doc)
            totaal_genooi = df_for_doc["Totaal Genooi"].sum()
            totaal_opgedaag = df_for_doc["Totaal Opgedaag"].sum()
            avg_attendance = df_for_doc["Opkoms %"].mean()

            doc.add_heading("Opsomming", level=2)
            table = doc.add_table(rows=5, cols=2)
            table.style = "Light Grid"
            table.cell(0,0).text = "Totaal Sessies"
            table.cell(0,1).text = str(totaal_sessies)
            table.cell(1,0).text = "Totaal Genooi"
            table.cell(1,1).text = str(totaal_genooi)
            table.cell(2,0).text = "Totaal Opgedaag"
            table.cell(2,1).text = str(totaal_opgedaag)
            table.cell(3,0).text = "Gem. Opkoms %"
            table.cell(3,1).text = f"{avg_attendance:.2f}%"
            table.cell(4,0).text = "Periode"
            table.cell(4,1).text = filter_type
            doc.add_paragraph("")

            # Detail inskrywings
            doc.add_heading("Besonderhede", level=2)
            for _, row in df_for_doc.iterrows():
                # some fields might be NaN
                date_str = pd.to_datetime(row["Datum"]).strftime("%Y-%m-%d") if pd.notna(row["Datum"]) else str(row.get("Datum",""))
                doc.add_paragraph(f"Datum: {date_str}")
                doc.add_paragraph(f"Vak: {row.get('Vak','')}")
                doc.add_paragraph(f"Tema: {row.get('Tema','')}")
                doc.add_paragraph(f"Totaal Genooi: {int(row.get('Totaal Genooi',0))}")
                doc.add_paragraph(f"Totaal Opgedaag: {int(row.get('Totaal Opgedaag',0))}")
                doc.add_paragraph(f"Opvoeder: {row.get('Opvoeder','')}")
                doc.add_paragraph(f"Opkoms %: {row.get('Opkoms %',0):.2f}%")

                # Foto
                foto_p = row.get("Foto","")
                if isinstance(foto_p, str) and foto_p and os.path.exists(foto_p):
                    try:
                        doc.add_paragraph("Foto:")
                        doc.add_picture(foto_p, width=Inches(3))
                    except Exception:
                        doc.add_paragraph("(Kon nie foto in voeg nie)")

                # Presensielys
                pres_p = row.get("Presensielys","")
                if isinstance(pres_p, str) and pres_p and os.path.exists(pres_p):
                    ext = pres_p.split(".")[-1].lower()
                    if ext in ["jpg","jpeg","png"]:
                        try:
                            doc.add_paragraph("Presensielys (beeld):")
                            doc.add_picture(pres_p, width=Inches(4))
                        except Exception:
                            doc.add_paragraph(f"Presensielys lêer: {os.path.basename(pres_p)} (kon nie beeld invoeg nie)")
                    else:
                        doc.add_paragraph(f"Presensielys lêer: {os.path.basename(pres_p)}")
                else:
                    doc.add_paragraph("Presensielys: Geen opgelaaide lêer")

                doc.add_paragraph("---------------------------")

            # Voeg grafiek by as 'n PNG
            try:
                chartbuf = create_bar_chart(df_for_doc)
                # save to temp file then add
                tmp_chart = "temp_chart.png"
                with open(tmp_chart, "wb") as f:
                    f.write(chartbuf.getbuffer())
                doc.add_heading("Grafiek", level=2)
                doc.add_picture(tmp_chart, width=Inches(6))
                # remove temp file
                try:
                    os.remove(tmp_chart)
                except Exception:
                    pass
            except Exception as e:
                doc.add_paragraph(f"(Kon grafiek nie byvoeg nie: {e})")

            # Gevolgtrekking
            doc.add_heading("Gevolgtrekking", level=2)
            doc.add_paragraph(f"Gemiddelde opkoms vir hierdie periode: {avg_attendance:.2f}%.")
            doc.add_paragraph("Gebruik hierdie verslag om intervensies te beplan en te verbeter.")

            # Save to BytesIO
            buf = BytesIO()
            doc.save(buf)
            buf.seek(0)
            return buf

        word_bytes = create_word_bytes(filtered_df)
        st.download_button(label="⬇️ Laai Word Verslag (.docx)", data=word_bytes, file_name="intervensie_verslag.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        # Also allow CSV download
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(label="⬇️ Laai Gefilterde Data as CSV", data=csv_bytes, file_name="intervensie_data_filtered.csv", mime="text/csv")

    else:
        st.info("Geen data om te laai in hierdie tydperk nie.")

with tab2:
    st.header("🛠️ Hulpmiddels / Instellings")
    st.markdown("""
    **Instruksies & wenke**
    - Laai 'n foto of presensielys in. Presensielyste kan .csv, .xlsx, .pdf of 'n foto wees.
    - Die app stoor data plaaslik (inskrywings en lêers). Om 'n permanente backup te hê, stel jou GitHub token en repo in Streamlit Secrets.
    - In Streamlit Community Cloud: voeg `GITHUB_TOKEN` en `GITHUB_REPO` as Secrets by. Voorbeeld `GITHUB_REPO = \"gebruikersnaam/intervensie-data\"`.
    """)
    st.markdown("**Kontroles:**")
    gh_token = st.secrets.get("GITHUB_TOKEN") if hasattr(st, "secrets") else None
    gh_repo = st.secrets.get("GITHUB_REPO") if hasattr(st, "secrets") else None
    st.text(f"GitHub repo (secrets): {gh_repo if gh_repo else 'Nie geset nie'}")
    st.text(f"GitHub token beskikbaar: {'Ja' if gh_token else 'Nee'}")

    st.markdown("---")
    st.write("**Handmatige GitHub Sync** (druk om plaaslike CSV na GitHub te push)")
    if st.button("Push plaaslike CSV na GitHub"):
        if gh_token and gh_repo:
            ok = upload_file_to_github(CSV_FILE, repo=gh_repo, path_in_repo=os.path.basename(CSV_FILE), token=gh_token)
            if ok:
                st.success("CSV suksesvol gepush na GitHub ✅")
        else:
            st.error("Stel asseblief GITHUB_TOKEN en GITHUB_REPO in Streamlit Secrets voordat u push.")

# End of app
