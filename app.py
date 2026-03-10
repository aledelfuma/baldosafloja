import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError
import time
import pytz
import io
import unicodedata
import re

# ======================================================
# 🌑 CONFIGURACIÓN DE TEMA OSCURO PREMIUM
# ======================================================
st.set_page_config(
    page_title="Hogar de Cristo - Gestión",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root {
  --primary: #60A5FA;
  --secondary: #A78BFA;
  --background: #121212;
  --surface: #1E1E1E;
  --text-primary: #FFFFFF;
  --text-secondary: #AAAAAA;
  --radius-sm: 10px;
  --radius-lg: 15px;
  --shadow: 0 4px 6px rgba(0,0,0,0.3);
}

/* Fondo Global, Forzando texto claro y estructura Mobile */
.stApp {
    background-color: var(--background) !important;
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    color: var(--text-primary) !important;
}

/* Títulos y etiquetas de widgets en blanco */
.stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {
    color: var(--text-primary) !important;
}

/* Elementos Nativos Ocultos */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;} 

/* Layout Mobile Centrado */
.css-18e3th9, .st-emotion-cache-1jicfl2 {
    padding-top: 1rem !important; 
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 90px !important; 
    max-width: 600px !important; 
    margin: 0 auto;
}

/* Tarjetas y Contenedores */
div[data-testid="stVerticalBlock"] > div {
    color: var(--text-primary);
}

.top-bar {
    background-color: var(--surface);
    padding: 15px 20px;
    border-radius: var(--radius-lg);
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
div.user-info {
    font-size: 1.2rem; 
    font-weight: 700; 
    color: var(--text-primary) !important;
    line-height: 1.2;
}
div.center-info {
    font-size: 0.85rem; 
    font-weight: 600; 
    color: var(--text-secondary) !important;
    margin-top: 2px;
}

/* Custom Buttons */
.stButton>button {
    background-color: var(--primary);
    color: #000000 !important;
    border-radius: var(--radius-sm);
    border: none;
    font-weight: 700;
    padding: 0.6rem 1rem;
    transition: 0.2s;
    width: 100%;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(96, 165, 250, 0.3);
}

/* Inputs para Modo Oscuro */
.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stMultiSelect>div>div>div {
    border-radius: var(--radius-sm) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background-color: #1A1A1A !important;
    color: var(--text-primary) !important;
    padding: 0.5rem;
}

/* FAQs y Expanders en negro */
.streamlit-expanderHeader {
    color: var(--text-primary) !important;
    background-color: var(--surface);
    border-radius: var(--radius-sm);
}

/* KPIs Modernos */
.kpi {
  border-radius: var(--radius-lg);
  padding: 15px;
  background: var(--surface);
  border: 1px solid rgba(255,255,255,0.05);
  text-align: center;
  height: 100%;
}
.kpi h3 { 
    margin: 0; 
    font-size: 0.65rem; 
    color: var(--text-secondary) !important;
    text-transform: uppercase; 
    letter-spacing: 0.5px; 
}
.kpi .v { 
    font-size: 2rem; 
    font-weight: 800; 
    color: var(--primary) !important; 
    line-height: 1;
}

/* Alertas */
.alert-box { 
    padding: 12px 15px; 
    border-radius: var(--radius-sm); 
    margin-bottom: 10px; 
    font-size: 0.9rem; 
    font-weight: 600;
}
.alert-danger { background-color: rgba(239, 68, 68, 0.1); color: #EF4444 !important; border: 1px solid rgba(239, 68, 68, 0.3); }
.alert-success { background-color: rgba(34, 197, 94, 0.1); color: #22C55E !important; border: 1px solid rgba(34, 197, 94, 0.3); }
.alert-gray { background-color: var(--surface); color: var(--text-secondary) !important; border: 1px solid rgba(255,255,255,0.05); }

/* Carnet Digital */
.id-card {
    background: linear-gradient(135deg, #004E7B 0%, #63296C 100%);
    border-radius: 20px;
    padding: 25px;
    color: white !important;
    box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.id-card * { color: white !important; }
.id-title { font-size: 0.70rem; letter-spacing: 1px; text-transform: uppercase; opacity: 0.8; margin-bottom: 5px;}
.id-name { font-size: 1.6rem; font-weight: 800; margin-bottom: 15px; line-height: 1.1; }
.id-data-row { display: flex; gap: 20px; margin-bottom: 15px; }
.id-data-col { display: flex; flex-direction: column; }
.id-label { font-size: 0.6rem; opacity: 0.7; text-transform: uppercase; }
.id-value { font-size: 0.95rem; font-weight: 600; }

.tag-container { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.tag-badge { background-color: rgba(255,255,255,0.15); padding: 3px 9px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }

.btn-wa {
    display: inline-flex; align-items: center; justify-content: center;
    background-color: #25D366; color: white !important; padding: 8px 15px;
    border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 0.9rem;
    margin-top: 10px; transition: 0.3s;
}

/* Pestañas (Tabs) estilo APP inferior */
.stTabs [data-baseweb="tab-list"] {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #0A0A0A; 
    border-top: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: space-around;
    padding: 8px 10px 18px 10px;
    z-index: 9999;
}
.stTabs [data-baseweb="tab"] {
    flex-grow: 1; text-align: center; justify-content: center;
    font-size: 0.75rem !important; font-weight: 600;
    color: var(--text-secondary) !important; padding: 8px 0;
    border: none !important; background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important;
    background-color: rgba(96, 165, 250, 0.05) !important;
    border-radius: 8px;
}
.stTabs [aria-selected="true"]::after { display: none; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================
# Zona Horaria & Helpers
# =========================
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')

def get_now_ar_str(): return datetime.now(TZ_AR).strftime("%Y-%m-%d %H:%M:%S")
def get_today_ar(): return datetime.now(TZ_AR).date()

def calculate_age(born):
    try:
        born = pd.to_datetime(born, dayfirst=True).date()
        today = get_today_ar()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except: return 0

def format_wa_number(phone):
    return re.sub(r'\D', '', str(phone))

# =========================
# Schemas y Nombres
# =========================
ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
ASISTENCIA_PERSONAS_TAB = "asistencia_personas"
USUARIOS_TAB = "config_usuarios"
SEGUIMIENTO_TAB = "seguimiento"

ASISTENCIA_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"]
PERSONAS_COLS = ["nombre", "frecuencia", "centro", "edad", "domicilio", "notas", "activo", "timestamp", "usuario", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"]
ASISTENCIA_PERSONAS_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario", "notas"]
USUARIOS_COLS = ["usuario", "password", "centro", "nombre"]
SEGUIMIENTO_COLS = ["timestamp", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"]

C_BELEN = "Calle Belén"
C_NUDO = "Nudo a Nudo"
C_MARANATHA = "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]

ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# =========================
# Google Sheets (Con Credenciales Incluidas)
# =========================
def normalize_private_key(pk: str) -> str:
    if not isinstance(pk, str): return pk
    if "\\n" in pk: pk = pk.replace("\\n", "\n")
    return pk

def clean_string(s):
    if not isinstance(s, str): return ""
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.strip().upper()

def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default

def norm_text(x): return str(x).strip() if x else ""

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    sa = {
        "type": "service_account",
        "project_id": "hogar-de-cristo-asistencia",
        "private_key_id": "cb7af14255a324107d2d2119a4f95d4348ed5b90",
        "private_key": """-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDA6M0EIfQYCvZ/\n2cF1j9knWNLM1nGE0nohznJz8C9XsIJYZyPNXruD/y0cjdiQWyNopjzx3o15hoy2\ncRQOHDBgQA2alX9r7xd7rWvazwOTsgkNpRQVk0+wlOFUZdg79vQe9cn42JB71I0b\n0qsSLaeW35n3c8RFAzcv0XVmUdkRm76lU8pNhBKWOv3/DJJ2wB8VMW4l9Iq7MKyL\ng5t6d7qMPVckc3kGBsq/N+mPiisRjsPLgyvP3IHRzddIvcKiW9JpzNZoSqvOwpha\n2o+eMHuPHcJKev1JcJcU72CO1djfwwGM4L4ioRVVuE4w2EfCNdshSQC8Ht14alL3\ngQ6DMugNAgMBAAECggEAF1x562yzMzAsrsnvkC2V5hpvGMhFYgjdKnfmS10EVrG0\n70C6SLYWrkL6MxGIbt7imFs9WSsS5esh4jwqahUG1LkdDKHbFvaS2PLk81ALhljS\nmNjraDt5NJCrAv38ZDKhWJh6V4zeXmicmAh4mBB4UaCNdDaMR7E+fyd1+KijyWpl\noRqGUdpyEHoKCaXbPKQoGC9lGNs7xB7MGjPGi2pMz6O78oDTE1Obocqxk6sZYjrQ\nCH0jKwqTSosxlAb40hOFlGUUpDW7DF03trH0D9w2vNJTN/PqVJNOp5X7VKf2GTcg\n44ivcaEH2ZZF8hHIn9uDjWglVUFNJEwBGfEBmfVcQQKBgQDkkZzYG9czVslP+OHY\nANFQHAJ1tyEQ69O4YF8RZVLU6+QTIv8GplObaapVa1cAXPp0kMrU/bzUUKs38gZG\n8PQXYYpkCv/iceHqyLSm8KsvtKRSwXBwlzI5sn9XjSE1qAQsfg68LKikK3DswGjB\nc6qnsrm4fhnj1vU/ffsa7Xo5LQKBgQDYD5z3YATFvF5LHv3Ihj3gZZBoJMFss+EA\nt1TVt4KHaI94F224Bp52NDS3sScumQa+01WAaMBmGhPkw0G0hszQ428i5G7TCVuz\nM89Xb1aaQCSyopFKP8dVJYSJXXbwj+Cyno0DQc4jkcjSsfj2GgbG1BAjJqlnUGzr\nKAqBm/r2YQKBgDZZ6dH5zNKIcJZzuECE8UD7aBpV0acUbOQLBpA8Z9X5weJLEBmk\ns3zhQ3/MZoPPmD7fr1u2epCCHjTPeG6mHWTx7NadRvux2ObbkxmfYRWW/vwuw24C\nhg7yQxWumZcIvPVXhGl6tR9UtSWXG1HlD0+RUFhuo/lpxCe07WEZ11aBAoGBANFp\nUJnzVqzQhhQJVbClbBOyXOSTu2XAcrRe/Lqnwru7fFLJYm6a+7tVnkLsUS244/DQ\npG5xGQnc/KsdFPIENT/BMFaBUWj6CQcHkE8OesHGqcr6BhgQ+QJt+qepDz7aNM7r\nHYGqpkGTazHLjaH6V9cecwWe01JvgSHrDUPSCswBAoGAZgc8T9KvJ5r5sZQC/SkN\nSLzLT47WGr57f+WAT2CiaHhBRV2kwInNcsljsHCi1viFyQO/YDCWVEvozTjh6BoF\nrt4XiT6vnkKojyyG5uKBu+WHmXyaSH0aHj8ZCZl/C0Ab8MMAUVJg5zZHWyrztQAJ\nRx/AQ42L3AHtN6gVhU0zvVU=\n-----END PRIVATE KEY-----\n""",
        "client_email": "hogar-asistencia-bot@hogar-de-cristo-asistencia.iam.gserviceaccount.com",
        "client_id": "101282710856404935805",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/hogar-asistencia-bot%40hogar-de-cristo-asistencia.iam.gserviceaccount.com"
    }
    sa["private_key"] = normalize_private_key(sa.get("private_key", ""))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    sid = "1nCK2Q2ddxUO-erDwa5jgfGsUYsjZD7e4doHXoQ4N9zg"
    gc = get_gspread_client()
    return gc.open_by_key(sid)

def get_or_create_ws(sh, title, cols):
    try: return sh.worksheet(title)
    except Exception: pass
    try:
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(20, len(cols)))
        ws.update("A1", [cols])
        return ws
    except Exception as e:
        if "already exists" in str(e).lower(): return sh.worksheet(title)
        st.error(f"Error crítico: {e}"); st.stop()

# ✅ CACHÉ INTELIGENTE (Soluciona la lentitud y previene bloqueos)
@st.cache_data(ttl=300, show_spinner="Sincronizando Base de Datos...")
def load_all_managed_data():
    sh = get_spreadsheet()
    to_load = {
        ASISTENCIA_TAB: ASISTENCIA_COLS,
        PERSONAS_TAB: PERSONAS_COLS,
        ASISTENCIA_PERSONAS_TAB: ASISTENCIA_PERSONAS_COLS,
        USUARIOS_TAB: USUARIOS_COLS,
        SEGUIMIENTO_TAB: SEGUIMIENTO_COLS
    }
    dfs = {}
    for key, cols in to_load.items():
        ws = get_or_create_ws(sh, key, cols)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            dfs[key] = pd.DataFrame(columns=cols)
        else:
            header = values[0]
            body = values[1:]
            df = pd.DataFrame(body, columns=header)
            dfs[key] = df
    return dfs

def append_rows_sa(title, cols, rows_list):
    sh = get_spreadsheet()
    ws = get_or_create_ws(sh, title, cols)
    ws.append_rows(rows_list, value_input_option="USER_ENTERED")

# =========================
# Lógica de Negocio
# =========================
def get_today_asistencia_summary(df_a):
    if df_a.empty: return pd.DataFrame()
    hoy = get_today_ar().isoformat()
    d = df_a[df_a["fecha"] == hoy].copy()
    if d.empty: return pd.DataFrame()
    d["timestamp_dt"] = pd.to_datetime(d["timestamp"], errors="coerce")
    return d.sort_values("timestamp_dt").groupby(["centro", "espacio"]).tail(1)

def filter_personas_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    df_c = personas_for_centro(df_personas, centro)
    df_c["timestamp_dt"] = pd.to_datetime(df_c["timestamp"], errors="coerce")
    return df_c.sort_values("timestamp_dt").groupby("nombre").tail(1)

def calculate_birthday_alerts(df_p_filtered):
    if df_p_filtered.empty: return []
    cumples = []
    today = get_today_ar()
    for _, row in df_p_filtered.iterrows():
        try:
            fn = pd.to_datetime(str(row.get("fecha_nacimiento")), dayfirst=True, errors="coerce")
            if not pd.isna(fn) and fn.month == today.month and fn.day == today.day:
                cumples.append(row["nombre"])
        except: pass
    return cumples

def calculate_ausentes_alerts(df_ap, centro):
    if df_ap.empty: return []
    d = df_ap[(df_ap["centro"] == centro) & (df_ap["estado"] == "Presente")].copy()
    if d.empty: return []
    d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    last_p = d.groupby("nombre")["fecha_dt"].max().reset_index()
    hoy_ts = pd.Timestamp(get_today_ar())
    last_p["dias"] = (hoy_ts - last_p["fecha_dt"]).dt.days
    alertas = last_p[(last_p["dias"] > 7) & (last_p["dias"] < 90)].sort_values("dias", ascending=False)
    res = []
    for _, r in alertas.iterrows():
        res.append(f"{r['nombre']} ({r['dias']} días)")
    return res

def personas_for_centro(df_p, centro):
    if df_p.empty: return df_p
    c_list = list(df_p["centro"].astype(str).tolist())
    clean_c_list = [clean_string(c) for c in c_list]
    target_clean = clean_string(centro)
    matches = [centro == target_clean for centro in clean_c_list]
    return df_p[matches].copy()

def upsert_persona_direct(nombre, centro, usuario, **kwargs):
    now = get_now_ar_str()
    row_data = {c: "" for c in PERSONAS_COLS}
    row_data.update({"nombre": nombre.strip(), "centro": centro, "activo": "SI", "timestamp": now, "usuario": usuario})
    for k, v in kwargs.items():
        if k in PERSONAS_COLS: row_data[k] = str(v).strip()
    append_rows_sa(PERSONAS_TAB, PERSONAS_COLS, [[row_data[c] for c in PERSONAS_COLS]])

def latest_asistencia(df):
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    return df2.sort_values("timestamp_dt").groupby(["fecha", "centro", "espacio"]).tail(1)

# =========================
# UI COMPONENTES
# =========================
def show_login_screen(dfs):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_hogar.png", width=200) 
        except: st.title("🏠 Hogar de Cristo")
        st.markdown("### Acceso Coordinadores")
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                db_users = dfs[USUARIOS_TAB]
                row = db_users[(db_users["usuario"].astype(str).str.strip() == u.strip()) & (db_users["password"].astype(str).str.strip() == p.strip())]
                if not row.empty:
                    r = row.iloc[0]
                    st.session_state.update({
                        "logged_in": True,
                        "usuario": r["usuario"].strip(),
                        "centro_asignado": r["centro"].strip(), 
                        "nombre_visible": r["nombre"].strip()
                    })
                    st.success(f"¡Hola {r['nombre']}!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
    st.stop()

def show_top_header(nombre, centro_asignado):
    st.markdown(f"""
<div class='top-bar'>
    <div class='user-info'>{nombre}</div>
    <div class='center-info'>📍 {centro_asignado}</div>
</div>
""", unsafe_allow_html=True)

def show_kpi_alerts_bar(dfs, centro):
    df_p = filter_personas_centro(dfs[PERSONAS_TAB], centro)
    df_p_act = df_p[df_p["activo"].str.upper() == "SI"]
    cumples = calculate_birthday_alerts(df_p_act)
    ausentes = calculate_ausentes_alerts(dfs[ASISTENCIA_PERSONAS_TAB], centro)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("<div class='kpi'><h3>Estado Carga</h3>", unsafe_allow_html=True)
        today_a = get_today_asistencia_summary(dfs[ASISTENCIA_TAB])
        c_a = today_a[today_a["centro"] == centro]
        if c_a.empty:
            st.markdown("<div class='alert-box alert-danger'>Falta Cargar</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='alert-box alert-success'>✅ Cargado</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<div class='kpi'><h3>Cumpleaños Hoy</h3>", unsafe_allow_html=True)
        if cumples:
            with st.expander(f"🎂 {len(cumples)} Chicos", expanded=True):
                for c in cumples: st.markdown(f"- **{c}**")
        else:
             st.markdown("<div class='alert-box alert-gray'>Sin cumpleaños</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col3:
        st.markdown("<div class='kpi'><h3>Alertas Inasistencia</h3>", unsafe_allow_html=True)
        if ausentes:
            with st.expander(f"🔴 {len(ausentes)} Chicos", expanded=False):
                for a in ausentes: st.write(f"- {a}")
        else:
            st.markdown("<div class='alert-box alert-gray'>Al día</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# PÁGINAS PRINCIPALES
# =========================
def page_asistencia(dfs, centro, nombre_visible, usuario):
    st.subheader(f"📝 Carga Diaria: {centro}")
    fecha = st.date_input("Fecha", value=get_today_ar())
    if fecha > get_today_ar():
        st.error("⛔ No se puede cargar asistencia futura.")
        return
        
    espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA) if centro == C_MARANATHA else DEFAULT_ESPACIO
    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    notas = st.text_area("Notas generales del día")
    st.markdown("---")

    df_p_filtered = filter_personas_centro(dfs[PERSONAS_TAB], centro)
    df_activos = df_p_filtered[df_p_filtered["activo"].str.upper() == "SI"]
    nombres = sorted(df_activos["nombre"].tolist())
    
    col1, col2 = st.columns([3, 1])
    presentes = col1.multiselect("Marcar Asistentes", options=nombres)
    
    total_input = col2.number_input("Total Presentes", min_value=0, value=len(presentes))
    total_presentes = total_input if not presentes else len(presentes)
    
    with st.expander("👤 ¿Vino alguien nuevo?"):
        nueva = st.text_input("Nombre completo del nuevo ingreso").strip().upper()
        dni_new = st.text_input("DNI (Opcional)")
        tel_new = st.text_input("Teléfono (Opcional)")
        agregar_nueva = st.checkbox("Vino y agregarlo a la base")

    if st.button("💾 Guardar Asistencia", type="primary", use_container_width=True):
        if total_presentes <= 0 and modo != "Cerrado":
            st.error("⛔ Debes marcar asistentes o indicar 'Cerrado' en Modo.")
            return

        with st.spinner("Guardando en base de datos..."):
            if agregar_nueva and nueva:
                dfs[PERSONAS_TAB] = dfs[PERSONAS_TAB].drop_duplicates()
                existing = dfs[PERSONAS_TAB][dfs[PERSONAS_TAB]["nombre"].str.upper() == nueva]
                if not existing.empty:
                    st.warning(f"La persona '{nueva}' ya existe. Se marcará como presente.")
                else:
                    upsert_persona_direct(nueva, centro, usuario, frecuencia="Nueva", dni=dni_new, telefono=tel_new)
                if nueva not in presentes: presentes.append(nueva)

            accion = "append" 
            append_rows_sa(ASISTENCIA_TAB, ASISTENCIA_COLS, [[get_now_ar_str(), str(fecha), year_of(str(fecha)), centro, espacio, str(total_presentes), nombre_visible, modo, notas, usuario, accion]])

            list_presentes = []
            final_presentes = presentes if presentes else [nueva] if agregar_nueva and nueva else []
            final_presentes = list(set([n for n in final_presentes if n]))

            for n in final_presentes:
                list_presentes.append([get_now_ar_str(), str(fecha), year_of(str(fecha)), centro, espacio, n, "Presente", "SI" if n == nueva and agregar_nueva else "NO", nombre_visible, usuario, ""])
            
            ausentes = [n for n in nombres if n not in final_presentes]
            for n in ausentes:
                 list_presentes.append([get_now_ar_str(), str(fecha), year_of(str(fecha)), centro, espacio, n, "Ausente", "NO", nombre_visible, usuario, ""])

            if list_presentes:
                 append_rows_sa(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS, list_presentes)

        st.balloons()
        st.toast("✅ Asistencia guardada correctamente"); time.sleep(1.5); st.cache_data.clear(); st.rerun()

def page_legajo(dfs, centro, usuario):
    st.subheader("👥 Legajo Digital")
    df_p = filter_personas_centro(dfs[PERSONAS_TAB], centro)
    if df_p.empty: st.info("Sin registros cargados."); return
    
    nombres = sorted(df_p["nombre"].unique())
    seleccion = st.selectbox("🔍 Buscar Persona:", [""] + nombres, help="Escriba para buscar por nombre")
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-gray'>ℹ️ Utilice el buscador para abrir una ficha individual, o revise el listado histórico debajo.</div>", unsafe_allow_html=True)
        st.markdown(f"### Listado Histórico ({len(nombres)} personas)")
        
        with st.expander("📥 Descargar Padrón o Ver Tabla", expanded=False):
            if not df_p.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_p.to_excel(writer, sheet_name='Personas', index=False)
                st.download_button("Descargar Excel de Padrón", buffer, f"padron_{centro}.xlsx", "application/vnd.ms-excel", use_container_width=True)
                
                solo_activos = st.checkbox("Mostrar Solo activos", value=True)
                df_show = df_p.copy()
                if solo_activos: df_show = df_show[df_show["activo"].astype(str).str.upper() == "SI"]
                
                cols_to_show = ["nombre", "dni", "fecha_nacimiento", "telefono", "activo", "etiquetas", "contacto_emergencia"]
                for c in cols_to_show:
                    if c not in df_show.columns: df_show[c] = ""
                st.dataframe(df_show[cols_to_show].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    datos = df_p[df_p["nombre"] == seleccion].iloc[0]
    
    tags_str = str(datos.get("etiquetas", ""))
    tags_html = ""
    if tags_str and tags_str.lower() != "nan":
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

    telefono = str(datos.get("telefono", ""))
    wa_btn_html = ""
    if telefono and telefono.lower() != "nan" and format_wa_number(telefono):
        wa_btn_html = f"<div style='margin-top:10px;'><a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>💬 Contactar por WhatsApp</a></div>"
        
    estado_badge = "🟢 SOCIO/A ACTIVO" if str(datos.get("activo")).upper() != "NO" else "🔴 INACTIVO"
    
    import urllib.parse
    avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(seleccion)}&backgroundColor=004e7b&textColor=ffffff"

    dni_val = str(datos.get('dni', '')).strip()
    if dni_val.lower() == 'nan' or not dni_val: dni_val = "No registrado"
        
    nac_val = str(datos.get('fecha_nacimiento', '')).strip()
    if nac_val.lower() == 'nan' or not nac_val:
        nacimiento_mostrar = "No registrada"
    else:
        nacimiento_mostrar = f"{nac_val} ({calculate_age(nac_val)} años)"

    html_carnet = f"""
<div class="id-card">
<div style="display:flex; justify-content: space-between; align-items:flex-start;">
<div class="id-title">HOGAR DE CRISTO • {centro.upper()}</div>
<span style="font-weight:700; background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 10px; font-size: 0.7rem;">
{estado_badge}
</span>
</div>
<div style="display:flex; gap: 15px; align-items: center; margin-bottom: 10px;">
<img src="{avatar_url}" style="width: 50px; height: 50px; border-radius: 50%; border: 2px solid white;"/>
<div class="id-name" style="margin-bottom:0;">{seleccion}</div>
</div>
<div class="id-data-row">
<div class="id-data-col">
<span class="id-label">DNI / Documento</span>
<span class="id-value">{dni_val}</span>
</div>
<div class="id-data-col">
<span class="id-label">F. Nacimiento (Edad)</span>
<span class="id-value">{nacimiento_mostrar}</span>
</div>
</div>
<div class="tag-container">
{tags_html}
</div>
</div>
"""
    st.markdown(html_carnet, unsafe_allow_html=True)

    c_info, c_bitacora = st.columns([1.5, 2], gap="medium")
    
    with c_info:
        st.markdown("#### Información y Contacto")
        if wa_btn_html: st.markdown(wa_btn_html, unsafe_allow_html=True)
        st.write(f"🚑 **Emergencia:** {datos.get('contacto_emergencia', '---')}")
        st.write(f"🏠 **Domicilio:** {datos.get('domicilio', '---')}")
        st.info(f"📌 **Notas Fijas:** {datos.get('notas', 'Sin notas')}")

        with st.expander("✏️ Editar Ficha"):
            with st.form("edit_persona"):
                dni = st.text_input("DNI", value=datos.get("dni", ""))
                tel = st.text_input("Teléfono", value=datos.get("telefono", ""))
                contacto_em = st.text_input("Contacto Emergencia", value=datos.get("contacto_emergencia", ""))
                nac = st.text_input("Fecha Nac. (DD/MM/AAAA)", value=datos.get("fecha_nacimiento", ""))
                dom = st.text_input("Domicilio", value=datos.get("domicilio", ""))
                etiquetas = st.text_input("Etiquetas (Separadas por coma)", value=datos.get("etiquetas", ""))
                notas_fija = st.text_area("Notas Fijas", value=datos.get("notas", ""))
                activo_chk = st.checkbox("Activo", value=(str(datos.get("activo")).upper() != "NO"))
                
                if st.form_submit_button("Guardar Cambios"):
                    nuevo_estado = "SI" if activo_chk else "NO"
                    upsert_persona_direct(seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija, etiquetas=etiquetas, contacto_emergencia=contacto_em, activo=nuevo_estado)
                    st.toast("Actualizado correctamente")
                    time.sleep(1)
                    st.cache_data.clear(); st.rerun()
        
    with c_bitacora:
        st.markdown("#### 📖 Bitácora / Seguimiento")
        df_seg = dfs[SEGUIMIENTO_TAB]
        mis_notas = df_seg[(df_seg["nombre"] == seleccion) & (df_seg["centro"] == centro)]
        
        with st.expander("➕ Nueva Nota"):
            with st.form("new_seg"):
                fecha_seg = st.date_input("Fecha", value=get_today_ar())
                cat = st.selectbox("Categoría", CATEGORIAS_SEGUIMIENTO)
                obs = st.text_area("Detalle...")
                if st.form_submit_button("Guardar Nota"):
                    if len(obs) > 5:
                        append_rows_sa(SEGUIMIENTO_TAB, SEGUIMIENTO_COLS, [[get_now_ar_str(), str(fecha_seg), year_of(str(fecha_seg)), centro, seleccion, cat, obs, usuario]])
                        st.toast("Nota guardada")
                        time.sleep(1)
                        st.cache_data.clear(); st.rerun()
                    else:
                        st.error("Agregue más detalles.")

        if not mis_notas.empty:
            mis_notas["fecha_dt"] = pd.to_datetime(mis_notas["fecha"], errors="coerce")
            mis_notas = mis_notas.sort_values("fecha_dt", ascending=False)
            for _, note in mis_notas.iterrows():
                st.markdown(f"""
<div style="background-color:var(--surface); padding:15px; border-radius:8px; margin-bottom:10px; border-left: 4px solid var(--secondary);">
<div style="display:flex; justify-content:space-between; margin-bottom:5px;">
<strong style="color:var(--primary)">{note['categoria']}</strong> <small style="color:var(--text-secondary)">{note['fecha']} ({note['usuario']})</small>
</div>
<span style="font-size:0.95rem;">{note['observacion']}</span>
</div>
""", unsafe_allow_html=True)
        else: st.info("Sin registros en bitácora.")

def page_reportes(dfs, centro):
    st.subheader("📊 Reportes y Resumen")
    df_a = get_today_asistencia_summary(dfs[ASISTENCIA_TAB])
    df_c = df_a[df_a["centro"] == centro].copy()
    
    with st.expander("💾 Seguridad / Copia de Seguridad", expanded=False):
        st.caption("Descargar copia de TODAS las asistencias para guardar en tu PC.")
        buffer_backup = io.BytesIO()
        with pd.ExcelWriter(buffer_backup, engine='xlsxwriter') as writer:
            df_hist = latest_asistencia(dfs[ASISTENCIA_TAB])
            df_hist.to_excel(writer, sheet_name='Global_Asistencias', index=False)
        st.download_button("📥 Descargar RESPALDO COMPLETO", buffer_backup, f"BACKUP_TOTAL_{date.today()}.xlsx", "application/vnd.ms-excel")

    if df_c.empty: st.info("Sin datos cargados hoy."); return
    
    st.dataframe(df_c[["espacio", "presentes", "coordinador", "modo", "notas"]].set_index("espacio"), use_container_width=True)

# ==========================================
# 🌍 PESTAÑA GLOBAL (ESTADÍSTICAS TOTALES)
# ==========================================
def page_global(dfs):
    st.subheader("🌍 Panorama Global Institucional")
    
    df_a = latest_asistencia(dfs[ASISTENCIA_TAB]).copy()
    if not df_a.empty:
        df_a["presentes_i"] = df_a["presentes"].apply(lambda x: clean_int(x, 0))
    else:
        df_a = pd.DataFrame(columns=["anio", "centro", "presentes_i", "fecha"])
        
    anio = str(get_today_ar().year)
    
    df_p = dfs[PERSONAS_TAB]
    df_personas_unq = pd.DataFrame()
    if not df_p.empty:
        df_personas_unq = df_p.sort_values("timestamp").groupby("nombre").tail(1)
        df_personas_unq["edad_calc"] = df_personas_unq["fecha_nacimiento"].apply(calculate_age)
        
    df_ap = dfs[ASISTENCIA_PERSONAS_TAB]

    # Cálculos Totales Sumados
    total_personas = len(df_personas_unq) if not df_personas_unq.empty else 0
    total_asist_anio = 0
    promedio_global = 0.0
    
    if not df_a.empty:
        df_a_anio = df_a[df_a["anio"].astype(str) == anio]
        total_asist_anio = df_a_anio["presentes_i"].sum()
        dias_unicos = df_a_anio["fecha"].nunique()
        if dias_unicos > 0:
            promedio_global = total_asist_anio / dias_unicos
            
    nuevos_anio = 0
    if not df_ap.empty:
        nuevos_anio = len(df_ap[(df_ap["es_nuevo"]=="SI") & (df_ap["anio"].astype(str)==anio)])
        
    st.markdown("#### 📊 Métricas Totales (Suma Todos los Centros)")
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='kpi'><h3>Padrón Total</h3><div class='v'>{total_personas}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3>Asistencias {anio}</h3><div class='v'>{total_asist_anio}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><h3>Nuevos {anio}</h3><div class='v'>{nuevos_anio}</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi'><h3>Promedio Diario</h3><div class='v'>{promedio_global:.1f}</div></div>", unsafe_allow_html=True)
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Asistencias por Centro ({anio})**")
        if not df_a.empty:
            st.bar_chart(df_a[df_a["anio"].astype(str)==anio].groupby("centro")["presentes_i"].sum(), color="#60A5FA")
    with c2:
        st.markdown("**👥 Distribución por Edad Global**")
        if not df_personas_unq.empty:
            df_edades = df_personas_unq[df_personas_unq["edad_calc"] > 0].copy()
            if not df_edades.empty:
                bins = [0, 12, 18, 30, 50, 100]
                labels = ['Niños (0-12)', 'Adolescentes (13-18)', 'Jóvenes (19-30)', 'Adultos (31-50)', 'Mayores (50+)']
                df_edades['rango_edad'] = pd.cut(df_edades['edad_calc'], bins=bins, labels=labels, right=False)
                st.bar_chart(df_edades['rango_edad'].value_counts().sort_index(), color="#A78BFA")
            else:
                st.info("Falta cargar fechas de nacimiento válidas.")
        else:
            st.info("No hay personas cargadas.")

# =========================
# MAIN APP
# =========================
def main():
    # 1. Cargar Datos Centralizados (Con Caché Inteligente)
    dfs = load_all_managed_data()
    
    # 2. Login Screen
    if not st.session_state.get("logged_in"):
        show_login_screen(dfs)
    
    # Datos del sesion state
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]

    c_original = centro
    centro_clean = clean_string(centro)
    match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
    if not match_centro:
        st.error(f"Error Crítico: El centro asignado en la base de usuarios '{c_original}' no coincide con los centros definidos en la App ({', '.join(CENTROS)}). Avise al administrador.")
        st.stop()
    centro = match_centro

    # 3. Header y Alertas Superiores
    show_top_header(nombre, centro)
    
    # ✅ REGLA ESTRICTA NATASHA & Calle Belén
    mostrar_belen = True
    if centro == C_BELEN and u.upper() != "NATASHA":
        st.error("🔒 ACCESO DENEGADO: El centro Calle Belén es de acceso exclusivo para Natasha.")
        st.markdown("---")
        if st.button("Salir de la cuenta", type="primary"):
            st.session_state.clear(); st.rerun()
        mostrar_belen = False
    
    if not mostrar_belen: return 

    show_kpi_alerts_bar(dfs, centro)
    st.markdown("---")

    # 4. TABS PRINCIPALES
    list_tabs = ["📝 Asistencia", "👥 Legajo", "📊 Reportes"]
    if u.upper() == "NATASHA": list_tabs.append("🌍 Global")

    tabs = st.tabs(list_tabs)
    
    with tabs[0]: page_asistencia(dfs, centro, nombre, u)
    with tabs[1]: page_legajo(dfs, centro, u)
    with tabs[2]: page_reportes(dfs, centro)
    if len(tabs) > 3:
        with tabs[3]: page_global(dfs)

if __name__ == "__main__":
    main()
