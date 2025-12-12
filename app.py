# =====================================================
# IMPORTS
# =====================================================
import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# =====================================================
# CONFIG STREAMLIT
# =====================================================
st.set_page_config(page_title="Asistencia — Hogar de Cristo BB", layout="wide")

PRIMARY_COLOR = "#004E7B"
ACCENT_COLOR = "#63296C"
LOGO_FILE = "logo_hogar.png"

st.markdown(
    f"""
    <style>
    [data-testid="stSidebar"] {{
        background-color: #0b1220;
        border-right: 4px solid {PRIMARY_COLOR};
    }}
    h1, h2, h3 {{ color: {PRIMARY_COLOR}; }}
    .stButton>button {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border-radius: 999px;
        font-weight: 700;
        border: none;
    }}
    .stButton>button:hover {{ background-color: {ACCENT_COLOR}; }}
    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# CHEQUEO DE SECRETS (CLARO Y TEMPRANO)
# =====================================================
if "gcp_service_account" not in st.secrets:
    st.error("Falta [gcp_service_account] en Secrets de Streamlit Cloud.")
    st.stop()

if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
    st.error("Falta [sheets] → spreadsheet_id en Secrets de Streamlit Cloud.")
    st.stop()


# =====================================================
# CONSTANTES
# =====================================================
CENTROS = ["Nudo a Nudo", "Casa Maranatha", "Calle Belén"]

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar primaria",
    "Apoyo escolar secundaria",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otros",
]

COORDINADORES = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellán"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"

ASISTENCIA_COLS = [
    "id_registro", "fecha", "centro", "espacio",
    "presentes", "coordinador", "notas",
    "timestamp", "usuario"
]

PERSONAS_COLS = ["nombre", "frecuencia", "centro"]


# =====================================================
# HELPERS
# =====================================================
def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def new_id():
    return str(uuid.uuid4())


# =====================================================
# GOOGLE SHEETS API v4 (SIN gspread)
# =====================================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

@st.cache_resource(show_spinner=False)
def get_sheets_service():
    sa = dict(st.secrets["gcp_service_account"])
    pk = sa.get("private_key", "")
    pk = pk.replace("\\n", "\n").strip()
    if not pk.endswith("\n"):
        pk += "\n"
    sa["private_key"] = pk
    creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def spreadsheet_id():
    return st.secrets["sheets"]["spreadsheet_id"]

def ensure_tab(service, sid, title):
    meta = service.spreadsheets().get(spreadsheetId=sid).execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    service.spreadsheets().batchUpdate(spreadsheetId=sid, body=body).execute()

def read_table(service, sid, tab):
    rng = f"{tab}!A1:Z"
    res = service.spreadsheets().values().get(
        spreadsheetId=sid, range=rng
    ).execute()
    values = res.get("values", [])
    if not values:
        return pd.DataFrame()
    return pd.DataFrame(values[1:], columns=values[0])

def write_table(service, sid, tab, df):
    values = [df.columns.tolist()] + df.astype(str).fillna("").values.tolist()
    service.spreadsheets().values().clear(
        spreadsheetId=sid, range=f"{tab}!A:Z", body={}
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"{tab}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()

def append_row(service, sid, tab, row):
    service.spreadsheets().values().append(
        spreadsheetId=sid,
        range=f"{tab}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]}
    ).execute()


# =====================================================
# CONEXIÓN Y BOOTSTRAP
# =====================================================
service = get_sheets_service()
sid = spreadsheet_id()

ensure_tab(service, sid, ASISTENCIA_TAB)
ensure_tab(service, sid, PERSONAS_TAB)

if read_table(service, sid, ASISTENCIA_TAB).empty:
    write_table(service, sid, ASISTENCIA_TAB, pd.DataFrame(columns=ASISTENCIA_COLS))

if read_table(service, sid, PERSONAS_TAB).empty:
    write_table(service, sid, PERSONAS_TAB, pd.DataFrame(columns=PERSONAS_COLS))


# =====================================================
# SIDEBAR
# =====================================================
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_container_width=True)

st.sidebar.title("Centro")
centro = st.sidebar.selectbox("Centro barrial", CENTROS)
coordinador = st.sidebar.selectbox("Quién carga", COORDINADORES.get(centro, []))


# =====================================================
# UI PRINCIPAL
# =====================================================
st.title("Sistema de Asistencia")
st.caption(f"Centro: **{centro}** — Coordinador/a: **{coordinador}**")

tabs = st.tabs(["📌 Registrar", "👥 Personas", "📊 Reportes"])


# =====================================================
# TAB 1 — REGISTRAR
# =====================================================
with tabs[0]:
    fecha = st.date_input("Fecha", value=date.today())
    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA)
    else:
        espacio = "General"
        st.info("Este centro carga en modo general.")

    presentes = st.number_input("Cantidad de personas", min_value=0, step=1)
    notas = st.text_area("Notas")

    if st.button("Guardar asistencia"):
        row = [
            new_id(), fecha.isoformat(), centro, espacio,
            str(int(presentes)), coordinador, notas,
            now_ts(), "app"
        ]
        append_row(service, sid, ASISTENCIA_TAB, row)
        st.success("Asistencia guardada")
        st.rerun()


# =====================================================
# TAB 2 — PERSONAS
# =====================================================
with tabs[1]:
    dfp = read_table(service, sid, PERSONAS_TAB)
    if not dfp.empty:
        dfp = dfp[dfp["centro"] == centro]
    st.dataframe(dfp, use_container_width=True)

    st.markdown("---")
    nombre = st.text_input("Nombre completo")
    frecuencia = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual", "No asiste"])
    if st.button("Agregar persona"):
        append_row(service, sid, PERSONAS_TAB, [nombre, frecuencia, centro])
        st.success("Persona agregada")
        st.rerun()


# =====================================================
# TAB 3 — REPORTES
# =====================================================
with tabs[2]:
    dfa = read_table(service, sid, ASISTENCIA_TAB)
    if dfa.empty:
        st.info("No hay datos todavía.")
    else:
        dfa["fecha"] = pd.to_datetime(dfa["fecha"])
        dfa = dfa[dfa["centro"] == centro]
        desde = date.today() - timedelta(days=30)
        dfa = dfa[dfa["fecha"].dt.date >= desde]
        serie = dfa.groupby(dfa["fecha"].dt.date)["presentes"].astype(int).sum()
        st.line_chart(serie)
        st.download_button(
            "Descargar CSV",
            dfa.to_csv(index=False).encode("utf-8"),
            file_name="asistencia.csv",
            mime="text/csv"
        )
