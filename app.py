import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import pytz
import io
import unicodedata
import re
from supabase import create_client, Client

# ======================================================
# 🌑 CONFIGURACIÓN DE TEMA OSCURO PREMIUM Y MOBILE
# ======================================================
st.set_page_config(
    page_title="Baldosa Floja",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
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

/* COMPORTAMIENTO NATIVO MOBILE */
header[data-testid="stHeader"] {display: none !important;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.viewerBadge_container {display: none !important;} 
[data-testid="stToolbar"] {display: none !important;} 
[data-testid="stAppDeployButton"] {display: none !important;}
.stDeployButton {display: none !important;}

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
    background-color: rgba(18, 18, 18, 0.95); 
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-top: 1px solid rgba(255,255,255,0.1);
    display: flex;
    justify-content: space-around;
    padding: 10px 5px env(safe-area-inset-bottom, 20px) 5px; 
    z-index: 999999 !important; 
}
.stTabs [data-baseweb="tab"] {
    flex-grow: 1; text-align: center; justify-content: center;
    font-size: 0.65rem !important;
    font-weight: 700;
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

# ======================================================
# ⚡ CONEXIÓN SEGURA A SUPABASE
# ======================================================
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ======================================================
# 🌑 ZONA HORARIA, CONFIGURACIONES Y HELPERS
# ======================================================
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')

def get_now_ar_str(): return datetime.now(TZ_AR).strftime("%Y-%m-%d %H:%M:%S")
def get_today_ar(): return datetime.now(TZ_AR).date()

def calculate_age(born):
    try:
        born = pd.to_datetime(born).date()
        today = get_today_ar()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except: return 0

def format_wa_number(phone):
    return re.sub(r'\D', '', str(phone))

def clean_string(s):
    if not isinstance(s, str): return ""
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.strip().upper()

def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default

C_BELEN = "Calle Belén"
C_NUDO = "Nudo a Nudo"
C_MARANATHA = "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]

ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# ======================================================
# 🔄 FLUJO DE DATOS (LECTURA TEMPORAL EN BLANCO)
# ======================================================
@st.cache_data(ttl=60, show_spinner="Sincronizando con Supabase...")
def load_all_data_supabase():
    # Nota: En los siguientes pasos cambiaremos estas lecturas simuladas por consultas SQL reales a Supabase
    df_a = pd.DataFrame(columns=["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"])
    df_p = pd.DataFrame(columns=["nombre", "centro", "edad", "domicilio", "notas", "activo", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"])
    df_ap = pd.DataFrame(columns=["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario"])
    df_seg = pd.DataFrame(columns=["timestamp", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"])
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

def filter_personas_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    centro_clean = clean_string(centro)
    df_temp = df_personas.copy()
    df_temp['centro_norm'] = df_temp['centro'].apply(clean_string)
    return df_temp[df_temp['centro_norm'] == centro_clean].copy()

# ======================================================
# 🖥️ VISTAS E INTERFAZ DE USUARIO (UI)
# ======================================================
def show_login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_hogar.png", width=200)
        except: st.title("Baldosa Floja")
        st.markdown("### Acceso al Sistema")
        
        with st.form("login_form"):
            u = st.text_input("Usuarios")
            p = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Ingresar", use_container_width=True):
                try:
                    # ⚡ CONSULTA DIRECTA A SUPABASE
                    query = supabase.table("usuarios").select("*").eq("usuario", u.strip()).execute()
                    
                    if query.data:
                        user_data = query.data[0]
                        if str(user_data["password_text"]) == p.strip():
                            st.session_state.update({
                                "logged_in": True, 
                                "usuario": user_data["usuario"], 
                                "centro_asignado": user_data["centro"].strip(), 
                                "nombre_visible": user_data["nombre_visible"]
                            })
                            st.rerun()
                        else:
                            st.error("🔒 Contraseña incorrecta.")
                    else:
                        st.error("🔍 Usuario no encontrado.")
                except Exception as e:
                    st.error(f"❌ Error de conexión con Supabase: {e}")
        
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
    st.markdown("<h4 style='font-size:1rem; margin-bottom:10px;'>📊 Novedades del Centro</h4>", unsafe_allow_html=True)
    ac1, ac2, ac3 = st.columns(3)
    with ac1: st.markdown("<div class='alert-box alert-gray'>⚠️ Sin datos hoy</div>", unsafe_allow_html=True)
    with ac2: st.markdown("<div class='alert-box alert-gray'>🎂 Sin cumples</div>", unsafe_allow_html=True)
    with ac3: st.markdown("<div class='alert-box alert-gray'>✔️ Sin Inasistencias</div>", unsafe_allow_html=True)

def kpi_row_full(df_latest, centro):
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>0</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>0</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi'><h3>Mes actual</h3><div class='v'>0</div></div>", unsafe_allow_html=True)

# ======================================================
# 📂 VISTAS DE PÁGINAS (PANELES VÍOS DE MOMENTO)
# ======================================================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>📝 Carga Diaria</h3>", unsafe_allow_html=True)
    st.info("Próximo paso: Conectar el buscador de asistencia a la tabla de personas de Supabase.")

def page_alta_persona(df_personas, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>➕ Alta de Persona al Padrón</h3>", unsafe_allow_html=True)
    st.info("Próximo paso: Desarrollar la inserción SQL para agregar legajos al padrón oficial.")

def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>👥 Buscador de Legajos</h3>", unsafe_allow_html=True)
    st.info("Próximo paso: Vincular las fichas técnicas e historias clínicas comunitarias con Supabase.")

def page_reportes(df_asistencia, centro):
    st.markdown("<h3 style='margin-bottom:15px;'>📊 Reportes</h3>", unsafe_allow_html=True)
    st.info("Próximo paso: Diseñar gráficos interactivos de evolución temporal con la nueva base de datos.")

def page_global(df_asistencia, df_personas, df_ap):
    st.markdown("<h3 style='margin-bottom:15px;'>🌍 Consola Central</h3>", unsafe_allow_html=True)
    st.info("Consola exclusiva de administración global habilitada.")

# ======================================================
# 🎮 CONTROLADOR PRINCIPAL
# ======================================================
def main():
    if not st.session_state.get("logged_in"): 
        show_login_screen()
    
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]
    
    centro_clean = clean_string(centro)
    match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
    if not match_centro:
        st.error(f"Error: El centro '{centro}' no está mapeado en el sistema.")
        st.stop()
    centro = match_centro

    if centro == C_BELEN and u.upper() != "NATASHA_TEST":
        st.error("🔒 ACCESO DENEGADO: El centro Calle Belén es de acceso exclusivo para la administración.")
        if st.button("⬅️ Salir de la cuenta", type="primary"):
            st.session_state.clear(); st.rerun()
        return

    show_top_header(nombre, centro)
    df_asistencia, df_personas, df_ap, df_seg = load_all_data_supabase()

    list_tabs = ["🏠 Inicio", "👥 Legajos", "➕ Alta", "📊 Reportes"]
    if u.upper() == "NATASHA_TEST": 
        list_tabs.append("🌍 Global")
    
    tabs = st.tabs(list_tabs)
    
    with tabs[0]: 
        show_top_alerts(latest_asistencia(df_asistencia), df_personas, df_ap, centro)
        kpi_row_full(latest_asistencia(df_asistencia), centro)
        st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
        page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
        
    with tabs[1]: 
        page_personas_full(df_personas, df_ap, df_seg, centro, u)

    with tabs[2]: 
        page_alta_persona(df_personas, centro, u)
        
    with tabs[3]: 
        page_reportes(df_asistencia, centro)
        
    if len(tabs) > 4:
        with tabs[4]: 
            page_global(df_asistencia, df_personas, df_ap)

if __name__ == "__main__":
    main()
