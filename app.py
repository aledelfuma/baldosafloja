import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession




# ---------------- UI ----------------
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

# --------------- Secrets check ---------------
if "gcp_service_account" not in st.secrets:
    st.error("Falta [gcp_service_account] en Secrets de Streamlit Cloud.")
    st.stop()
if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
    st.error("Falta [sheets] → spreadsheet_id en Secrets de Streamlit Cloud.")
    st.stop()

# --------------- Constantes ---------------
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

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ---------------- Helpers ----------------
def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def new_id():
    return str(uuid.uuid4())

def spreadsheet_id():
    return st.secrets["sheets"]["spreadsheet_id"]


# ---------------- Google auth via Requests ----------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

@st.cache_resource(show_spinner=False)
def get_authed_session():
    sa = dict(st.secrets["gcp_service_account"])

    # chequeos sin exponer secretos
    must = ["type","project_id","private_key","client_email","token_uri"]
    missing = [k for k in must if not str(sa.get(k, "")).strip()]
    if missing:
        st.error(f"Secrets incompletos. Faltan: {missing}")
        st.stop()

    # normalizar private_key
    pk = sa.get("private_key", "")
    pk = pk.replace("\\n", "\n").strip()
    if not pk.endswith("\n"):
        pk += "\n"
    sa["private_key"] = pk

    try:
        creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
        # fuerza refresh acá para capturar el error real
        creds.refresh(Request())
        st.success("✅ Token OK (service account autenticado)")
        return AuthorizedSession(creds)

    except RefreshError as e:
        st.error("❌ RefreshError: Google rechazó la autenticación del service account.")
        st.write("Detalle (texto real):")
        st.code(str(e))
        st.stop()

def sheets_get_meta():
    r = session.get(BASE)
    if r.status_code != 200:
        st.error("Error leyendo metadata del Sheet.")
        st.write("Status:", r.status_code)
        st.write("Body:", r.text)
        st.stop()
    return r.json()


def ensure_tab(title: str):
    meta = sheets_get_meta()
    for s in meta.get("sheets", []):
        if s.get("properties", {}).get("title") == title:
            return

    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    r = session.post(BASE + ":batchUpdate", json=body)
    if r.status_code != 200:
        st.error("Error creando pestaña.")
        st.write("Status:", r.status_code)
        st.write("Body:", r.text)
        st.stop()


def values_get(a1_range: str):
    url = BASE + f"/values/{a1_range}"
    r = session.get(url)
    if r.status_code != 200:
        st.error("Error leyendo valores.")
        st.write("Status:", r.status_code)
        st.write("Body:", r.text)
        st.stop()
    return r.json().get("values", [])


def values_clear(a1_range: str):
    url = BASE + f"/values/{a1_range}:clear"
    r = session.post(url, json={})
    if r.status_code != 200:
        st.error("Error limpiando rango.")
        st.write("Status:", r.status_code)
        st.write("Body:", r.text)
        st.stop()


def values_update(a1_range: str, values):
    url = BASE + f"/values/{a1_range}?valueInputOption=USER_ENTERED"
    r = session.put(url, json={"range": a1_range, "majorDimension": "ROWS", "values": values})
    if r.status_code != 200:
        st.error("Error actualizando valores.")
        st.write("Status:", r.status_code)
        st.write("Body:", r.text)
        st.stop()


def values_append(tab: str, row):
    url = BASE + f"/values/{tab}!A1:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    r = session.post(url, json={"values": [row]})
    if r.status_code != 200:
        st.error("Error agregando fila.")
        st.write("Status:", r.status_code)
        st.write("Body:", r.text)
        st.stop()


def read_table(tab: str) -> pd.DataFrame:
    vals = values_get(f"{tab}!A1:Z")
    if not vals:
        return pd.DataFrame()
    header = vals[0]
    rows = vals[1:]
    return pd.DataFrame(rows, columns=header)


def write_table(tab: str, df: pd.DataFrame):
    values_clear(f"{tab}!A:Z")
    values = [df.columns.tolist()] + df.astype(str).fillna("").values.tolist()
    values_update(f"{tab}!A1", values)


# ---------------- Bootstrap ----------------
ensure_tab(ASISTENCIA_TAB)
ensure_tab(PERSONAS_TAB)

if read_table(ASISTENCIA_TAB).empty:
    write_table(ASISTENCIA_TAB, pd.DataFrame(columns=ASISTENCIA_COLS))
if read_table(PERSONAS_TAB).empty:
    write_table(PERSONAS_TAB, pd.DataFrame(columns=PERSONAS_COLS))


# ---------------- Sidebar ----------------
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_container_width=True)

st.sidebar.title("Centro")
centro = st.sidebar.selectbox("Centro barrial", CENTROS)
coordinador = st.sidebar.selectbox("Quién carga", COORDINADORES.get(centro, []))


# ---------------- Main UI ----------------
st.title("Sistema de Asistencia")
st.caption(f"Centro: **{centro}** — Coordinador/a: **{coordinador}**")

tabs = st.tabs(["📌 Registrar", "👥 Personas", "📊 Reportes"])


# TAB Registrar
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
            new_id(),
            fecha.isoformat(),
            centro,
            espacio,
            str(int(presentes)),
            coordinador,
            (notas or "").strip(),
            now_ts(),
            "app",
        ]
        values_append(ASISTENCIA_TAB, row)
        st.success("Asistencia guardada ✅")
        st.rerun()


# TAB Personas
with tabs[1]:
    dfp = read_table(PERSONAS_TAB)
    if not dfp.empty and "centro" in dfp.columns:
        dfp = dfp[dfp["centro"] == centro]
    st.dataframe(dfp, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona")
    nombre = st.text_input("Nombre completo")
    frecuencia = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual", "No asiste"])

    if st.button("Agregar persona"):
        if not nombre.strip():
            st.error("Poné un nombre.")
        else:
            values_append(PERSONAS_TAB, [nombre.strip(), frecuencia, centro])
            st.success("Persona agregada ✅")
            st.rerun()


# TAB Reportes
with tabs[2]:
    dfa = read_table(ASISTENCIA_TAB)
    if dfa.empty:
        st.info("No hay datos todavía.")
    else:
        if "fecha" in dfa.columns:
            dfa["fecha"] = pd.to_datetime(dfa["fecha"], errors="coerce")
        if "centro" in dfa.columns:
            dfa = dfa[dfa["centro"] == centro]

        desde = date.today() - timedelta(days=30)
        dfa = dfa[dfa["fecha"].dt.date >= desde]

        if dfa.empty:
            st.info("No hay datos en los últimos 30 días.")
        else:
            dfa["presentes"] = pd.to_numeric(dfa.get("presentes", 0), errors="coerce").fillna(0).astype(int)
            serie = dfa.groupby(dfa["fecha"].dt.date)["presentes"].sum()
            st.line_chart(serie)

            st.download_button(
                "Descargar CSV",
                dfa.to_csv(index=False).encode("utf-8"),
                file_name="asistencia.csv",
                mime="text/csv"
            )

