import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
from docx import Document
from docx.shared import Inches

# ---------------------------------------------------------
# APP TITEL
# ---------------------------------------------------------
st.set_page_config(page_title="Intervensie App", layout="wide")
st.title("📘 Intervensie Log App")
st.markdown("Hier kan jy intervensies invul, filter, sien en aflaai.")

# ---------------------------------------------------------
# DATA LAAI OF SKOON MAAK
# ---------------------------------------------------------
LOG_FILE = "intervensie_log.csv"

if os.path.exists(LOG_FILE):
    df = pd.read_csv(LOG_FILE)
    if "Datum" in df.columns:
        df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
else:
    df = pd.DataFrame(columns=["Datum", "Opvoeder", "Vak", "Graad", "Beskrywing"])

# ---------------------------------------------------------
# FORM OM NUWE INSINSKRYWING TE MAAK
# ---------------------------------------------------------
st.header("➕ Nuwe Intervensie Inskrywing")

with st.form("new_entry_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        opvoeder = st.text_input("Opvoeder", "")
    with col2:
        vak = st.text_input("Vak", "")
    with col3:
        graad = st.text_input("Graad", "")

    beskrywing = st.text_area("Beskrywing van intervensie", "")

    submitted = st.form_submit_button("Stoor Inskrywing")

    if submitted:
        if not opvoeder or not vak or not graad or not beskrywing:
            st.error("⚠️ Alle velde is verpligtend.")
        else:
            new_entry = {
                "Datum": datetime.today().strftime("%Y-%m-%d"),
                "Opvoeder": opvoeder,
                "Vak": vak,
                "Graad": graad,
                "Beskrywing": beskrywing,
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(LOG_FILE, index=False)
            st.success("✅ Inskrywing gestoor!")

# ---------------------------------------------------------
# FILTERS
# ---------------------------------------------------------
st.sidebar.header("🔍 Filters")

opvoeder_filter = st.sidebar.multiselect("Kies Opvoeder", options=df["Opvoeder"].unique(), default=df["Opvoeder"].unique())
vak_filter = st.sidebar.multiselect("Kies Vak", options=df["Vak"].unique(), default=df["Vak"].unique())
graad_filter = st.sidebar.multiselect("Kies Graad", options=df["Graad"].unique(), default=df["Graad"].unique())
tydperk = st.sidebar.selectbox("Kies tydperk", ["Alles", "Weekliks", "Maandeliks", "Kwartaalliks", "Jaarliks"])

# Pas filters toe
filtered_data = df[
    (df["Opvoeder"].isin(opvoeder_filter)) &
    (df["Vak"].isin(vak_filter)) &
    (df["Graad"].isin(graad_filter))
]

if tydperk != "Alles" and "Datum" in filtered_data.columns:
    today = pd.to_datetime("today")
    if tydperk == "Weekliks":
        start_date = today - pd.Timedelta(days=7)
    elif tydperk == "Maandeliks":
        start_date = today - pd.DateOffset(months=1)
    elif tydperk == "Kwartaalliks":
        start_date = today - pd.DateOffset(months=3)
    elif tydperk == "Jaarliks":
        start_date = today - pd.DateOffset(years=1)
    filtered_data = filtered_data[filtered_data["Datum"] >= start_date]

# ---------------------------------------------------------
# WYS DATA
# ---------------------------------------------------------
st.header("📋 Geselekteerde Intervensies")
st.dataframe(filtered_data, use_container_width=True)

# ---------------------------------------------------------
# AFLaAI VAN DATA
# ---------------------------------------------------------
st.subheader("📥 Aflaai van Log Data")

# CSV aflaai
csv_buffer = io.StringIO()
filtered_data.to_csv(csv_buffer, index=False)
st.download_button(
    label="Laai af as CSV",
    data=csv_buffer.getvalue(),
    file_name="intervensie_log.csv",
    mime="text/csv"
)

# Excel aflaai
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
    filtered_data.to_excel(writer, index=False, sheet_name="LogData")
st.download_button(
    label="Laai af as Excel",
    data=excel_buffer.getvalue(),
    file_name="intervensie_log.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ---------------------------------------------------------
# WOORD VERSLAG (OPSIONEEL)
# ---------------------------------------------------------
st.subheader("📑 Genereer Word Verslag")

if st.button("Skep Word Verslag"):
    if filtered_data.empty:
        st.warning("Geen data om te genereer nie.")
    else:
        doc = Document()
        doc.add_heading("Intervensie Verslag", 0)
        doc.add_paragraph(f"Gegenereer op {datetime.today().strftime('%Y-%m-%d')}")

        table = doc.add_table(rows=1, cols=len(filtered_data.columns))
        hdr_cells = table.rows[0].cells
        for i, col in enumerate(filtered_data.columns):
            hdr_cells[i].text = col

        for _, row in filtered_data.iterrows():
            row_cells = table.add_row().cells
            for i, col in enumerate(filtered_data.columns):
                row_cells[i].text = str(row[col])

        word_buffer = io.BytesIO()
        doc.save(word_buffer)

        st.download_button(
            label="Laai Word Verslag af",
            data=word_buffer.getvalue(),
            file_name="intervensie_verslag.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
