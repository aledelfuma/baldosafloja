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
# 🌑 CONFIGURACIÓN DE TEMA OSCURO PREMIUM Y MOBILE
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
  --radius-sm: 12px;
  --radius-lg: 18px;
}

/* =========================================
   COMPORTAMIENTO 100% NATIVO MOBILE
   ========================================= */
header[data-testid="stHeader"] {display: none !important;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.stApp {
    background-color: var(--background) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: var(--text-primary) !important;
}

.block-container {
    padding-top: 1rem !important; 
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    padding-bottom: 120px !important; 
    max-width: 650px !important; 
    margin: 0 auto;
    overflow-x: hidden;
}

.stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {
    color: var(--text-primary) !important;
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
div.user-info { font-size: 1.2rem; font-weight: 700; line-height: 1.2; }
div.center-info { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary) !important; margin-top: 2px; }

.stButton>button {
    background-color: var(--primary);
    color: #000000 !important;
    border-radius: var(--radius-sm);
    border: none;
    font-weight: 800;
    padding: 0.7rem 1rem;
    transition: 0.2s;
    width: 100%;
}
.stButton>button:active { transform: scale(0.98); } 

.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stMultiSelect>div>div>div {
    border-radius: var(--radius-sm) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background-color: #1A1A1A !important;
    color: var(--text-primary) !important;
    padding: 0.6rem;
}

.streamlit-expanderHeader {
    color: var(--text-primary) !important;
    background-color: var(--surface);
    border-radius: var(--radius-sm);
}

.kpi {
  border-radius: var(--radius-lg);
  padding: 15px;
  background: var(--surface);
  border: 1px solid rgba(255,255,255,0.05);
  text-align: center;
  height: 100%;
}
.kpi h3 { margin: 0; font-size: 0.65rem; color: var(--text-secondary) !important; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi .v { font-size: 2rem; font-weight: 800; color: var(--primary) !important; line-height: 1; margin-top: 5px; }

.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; }
.alert-danger { background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.3); }
.alert-success { background-color: rgba(34, 197, 94, 0.15); color: #86EFAC !important; border: 1px solid rgba(34, 197, 94, 0.3); }
.alert-gray { background-color: var(--surface); color: var(--text-secondary) !important; border: 1px solid rgba(255,255,255,0.05); }

.id-card {
    background: linear-gradient(135deg, #004E7B 0%, #63296C 100%);
    border-radius: 20px;
    padding: 25px;
    color: white !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
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
.tag-badge { background-color: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 15px; font-size: 0.75rem; font-weight: 600; }

.btn-wa {
    display: inline-flex; align-items: center; justify-content: center;
    background-color: #25D366; color: white !important; padding: 10px 15px;
    border-radius: var(--radius-sm); text-decoration: none; font-weight: bold; font-size: 0.9rem;
    margin-top: 10px; transition: 0.3s; width: 100%;
}

.stTabs [data-baseweb="tab-list"] {
    position: fixed; 
    bottom: 0; 
    left: 0; 
    right: 0;
    background-color: rgba(18, 18, 18, 0.85); 
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-top: 1px solid rgba(255,255,255,0.1);
    display: flex;
    justify-content: space-around;
    padding: 10px 5px env(safe-area-inset-bottom, 20px) 5px; 
    z-index: 9999;
}
.stTabs [data-baseweb="tab"] {
    flex-grow: 1; text-align: center; justify-content: center;
    font-size: 0.70rem !important; font-weight: 700;
    color: var(--text-secondary) !important; padding: 10px 0; 
    border: none !important; background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important; 
    background-color: rgba(96, 165, 250, 0.1) !important; 
    border-radius: 12px;
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
# Google Sheets
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

def safe_get_all_values(ws, tries=3):
    for i in range(tries):
        try: return ws.get_all_values()
        except: time.sleep(0.5)
    st.error("Error conexión Sheets."); st.stop()

def read_ws_df(title: str, cols: list) -> pd.DataFrame:
    ws = get_or_create_ws(get_spreadsheet(), title, cols)
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
    sh = get_spreadsheet()
    ws = get_or_create_ws(sh, title, cols)
    ws.append_rows(rows, value_input_option="USER_ENTERED")

# =========================
# Data & Logic
# =========================
@st.cache_data(ttl=600, show_spinner=False)
def get_users_db(): 
    return read_ws_df(USUARIOS_TAB, USUARIOS_COLS)

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

def get_today_asistencia_summary(df_a):
    if df_a.empty: return df_a.copy()
    hoy = get_today_ar().isoformat()
    d = df_a[df_a["fecha"] == hoy].copy()
    if d.empty: return d.copy()
    d["timestamp_dt"] = pd.to_datetime(d["timestamp"], errors="coerce")
    return d.sort_values("timestamp_dt").groupby(["centro", "espacio"]).tail(1)

def personas_for_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    if "centro" in df_personas.columns:
        centro_clean = clean_string(centro)
        df_temp = df_personas.copy()
        df_temp['centro_norm'] = df_temp['centro'].apply(clean_string)
        return df_temp[df_temp['centro_norm'] == centro_clean].copy()
    return df_personas.copy()

def filter_personas_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    df_c = personas_for_centro(df_personas, centro)
    if not df_c.empty and "timestamp" in df_c.columns:
        df_c["timestamp_dt"] = pd.to_datetime(df_c["timestamp"], errors="coerce")
        return df_c.sort_values("timestamp_dt").groupby("nombre").tail(1)
    return df_c

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
        
        st.markdown("""
        <div style='text-align: center; margin-top: 30px; font-size: 0.85rem; color: #888;'>
            ¿Problemas con la App o tu clave? <br>
            <a href='mailto:alejandrodelfuma@gmail.com' style='color: #60A5FA; text-decoration: none; font-weight: bold;'>
                ✉️ Contactame: alejandrodelfuma@gmail.com
            </a>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

def show_top_header(nombre, centro):
    st.markdown(f"""
<div class='top-bar'>
    <div style='display:flex; align-items:center; gap:15px;'>
        <div style='background-color: var(--primary); width: 45px; height: 45px; border-radius: 50%; display:flex; align-items:center; justify-content:center; color:black; font-weight:bold; font-size:1.2rem;'>
            {nombre[0].upper() if nombre else 'U'}
        </div>
        <div>
            <div class='user-info'>Hola, {nombre}</div>
            <div class='center-info'>📍 {centro}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

def show_top_alerts(df_latest, df_personas, df_ap, centro):
    last_date, days = last_load_info(df_latest, centro)
    
    cumples = []
    if not df_personas.empty:
        df_c = filter_personas_centro(df_personas, centro)
        df_c_act = df_c[df_c["activo"].str.upper() == "SI"]
        today = get_today_ar()
        for _, row in df_c_act.iterrows():
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

    st.markdown("<h4 style='font-size:1rem; margin-bottom:10px;'>📊 Novedades del Centro</h4>", unsafe_allow_html=True)
    
    today_a = get_today_asistencia_summary(df_latest)
    if today_a.empty or "centro" not in today_a.columns: c_a = pd.DataFrame()
    else: c_a = today_a[today_a["centro"] == centro]

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if c_a.empty: st.markdown("<div class='alert-box alert-danger'>⚠️ Faltan Asistencias</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alert-box alert-success'>✅ Asistencias al día</div>", unsafe_allow_html=True)
    with ac2:
        if cumples:
            with st.expander(f"🎉 Cumpleaños ({len(cumples)})", expanded=True):
                for c in cumples: st.write(f"- {c}")
        else:
             st.markdown("<div class='alert-box alert-gray'>🎂 Sin cumples</div>", unsafe_allow_html=True)
    with ac3:
        if ausentes:
            with st.expander(f"⚠️ Inasistencias ({len(ausentes)})", expanded=False):
                for a in ausentes: st.write(f"🔴 {a}")
        else:
            st.markdown("<div class='alert-box alert-gray'>✔️ Sin Inasistencias</div>", unsafe_allow_html=True)

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
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi'><h3>Mes actual</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)

# =========================
# PAGES
# =========================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>📝 Carga Diaria</h3>", unsafe_allow_html=True)
    fecha = st.date_input("Fecha de carga", value=get_today_ar())
    if fecha > get_today_ar():
        st.error("⛔ No se puede cargar asistencia de días futuros.")
        return
    fecha_str = fecha.isoformat()
    
    col_e, col_m = st.columns(2)
    with col_e: espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA) if centro == C_MARANATHA else DEFAULT_ESPACIO
    with col_m: modo = st.selectbox("Modo / Actividad", ["Día habitual", "Actividad especial", "Cerrado"])
    
    notas = st.text_area("Notas generales del día (Opcional)", height=70)

    df_centro = filter_personas_centro(df_personas, centro)
    df_activos = df_centro[df_centro["activo"].str.upper() == "SI"]
    nombres = sorted(list(set([n for n in df_activos["nombre"].astype(str).tolist() if n.strip()])))
    
    st.markdown("#### 👥 Marcar Asistencia")
    presentes = st.multiselect("Buscador de personas (Escribí para filtrar)", options=nombres, placeholder="Seleccionar asistentes...")
    total_presentes = st.number_input("Total numérico (En caso de visitas rápidas)", min_value=0, value=len(presentes))
    if not presentes: total_presentes = total_presentes
    else: total_presentes = len(presentes)
    
    with st.expander("➕ ¿Vino alguien nuevo?"):
        nueva = st.text_input("Nombre completo")
        dni_new = st.text_input("DNI")
        tel_new = st.text_input("Teléfono")
        nac_new = st.text_input("Fecha Nac. (DD/MM/AAAA)")
        agregar_nueva = st.checkbox("Agregar al Padrón Oficial")
        
        if agregar_nueva and dni_new.strip() and not df_personas.empty:
            existe_dni = df_personas[df_personas['dni'].astype(str).str.strip() == dni_new.strip()]
            if not existe_dni.empty:
                st.markdown(f"<div class='alert-box alert-danger'>⚠️ DNI duplicado: {existe_dni.iloc[0]['nombre']}</div>", unsafe_allow_html=True)

    df_latest = latest_asistencia(df_asistencia)
    ya = pd.DataFrame()
    if not df_latest.empty and "centro" in df_latest.columns:
        ya = df_latest[(df_latest["fecha"]==fecha_str) & (df_latest["centro"]==centro) & (df_latest["espacio"]==espacio)]
        
    overwrite = True
    if not ya.empty:
        st.warning("⚠️ Ya existe una carga de asistencia para hoy en este espacio. Si guardás, se sobreescribirá.")
        overwrite = st.checkbox("Confirmar que quiero sobreescribir", value=False)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 GUARDAR ASISTENCIA", type="primary", use_container_width=True):
        if not overwrite: st.error("Debes tildar la confirmación para sobreescribir."); st.stop()
        if total_presentes <= 0 and modo != "Cerrado":
            st.error("⛔ Debes marcar asistentes o indicar 'Cerrado'."); st.stop()
            
        if agregar_nueva and nueva.strip():
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, frecuencia="Nueva", dni=dni_new, telefono=tel_new, fecha_nacimiento=nac_new)
            if nueva not in presentes: presentes.append(nueva)
        
        if len(presentes)>0: total_presentes = len(presentes)
        accion = "overwrite" if not ya.empty else "append"
        
        with st.spinner("Sincronizando con la nube..."):
            append_asistencia(fecha_str, centro, espacio, total_presentes, nombre_visible, modo, notas, usuario, accion)
            for n in presentes:
                append_asistencia_personas(fecha_str, centro, espacio, n, "Presente", "SI" if (agregar_nueva and n==nueva) else "NO", nombre_visible, usuario)
            ausentes = [n for n in nombres if n not in presentes]
            for n in ausentes:
                append_asistencia_personas(fecha_str, centro, espacio, n, "Ausente", "NO", nombre_visible, usuario)

        st.balloons()
        st.toast("✅ Guardado Exitoso"); time.sleep(1.5); st.cache_data.clear(); st.rerun()

def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>👥 Buscador y Legajos</h3>", unsafe_allow_html=True)
    df_centro = filter_personas_centro(df_personas, centro)
    nombres = sorted(df_centro["nombre"].unique()) if not df_centro.empty else []

    seleccion = st.selectbox("Escribí el nombre para ver su ficha:", [""] + nombres, help="Buscador inteligente")
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-gray' style='margin-top:20px;'>🔍 Buscá a alguien arriba para ver su carnet y bitácora, o mirá la tabla completa abajo.</div>", unsafe_allow_html=True)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"#### 📋 Padrón Completo ({len(nombres)})")
        with st.expander("Ver / Descargar Tabla Excel", expanded=False):
            if not df_centro.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_centro.to_excel(writer, sheet_name='Personas', index=False)
                st.download_button("📥 Descargar Excel", buffer, f"padron_{centro}.xlsx", "application/vnd.ms-excel", use_container_width=True)
                
                solo_activos = st.checkbox("Mostrar Solo activos", value=True)
                df_show = df_centro.copy()
                if solo_activos: df_show = df_show[df_show["activo"].astype(str).str.upper() == "SI"]
                
                cols_to_show = ["nombre", "dni", "fecha_nacimiento", "telefono", "activo"]
                for c in cols_to_show:
                    if c not in df_show.columns: df_show[c] = ""
                st.dataframe(df_show[cols_to_show].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    tags_str = str(datos_persona.get("etiquetas", ""))
    tags_html = ""
    if tags_str and tags_str.lower() != "nan":
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

    telefono = str(datos_persona.get("telefono", ""))
    wa_btn_html = ""
    if telefono and telefono.lower() != "nan" and format_wa_number(telefono):
        wa_btn_html = f"<div style='margin-top:5px;'><a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>💬 Enviar WhatsApp</a></div>"
        
    estado_badge = "🟢 ACTIVO" if str(datos_persona.get("activo")).upper() != "NO" else "🔴 INACTIVO"
    
    import urllib.parse
    avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(seleccion)}&backgroundColor=004e7b&textColor=ffffff"

    dni_val = str(datos_persona.get('dni', '')).strip()
    if dni_val.lower() == 'nan' or not dni_val:
        dni_val = "S/D"
        
    nac_val = str(datos_persona.get('fecha_nacimiento', '')).strip()
    if nac_val.lower() == 'nan' or not nac_val:
        nacimiento_mostrar = "S/D"
    else:
        nacimiento_mostrar = f"{nac_val} ({calculate_age(nac_val)} años)"

    # 🚨 FIX HTML (Alineado a la izquierda sin espacios) 🚨
    html_carnet = f"""
<div class="id-card">
<div style="display:flex; justify-content: space-between; align-items:flex-start; margin-bottom: 5px;">
<div class="id-title">HOGAR DE CRISTO</div>
<span style="font-weight:800; background: rgba(255,255,255,0.25); padding: 5px 12px; border-radius: 12px; font-size: 0.70rem; letter-spacing:1px;">
{estado_badge}
</span>
</div>
<div style="display:flex; gap: 15px; align-items: center; margin-bottom: 20px;">
<img src="{avatar_url}" style="width: 60px; height: 60px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.8); box-shadow: 0 4px 10px rgba(0,0,0,0.1);"/>
<div class="id-name" style="margin-bottom:0;">{seleccion}</div>
</div>
<div class="id-data-row">
<div class="id-data-col">
<span class="id-label">Documento</span>
<span class="id-value">{dni_val}</span>
</div>
<div class="id-data-col">
<span class="id-label">Nacimiento</span>
<span class="id-value">{nacimiento_mostrar}</span>
</div>
</div>
<div class="tag-container">
{tags_html}
</div>
</div>
"""
    st.markdown(html_carnet, unsafe_allow_html=True)
    
    domicilio_val = str(datos_persona.get('domicilio', '')).strip()
    if domicilio_val.lower() == 'nan' or not domicilio_val: domicilio_val = 'No registrado'
    tel_val = str(datos_persona.get('telefono', '')).strip()
    if tel_val.lower() == 'nan' or not tel_val: tel_val = 'No registrado'
        
    html_contacto = f"""
<div style="background:var(--surface); padding:15px; border-radius:var(--radius-sm); border:1px solid rgba(255,255,255,0.05); margin-bottom:15px;">
<div style="margin-bottom:10px;">
<div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">📱 Teléfono</div>
<div style="font-size:1.1rem;">{tel_val}</div>
{wa_btn_html}
</div>
<div>
<div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">🏠 Dirección</div>
<div style="font-size:1.1rem;">{domicilio_val}</div>
</div>
</div>
"""
    st.markdown(html_contacto, unsafe_allow_html=True)
        
    emergencia = str(datos_persona.get('contacto_emergencia', '')).strip()
    if emergencia and emergencia.lower() != 'nan':
        html_emergencia = f"""
<div style="background:rgba(239, 68, 68, 0.1); padding:15px; border-radius:var(--radius-sm); border-left:4px solid #EF4444; margin-bottom:15px;">
<div style="font-size:0.75rem; color:#EF4444; text-transform:uppercase; font-weight:800;">🚨 Emergencia</div>
<div style="font-weight:700; font-size:1.1rem; color:#FCA5A5;">{emergencia}</div>
</div>
"""
        st.markdown(html_emergencia, unsafe_allow_html=True)
            
    notas_str = str(datos_persona.get('notas', '')).strip()
    if notas_str and notas_str.lower() != 'nan':
        st.info(f"**📌 Notas (Salud/Contexto):**\n\n{notas_str}")

    with st.expander("✏️ Editar Ficha (DNI, Tel, etc)"):
        with st.form("edit_persona"):
            dni = st.text_input("DNI", value=datos_persona.get("dni", ""))
            tel = st.text_input("Teléfono", value=datos_persona.get("telefono", ""))
            contacto_em = st.text_input("Contacto de Emergencia", value=datos_persona.get("contacto_emergencia", ""))
            nac = st.text_input("Fecha Nacimiento (DD/MM/AAAA)", value=datos_persona.get("fecha_nacimiento", ""))
            dom = st.text_input("Dirección", value=datos_persona.get("domicilio", ""))
            etiquetas = st.text_input("Etiquetas (Separadas por coma)", value=datos_persona.get("etiquetas", ""), help="Ej: Diabético, Medicación")
            notas_fija = st.text_area("Notas Permanentes", value=datos_persona.get("notas", ""))
            activo_chk = st.checkbox("Persona Activa (Desmarcar para ocultar del padrón)", value=(str(datos_persona.get("activo")).upper() != "NO"))
            
            if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                nuevo_estado = "SI" if activo_chk else "NO"
                upsert_persona(df_personas, seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija, activo=nuevo_estado, contacto_emergencia=contacto_em, etiquetas=etiquetas)
                st.success("¡Ficha actualizada!")
                time.sleep(1)
                st.cache_data.clear(); st.rerun()
        
    st.markdown("---")
    st.markdown("### 📖 Bitácora Reciente")
    
    with st.expander("➕ Cargar un Nuevo Registro", expanded=False):
        with st.form("new_seg"):
            fecha_seg = st.date_input("Fecha", value=get_today_ar())
            cat = st.selectbox("Área", CATEGORIAS_SEGUIMIENTO)
            obs = st.text_area("Describí la intervención o charla...")
            
            if st.form_submit_button("📝 Guardar Registro", use_container_width=True):
                if len(obs) > 5:
                    append_seguimiento(str(fecha_seg), centro, seleccion, cat, obs, usuario)
                    st.success("Guardado en la bitácora.")
                    time.sleep(1)
                    st.cache_data.clear(); st.rerun()
                else:
                    st.error("Escribí un poco más de detalle.")
    
    if not df_seg.empty:
        mis_notas = df_seg[(df_seg["nombre"]==seleccion) & (df_seg["centro"]==centro)].copy()
        if not mis_notas.empty:
            mis_notas["fecha_dt"] = pd.to_datetime(mis_notas["fecha"], errors="coerce")
            mis_notas = mis_notas.sort_values("fecha_dt", ascending=False)
            
            st.markdown("<br>", unsafe_allow_html=True)
            for _, note in mis_notas.iterrows():
                cat = str(note['categoria']).lower()
                icon = "🩺" if "salud" in cat else "📝" if "trámite" in cat else "🫂" if 'escucha' in cat else "🚨" if 'crisis' in cat else "📌"
                color_left = "#EF4444" if "crisis" in cat else SECONDARY
                
                html_nota = f"""
<div style="background-color: var(--surface); padding:15px; border-radius:var(--radius-sm); margin-bottom:12px; border-left: 4px solid {color_left}; border: 1px solid rgba(255,255,255,0.02);">
<div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom:8px; margin-bottom:8px;">
<strong style="color:var(--primary); font-size:1.0rem;">{icon} {note['categoria']}</strong>
<div style="text-align:right;">
<div style="color:var(--text-secondary); font-size:0.75rem; font-weight:700;">{note['fecha']}</div>
<div style="color:var(--text-secondary); font-size:0.65rem;">Por {str(note.get('usuario', ''))}</div>
</div>
</div>
<div style="font-size:0.95rem; line-height:1.4;">{note['observacion']}</div>
</div>
"""
                st.markdown(html_nota, unsafe_allow_html=True)
        else: st.info("Esta persona todavía no tiene registros en la bitácora.")

def page_reportes(df_asistencia, centro):
    st.markdown("<h3 style='margin-bottom:15px;'>📊 Reportes</h3>", unsafe_allow_html=True)
    
    df_latest = latest_asistencia(df_asistencia)
    
    if df_latest.empty or "centro" not in df_latest.columns:
        st.info("No hay datos en la plataforma aún.")
        return
        
    df_c = df_latest[df_latest["centro"] == centro].copy()
    
    with st.expander("📥 Exportar Datos (Backup)", expanded=False):
        st.caption("Bajá un Excel con absolutamente todo el registro histórico de asistencias de este centro.")
        buffer_backup = io.BytesIO()
        with pd.ExcelWriter(buffer_backup, engine='xlsxwriter') as writer:
            df_latest.to_excel(writer, sheet_name='Global_Asistencias', index=False)
        st.download_button("Descargar Respaldo Completo", buffer_backup, f"BACKUP_HC_{date.today()}.xlsx", "application/vnd.ms-excel", use_container_width=True)

    if df_c.empty: 
        st.info("Sin datos para este centro.")
        return
    
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"])
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c = df_c.sort_values("fecha_dt")
    
    st.markdown("#### Evolución de Asistencias")
    st.line_chart(df_c.set_index("fecha")["presentes_i"], color="#60A5FA")
    
    st.markdown(f"**Promedio general:** {df_c['presentes_i'].mean():.1f} chicos/as por día.")
    
    st.markdown("#### Detalle Diario")
    st.dataframe(df_c[["fecha", "espacio", "presentes", "coordinador"]].sort_values("fecha", ascending=False), use_container_width=True)

    # 📩 MENSAJE DE SOPORTE EN REPORTES
    st.markdown("""
    <br><hr style='opacity:0.2;'>
    <div style='text-align: center; color: var(--text-secondary); font-size: 0.8rem; margin-top: 20px;'>
        🔧 ¿Encontraste un error o necesitas ayuda?<br>
        Contactá al desarrollador en: <a href='mailto:alejandrodelfuma@gmail.com' style='color: var(--primary);'>alejandrodelfuma@gmail.com</a>
    </div>
    """, unsafe_allow_html=True)

def page_global(df_asistencia, df_personas, df_ap):
    st.markdown("<h3 style='margin-bottom:15px;'>🌍 Consola Central</h3>", unsafe_allow_html=True)
    
    df_a = latest_asistencia(df_asistencia).copy()
    if not df_a.empty and "presentes" in df_a.columns:
        df_a["presentes_i"] = df_a["presentes"].apply(lambda x: clean_int(x, 0))
    else:
        df_a = pd.DataFrame(columns=["anio", "centro", "presentes_i", "fecha"])
        
    anio = str(get_today_ar().year)
    
    df_personas_unq = pd.DataFrame()
    if not df_personas.empty and "nombre" in df_personas.columns:
        df_personas_unq = df_personas.sort_values("timestamp").groupby("nombre").tail(1)
        df_personas_unq["edad_calc"] = df_personas_unq["fecha_nacimiento"].apply(calculate_age)
        
    total_personas = len(df_personas_unq) if not df_personas_unq.empty else 0
    total_asist_anio = 0
    promedio_global = 0.0
    
    if not df_a.empty and "anio" in df_a.columns:
        df_a_anio = df_a[df_a["anio"].astype(str) == anio]
        total_asist_anio = df_a_anio["presentes_i"].sum()
        dias_unicos = df_a_anio["fecha"].nunique()
        if dias_unicos > 0:
            promedio_global = total_asist_anio / dias_unicos
            
    nuevos_anio = 0
    if not df_ap.empty and "es_nuevo" in df_ap.columns:
        nuevos_anio = len(df_ap[(df_ap["es_nuevo"]=="SI") & (df_ap["anio"].astype(str)==anio)])
        
    st.caption("Suma de todos los centros a nivel institución.")
    k1, k2 = st.columns(2)
    k1.markdown(f"<div class='kpi'><h3>Padrón Total</h3><div class='v'>{total_personas}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3>Promedio Día</h3><div class='v'>{promedio_global:.1f}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    k3, k4 = st.columns(2)
    k3.markdown(f"<div class='kpi'><h3>Asistencias {anio}</h3><div class='v'>{total_asist_anio}</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi'><h3>Nuevos {anio}</h3><div class='v'>{nuevos_anio}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
    
    st.markdown(f"#### 🏢 Ingresos por Centro ({anio})")
    if not df_a.empty and "anio" in df_a.columns:
        st.bar_chart(df_a[df_a["anio"].astype(str)==anio].groupby("centro")["presentes_i"].sum(), color="#60A5FA")
    
    st.markdown("#### 👥 Edades (Toda la institución)")
    if not df_personas_unq.empty and "edad_calc" in df_personas_unq.columns:
        df_edades = df_personas_unq[df_personas_unq["edad_calc"] > 0].copy()
        if not df_edades.empty:
            bins = [0, 12, 18, 30, 50, 100]
            labels = ['Niños (0-12)', 'Adolescentes (13-18)', 'Jóvenes (19-30)', 'Adultos (31-50)', 'Mayores (50+)']
            df_edades['rango_edad'] = pd.cut(df_edades['edad_calc'], bins=bins, labels=labels, right=False)
            st.bar_chart(df_edades['rango_edad'].value_counts().sort_index(), color="#A78BFA")
        else:
            st.info("Falta cargar fechas de nacimiento.")

# =========================
# MAIN APP (CONTROLADOR)
# =========================
def main():
    if not st.session_state.get("logged_in"): 
        show_login_screen()
    
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]
    
    centro_clean = clean_string(centro)
    match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
    if not match_centro:
        st.error(f"Error: El centro '{centro}' no está registrado.")
        st.stop()
    centro = match_centro

    # 🚨 REGLA ESTRICTA NATASHA PARA CALLE BELÉN
    mostrar_app = True
    if centro == C_BELEN and u.upper() != "NATASHA":
        st.error("🔒 ACCESO DENEGADO: El centro Calle Belén es de acceso exclusivo para la administración.")
        st.markdown("---")
        if st.button("⬅️ Salir de la cuenta", type="primary"):
            st.session_state.clear(); st.rerun()
        mostrar_app = False
        
    if not mostrar_app: return

    show_top_header(nombre, centro)
    
    df_asistencia, df_personas, df_ap, df_seg = load_all_data()

    # 📱 PANTALLA PRINCIPAL DE INICIO
    list_tabs = ["🏠 Inicio", "👥 Legajos", "📊 Reportes"]
    if u.upper() == "NATASHA": list_tabs.append("🌍 Global")
    
    tabs = st.tabs(list_tabs)
    
    with tabs[0]: 
        show_top_alerts(latest_asistencia(df_asistencia), df_personas, df_ap, centro)
        kpi_row_full(latest_asistencia(df_asistencia), centro)
        st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
        page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
        
    with tabs[1]: 
        page_personas_full(df_personas, df_ap, df_seg, centro, u)
        
    with tabs[2]: 
        page_reportes(df_asistencia, centro)
        
    if len(tabs) > 3:
        with tabs[3]: page_global(df_asistencia, df_personas, df_ap)

if __name__ == "__main__":
    main()
