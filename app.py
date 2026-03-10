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
# Paleta: Fondo Negro (#121212), Superficie (#1E1E1E), 
# Primario (Celeste #60A5FA), Secundario (Violeta #A78BFA)
st.set_page_config(
    page_title="Hogar de Cristo - Gestión",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
/* ======================================================
   🌑 HOGAR DE CRISTO - DARK MODE INTERFACE
   ====================================================== */
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

/* Elementos Nativos Ocultos (Branding) */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;} 

/* Layout Mobile Centrado */
.css-18e3th9, .st-emotion-cache-1jicfl2 {
    padding-top: 1rem !important; 
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 90px !important; /* Espacio para tabs inferiores */
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

/* KPIs Modernos (Métricas Resumen) */
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

/* Alertas iOS Style (Ajustadas a Oscuro) */
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

/* ===============================================
   💳 CARNET DIGITAL (Legajo Profile Card)
   =============================================== */
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

/* Etiquetas Visuales (Tags) */
.tag-container { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.tag-badge {
    background-color: rgba(255,255,255,0.15);
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
}

/* Botón WhatsApp */
.btn-wa {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background-color: #25D366;
    color: white !important;
    padding: 8px 15px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
    font-size: 0.9rem;
    margin-top: 10px;
    transition: 0.3s;
}

/* ===============================================
   📱 PESTAÑAS (TABS) COMO BOTTOM NAVIGATION BAR
   =============================================== */
.stTabs [data-baseweb="tab-list"] {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #0A0A0A; /* Negro puro para la barra */
    border-top: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: space-around;
    padding: 8px 10px 18px 10px;
    z-index: 9999;
}
.stTabs [data-baseweb="tab"] {
    flex-grow: 1;
    text-align: center;
    justify-content: center;
    font-size: 0.75rem !important;
    font-weight: 600;
    color: var(--text-secondary) !important;
    padding: 8px 0;
    border: none !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important;
    background-color: rgba(96, 165, 250, 0.05) !important;
    border-radius: 8px;
}
/* Ocultar la línea por defecto de streamlit tabs */
.stTabs [aria-selected="true"]::after {
    display: none;
}
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
# Schemas y Nombres (Ajustado)
# =========================
ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
ASISTENCIA_PERSONAS_TAB = "asistencia_personas"
USUARIOS_TAB = "config_usuarios"
SEGUIMIENTO_TAB = "seguimiento"

# Nombres exactos de los centros (para comparaciones)
C_BELEN = "Calle Belén"
C_NUDO = "Nudo a Nudo"
C_MARANATHA = "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]

ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# ======================================================
# 🔒 GOOGLE SHEETS CONNECTION (SECURITY FIXED)
# ======================================================
# ✅ CORRECCIÓN DE SEGURIDAD: Ahora usa Streamlit Secrets
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    sa = st.secrets["gspread_sa"] # Levanta credenciales del dashboard
    sa_dict = sa.to_dict()
    # Corrige problemas de formato con la private key
    if "\\n" in sa_dict["private_key"]:
        sa_dict["private_key"] = sa_dict["private_key"].replace("\\n", "\n")
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(sa_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    sid = "1nCK2Q2ddxUO-erDwa5jgfGsUYsjZD7e4doHXoQ4N9zg" # Tu ID de Sheet
    gc = get_gspread_client()
    return gc.open_by_key(sid)

def get_or_create_ws(sh, title, cols):
    try: return sh.worksheet(title)
    except Exception: pass
    try:
        ws = sh.add_worksheet(title=title, rows=2000, cols=len(cols)+5)
        ws.update("A1", [cols])
        return ws
    except: return sh.worksheet(title) # Por si se creó en el interín

# ✅ OPTIMIZACIÓN: Caching para no saturar las lecturas (ttl = 5 minutos)
@st.cache_data(ttl=300, show_spinner="Sincronizando...")
def load_all_managed_data():
    sh = get_spreadsheet()
    # Estructura del cargador (hoja, columnas por defecto)
    to_load = {
        ASISTENCIA_TAB: ["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"],
        PERSONAS_TAB: ["nombre", "frecuencia", "centro", "edad", "domicilio", "notas", "activo", "timestamp", "usuario", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"],
        ASISTENCIA_PERSONAS_TAB: ["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario", "notas"],
        USUARIOS_TAB: ["usuario", "password", "centro", "nombre"],
        SEGUIMIENTO_TAB: ["timestamp", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"]
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
    # USER_ENTERED permite formatos de Excel como fechas y números
    ws.append_rows(rows_list, value_input_option="USER_ENTERED")

# =========================
# Lógica de Negocio
# =========================
def clean_string(s):
    if not isinstance(s, str): return ""
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.strip().upper()

def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default

# Optimizado para Dark Mode y reglas de Natasha
def get_user_config(df_usuarios):
    return df_usuarios

def get_today_asistencia_summary(df_a):
    if df_a.empty: return pd.DataFrame()
    hoy = get_today_ar().isoformat()
    # Se queda con la carga más reciente por centro y espacio del día de hoy
    d = df_a[df_a["fecha"] == hoy].copy()
    if d.empty: return pd.DataFrame()
    d["timestamp_dt"] = pd.to_datetime(d["timestamp"], errors="coerce")
    return d.sort_values("timestamp_dt").groupby(["centro", "espacio"]).tail(1)

def filter_personas_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    df_c = personas_for_centro(df_personas, centro)
    # Se queda con el estado más reciente de cada persona
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
    # Busca la última fecha en que cada persona estuvo "Presente" en ese centro
    d = df_ap[(df_ap["centro"] == centro) & (df_ap["estado"] == "Presente")].copy()
    if d.empty: return []
    d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    last_p = d.groupby("nombre")["fecha_dt"].max().reset_index()
    
    hoy_ts = pd.Timestamp(get_today_ar())
    last_p["dias"] = (hoy_ts - last_p["fecha_dt"]).dt.days
    # Alerta si faltan entre 7 y 90 días
    alertas = last_p[(last_p["dias"] > 7) & (last_p["dias"] < 90)].sort_values("dias", ascending=False)
    
    res = []
    for _, r in alertas.iterrows():
        res.append(f"{r['nombre']} ({r['dias']} días)")
    return res

# Helper para normalizar centros de datos a centros fijos
def personas_for_centro(df_p, centro):
    if df_p.empty: return df_p
    c_list = list(df_p["centro"].astype(str).tolist())
    clean_c_list = [clean_string(c) for c in c_list]
    target_clean = clean_string(centro)
    matches = [centro == target_clean for centro in clean_c_list]
    return df_p[matches].copy()

# Upsert (update or insert) de personas
def upsert_persona_direct(nombre, centro, usuario, **kwargs):
    now = get_now_ar_str()
    cols = ["nombre", "frecuencia", "centro", "edad", "domicilio", "notas", "activo", "timestamp", "usuario", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"]
    row_data = {c: "" for c in cols}
    row_data.update({"nombre": nombre.strip(), "centro": centro, "activo": "SI", "timestamp": now, "usuario": usuario})
    for k, v in kwargs.items():
        if k in cols: row_data[k] = str(v).strip()
    append_rows_sa(PERSONAS_TAB, cols, [[row_data[c] for c in cols]])

# =========================
# UI COMPONENTES (Modo Oscuro)
# =========================
def show_login_screen(dfs):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_hogar.png", width=200) # Imagen que me enviaste
        except: st.title("🏠 Hogar de Cristo")
        st.markdown("### Acceso Coordinadores")
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                db_users = dfs[USUARIOS_TAB]
                # Comparación limpia
                row = db_users[(db_users["usuario"].astype(str).str.strip() == u.strip()) & (db_users["password"].astype(str).str.strip() == p.strip())]
                if not row.empty:
                    r = row.iloc[0]
                    st.session_state.update({
                        "logged_in": True,
                        "usuario": r["usuario"].strip(),
                        # Se quita el espacio de ' Calle Belén'
                        "centro_asignado": r["centro"].strip(), 
                        "nombre_visible": r["nombre"].strip()
                    })
                    st.success(f"¡Hola {r['nombre']}!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
    st.stop()

def show_top_header(dfs, nombre, centro_asignado):
    st.markdown(f"""
<div class='top-bar'>
    <div class='user-info'>{nombre}</div>
    <div class='center-info'>📍 {centro_asignado}</div>
</div>
""", unsafe_allow_html=True)

def show_kpi_alerts_bar(dfs, centro):
    df_p = filter_personas_centro(dfs[PERSONAS_TAB], centro)
    # Solo activos para alertas
    df_p_act = df_p[df_p["activo"].str.upper() == "SI"]
    cumples = calculate_birthday_alerts(df_p_act)
    ausentes = calculate_ausentes_alerts(dfs[ASISTENCIA_PERSONAS_TAB], centro)

    col1, col2, col3 = st.columns(3)
    
    # 🌑 Estilo para Modo Oscuro
    with col1:
        st.markdown("<div class='kpi'><h3>Estado Carga</h3>", unsafe_allow_html=True)
        today_a = get_today_asistencia_summary(dfs[ASISTENCIA_TAB])
        c_a = today_a[today_a["centro"] == centro]
        if c_a.empty:
            st.markdown("<div class='alert-box alert-danger'>Falta Cargar</div>", unsafe_allow_html=True)
        else:
            presentes_tot = c_a["presentes"].apply(clean_int).sum()
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

def show_quick_access_mobile():
    st.markdown("#### Accesos Rápidos")
    st.caption("Ve a las pestañas de abajo para las acciones diarias.")
    col1, col2 = st.columns(2)
    # Iconos grandes estilo mobile
    col1.markdown("<div class='stButton'><button>📝 Cargar Asistencia</button></div>", unsafe_allow_html=True)
    col2.markdown("<div class='stButton'><button>👤 Nuevo Ingreso</button></div>", unsafe_allow_html=True)

# =========================
# PÁGINAS PRINCIPALES
# =========================
def page_asistencia(dfs, centro, nombre_visible, usuario):
    st.subheader(f"Carga Diaria: {centro}")
    fecha = st.date_input("Fecha", value=get_today_ar())
    espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA) if centro == C_MARANATHA else DEFAULT_ESPACIO
    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    notas = st.text_area("Notas generales del día")
    st.markdown("---")

    # Personas activas de este centro
    df_p_filtered = filter_personas_centro(dfs[PERSONAS_TAB], centro)
    df_activos = df_p_filtered[df_p_filtered["activo"].str.upper() == "SI"]
    nombres = sorted(df_activos["nombre"].tolist())
    
    col1, col2 = st.columns([3, 1])
    presentes = col1.multiselect("Marcar Asistentes", options=nombres)
    
    # Campo para contar los presentes (automático + manual)
    total_input = col2.number_input("Total Presentes", min_value=0, value=len(presentes))
    # Si multiselect está vacío, prioriza el total input
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
            # 1. Registrar Persona Nueva si corresponde
            if agregar_nueva and nueva:
                # Evitar duplicados rápidos
                dfs[PERSONAS_TAB] = dfs[PERSONAS_TAB].drop_duplicates()
                existing = dfs[PERSONAS_TAB][dfs[PERSONAS_TAB]["nombre"].str.upper() == nueva]
                if not existing.empty:
                    st.warning(f"La persona '{nueva}' ya existe. No se duplicó, pero se marcará como presente.")
                else:
                    upsert_persona_direct(nueva, centro, usuario, frecuencia="Nueva", dni=dni_new, telefono=tel_new)
                    st.success(f"✅ Se agregó {nueva} como Nuevo Ingreso.")
                # Asegura que la nueva persona esté en la lista de presentes a guardar
                if nueva not in presentes: presentes.append(nueva)

            # 2. Guardar Asistencia General
            accion = " append" # Por defecto
            append_rows_sa(ASISTENCIA_TAB, ["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"], [[get_now_ar_str(), str(fecha), year_of(str(fecha)), centro, espacio, str(total_presentes), nombre_visible, modo, notas, usuario, accion]])

            # 3. Guardar Asistencia Individual (asistencia_personas)
            list_presentes = []
            final_presentes = presents if present else [nueva] if agregar_nueva and nueva else []
            # Elimina duplicados si los hubiera
            final_presentes = list(set([n for n in final_presentes if n]))

            for n in final_presentes:
                list_presentes.append([get_now_ar_str(), str(fecha), year_of(str(fecha)), centro, espacio, n, "Presente", "SI" if n == nueva and agregar_nueva else "NO", nombre_visible, usuario, ""])
            
            # Registrar ausentes (los que estaban activos y no se marcaron)
            ausentes = [n for n in nombres if n not in final_presentes]
            for n in ausentes:
                 list_presentes.append([get_now_ar_str(), str(fecha), year_of(str(fecha)), centro, espacio, n, "Ausente", "NO", nombre_visible, usuario, ""])

            if list_presentes:
                 append_rows_sa(ASISTENCIA_PERSONAS_TAB, ["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario", "notas"], list_presentes)

        st.balloons()
        st.toast("✅ Asistencia guardada correctamente"); time.sleep(1.5); st.cache_data.clear(); st.rerun()

def page_legajo(dfs, centro, usuario):
    st.subheader("👥 Legajo Digital")
    df_p = filter_personas_centro(dfs[PERSONAS_TAB], centro)
    if df_p.empty: st.info("Sin registros cargados."); return
    nombres = sorted(df_p["nombre"].unique())
    seleccion = st.selectbox("🔍 Buscar Persona:", [""] + nombres, help="Escriba para buscar por nombre")
    
    if seleccion:
        datos = df_p[df_p["nombre"] == seleccion].iloc[0]
        
        # Procesar Etiquetas Html
        tags_str = str(datos.get("etiquetas", ""))
        tags_html = ""
        if tags_str and tags_str.lower() != "nan":
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

        # Link WhatsApp
        telefono = str(datos.get("telefono", ""))
        wa_btn_html = ""
        if telefono and telefono.lower() != "nan" and format_wa_number(telefono):
            wa_btn_html = f"<a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>💬 WhatsApp</a>"

        # Avatar Dinámico DiceBear Initial
        import urllib.parse
        avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(seleccion)}&backgroundColor=004e7b&textColor=ffffff"

        # ✅ CARNET DIGITAL (HTML Pegado a la izquierda sin sangría para evitar que streamlit lo tome como código)
        html_carnet = f"""
<div class="id-card">
<div style="display:flex; justify-content: space-between; align-items:flex-start;">
<div class="id-title">HOGAR DE CRISTO • {centro.upper()}</div>
<span style="font-weight:700; background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 10px; font-size: 0.7rem;">
SOCIO/A ACTIVO
</span>
</div>
<div style="display:flex; gap: 15px; align-items: center; margin-bottom: 10px;">
<img src="{avatar_url}" style="width: 50px; height: 50px; border-radius: 50%; border: 2px solid white;"/>
<div class="id-name" style="margin-bottom:0;">{seleccion}</div>
</div>
<div class="id-data-row">
<div class="id-data-col">
<span class="id-label">DNI</span>
<span class="id-value">{datos.get('dni', '---')}</span>
</div>
<div class="id-data-col">
<span class="id-label">F. Nacimiento (Edad)</span>
<span class="id-value">{datos.get('fecha_nacimiento', '---')} ({calculate_age(datos.get('fecha_nacimiento', ''))} años)</span>
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
            # Datos principales con icono
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
                    dom = st.text_input("Domicilio", value=datos_persona.get("domicilio", ""))
                    etiquetas = st.text_input("Etiquetas (Separadas por coma)", value=datos.get("etiquetas", ""))
                    notas_fija = st.text_area("Notas Fijas", value=datos.get("notas", ""))
                    
                    if st.form_submit_button("Guardar Cambios"):
                        # Se usa el Upsert para guardar una nueva fila (mismo nombre) -> historial
                        upsert_persona_direct(seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija, etiquetas=etiquetas)
                        st.toast("Actualizado correctamente")
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
                        append_rows_sa(SEGUIMIENTO_TAB, ["timestamp", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"], [[get_now_ar_str(), str(fecha_seg), year_of(str(fecha_seg)), centro, seleccion, cat, obs, usuario]])
                        st.toast("Nota guardada")
                        st.cache_data.clear(); st.rerun()

            if not mis_notas.empty:
                mis_notas["fecha_dt"] = pd.to_datetime(mis_notas["fecha"], errors="coerce")
                mis_notas = mis_notas.sort_values("fecha_dt", ascending=False)
                # Feed style
                for _, note in mis_notas.iterrows():
                    st.markdown(f"""
<div style="background-color:#262626; padding:10px; border-radius:8px; margin-bottom:10px; border-left: 3px solid #AAAAAA;">
<div style="display:flex; justify-content:space-between;">
<strong>{note['categoria']}</strong> <small>{note['fecha']}</small>
</div>
{note['observacion']}
</div>
""", unsafe_allow_html=True)
            else: st.info("Sin registros en bitácora.")

def page_reportes(dfs, centro):
    st.subheader("📊 Reportes y Resumen")
    # ✅ OPTIMIZACIÓN: Caching en la obtención de datos
    df_a = get_today_asistencia_summary(dfs[ASISTENCIA_TAB])
    df_c = df_a[df_a["centro"] == centro].copy()
    if df_c.empty: st.info("Sin datos cargados hoy."); return
    
    st.dataframe(df_c[["espacio", "presentes", "coordinador", "modo", "notas"]].set_index("espacio"), use_container_width=True)
    
    with st.expander("📥 Descargar Base Completa (Historico)", expanded=False):
        # Generar Excel en memoria para descarga
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_hist = latest_asistencia(dfs[ASISTENCIA_TAB])
            df_hist[df_hist["centro"] == centro].to_excel(writer, sheet_name='Historico_Asistencia', index=False)
        st.download_button("Descargar Historico (Excel)", buffer, f"historico_{centro}.xlsx", "application/vnd.ms-excel", use_container_width=True)

#Helper para reports
def latest_asistencia(df):
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    # Se queda con la carga más reciente por día/centro/espacio (histórico)
    return df2.sort_values("timestamp_dt").groupby(["fecha", "centro", "espacio"]).tail(1)

# Pestaña Global (Suma de todo)
def page_global(dfs):
    st.subheader("🌍 Panorama Global")
    df_a = latest_asistencia(dfs[ASISTENCIA_TAB]).copy()
    if df_a.empty: st.info("Sin datos."); return
    
    df_a["presentes_i"] = df_a["presentes"].apply(clean_int)
    # Sumar presentes por centro de todo el año
    res = df_a.groupby("centro")["presentes_i"].sum().reset_index()
    # Grafico moderno celeste
    st.bar_chart(res.set_index("centro"), color="#60A5FA")

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

    # ✅ CORRECCIÓN 3: Normalización de Nombres de Centro (Previene errores de espacios/acentos en Sheet)
    c_original = centro
    centro_clean = clean_string(centro)
    match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
    if not match_centro:
        st.error(f"Error Crítico: El centro asignado en la base de usuarios '{c_original}' no coincide con los centros definidos en la App ({', '.join(CENTROS)}). Avise a NATASHA.")
        st.stop()
    centro = match_centro

    # 3. Header y Alertas Superiores
    show_top_header(dfs, nombre, centro)
    show_kpi_alerts_bar(dfs, centro)
    
    # ✅ CORRECCIÓN REQUERIMIENTO ESPECIAL: Regla NATASHA & Calle Belén
    # Esconder pestaña si el centro es Calle Belén pero el usuario no es Natasha.
    mostrar_belen = True
    if centro == C_BELEN and u.upper() != "NATASHA":
        st.error("🔒 Este centro es exclusivo de Natasha. Acceso denegado.")
        st.markdown("---")
        mostrar_belen = False
    
    # Separador visual
    st.markdown("---")

    # 4. TABS PRINCIPALES (Bottom Navigation simulado con custom CSS)
    # Se definen las tabs según la regla de Natasha
    list_tabs = ["📝 Asistencia", "👥 Legajo", "📊 Reportes"]
    
    if u.upper() == "NATASHA": list_tabs.append("🌎 Global")

    # Si se denegó el acceso a Belén, solo muestra el error
    if not mostrar_belen: return 

    tabs = st.tabs(list_tabs)
    
    # Tab 1: Carga
    with tabs[0]:
        page_asistencia(dfs, centro, nombre, u)
    
    # Tab 2: Legajo
    with tabs[1]:
        page_legajo(dfs, centro, u)
    
    # Tab 3: Reportes
    with tabs[2]:
        page_reportes(dfs, centro)
        
    # Tab 4: Global (Si existe Natasha)
    if len(tabs) > 3:
        with tabs[3]: page_global(dfs)

if __name__ == "__main__":
    main()
