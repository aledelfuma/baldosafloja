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

# =========================
# Config UI / Branding
# =========================
PRIMARY = "#004E7B"
SECONDARY = "#63296C"

st.set_page_config(
    page_title="Hogar de Cristo",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = f"""
<style>
/* 
======================================================
📱 HOGAR DE CRISTO: MOBILE-FIRST UI (STREAMLIT NATIVE)
======================================================
*/
:root {{
  --primary: {PRIMARY};
  --primary-light: rgba(0, 78, 123, 0.1);
  --secondary: {SECONDARY};
  --bg-color: #f8f9fa;
  --surface-color: #ffffff;
  --text-dark: #1e293b !important;
  --text-gray: #475569 !important;
  --radius-sm: 12px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --shadow-soft: 0 8px 30px rgba(0, 0, 0, 0.04);
  --shadow-inner: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
}}

/* Escondiendo y ajustando elementos nativos de Streamlit */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}} 

/* Fondo Global, Forzando texto oscuro y estructura Mobile */
.stApp {{
    background-color: var(--bg-color);
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    color: var(--text-dark);
}}
.stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {{
    color: var(--text-dark) !important;
}}

.css-18e3th9, .st-emotion-cache-1jicfl2 {{
    padding-top: 1rem !important; 
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 90px !important; 
    max-width: 600px !important; 
    margin: 0 auto;
}}

/* Tarjetas y Layouts (Sobrescribiendo Theme oscuro accidental de Streamlit) */
div[data-testid="stVerticalBlock"] > div {{
    color: var(--text-dark);
}}

.top-bar {{
    background-color: var(--surface-color);
    padding: 20px;
    border-radius: var(--radius-xl);
    border: 1px solid rgba(0,0,0,0.05);
    margin-bottom: 25px;
    box-shadow: var(--shadow-soft);
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
div.user-info {{
    font-size: 1.35rem; 
    font-weight: 800; 
    color: var(--text-dark) !important;
    line-height: 1.2;
}}
div.center-info {{
    font-size: 0.85rem; 
    font-weight: 600; 
    color: var(--text-gray) !important;
    margin-top: 4px;
}}

/* Custom Buttons (Primary style) */
.stButton>button {{
    background-color: var(--primary);
    color: white !important;
    border-radius: var(--radius-sm);
    border: none;
    font-weight: 600;
    padding: 0.6rem 1rem;
    box-shadow: 0 4px 15px var(--primary-light);
    transition: all 0.2s ease;
    width: 100%;
}}
.stButton>button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 78, 123, 0.2);
    background-color: #004269;
}}

/* Inputs Forzados a Claros con Texto Oscuro */
.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stMultiSelect>div>div>div {{
    border-radius: var(--radius-sm) !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    background-color: var(--surface-color) !important;
    color: var(--text-dark) !important;
    box-shadow: var(--shadow-inner);
    padding: 0.5rem;
}}

/* Fijando el Color de los Títulos de los Expanders */
.streamlit-expanderHeader {{
    color: var(--text-dark) !important;
    background-color: rgba(255,255,255,0.8);
    border-radius: var(--radius-sm);
}}

/* KPIs Modernos (Métricas Resumen) */
.kpi {{
  border-radius: var(--radius-lg);
  padding: 18px;
  background: var(--surface-color);
  box-shadow: var(--shadow-soft);
  text-align: center;
  border: 1px solid rgba(0,0,0,0.02);
  height: 100%;
}}
.kpi h3 {{ 
    margin: 0; 
    font-size: 0.70rem; 
    color: var(--text-gray) !important;
    text-transform: uppercase; 
    font-weight: 700;
    letter-spacing: 0.5px; 
}}
.kpi .v {{ 
    font-size: 2.2rem; 
    font-weight: 800; 
    margin-top: 5px; 
    color: var(--primary) !important; 
    line-height: 1;
}}

/* Alertas Estilo iOS */
.alert-box {{ 
    padding: 15px; 
    border-radius: var(--radius-sm); 
    margin-bottom: 12px; 
    font-size: 0.9rem; 
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.alert-danger {{ background-color: #FEF2F2; color: #991B1B !important; border: 1px solid #FEE2E2; }}
.alert-success {{ background-color: #F0FDF4; color: #166534 !important; border: 1px solid #DCFCE7; }}
.alert-gray {{ background-color: var(--surface-color); color: var(--text-gray) !important; border: 1px solid rgba(0,0,0,0.05); box-shadow: var(--shadow-soft); }}

/* ===============================================
   💳 CARNET DIGITAL (Legajo Profile Card)
   =============================================== */
.id-card {{
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    border-radius: var(--radius-xl);
    padding: 30px;
    color: white !important;
    box-shadow: 0 15px 35px rgba(0, 78, 123, 0.25);
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 25px;
    position: relative;
    overflow: hidden;
}}
.id-card * {{ color: white !important; }}
.id-card::before {{
    content: "";
    position: absolute;
    top: -50px;
    right: -20px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 70%);
    border-radius: 50%;
}}
.id-card::after {{
    content: "";
    position: absolute;
    bottom: -60px;
    left: -40px;
    width: 150px;
    height: 150px;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
    border-radius: 50%;
}}
.id-title {{ font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; opacity: 0.7; margin-bottom: 12px; font-weight: 700;}}
.id-name {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 20px; line-height: 1.1; letter-spacing: -0.5px; text-shadow: 0 2px 10px rgba(0,0,0,0.1);}}
.id-data-row {{ display: flex; gap: 25px; margin-bottom: 15px; }}
.id-data-col {{ display: flex; flex-direction: column; }}
.id-label {{ font-size: 0.65rem; opacity: 0.7; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 2px;}}
.id-value {{ font-size: 1.05rem; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.1);}}

/* Etiquetas Visuales (Tags) */
.tag-container {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 15px; }}
.tag-badge {{
    background-color: rgba(255,255,255,0.15);
    backdrop-filter: blur(10px);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid rgba(255,255,255,0.2);
    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}}

/* Botón WhatsApp */
.btn-wa {{
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #25D366;
    color: white !important;
    padding: 12px 20px;
    border-radius: var(--radius-sm);
    text-decoration: none;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 20px;
    box-shadow: 0 6px 15px rgba(37, 211, 102, 0.25);
    transition: all 0.2s ease;
    width: 100%;
}}
.btn-wa:hover {{ background-color: #128C7E; transform: translateY(-2px); }}

.profile-card {{
    background-color: var(--surface-color);
    padding: 24px;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-soft);
    margin-bottom: 20px;
    border: 1px solid rgba(0,0,0,0.05);
}}

/* ===============================================
   📱 PESTAÑAS (TABS) COMO BOTTOM NAVIGATION BAR
   =============================================== */
.stTabs [data-baseweb="tab-list"] {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(15px);
    border-top: 1px solid rgba(0,0,0,0.05);
    display: flex;
    justify-content: space-around;
    padding: 10px 10px 20px 10px;
    z-index: 9999;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.03);
}}
.stTabs [data-baseweb="tab"] {{
    flex-grow: 1;
    text-align: center;
    justify-content: center;
    font-size: 0.8rem !important;
    font-weight: 600;
    color: var(--text-gray) !important;
    padding: 10px 0;
    border: none !important;
    background: transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--primary) !important;
    border-radius: 10px;
    background-color: rgba(0, 78, 123, 0.05) !important;
}}
.stTabs [aria-selected="true"]::after {{
    display: none;
}}
div[role="tabpanel"] {{
    padding-bottom: 40px; 
}}
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
# Schemas
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

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]
ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# =========================
# Google Sheets (Hardcoded)
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

def get_or_create_ws(title: str, cols: list):
    sh = get_spreadsheet()
    try: return sh.worksheet(title)
    except Exception: pass
    try:
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(20, len(cols)))
        ws.update("A1", [cols])
        return ws
    except Exception as e:
        if "already exists" in str(e).lower(): return sh.worksheet(title)
        st.error(f"Error crítico: {e}"); st.stop()

def safe_get_all_values(ws, tries=3):
    for i in range(tries):
        try: return ws.get_all_values()
        except: time.sleep(0.5)
    st.error("Error conexión Sheets."); st.stop()

def read_ws_df(title: str, cols: list) -> pd.DataFrame:
    ws = get_or_create_ws(title, cols)
    values = safe_get_all_values(ws)
    if not values:
        ws.update("A1", [cols])
        return pd.DataFrame(columns=cols)
    header = values[0]
    body = values[1:] if len(values) > 1 else []
    df = pd.DataFrame(body)
    if not df.empty:
        df = df.iloc[:, :len(header)]
        df.columns = header
    else:
        df = pd.DataFrame(columns=header)
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df[cols]

def append_ws_rows(title: str, cols: list, rows: list[list]):
    ws = get_or_create_ws(title, cols)
    first = safe_get_all_values(ws)[:1]
    if not first or first[0][: len(cols)] != cols: ws.update("A1", [cols])
    ws.append_rows(rows, value_input_option="USER_ENTERED")

# =========================
# Data & Logic
# =========================
@st.cache_data(ttl=600, show_spinner=False)
def get_users_db(): return read_ws_df(USUARIOS_TAB, USUARIOS_COLS)

@st.cache_data(ttl=300, show_spinner="Sincronizando...")
def load_all_data():
    df_a = read_ws_df(ASISTENCIA_TAB, ASISTENCIA_COLS)
    df_p = read_ws_df(PERSONAS_TAB, PERSONAS_COLS)
    df_ap = read_ws_df(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS)
    df_seg = read_ws_df(SEGUIMIENTO_TAB, SEGUIMIENTO_COLS)
    return df_a, df_p, df_ap, df_seg

def year_of(fecha_iso: str) -> str:
    try: return str(pd.to_datetime(fecha_iso).year)
    except: return str(get_today_ar().year)

def latest_asistencia(df):
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    df2["k"] = (df2["anio"].astype(str)+"|"+df2["fecha"].astype(str)+"|"+df2["centro"].astype(str)+"|"+df2["espacio"].astype(str))
    return df2.sort_values("timestamp_dt").groupby("k", as_index=False).tail(1)

def last_load_info(df_latest, centro):
    if df_latest.empty: return None, None
    d = df_latest[df_latest["centro"] == centro].copy()
    if d.empty: return None, None
    last = pd.to_datetime(d["fecha"], errors="coerce").max()
    if pd.isna(last): return None, None
    days = (pd.Timestamp(get_today_ar()).date() - last.date()).days
    return last.date().isoformat(), int(days)

def personas_for_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    if "centro" in df_personas.columns:
        centro_clean = clean_string(centro)
        df_temp = df_personas.copy()
        df_temp['centro_norm'] = df_temp['centro'].apply(clean_string)
        return df_temp[df_temp['centro_norm'] == centro_clean].copy()
    return df_personas.copy()

def upsert_persona(df_personas, nombre, centro, usuario, **kwargs):
    nombre = norm_text(nombre)
    if not nombre: return df_personas
    now = get_now_ar_str()
    row = {c: "" for c in PERSONAS_COLS}
    row.update({"nombre": nombre, "centro": centro, "activo": "SI", "timestamp": now, "usuario": usuario})
    for k, v in kwargs.items():
        if k in PERSONAS_COLS: row[k] = str(v)
    append_ws_rows(PERSONAS_TAB, PERSONAS_COLS, [[row[c] for c in PERSONAS_COLS]])
    return pd.concat([df_personas, pd.DataFrame([row])], ignore_index=True)

def append_asistencia(fecha, centro, espacio, presentes, coordinador, modo, notas, usuario, accion="append"):
    ts = get_now_ar_str()
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha), "centro": centro, 
        "espacio": espacio, "presentes": str(presentes), "coordinador": coordinador, 
        "modo": modo, "notas": notas, "usuario": usuario, "accion": accion
    }
    append_ws_rows(ASISTENCIA_TAB, ASISTENCIA_COLS, [[row.get(c, "") for c in ASISTENCIA_COLS]])

def append_asistencia_personas(fecha, centro, espacio, nombre, estado, es_nuevo, coordinador, usuario, notas=""):
    ts = get_now_ar_str()
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha), "centro": centro, 
        "espacio": espacio, "nombre": nombre, "estado": estado, "es_nuevo": es_nuevo, 
        "coordinador": coordinador, "usuario": usuario, "notas": notas
    }
    append_ws_rows(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS, [[row.get(c, "") for c in ASISTENCIA_PERSONAS_COLS]])

def append_seguimiento(fecha, centro, nombre, categoria, observacion, usuario):
    ts = get_now_ar_str()
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha), "centro": centro,
        "nombre": nombre, "categoria": categoria, "observacion": observacion, "usuario": usuario
    }
    append_ws_rows(SEGUIMIENTO_TAB, SEGUIMIENTO_COLS, [[row.get(c, "") for c in SEGUIMIENTO_COLS]])

# =========================
# UI COMPONENTES
# =========================
def show_login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_hogar.png", width=200)
        except: st.title("Hogar de Cristo")
        st.markdown("### Acceso al Sistema")
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                df_users = get_users_db()
                row = df_users[(df_users["usuario"].astype(str).str.strip()==u.strip()) & (df_users["password"].astype(str).str.strip()==p.strip())]
                if not row.empty:
                    r = row.iloc[0]
                    st.session_state.update({"logged_in": True, "usuario": r["usuario"], "centro_asignado": r["centro"].strip(), "nombre_visible": r["nombre"]})
                    st.rerun()
                else:
                    st.error("Error de credenciales.")
    st.stop()

def show_top_header(nombre, centro):
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        try: st.image("logo_hogar.png", width=100)
        except: st.write("🏠")
    with c2:
        st.markdown(f"<div class='user-info'>Hola, {nombre}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='center-info'>📍 {centro}</div>", unsafe_allow_html=True)
    with c3:
        if st.button("Salir", key="logout", use_container_width=True):
            st.session_state.clear(); st.cache_data.clear(); st.rerun()
        if st.button("🔄 Refrescar", key="refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()

def show_top_alerts(df_latest, df_personas, df_ap, centro):
    last_date, days = last_load_info(df_latest, centro)
    
    cumples = []
    if not df_personas.empty:
        df_c = personas_for_centro(df_personas, centro)
        df_c["timestamp_dt"] = pd.to_datetime(df_c["timestamp"], errors="coerce")
        df_c = df_c.sort_values("timestamp_dt").groupby("nombre").tail(1)
        today = get_today_ar()
        for _, row in df_c.iterrows():
            try:
                fn = pd.to_datetime(str(row.get("fecha_nacimiento")), dayfirst=True, errors="coerce")
                if not pd.isna(fn) and fn.month == today.month and fn.day == today.day:
                    cumples.append(row["nombre"])
            except: pass

    ausentes = []
    if not df_ap.empty:
        d = df_ap[(df_ap["centro"]==centro) & (df_ap["estado"]=="Presente")].copy()
        if not d.empty:
            d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
            last = d.groupby("nombre")["fecha_dt"].max().reset_index()
            hoy_ts = pd.Timestamp(get_today_ar())
            last["dias"] = (hoy_ts - last["fecha_dt"]).dt.days
            alertas = last[(last["dias"]>7) & (last["dias"]<90)].sort_values("dias", ascending=False)
            for _, r in alertas.iterrows(): ausentes.append(f"{r['nombre']} ({r['dias']} días)")

    # Dashboard Inspirado en tu diseño
    st.markdown("### 📊 Resumen de Asistencia y Alertas")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if last_date is None: st.markdown("<div class='alert-box alert-danger'>⚠️ Estado: Sin cargas</div>", unsafe_allow_html=True)
        elif days == 0: st.markdown("<div class='alert-box alert-success'>✅ Estado: Al día (Hoy)</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='alert-box alert-danger'>⚠️ Faltan cargar asistencias (hace {days}d)</div>", unsafe_allow_html=True)
    with ac2:
        if cumples:
            with st.expander(f"🎉 Cumpleaños Hoy ({len(cumples)})", expanded=True):
                for c in cumples: st.write(f"- {c}")
        else:
             st.markdown("<div class='alert-box' style='color:grey; border:1px solid #ccc;'>🎂 Sin cumpleaños hoy</div>", unsafe_allow_html=True)
    with ac3:
        if ausentes:
            with st.expander(f"⚠️ Alerta de Inasistencia ({len(ausentes)})", expanded=False):
                for a in ausentes: st.write(f"🔴 {a}")
        else:
            st.markdown("<div class='alert-box' style='color:grey; border:1px solid #ccc;'>✔️ Sin alertas de inasistencia</div>", unsafe_allow_html=True)

def kpi_row_full(df_latest, centro):
    hoy_date = get_today_ar()
    hoy = hoy_date.isoformat()
    week_ago = (hoy_date - timedelta(days=6)).isoformat()
    month_start = hoy_date.replace(day=1).isoformat()
    d = df_latest.copy()
    if d.empty: c1=c2=c3=0
    else:
        d["presentes_i"] = d.get("presentes", "").apply(lambda x: clean_int(x, 0))
        c1 = int(d[(d["centro"] == centro) & (d["fecha"] == hoy)]["presentes_i"].sum())
        c2 = int(d[(d["centro"] == centro) & (d["fecha"] >= week_ago) & (d["fecha"] <= hoy)]["presentes_i"].sum())
        c3 = int(d[(d["centro"] == centro) & (d["fecha"] >= month_start) & (d["fecha"] <= hoy)]["presentes_i"].sum())
    
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    col1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi'><h3>Este mes</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div style='text-align:center; padding-top:10px; opacity:0.8;'><b>Accesos Rápidos</b></div>", unsafe_allow_html=True)
        st.caption("Ve a las pestañas de abajo para:")
        st.markdown("📝 **Cargar Asistencia**")
        st.markdown("👤 **Nuevo Ingreso / Legajo**")

# =========================
# PAGES
# =========================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.subheader(f"📝 Carga Diaria: {centro}")
    fecha = st.date_input("Fecha", value=get_today_ar())
    if fecha > get_today_ar():
        st.error("⛔ No se puede cargar asistencia futura.")
        return
    fecha_str = fecha.isoformat()
    espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA) if centro == "Casa Maranatha" else DEFAULT_ESPACIO
    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    notas = st.text_area("Notas generales del día")
    st.markdown("---")

    df_centro = personas_for_centro(df_personas, centro)
    nombres = sorted(list(set([n for n in df_centro["nombre"].astype(str).tolist() if n.strip()])))
    
    c1, c2 = st.columns([3, 1])
    presentes = c1.multiselect("Asistentes", options=nombres)
    total_presentes = c2.number_input("Total", min_value=0, value=len(presentes))
    
    with st.expander("👤 ¿Vino alguien nuevo?"):
        cn1, cn2 = st.columns(2)
        nueva = cn1.text_input("Nombre completo")
        dni_new = cn2.text_input("DNI (Opcional)")
        cn3, cn4 = st.columns(2)
        tel_new = cn3.text_input("Tel (Opcional)")
        nac_new = cn4.text_input("Fecha Nac. (DD/MM/AAAA) (Opcional)")
        agregar_nueva = st.checkbox("Agregar a la base")
        
        if agregar_nueva and dni_new.strip() and not df_personas.empty:
            existe_dni = df_personas[df_personas['dni'].astype(str).str.strip() == dni_new.strip()]
            if not existe_dni.empty:
                st.markdown(f"<div class='alert-box alert-danger'>⚠️ DNI duplicado: {existe_dni.iloc[0]['nombre']}</div>", unsafe_allow_html=True)

    df_latest = latest_asistencia(df_asistencia)
    ya = df_latest[(df_latest.get("fecha","")==fecha_str) & (df_latest.get("centro","")==centro) & (df_latest.get("espacio","")==espacio)]
    overwrite = True
    if not ya.empty:
        st.warning("⚠️ Ya existe carga para hoy. Se sobreescribirá.")
        overwrite = st.checkbox("Confirmar", value=False)
    
    if st.button("💾 Guardar Asistencia", type="primary", use_container_width=True):
        if not overwrite: st.error("Confirmá sobreescritura"); st.stop()
        
        if agregar_nueva and nueva.strip():
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, frecuencia="Nueva", dni=dni_new, telefono=tel_new, fecha_nacimiento=nac_new)
            if nueva not in presentes: presentes.append(nueva)
        
        if len(presentes)>0: total_presentes = len(presentes)
        accion = "overwrite" if not ya.empty else "append"
        
        with st.spinner("Guardando..."):
            append_asistencia(fecha_str, centro, espacio, total_presentes, nombre_visible, modo, notas, usuario, accion)
            for n in presentes:
                append_asistencia_personas(fecha_str, centro, espacio, n, "Presente", "SI" if (agregar_nueva and n==nueva) else "NO", nombre_visible, usuario)
            ausentes = [n for n in nombres if n not in presentes]
            for n in ausentes:
                append_asistencia_personas(fecha_str, centro, espacio, n, "Ausente", "NO", nombre_visible, usuario)

        st.balloons()
        st.toast("✅ Guardado Exitoso"); time.sleep(1.5); st.cache_data.clear(); st.rerun()

def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.subheader("👥 Ficha de la Persona")
    df_centro = personas_for_centro(df_personas, centro)
    
    # Nos quedamos con la fila más reciente por persona
    if not df_centro.empty:
        df_centro["timestamp_dt"] = pd.to_datetime(df_centro["timestamp"], errors="coerce")
        df_centro = df_centro.sort_values("timestamp", ascending=True).groupby("nombre").tail(1)
    
    nombres = sorted(df_centro["nombre"].unique()) if not df_centro.empty else []

    col_sel, col_act = st.columns([3, 1])
    seleccion = col_sel.selectbox("🔍 Buscar a una persona en el padrón:", [""] + nombres, help="Escriba aquí para buscar por nombre")
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-gray'>ℹ️ Utilice el buscador para abrir una ficha individual, o revise el listado histórico debajo.</div>", unsafe_allow_html=True)
        st.markdown(f"### Listado Histórico ({len(nombres)} personas)")
        
        with st.expander("📥 Descargar Padrón o Ver Tabla", expanded=False):
            if not df_centro.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_centro.to_excel(writer, sheet_name='Personas', index=False)
                st.download_button("Descargar Excel de Padrón", buffer, f"padron_{centro}.xlsx", "application/vnd.ms-excel", use_container_width=True)
                
                solo_activos = st.checkbox("Mostrar Solo activos", value=True)
                df_show = df_centro.copy()
                if solo_activos: df_show = df_show[df_show["activo"].astype(str).str.upper() == "SI"]
                
                cols_to_show = ["nombre", "dni", "fecha_nacimiento", "telefono", "activo", "etiquetas", "contacto_emergencia"]
                for c in cols_to_show:
                    if c not in df_show.columns: df_show[c] = ""
                st.dataframe(df_show[cols_to_show].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    # === CARGAMOS LA FICHA INDIVIDUAL ===
    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    # Procesar Etiquetas Html
    tags_str = str(datos_persona.get("etiquetas", ""))
    tags_html = ""
    if tags_str and tags_str.lower() != "nan":
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

    # Preparar Datos de Contacto
    telefono = str(datos_persona.get("telefono", ""))
    wa_btn_html = ""
    if telefono and telefono.lower() != "nan" and format_wa_number(telefono):
        wa_btn_html = f"<div style='margin-top:10px;'><a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>💬 Contactar por WhatsApp</a></div>"
        
    estado_badge = "🟢 SOCIO/A ACTIVO" if str(datos_persona.get("activo")).upper() != "NO" else "🔴 INACTIVO"
    
    # Avatar Dinámico Generado
    import urllib.parse
    avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(seleccion)}&backgroundColor=004e7b&textColor=ffffff"

    # ==========================
    # CÓDIGO HTML DE LA FICHA Y EL CARNET
    # ==========================
    st.markdown(f"""
    <div style="display: flex; flex-direction: column; gap: 20px;">
        
        <!-- CARD PRINCIPAL (CABECERA) -->
        <div class="id-card" style="margin-bottom:0px;">
            <div style="display:flex; justify-content: space-between; align-items:flex-start; margin-bottom: 5px;">
                <div class="id-title">HOGAR DE CRISTO • {{centro.upper()}}</div>
                <span style="font-weight:800; background: rgba(255,255,255,0.25); padding: 5px 12px; border-radius: 12px; font-size: 0.70rem; letter-spacing:1px;">
                    {estado_badge}
                </span>
            </div>
            
            <div style="display:flex; gap: 20px; align-items: center; margin-bottom: 20px;">
                <img src="{avatar_url}" style="width: 70px; height: 70px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.8); box-shadow: 0 4px 10px rgba(0,0,0,0.1);"/>
                <div class="id-name" style="margin-bottom:0;">{seleccion}</div>
            </div>
            
            <div class="id-data-row">
                <div class="id-data-col">
                    <span class="id-label">DNI / Documento</span>
                    <span class="id-value">{datos_persona.get('dni', 'No registrado')}</span>
                </div>
                <div class="id-data-col">
                    <span class="id-label">Nacimiento (Edad)</span>
                    <span class="id-value">{datos_persona.get('fecha_nacimiento', '---')} ({calculate_age(datos_persona.get('fecha_nacimiento', ''))} años)</span>
                </div>
            </div>
            
            <div class="tag-container">
                {tags_html}
            </div>
        </div>

    </div>
    <br>
    """, unsafe_allow_html=True)
    
    # ==========================
    # PANELES DE INFORMACIÓN (2 Columnas)
    # ==========================
    c_info, c_bitacora = st.columns([1.2, 1.8], gap="medium")
    
    with c_info:
        # TARJETAS DE CONTACTO (Estilo Streamlit Metrics/Containers + Markdown)
        st.markdown("### 📞 Datos de Contacto")
        st.markdown(f"""
        <div class="profile-card" style="padding: 15px;">
            <div style="font-size: 0.8rem; color:var(--text-gray); text-transform:uppercase; font-weight:700;">🏠 Domicilio Actual</div>
            <div style="font-weight: 600; font-size:1.1rem; color:var(--text-dark); margin-top:2px;">{datos_persona.get('domicilio', 'No registrado') if datos_persona.get('domicilio', '') else 'No registrado'}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="profile-card" style="padding: 15px; border-left: 4px solid var(--primary);">
            <div style="font-size: 0.8rem; color:var(--text-gray); text-transform:uppercase; font-weight:700;">📱 Celular Principal</div>
            <div style="font-weight: 600; font-size:1.2rem; color:var(--text-dark); margin-top:2px;">{datos_persona.get('telefono', 'No registrado') if datos_persona.get('telefono', '') else 'No registrado'}</div>
            {wa_btn_html}
        </div>
        """, unsafe_allow_html=True)
        
        # Tarjeta de Emergencia
        emergencia = str(datos_persona.get('contacto_emergencia', '')).strip()
        if emergencia and emergencia.lower() != 'nan':
            st.markdown(f"""
            <div class="profile-card" style="padding: 15px; background-color: #FEF2F2; border: 1px solid #FEE2E2; border-left: 4px solid #DF2020;">
                <div style="font-size: 0.8rem; color:#991B1B; text-transform:uppercase; font-weight:800;">🚨 Contacto de Emergencia</div>
                <div style="font-weight: 700; font-size:1.0rem; color:#7F1D1D; margin-top:2px;">{emergencia}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("🚨 No posee contacto de emergencia cargado.")
            
        # Notas Fijas Médicas/Sociales
        notas_str = str(datos_persona.get('notas', '')).strip()
        if notas_str and notas_str.lower() != 'nan':
            st.info(f"**Notas Fijas (Alergias/Contexto):**\n\n{notas_str}")

        # Formulario Oculto de Edición
        with st.expander("✏️ Editar Ficha de la Persona"):
            with st.form("edit_persona"):
                dni = st.text_input("DNI", value=datos_persona.get("dni", ""))
                tel = st.text_input("Teléfono", value=datos_persona.get("telefono", ""))
                contacto_em = st.text_input("🚨 Contacto Emergencia", value=datos_persona.get("contacto_emergencia", ""))
                nac = st.text_input("Fecha Nac. (DD/MM/AAAA)", value=datos_persona.get("fecha_nacimiento", ""))
                dom = st.text_input("Domicilio", value=datos_persona.get("domicilio", ""))
                etiquetas = st.text_input("Etiquetas (Separadas por coma)", value=datos_persona.get("etiquetas", ""), help="Ej: Diabético, Medicación, Pensionado")
                notas_fija = st.text_area("Notas Fijas (Alergias, Condiciones crónicas)", value=datos_persona.get("notas", ""))
                activo_chk = st.checkbox("Sigue Activo (Si se desmarca, no saldrá en el padrón de asistencias)", value=(str(datos_persona.get("activo")).upper() != "NO"))
                
                if st.form_submit_button("💾 Guardar Cambios Permanentes", use_container_width=True):
                    nuevo_estado = "SI" if activo_chk else "NO"
                    upsert_persona(df_personas, seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija, activo=nuevo_estado, contacto_emergencia=contacto_em, etiquetas=etiquetas)
                    st.success("¡Ficha actualizada!")
                    time.sleep(1)
                    st.cache_data.clear(); st.rerun()
        
    with c_bitacora:
        st.markdown("### 📖 Bitácora Reciente")
        st.caption("Carga aquí cualquier seguimiento médico, trabajador social, psicólogo, o charla importante que hayas tenido con esta persona.")
        
        with st.expander("➕ Escribir en la Bitácora", expanded=False):
            with st.form("new_seg"):
                fecha_seg = st.date_input("Fecha de Consulta", value=get_today_ar())
                cat = st.selectbox("Categoría / Área", CATEGORIAS_SEGUIMIENTO)
                obs = st.text_area("Detalle de lo hablado o sucedido...")
                if st.form_submit_button("📝 Guardar Registro", use_container_width=True):
                    if len(obs) > 5:
                        append_seguimiento(str(fecha_seg), centro, seleccion, cat, obs, usuario)
                        st.success("Guardado correctame")
                        time.sleep(1)
                        st.cache_data.clear(); st.rerun()
                    else:
                        st.error("Por favor escriba más detalles.")
        
        # Historial (Feed Layout)
        if not df_seg.empty:
            mis_notas = df_seg[(df_seg["nombre"]==seleccion) & (df_seg["centro"]==centro)].copy()
            if not mis_notas.empty:
                mis_notas["fecha_dt"] = pd.to_datetime(mis_notas["fecha"], errors="coerce")
                mis_notas = mis_notas.sort_values("fecha_dt", ascending=False)
                
                st.markdown("<br>", unsafe_allow_html=True)
                for _, note in mis_notas.iterrows():
                    # Definimos iconos basados en la categoría para dar feedback visual
                    cat = str(note['categoria']).lower()
                    icon = "🩺" if "salud" in cat else "📝" if "trámite" in cat else "🫂" if 'escucha' in cat else "🚨" if 'crisis' in cat else "📌"
                    color_left = "#DC2626" if "crisis" in cat else SECONDARY
                    
                    st.markdown(f"""
                    <div style="background-color: var(--surface-color); padding:15px; border-radius:var(--radius-sm); margin-bottom:12px; border-left: 5px solid {color_left}; box-shadow: var(--shadow-soft);">
                        <div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom:8px; margin-bottom:8px;">
                            <strong style="color:var(--primary); font-size:1.05rem;">{icon} {note['categoria']}</strong>
                            <div style="text-align:right;">
                                <div style="color:var(--text-gray); font-size:0.75rem; font-weight:700;">{note['fecha']}</div>
                                <div style="color:var(--text-gray); font-size:0.65rem; padding-top:2px;">Por: {str(note.get('usuario', ''))}</div>
                            </div>
                        </div>
                        <div style="font-size:0.95rem; color:var(--text-dark); line-height:1.5;">{note['observacion']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.info("Sin registros en la bitácora aún. (Pulsa '+ Escribir' arriba).")

def page_reportes(df_asistencia, centro):
    st.subheader("📊 Reportes")
    df_latest = latest_asistencia(df_asistencia)
    df_c = df_latest[df_latest["centro"] == centro].copy()
    
    with st.expander("💾 Seguridad / Copia de Seguridad"):
        st.caption("Descargar copia de TODAS las asistencias.")
        buffer_backup = io.BytesIO()
        with pd.ExcelWriter(buffer_backup, engine='xlsxwriter') as writer:
            df_latest.to_excel(writer, sheet_name='Global_Asistencias', index=False)
        st.download_button("📥 Descargar RESPALDO COMPLETO", buffer_backup, f"BACKUP_TOTAL_{date.today()}.xlsx", "application/vnd.ms-excel")

    if df_c.empty: st.info("Sin datos."); return
    
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"])
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c = df_c.sort_values("fecha_dt")
    
    c1, c2 = st.columns([3,1])
    c1.line_chart(df_c.set_index("fecha")["presentes_i"])
    with c2:
        st.markdown("##### Resumen")
        st.metric("Promedio Diario", f"{df_c['presentes_i'].mean():.1f}")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_c.to_excel(writer, sheet_name='Asistencia', index=False)
        st.download_button("📥 Bajar Excel Centro", buffer, f"asistencia_{centro}.xlsx", "application/vnd.ms-excel")
    
    st.dataframe(df_c[["fecha", "espacio", "presentes", "coordinador", "notas"]].sort_values("fecha", ascending=False), use_container_width=True)

def page_global(df_asistencia, df_personas, df_ap):
    st.subheader("🌍 Panorama Global")
    df = latest_asistencia(df_asistencia).copy()
    if df.empty: return
    df["presentes_i"] = df["presentes"].apply(lambda x: clean_int(x, 0))
    anio = str(get_today_ar().year)
    
    df_personas_unq = df_personas.sort_values("timestamp").groupby("nombre").tail(1)
    df_personas_unq["edad_calc"] = df_personas_unq["fecha_nacimiento"].apply(calculate_age)
    df_personas_unq = df_personas_unq[df_personas_unq["edad_calc"] > 0]
    bins = [0, 12, 18, 30, 50, 100]
    labels = ['Niños (0-12)', 'Adolescentes (13-18)', 'Jóvenes (19-30)', 'Adultos (31-50)', 'Mayores (50+)']
    df_personas_unq['rango_edad'] = pd.cut(df_personas_unq['edad_calc'], bins=bins, labels=labels, right=False)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Asistencias {anio}**")
        st.bar_chart(df[df["anio"].astype(str)==anio].groupby("centro")["presentes_i"].sum())
    with c2:
        st.markdown("**👥 Distribución por Edad (Padrón)**")
        if not df_personas_unq.empty:
            st.bar_chart(df_personas_unq['rango_edad'].value_counts().sort_index(), color="#63296C")
        else:
            st.info("Falta cargar fechas de nacimiento.")

# =========================
# MAIN
# =========================
def main():
    if not st.session_state.get("logged_in"): show_login_screen()
    
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]
    
    centro_clean = clean_string(centro)
    match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
    if not match_centro: st.error("Centro inválido."); st.stop()
    centro = match_centro

    show_top_header(nombre, centro)
    
    df_asistencia, df_personas, df_ap, df_seg = load_all_data()

    show_top_alerts(latest_asistencia(df_asistencia), df_personas, df_ap, centro)
    kpi_row_full(latest_asistencia(df_asistencia), centro)

    st.markdown("---")
    t1, t2, t3, t4 = st.tabs(["📝 Asistencia", "👥 Legajo", "📊 Reportes", "🌍 Global"])
    with t1: page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
    with t2: page_personas_full(df_personas, df_ap, df_seg, centro, u)
    with t3: page_reportes(df_asistencia, centro)
    with t4: page_global(df_asistencia, df_personas, df_ap)

if __name__ == "__main__":
    main()
