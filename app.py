import re
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from google.auth.exceptions import RefreshError

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
      .small-note {{
        opacity: .8;
        font-size: 0.9rem;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

CENTROS = ["Calle Belén", "Casa Maranatha", "Nudo a Nudo"]

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

TAB_PERSONAS = "personas"
TAB_ASISTENCIA = "asistencia"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# -------------------------
# Helpers: limpieza de texto para evitar “desalineado”
# -------------------------
def clean_cell(x: str) -> str:
    if x is None:
        return ""
    s = str(x)
    # Evita que Sheets interprete tabs / saltos como nuevas columnas/filas al pegar
    s = s.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_frecuencia(x: str) -> str:
    s = clean_cell(x).lower()
    if "diar" in s:
        return "Diaria"
    if "seman" in s:
        return "Semanal"
    if "mens" in s:
        return "Mensual"
    if "no" in s and "asist" in s:
        return "No asiste"
    # fallback
    return "Semanal" if s else "Semanal"

def normalize_centro(x: str) -> str:
    s = clean_cell(x).lower()
    if "bel" in s:
        return "Calle Belén"
    if "mara" in s:
        return "Casa Maranatha"
    if "nudo" in s:
        return "Nudo a Nudo"
    return clean_cell(x)

# -------------------------
# Google Sheets (REST)
# -------------------------
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

def _base(spreadsheet_id: str) -> str:
    return f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"

def sheets_get_meta(session: AuthorizedSession, sid: str) -> dict:
    r = session.get(_base(sid))
    r.raise_for_status()
    return r.json()

def ensure_sheet(session: AuthorizedSession, sid: str, title: str):
    meta = sheets_get_meta(session, sid)
    titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if title in titles:
        return
    url = _base(sid) + ":batchUpdate"
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    r = session.post(url, json=body)
    r.raise_for_status()

def get_values(session: AuthorizedSession, sid: str, a1: str) -> list:
    url = _base(sid) + f"/values/{a1}"
    r = session.get(url)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get("values", [])

def put_values(session: AuthorizedSession, sid: str, a1: str, values: list):
    url = _base(sid) + f"/values/{a1}?valueInputOption=USER_ENTERED"
    body = {"range": a1, "majorDimension": "ROWS", "values": values}
    r = session.put(url, json=body)
    r.raise_for_status()

def append_values(session: AuthorizedSession, sid: str, a1: str, values: list):
    # values = [[...], [...]]
    url = _base(sid) + f"/values/{a1}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    body = {"range": a1, "majorDimension": "ROWS", "values": values}
    r = session.post(url, json=body)
    r.raise_for_status()

def _df_from_sheet(values: list, cols: list) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=cols)
    header = values[0]
    rows = values[1:] if len(values) > 1 else []
    if [c.strip().lower() for c in header] != [c.strip().lower() for c in cols]:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=cols)
    return df

def ensure_headers(session, sid):
    ensure_sheet(session, sid, TAB_PERSONAS)
    ensure_sheet(session, sid, TAB_ASISTENCIA)

    if not get_values(session, sid, f"{TAB_PERSONAS}!A1:C1"):
        put_values(session, sid, f"{TAB_PERSONAS}!A1:C1", [["nombre", "frecuencia", "centro"]])

    if not get_values(session, sid, f"{TAB_ASISTENCIA}!A1:H1"):
        put_values(session, sid, f"{TAB_ASISTENCIA}!A1:H1", [[
            "fecha","anio","centro","espacio","presentes","coordinador","notas","timestamp"
        ]])

def load_personas(session, sid) -> pd.DataFrame:
    vals = get_values(session, sid, f"{TAB_PERSONAS}!A1:Z")
    return _df_from_sheet(vals, ["nombre","frecuencia","centro"])

def load_asistencia(session, sid) -> pd.DataFrame:
    vals = get_values(session, sid, f"{TAB_ASISTENCIA}!A1:Z")
    return _df_from_sheet(vals, ["fecha","anio","centro","espacio","presentes","coordinador","notas","timestamp"])


# -------------------------
# LOGIN
# -------------------------
def require_users():
    if "users" not in st.secrets:
        st.error("Falta [users] en Secrets.")
        st.stop()

def do_login():
    require_users()
    users = dict(st.secrets["users"])

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if st.session_state.auth_ok:
        return

    st.title("Acceso — Sistema de Asistencia")
    st.write("Ingresá con tu usuario y contraseña.")

    user_keys = list(users.keys())
    u = st.selectbox("Usuario", user_keys)
    pw = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        info = dict(users[u])
        if pw == info.get("password", ""):
            st.session_state.auth_ok = True
            st.session_state.user_key = u
            st.session_state.user_nombre = info.get("nombre", u)
            st.session_state.user_centro = info.get("centro", "")
            st.success("✅ Acceso correcto")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

    st.stop()

def logout_button():
    if st.sidebar.button("Salir"):
        st.session_state.auth_ok = False
        isolist = ["user_key","user_nombre","user_centro"]
        for k in isolist:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()


# =========================
# APP
# =========================
do_login()

st.title("Sistema de Asistencia — Hogar de Cristo Bahía Blanca")

# Conexión Sheets
sid = st.secrets["sheets"]["spreadsheet_id"]
session = get_session()
ensure_headers(session, sid)

df_personas = load_personas(session, sid)
df_asistencia = load_asistencia(session, sid)

# Sidebar: bloqueado por usuario
st.sidebar.header("Acceso")
st.sidebar.success(f"Conectado como: {st.session_state.user_key}")
logout_button()

centro = st.session_state.user_centro  # BLOQUEADO
coordinador = st.session_state.user_nombre  # BLOQUEADO

st.sidebar.markdown("---")
st.sidebar.write(f"Centro asignado: **{centro}**")
st.sidebar.write(f"¿Quién carga?: **{coordinador}**")
st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

st.markdown(
    f"""<div class="hc-pill">Estás trabajando sobre: {centro} — 👤 {coordinador}</div>""",
    unsafe_allow_html=True
)

# KPIs
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

start_week = today - timedelta(days=today.weekday())
dias_cargados = set(dfCentroYear[dfCentroYear["fecha"].dt.date >= start_week]["fecha"].dt.date.unique()) if not dfCentroYear.empty else set()
dias_semana = [start_week + timedelta(days=i) for i in range(7)]
dias_sin = sum(1 for d in dias_semana if d not in dias_cargados and d <= today)

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f'<div class="hc-card"><b>Ingresos HOY</b><br><span style="font-size:42px;font-weight:800;">{ing_hoy}</span></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="hc-card"><b>Ingresos últimos 7 días</b><br><span style="font-size:42px;font-weight:800;">{ing_7}</span></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="hc-card"><b>Días sin cargar esta semana</b><br><span style="font-size:42px;font-weight:800;">{dias_sin}</span></div>', unsafe_allow_html=True)

tabs = st.tabs(["📌 Registrar asistencia", "👥 Personas", "⬆️ Importar personas", "📊 Reportes / Base de datos", "🌍 Global"])

# TAB Registrar
with tabs[0]:
    st.subheader("Registrar asistencia para este centro")

    c1, c2 = st.columns([2,1])
    with c1:
        fecha = st.date_input("Fecha", value=today)
    with c2:
        anio = st.number_input("Año", min_value=2020, max_value=2100, value=fecha.year, step=1)

    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio (solo Maranatha)", ESPACIOS_MARANATHA)
    else:
        espacio = "General"
        st.info("Este centro registra asistencia general (sin espacios).")

    presentes = st.number_input("Total presentes", min_value=0, step=1)
    notas = st.text_area("Notas (opcional)")

    if st.button("Guardar asistencia"):
        row = [[
            fecha.isoformat(),
            str(anio),
            clean_cell(centro),
            clean_cell(espacio),
            str(int(presentes)),
            clean_cell(coordinador),
            clean_cell(notas),
            datetime.now().isoformat(timespec="seconds"),
        ]]
        append_values(session, sid, f"{TAB_ASISTENCIA}!A1", row)
        st.success("✅ Asistencia guardada.")
        st.rerun()

    st.markdown("---")
    st.caption("Últimos registros (este centro / este año)")
    show = dfCentroYear.sort_values("fecha", ascending=False).head(20) if not dfCentroYear.empty else dfCentroYear
    st.dataframe(show, use_container_width=True)

# TAB Personas
with tabs[1]:
    st.subheader("Personas registradas (este centro)")

    dfP = df_personas.copy()
    if dfP.empty:
        dfP = pd.DataFrame(columns=["nombre","frecuencia","centro"])

    dfP["nombre"] = dfP["nombre"].map(clean_cell)
    dfP["frecuencia"] = dfP["frecuencia"].map(clean_cell)
    dfP["centro"] = dfP["centro"].map(clean_cell)

    dfP_c = dfP[dfP["centro"] == centro].copy()
    dfP_c = dfP_c.sort_values("nombre") if not dfP_c.empty else dfP_c
    st.dataframe(dfP_c, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona (manual)")

    nombre = st.text_input("Nombre completo")
    frecuencia = st.selectbox("Frecuencia", FRECUENCIAS)

    if st.button("Agregar"):
        n = clean_cell(nombre)
        if not n:
            st.error("Poné un nombre.")
        else:
            row = [[n, frecuencia, centro]]
            append_values(session, sid, f"{TAB_PERSONAS}!A1", row)
            st.success("✅ Persona agregada.")
            st.rerun()

# TAB Importar personas
with tabs[2]:
    st.subheader("Importar personas (limpieza automática)")
    st.write("Acá pegás la tabla que te mandaron (C/S/B, etc.) y la app la normaliza a: **nombre / frecuencia / centro**.")
    st.caption("Tip: podés pegar tal cual desde WhatsApp/Sheets/Word.")

    raw = st.text_area("Pegá acá el listado (filas)", height=220, placeholder="Ej:\nAcebedo Coca, Reynaldo\tMensual\nAcosta, Carlos Alberto\tDiaria\n...")

    col1, col2 = st.columns(2)
    with col1:
        centro_import = st.selectbox("Centro destino", [centro], index=0, disabled=True)
    with col2:
        default_freq = st.selectbox("Frecuencia por defecto (si falta)", FRECUENCIAS, index=1)

    def parse_raw(text: str) -> pd.DataFrame:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        out = []
        for ln in lines:
            # separadores típicos: tab, ;, , , múltiples espacios
            parts = re.split(r"\t|;|\s{2,}", ln)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) == 1:
                nombre = parts[0]
                freq = default_freq
            else:
                nombre = parts[0]
                freq = parts[1]
            out.append([clean_cell(nombre), normalize_frecuencia(freq), centro_import])
        df = pd.DataFrame(out, columns=["nombre","frecuencia","centro"])
        # quitar vacíos y duplicados por nombre+centro
        df = df[df["nombre"] != ""]
        df = df.drop_duplicates(subset=["nombre","centro"], keep="first")
        return df

    if st.button("Previsualizar"):
        if not raw.strip():
            st.warning("Pegá algo primero.")
        else:
            df_prev = parse_raw(raw)
            st.session_state.import_preview = df_prev

    if "import_preview" in st.session_state:
        df_prev = st.session_state.import_preview
        st.write("Previsualización:")
        st.dataframe(df_prev, use_container_width=True)
        st.markdown(f"<div class='small-note'>Filas a importar: <b>{len(df_prev)}</b></div>", unsafe_allow_html=True)

        if st.button("✅ Importar a Google Sheets"):
            # Append en bloque para no hacer 200 requests
            rows = df_prev[["nombre","frecuencia","centro"]].values.tolist()
            append_values(session, sid, f"{TAB_PERSONAS}!A1", rows)
            st.success("✅ Importación completa.")
            del st.session_state.import_preview
            st.rerun()

# TAB Reportes
with tabs[3]:
    st.subheader("Reportes (este centro)")

    anios = sorted(dfCentro["anio"].dropna().unique().tolist()) if not dfCentro.empty else [anio_actual]
    if anio_actual not in anios:
        anios = [anio_actual] + anios

    anio_sel = st.selectbox("Año", anios, index=0)
    data = dfCentro[dfCentro["anio"] == anio_sel].copy()

    if data.empty:
        st.info("No hay registros para ese año.")
    else:
        serie = data.groupby(data["fecha"].dt.date)["presentes"].sum().sort_index()
        st.caption("Asistencia por día")
        st.line_chart(serie)

        by_coord = data.groupby("coordinador")["presentes"].sum().sort_values(ascending=False)
        st.caption("Asistencia acumulada por coordinador/a")
        st.bar_chart(by_coord)

        if centro == "Casa Maranatha":
            by_esp = data.groupby("espacio")["presentes"].sum().sort_values(ascending=False)
            st.caption("Asistencia por espacio (Maranatha)")
            st.bar_chart(by_esp)

        st.markdown("---")
        st.subheader("Base de datos (descargas)")
        st.download_button(
            "⬇️ Descargar asistencia filtrada (CSV)",
            data.to_csv(index=False).encode("utf-8"),
            file_name=f"asistencia_{centro}_{anio_sel}.csv",
            mime="text/csv"
        )

        dfP = df_personas.copy()
        if dfP.empty:
            dfP = pd.DataFrame(columns=["nombre","frecuencia","centro"])
        dfP["nombre"] = dfP["nombre"].map(clean_cell)
        dfP["frecuencia"] = dfP["frecuencia"].map(clean_cell)
        dfP["centro"] = dfP["centro"].map(clean_cell)
        dfP_c = dfP[dfP["centro"] == centro].copy()

        st.download_button(
            "⬇️ Descargar personas del centro (CSV)",
            dfP_c.to_csv(index=False).encode("utf-8"),
            file_name=f"personas_{centro}.csv",
            mime="text/csv"
        )

# TAB Global
with tabs[4]:
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
