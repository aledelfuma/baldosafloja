import re
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from google.auth.exceptions import RefreshError

# =========================
# CONFIG
# =========================
PRIMARY = "#004E7B"
ACCENT = "#63296C"

st.set_page_config(page_title="Asistencia – Hogar de Cristo", layout="wide")

st.markdown(
    f"""
    <style>
      :root {{
        --hc-primary: {PRIMARY};
        --hc-accent: {ACCENT};
      }}
      h1, h2, h3 {{ color: var(--hc-primary); }}
      .hc-pill {{
        display:inline-block; padding:6px 12px; border-radius:999px;
        background: rgba(0,78,123,.15); border:1px solid rgba(0,78,123,.35);
        color:white; font-weight:600;
      }}
      .hc-card {{
        border: 1px solid rgba(99,41,108,.35);
        background: rgba(255,255,255,.03);
        border-radius: 16px;
        padding: 14px 16px;
      }}
      .stButton>button {{
        background: var(--hc-primary) !important;
        color: white !important;
        border-radius: 999px !important;
        font-weight: 700 !important;
        border: 1px solid rgba(255,255,255,.08) !important;
      }}
      .stButton>button:hover {{
        background: var(--hc-accent) !important;
      }}
      .stTabs [data-baseweb="tab"] {{
        font-weight: 700 !important;
      }}
      .stTabs [aria-selected="true"] {{
        border-bottom: 3px solid var(--hc-accent) !important;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# DOMINIO
# =========================
CENTROS = ["Calle Belén", "Casa Maranatha", "Nudo a Nudo"]

COORDINADORES = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellán"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar primaria",
    "Apoyo escolar secundaria",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]

FRECUENCIAS = ["Diaria", "Semanal", "Mensual", "No asiste"]

# Tabs (hojas) dentro del spreadsheet
TAB_PERSONAS = "personas"
TAB_ASISTENCIA = "asistencia"

# =========================
# GOOGLE SHEETS (vía REST)
# =========================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _require_secrets():
    if "gcp_service_account" not in st.secrets:
        st.error("Falta [gcp_service_account] en Secrets.")
        st.stop()
    if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
        st.error("Falta [sheets] spreadsheet_id en Secrets.")
        st.stop()

@st.cache_resource(show_spinner=False)
def get_session():
    _require_secrets()
    sa = dict(st.secrets["gcp_service_account"])

    # normalizar private_key (por si vino con \\n)
    pk = str(sa.get("private_key", ""))
    pk = pk.replace("\\n", "\n").strip()
    if not pk.endswith("\n"):
        pk += "\n"
    sa["private_key"] = pk

    try:
        creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
        creds.refresh(Request())
        return AuthorizedSession(creds)
    except RefreshError as e:
        st.error("Google rechazó la autenticación (RefreshError).")
        st.code(str(e))
        st.stop()

def _sheet_base_url(spreadsheet_id: str):
    return f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"

def sheets_get_meta(session: AuthorizedSession, spreadsheet_id: str) -> dict:
    r = session.get(_sheet_base_url(spreadsheet_id))
    r.raise_for_status()
    return r.json()

def ensure_sheet_exists(session: AuthorizedSession, spreadsheet_id: str, title: str):
    meta = sheets_get_meta(session, spreadsheet_id)
    titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if title in titles:
        return

    # crear hoja
    url = _sheet_base_url(spreadsheet_id) + ":batchUpdate"
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    r = session.post(url, json=body)
    r.raise_for_status()

def get_values(session: AuthorizedSession, spreadsheet_id: str, a1: str) -> list:
    url = _sheet_base_url(spreadsheet_id) + f"/values/{a1}"
    r = session.get(url)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get("values", [])

def put_values(session: AuthorizedSession, spreadsheet_id: str, a1: str, values: list):
    url = _sheet_base_url(spreadsheet_id) + f"/values/{a1}?valueInputOption=USER_ENTERED"
    body = {"range": a1, "majorDimension": "ROWS", "values": values}
    r = session.put(url, json=body)
    r.raise_for_status()

def append_values(session: AuthorizedSession, spreadsheet_id: str, a1: str, values: list):
    url = _sheet_base_url(spreadsheet_id) + f"/values/{a1}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    body = {"range": a1, "majorDimension": "ROWS", "values": values}
    r = session.post(url, json=body)
    r.raise_for_status()

def _df_from_sheet(values: list, columns: list) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=columns)
    header = values[0]
    rows = values[1:] if len(values) > 1 else []

    # Si la hoja está vacía o el header no coincide, devolver vacío con columnas correctas
    if [c.strip().lower() for c in header] != [c.strip().lower() for c in columns]:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    return df

def load_personas(session, sid) -> pd.DataFrame:
    values = get_values(session, sid, f"{TAB_PERSONAS}!A1:Z")
    cols = ["nombre", "frecuencia", "centro"]
    return _df_from_sheet(values, cols)

def load_asistencia(session, sid) -> pd.DataFrame:
    values = get_values(session, sid, f"{TAB_ASISTENCIA}!A1:Z")
    cols = ["fecha", "anio", "centro", "espacio", "presentes", "coordinador", "notas", "timestamp"]
    return _df_from_sheet(values, cols)

def ensure_headers(session, sid):
    # crea tabs si no existen
    ensure_sheet_exists(session, sid, TAB_PERSONAS)
    ensure_sheet_exists(session, sid, TAB_ASISTENCIA)

    # headers personas
    p = get_values(session, sid, f"{TAB_PERSONAS}!A1:C1")
    if not p:
        put_values(session, sid, f"{TAB_PERSONAS}!A1:C1", [["nombre", "frecuencia", "centro"]])

    # headers asistencia
    a = get_values(session, sid, f"{TAB_ASISTENCIA}!A1:H1")
    if not a:
        put_values(session, sid, f"{TAB_ASISTENCIA}!A1:H1", [[
            "fecha","anio","centro","espacio","presentes","coordinador","notas","timestamp"
        ]])

# =========================
# UI
# =========================
st.title("Sistema de Asistencia — Hogar de Cristo Bahía Blanca")

# Logo opcional (si subís /assets/logo.png)
# if os.path.exists("assets/logo.png"):
#     st.image("assets/logo.png", width=120)

# Conexión
sid = st.secrets["sheets"]["spreadsheet_id"]
session = get_session()
ensure_headers(session, sid)

# Carga data
df_personas = load_personas(session, sid)
df_asistencia = load_asistencia(session, sid)

# Sidebar (fijar centro y coordinador)
st.sidebar.header("Acceso")
centro = st.sidebar.selectbox("Centro asignado", CENTROS)
coordinador = st.sidebar.selectbox("¿Quién carga?", COORDINADORES[centro])

st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

st.markdown(
    f"""<div class="hc-pill">Estás trabajando sobre: {centro} — 👤 {coordinador}</div>""",
    unsafe_allow_html=True
)

# KPIs rápidos
colk1, colk2, colk3 = st.columns(3)

today = date.today()
anio_actual = today.year

dfA = df_asistencia.copy()
if not dfA.empty:
    dfA["presentes"] = pd.to_numeric(dfA["presentes"], errors="coerce").fillna(0).astype(int)
    dfA["fecha"] = pd.to_datetime(dfA["fecha"], errors="coerce")
    dfA["anio"] = pd.to_numeric(dfA["anio"], errors="coerce").fillna(dfA["fecha"].dt.year).astype(int)
else:
    dfA = pd.DataFrame(columns=["fecha","anio","centro","espacio","presentes","coordinador","notas","timestamp"])

dfCentro = dfA[dfA["centro"] == centro].copy()
dfCentroYear = dfCentro[dfCentro["anio"] == anio_actual].copy()

ing_hoy = int(dfCentroYear[dfCentroYear["fecha"].dt.date == today]["presentes"].sum()) if not dfCentroYear.empty else 0
ing_7 = int(dfCentroYear[dfCentroYear["fecha"].dt.date >= (today - timedelta(days=6))]["presentes"].sum()) if not dfCentroYear.empty else 0

# días sin cargar en la semana (lun-dom)
start_week = today - timedelta(days=today.weekday())
dias_cargados = set(dfCentroYear[dfCentroYear["fecha"].dt.date >= start_week]["fecha"].dt.date.unique()) if not dfCentroYear.empty else set()
dias_semana = [start_week + timedelta(days=i) for i in range(7)]
dias_sin = sum(1 for d in dias_semana if d not in dias_cargados and d <= today)

with colk1:
    st.markdown('<div class="hc-card"><b>Ingresos HOY</b><br><span style="font-size:42px;font-weight:800;">{}</span></div>'.format(ing_hoy), unsafe_allow_html=True)
with colk2:
    st.markdown('<div class="hc-card"><b>Ingresos últimos 7 días</b><br><span style="font-size:42px;font-weight:800;">{}</span></div>'.format(ing_7), unsafe_allow_html=True)
with colk3:
    st.markdown('<div class="hc-card"><b>Días sin cargar esta semana</b><br><span style="font-size:42px;font-weight:800;">{}</span></div>'.format(dias_sin), unsafe_allow_html=True)

tabs = st.tabs(["📌 Registrar asistencia", "👥 Personas", "📊 Reportes / Base de datos", "🌍 Tablero global"])

# =========================
# TAB 1 Registrar
# =========================
with tabs[0]:
    st.subheader("Registrar asistencia para este centro")

    c1, c2 = st.columns([2, 1])
    with c1:
        fecha = st.date_input("Fecha", value=today, key="fecha_reg")
    with c2:
        anio = st.number_input("Año", min_value=2020, max_value=2100, value=fecha.year, step=1)

    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio (solo Maranatha)", ESPACIOS_MARANATHA)
    else:
        espacio = "General"
        st.info("Este centro registra asistencia general (sin espacios).")

    presentes = st.number_input("Total presentes", min_value=0, step=1)
    notas = st.text_area("Notas (opcional)")

    if st.button("Guardar asistencia", key="btn_guardar_asistencia"):
        row = [[
            fecha.isoformat(),
            str(anio),
            centro,
            espacio,
            str(int(presentes)),
            coordinador,
            notas,
            datetime.now().isoformat(timespec="seconds"),
        ]]
        append_values(session, sid, f"{TAB_ASISTENCIA}!A1", row)
        st.success("✅ Asistencia guardada en Google Sheets.")
        st.rerun()

    st.markdown("---")
    st.caption("Últimos registros (este centro / este año)")
    show = dfCentroYear.sort_values("fecha", ascending=False).head(20) if not dfCentroYear.empty else dfCentroYear
    st.dataframe(show, use_container_width=True)

# =========================
# TAB 2 Personas
# =========================
with tabs[1]:
    st.subheader("Personas registradas (este centro)")

    dfP = df_personas.copy()
    if dfP.empty:
        dfP = pd.DataFrame(columns=["nombre", "frecuencia", "centro"])

    dfP_c = dfP[dfP["centro"] == centro].copy()
    dfP_c = dfP_c.sort_values("nombre") if not dfP_c.empty else dfP_c

    st.dataframe(dfP_c, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona")

    nombre = st.text_input("Nombre completo")
    frecuencia = st.selectbox("Frecuencia", FRECUENCIAS)

    if st.button("Agregar", key="btn_add_persona"):
        n = nombre.strip()
        if not n:
            st.error("Poné un nombre.")
        else:
            row = [[n, frecuencia, centro]]
            append_values(session, sid, f"{TAB_PERSONAS}!A1", row)
            st.success("✅ Persona agregada.")
            st.rerun()

# =========================
# TAB 3 Reportes
# =========================
with tabs[2]:
    st.subheader("Reportes (este centro)")

    # filtro año
    anios = sorted(dfCentro["anio"].dropna().unique().tolist()) if not dfCentro.empty else [anio_actual]
    if anio_actual not in anios:
        anios = [anio_actual] + anios

    anio_sel = st.selectbox("Año", anios, index=0)

    data = dfCentro[dfCentro["anio"] == anio_sel].copy()
    if data.empty:
        st.info("No hay registros para ese año.")
    else:
        # por día
        serie = data.groupby(data["fecha"].dt.date)["presentes"].sum().sort_index()
        st.caption("Asistencia por día")
        st.line_chart(serie)

        # por coordinador
        st.caption("Asistencia acumulada por coordinador/a")
        by_coord = data.groupby("coordinador")["presentes"].sum().sort_values(ascending=False)
        st.bar_chart(by_coord)

        # Maranatha por espacio
        if centro == "Casa Maranatha":
            st.caption("Asistencia por espacio (Maranatha)")
            by_esp = data.groupby("espacio")["presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_esp)

        st.markdown("---")
        st.subheader("Base de datos (descargas)")

        st.download_button(
            "⬇️ Descargar asistencia filtrada (CSV)",
            data.to_csv(index=False).encode("utf-8"),
            file_name=f"asistencia_{centro}_{anio_sel}.csv",
            mime="text/csv"
        )

        st.download_button(
            "⬇️ Descargar personas del centro (CSV)",
            dfP_c.to_csv(index=False).encode("utf-8"),
            file_name=f"personas_{centro}.csv",
            mime="text/csv"
        )

# =========================
# TAB 4 Global
# =========================
with tabs[3]:
    st.subheader("Tablero global (todos los centros)")

    if dfA.empty:
        st.info("Todavía no hay registros globales.")
    else:
        anios_g = sorted(dfA["anio"].dropna().unique().tolist())
        anio_g = st.selectbox("Año (global)", anios_g, index=(anios_g.index(anio_actual) if anio_actual in anios_g else 0))

        dg = dfA[dfA["anio"] == anio_g].copy()
        if dg.empty:
            st.info("Sin datos para ese año.")
        else:
            st.caption("Asistencia total por centro")
            by_c = dg.groupby("centro")["presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_c)

            st.caption("Evolución diaria total (todos los centros)")
            serie_g = dg.groupby(dg["fecha"].dt.date)["presentes"].sum().sort_index()
            st.line_chart(serie_g)

            st.markdown("---")
            st.caption("Tabla completa (filtrada por año)")
            st.dataframe(dg.sort_values("fecha", ascending=False), use_container_width=True)
