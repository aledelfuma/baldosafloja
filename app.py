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
    # ERROR CORREGIDO: Se guardaba en COLS en lugar de TAB
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
             st.markdown("<div class='alert-box alert-gray'>🎂 Sin cumpleaños hoy</div>", unsafe_allow_html=True)
    with ac3:
        if ausentes:
            with st.expander(f"⚠️ Alerta de Inasistencia ({len(ausentes)})", expanded=False):
                for a in ausentes: st.write(f"🔴 {a}")
        else:
            st.markdown("<div class='alert-box alert-gray'>✔️ Sin alertas de inasistencia</div>", unsafe_allow_html=True)

def kpi_row_full(df_latest, centro):
    hoy_date = get_today_ar()
    hoy = hoy_date.isoformat()
    week_ago = (hoy_date - timedelta(days=6)).isoformat()
    month_start = hoy_date.replace(day=1).isoformat()
    d = df_latest.copy()
    if d.
