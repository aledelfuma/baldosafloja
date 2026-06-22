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
# CONFIGURACIÓN DE TEMA OSCURO PREMIUM Y MOBILE
# ======================================================
st.set_page_config(
    page_title="Hogar de Cristo Bahía Blanca",
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

/* COMPORTAMIENTO NATIVO MOBILE Y OCULTAMIENTO DE INTERFAZ DE SISTEMA */
header[data-testid="stHeader"] {display: none !important;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;} 
[data-testid="stAppDeployButton"] {display: none !important;}
.stDeployButton {display: none !important;}

.css-1jc7ptx, .e1ewe7hr3, [class^="viewerBadge"] { display: none !important; }

.stApp {
    background-color: var(--background) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: var(--text-primary) !important;
}

.block-container {
    padding-top: 2rem !important; 
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    padding-bottom: 220px !important; 
    max-width: 500px !important;
    margin: 0 auto;
    overflow-x: hidden;
}

.stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {
    color: var(--text-primary) !important;
}

/* BARRA SUPERIOR GEOMÉTRICA */
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
div.user-info { font-size: 1.1rem; font-weight: 700; line-height: 1.2; }
div.center-info { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary) !important; margin-top: 2px; }

/* BOTONES PREMIUM */
.stButton>button, .stDownloadButton>button {
    background-color: var(--primary) !important;
    color: #000000 !important;
    border-radius: var(--radius-sm) !important;
    border: none !important;
    font-weight: 800 !important;
    padding: 0.7rem 1rem !important;
    transition: 0.2s !important;
    width: 100% !important;
}
.stButton>button:active, .stDownloadButton>button:active { transform: scale(0.98); } 

/* Botón de salida sutil */
div.logout-wrapper > div > button {
    background-color: rgba(239, 68, 68, 0.15) !important;
    color: #FCA5A5 !important;
    border: 1px solid rgba(239, 68, 68, 0.2) !important;
    padding: 0.4rem 0.8rem !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    width: auto !important;
}

.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stMultiSelect>div>div>div {
    border-radius: var(--radius-sm) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    background-color: #1A1A1A !important;
    color: var(--text-primary) !important;
    padding: 0.6rem;
}

[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* KPIs GEOMÉTRICOS */
.kpi {
  border-radius: var(--radius-lg);
  padding: 12px;
  background: var(--surface);
  border: 1px solid rgba(255,255,255,0.05);
  text-align: center;
  height: 100%;
}
.kpi h3 { margin: 0; font-size: 0.6rem; color: var(--text-secondary) !important; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary) !important; line-height: 1; margin-top: 5px; }

.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; }
.alert-danger { background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.3); }
.alert-success { background-color: rgba(34, 197, 94, 0.15); color: #86EFAC !important; border: 1px solid rgba(34, 197, 94, 0.3); }
.alert-warning { background-color: rgba(245, 158, 11, 0.15); color: #FDE047 !important; border: 1px solid rgba(245, 158, 11, 0.3); }
.alert-gray { background-color: var(--surface); color: var(--text-secondary) !important; border: 1px solid rgba(255,255,255,0.05); }

/* CONTROLADOR DE ACTIVIDADES (ESTILO SEMÁFORO GEOMÉTRICO) */
.workshop-status-container {
    background: var(--surface);
    border-radius: var(--radius-lg);
    padding: 15px;
    border: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 20px;
}
.workshop-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.workshop-row:last-child { border-bottom: none; }
.workshop-name { font-size: 0.85rem; font-weight: 600; color: #FFFFFF; }
.workshop-badge { font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; text-transform: uppercase; }
.badge-done { background: rgba(34, 197, 94, 0.15); color: #86EFAC; border: 1px solid rgba(34, 197, 94, 0.2); }
.badge-pending { background: rgba(239, 68, 68, 0.15); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.2); }

/* FICHA DE LEGAJO MINIMALISTA Y GEOMÉTRICA */
.profile-card {
    background-color: var(--surface);
    border-radius: var(--radius-lg);
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 20px;
}
.profile-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 12px;
    margin-bottom: 15px;
}
.profile-institution {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--primary);
    text-transform: uppercase;
}
.profile-status { font-size: 0.75rem; font-weight: 600; }
.status-active { color: #86EFAC; }
.status-inactive { color: #FCA5A5; }
.profile-name { font-size: 1.4rem; font-weight: 800; line-height: 1.1; margin-top: 2px; color: var(--text-primary); }
.profile-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }
.profile-meta-item { display: flex; flex-direction: column; }
.profile-meta-label { font-size: 0.65rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
.profile-meta-value { font-size: 0.95rem; font-weight: 600; color: var(--text-primary); }
.profile-footer-data { background-color: rgba(0, 0, 0, 0.15); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.03); }

/* MENÚ FLOTANTE ELEVADO */
.stTabs [data-baseweb="tab-list"] {
    position: fixed; 
    bottom: 50px !important; 
    left: 15px !important; 
    right: 15px !important;
    background-color: rgba(30, 30, 30, 0.95) !important; 
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 20px !important; 
    display: flex;
    justify-content: space-around;
    padding: 8px 5px !important; 
    z-index: 999999 !important; 
    box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
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
    background-color: rgba(96, 165, 250, 0.12) !important; 
    border-radius: 14px;
}
.stTabs [aria-selected="true"]::after { display: none; }

.note-card {
    background-color: var(--surface);
    border-left: 4px solid var(--secondary);
    padding: 12px 15px;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    margin-bottom: 12px;
    border-top: 1px solid rgba(255,255,255,0.02);
    border-right: 1px solid rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.02);
}

.btn-wa {
    display: block; text-align: center; background-color: #25D366 !important; color: white !important;
    padding: 10px; border-radius: var(--radius-sm); text-decoration: none; font-weight: 700; font-size: 0.9rem; margin-top: 10px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONEXIÓN SEGURA A SUPABASE
# ======================================================
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ======================================================
# ZONA HORARIA, CONFIGURACIONES Y HELPERS
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

# ✅ CONFIGURACIÓN DEL CALENDARIO SEMANAL DE RELEVAMIENTO (IMAGE_816E1F)
CALENDARIO_MARANATHA = {
    0: ["Taller Costura CFP", "Apoyo sec.", "Plan FinEs", "General"], # Lunes
    1: ["Taller de Arte", "La Ronda", "Plan FinEs", "General"],      # Martes
    2: ["Taller Costura CFP", "Apoyo sec.", "General"],              # Miércoles
    3: ["Apoyo Esc. Primario", "Almuerzo", "Fútbol Calle Belén", "Espacio Joven", "General"], # Jueves
    4: ["Pre-Juvenil", "Plan FinEs", "General"],                    # Viernes
    5: ["General"],                                                 # Sábado
    6: ["General"]                                                  # Domingo
}

DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# ======================================================
# FLUJO DE DATOS CONEXIÓN REAL A SUPABASE
# ======================================================
@st.cache_data(ttl=10, show_spinner="Sincronizando...")
def load_all_data_supabase():
    try:
        res_a = supabase.table("asistencia_diaria").select("*").execute()
        res_p = supabase.table("personas").select("*").execute()
        res_ap = supabase.table("asistencia_personas").select("*").execute()
        res_seg = supabase.table("bitacora_seguimiento").select("*").execute()
        
        df_a = pd.DataFrame(res_a.data) if res_a.data else pd.DataFrame(columns=["created_at", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"])
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame(columns=["nombre", "centro", "domicilio", "notas", "activo", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"])
        df_ap = pd.DataFrame(res_ap.data) if res_ap.data else pd.DataFrame(columns=["created_at", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario"])
        df_seg = pd.DataFrame(res_seg.data) if res_seg.data else pd.DataFrame(columns=["created_at", "fecha", "anio", "centro", "nombre_persona", "categoria", "observacion", "usuario_registro"])
        
        return df_a, df_p, df_ap, df_seg
    except Exception as e:
        st.error(f"Error crítico al leer datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def year_of(fecha_iso: str) -> str:
    try: return str(pd.to_datetime(fecha_iso).year)
    except: return str(get_today_ar().year)

def latest_asistencia(df):
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["created_at"], errors="coerce")
    df2["k"] = (df2["anio"].astype(str)+"|"+df2["fecha"].astype(str)+"|"+df2["centro"].astype(str)+"|"+df2["espacio"].astype(str))
    return df2.sort_values("timestamp_dt").groupby("k", as_index=False).tail(1)

def get_today_asistencia_summary(df_a):
    if df_a.empty: return df_a.copy()
    hoy = get_today_ar().isoformat()
    d = df_a[df_a["fecha"] == hoy].copy()
    if d.empty: return d.copy()
    d["timestamp_dt"] = pd.to_datetime(df_a["created_at"], errors="coerce") if "created_at" in df_a.columns else pd.to_datetime(d["created_at"], errors="coerce")
    return d.sort_values("timestamp_dt").groupby(["centro", "espacio"]).tail(1)

def filter_personas_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    if centro in ["Administración", "coordinacion"]: return df_personas.copy()
    centro_clean = clean_string(centro)
    df_temp = df_personas.copy()
    df_temp['centro_norm'] = df_temp['centro'].apply(clean_string)
    return df_temp[df_temp['centro_norm'] == centro_clean].copy()

# ======================================================
# VISTAS E INTERFAZ DE USUARIO (UI)
# ======================================================
def show_login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    try: st.image("logo_hogar.png", width=160)
    except: pass
    
    st.markdown("### HOGAR DE CRISTO BAHIA BLANCA")
    st.markdown("<p style='color:var(--text-secondary); font-size:0.9rem; margin-top:-10px; margin-bottom:25px;'>Ingresá tus credenciales para gestionar el centro.</p>", unsafe_allow_html=True)
    
    with st.form("login_form_oficial"):
        u = st.text_input("Usuario", placeholder="Ej: guillermina").strip()
        p = st.text_input("Contraseña", type="password", placeholder="••••••••").strip()
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Ingresar al Sistema", use_container_width=True):
            if not u or not p:
                st.error("Completá ambos campos.")
            else:
                with st.spinner("Autenticando..."):
                    try:
                        query = supabase.table("usuarios").select("*").execute()
                        if query.data:
                            user_data = None
                            for row in query.data:
                                db_user = row.get("usuarios") or row.get("usuario")
                                if db_user and str(db_user).strip().lower() == u.lower():
                                    user_data = row
                                    break
                            
                            if user_data:
                                if str(user_data["password_text"]) == p:
                                    st.session_state.update({
                                        "logged_in": True, 
                                        "usuario": u, 
                                        "centro_asignado": user_data["centro"].strip(), 
                                        "nombre_visible": user_data["nombre_visible"]
                                    })
                                    st.rerun()
                                else: st.error("Contraseña incorrecta.")
                            else: st.error("El usuario ingresado no existe.")
                        else: st.error("Error crítico: No hay usuarios registrados.")
                    except Exception as e: st.error(f"Error de conexión: {e}")
                    
    st.markdown("""
    <div style='text-align: center; margin-top: 60px; font-size: 0.85rem; color: #444;'>
        Hogar de Cristo Bahía Blanca <br>
        <a href='mailto:alejandrodelfuma@gmail.com' style='color: #60A5FA; text-decoration: none; font-weight: 600;'>
            Soporte Técnico
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

def show_top_header(nombre, centro):
    col_inf, col_out = st.columns([3, 1])
    with col_inf:
        st.markdown(f"""
        <div style='display:flex; align-items:center; gap:12px; background-color: var(--surface); padding: 10px 15px; border-radius: var(--radius-lg); border: 1px solid rgba(255,255,255,0.05);'>
            <div style='background-color: var(--primary); width: 38px; height: 35px; border-radius: 50%; display:flex; align-items:center; justify-content:center; color:black; font-weight:bold; font-size:1rem;'>
                {nombre[0].upper() if nombre else 'U'}
            </div>
            <div>
                <div class='user-info'>{nombre}</div>
                <div class='center-info'>Centro: {centro}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_out:
        st.markdown("<div class='logout-wrapper'>", unsafe_allow_html=True)
        if st.button("Salir"):
            st.session_state.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

# ✅ SEMÁFORO DINÁMICO GEOMÉTRICO (SIN TEXTO CRUDO HTML) BASADO EN CALENDARIO DIARIO
def show_workshop_monitor(df_asistencia, centro_seleccionado, fecha_seleccionada):
    if centro_seleccionado not in [C_MARANATHA]:
        return
        
    st.markdown("<h4 style='font-size:0.9rem; margin-bottom:10px; color:var(--text-secondary); text-transform:uppercase;'>Control de Actividades para este Día</h4>", unsafe_allow_html=True)
    
    fecha_iso = fecha_seleccionada.isoformat()
    dia_semana_num = fecha_seleccionada.weekday() # 0=Lunes, 6=Domingo
    
    actividades_del_dia = CALENDARIO_MARANATHA.get(dia_semana_num, ["General"])
    
    df_hoy = df_asistencia[(df_asistencia["centro"] == centro_seleccionado) & (df_asistencia["fecha"] == fecha_iso)]
    actividades_cargadas = df_hoy["espacio"].unique() if not df_hoy.empty else []
    
    html_monitor = "<div class='workshop-status-container'>"
    for act in actividades_del_dia:
        if act in actividades_cargadas:
            html_monitor += "<div class='workshop-row'><span class='workshop-name'>• " + str(act) + "</span><span class='workshop-badge badge-done'>Cargado</span></div>"
        else:
            html_monitor += "<div class='workshop-row'><span class='workshop-name'>• " + str(act) + "</span><span class='workshop-badge badge-pending'>Falta Cargar</span></div>"
    html_monitor += "</div>"
    st.markdown(html_monitor, unsafe_allow_html=True)

def show_top_alerts(df_latest, df_personas, df_ap, centro):
    if centro in ["Administración", "coordinacion"]:
        return
        
    df_c = filter_personas_centro(df_personas, centro)
    df_c_act = df_c[df_c["activo"].astype(str).str.upper() == "SI"] if not df_c.empty else pd.DataFrame()
    
    cumples = []
    alertas_inasistencia = []
    today = get_today_ar()
    
    if not df_c_act.empty:
        for _, row in df_c_act.iterrows():
            try:
                fn = pd.to_datetime(str(row.get("fecha_nacimiento")), errors="coerce")
                if not pd.isna(fn) and fn.month == today.month and fn.day == today.day:
                    cumples.append(row["nombre"])
            except: pass
            
        if not df_ap.empty:
            df_ap_c = df_ap[(df_ap["centro"] == centro) & (df_ap["estado"] == "Ausente")].copy()
            if not df_ap_c.empty:
                df_ap_c["fecha_dt"] = pd.to_datetime(df_ap_c["fecha"])
                ultimas_fechas = sorted(df_ap["fecha"].unique(), reverse=True)[:4]
                if len(ultimas_fechas) >= 3:
                    for p_nom in df_c_act["nombre"].unique():
                        asist_p = df_ap[(df_ap["nombre"] == p_nom) & (df_ap["fecha"].isin(ultimas_fechas))]
                        if len(asist_p) >= 3 and (asist_p["estado"] == "Ausente").all():
                            alertas_inasistencia.append(p_nom)

    st.markdown("<h4 style='font-size:1rem; margin-bottom:10px;'>Novedades del Centro</h4>", unsafe_allow_html=True)
    today_a = get_today_asistencia_summary(df_latest)
    c_a = today_a[today_a["centro"] == centro] if not today_a.empty else pd.DataFrame()

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if c_a.empty: st.markdown("<div class='alert-box alert-danger'>Faltan Asistencias</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alert-box alert-success'>Asistencias al día</div>", unsafe_allow_html=True)
    with ac2:
        if cumples:
            with st.expander(f"Cumpleaños ({len(cumples)})", expanded=True):
                for c in cumples: st.write(f"- {c}")
        else: st.markdown("<div class='alert-box alert-gray'>Sin cumples</div>", unsafe_allow_html=True)
    with ac3:
        if alertas_inasistencia:
            with st.expander(f"Alerta: Ausencias ({len(alertas_inasistencia)})", expanded=True):
                for a in alertas_inasistencia: st.write(f"- {a}")
        else: st.markdown("<div class='alert-box alert-gray'>Sin alertas críticas</div>", unsafe_allow_html=True)

def kpi_row_full(df_asistencia, centro):
    hoy_date = get_today_ar()
    hoy_str = hoy_date.isoformat()
    hace_7_dias_str = (hoy_date - timedelta(days=6)).isoformat()
    inicio_mes_str = hoy_date.replace(day=1).isoformat()
    
    c1 = c2 = c3 = 0
    if not df_asistencia.empty:
        df_kpi = df_asistencia.copy()
        df_kpi["presentes_i"] = df_kpi["presentes"].apply(lambda x: clean_int(x, 0))
        df_kpi["fecha_str"] = df_kpi["fecha"].astype(str)
        
        if centro in ["Administración", "coordinacion"]:
            df_centro = df_kpi
        else:
            df_centro = df_kpi[df_kpi["centro"] == centro]
        
        c1 = int(df_centro[df_centro["fecha_str"] == hoy_str]["presentes_i"].sum())
        c2 = int(df_centro[(df_centro["fecha_str"] >= hace_7_dias_str) & (df_centro["fecha_str"] <= hoy_str)]["presentes_i"].sum())
        c3 = int(df_centro[(df_centro["fecha_str"] >= inicio_mes_str) & (df_centro["fecha_str"] <= hoy_str)]["presentes_i"].sum())
        
    kc1, kc2, kc3 = st.columns(3)
    kc1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    kc2.markdown(f"<div class='kpi'><h3>Ultimos 7 dias</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    kc3.markdown(f"<div class='kpi'><h3>Mes actual</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)

# ======================================================
# PESTAÑA: CARGA DIARIA CON FILTRO POR TALLER INTERACTIVO
# ======================================================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Carga Diaria</h3>", unsafe_allow_html=True)
    
    if centro in ["Administración", "coordinacion"]:
        centro_seleccionado = st.selectbox("Seleccionar Centro a gestionar:", CENTROS)
    else:
        centro_seleccionado = centro

    fecha = st.date_input("Fecha de carga", value=get_today_ar())
    if fecha > get_today_ar():
        st.error("No se puede cargar asistencia de días futuros.")
        return
    fecha_str = fecha.isoformat()
    
    # Renderizar el monitor de estado específico del día
    show_workshop_monitor(df_asistencia, centro_seleccionado, fecha)
    
    # ✅ ASIGNACIÓN DINÁMICA DE ESPACIOS POR TALLER
    if centro_seleccionado == C_MARANATHA:
        dia_semana_idx = fecha.weekday()
        opciones_espacio = CALENDARIO_MARANATHA.get(dia_semana_idx, ["General"])
        col_e, col_m = st.columns(2)
        with col_e: espacio = st.selectbox("Actividad / Taller del Día", opciones_espacio)
        with col_m: modo = st.selectbox("Modo / Actividad", ["Día habitual", "Actividad especial", "Cerrado"])
    else:
        espacio = DEFAULT_ESPACIO
        col_m = st.columns(1)[0]
        with col_m: modo = st.selectbox("Modo / Actividad", ["Día habitual", "Actividad especial", "Cerrado"])

    notas = st.text_area("Notas generales del día (Opcional)", height=70)

    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    df_activos = df_centro[df_centro["activo"].astype(str).str.upper() == "SI"] if not df_centro.empty else pd.DataFrame()
    nombres = sorted(list(set(df_activos["nombre"].astype(str).tolist()))) if not df_activos.empty else []
    
    st.markdown("#### Marcar Asistencia")
    presentes = st.multiselect("Buscador de personas", options=nombres, placeholder="Seleccionar asistentes...")
    total_presentes = len(presentes)
    
    st.markdown("<br>", unsafe_allow_html=True)
    forrar_reemplazo = st.checkbox("Corregir datos: tildar aca para reemplazar la planilla anterior.", value=False)
    
    if st.button("GUARDAR ASISTENCIA (SUPABASE)", type="primary", use_container_width=True):
        if total_presentes <= 0 and modo != "Cerrado":
            st.error("Debes marcar asistentes o indicar 'Cerrado'.")
            return
            
        with st.spinner("Procesando en Supabase..."):
            try:
                st.cache_data.clear()
                if forrar_reemplazo:
                    supabase.table("asistencia_diaria").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                    supabase.table("asistencia_personas").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                
                cabecera = {
                    "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado,
                    "espacio": espacio, "presentes": total_presentes, "coordinador": nombre_visible,
                    "modo": modo, "notas": notas, 
                    "usuario": usuario, "accion": "replaced" if forrar_reemplazo else "append"
                }
                supabase.table("asistencia_diaria").insert(cabecera).execute()
                
                filas_personas = []
                for n in presentes:
                    filas_personas.append({
                        "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado,
                        "espacio": espacio, "nombre": n, "estado": "Presente", "es_nuevo": "NO",
                        "coordinador": nombre_visible, "usuario": usuario
                    })
                ausentes = [n for n in nombres if n not in presentes]
                for n in ausentes:
                    filas_personas.append({
                        "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado,
                        "espacio": espacio, "nombre": n, "estado": "Ausente", "es_nuevo": "NO",
                        "coordinador": nombre_visible, "usuario": usuario
                    })
                
                if filas_personas:
                    supabase.table("asistencia_personas").insert(filas_personas).execute()
                
                st.balloons()
                st.toast("Cambios guardados correctamente")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                err_str = str(e)
                if "23505" in err_str or "already exists" in err_str.lower():
                    st.markdown(f"""
                    <div class='alert-box alert-warning'>
                        <b>Planilla existente:</b> Ya se cargo una asistencia para el espacio '{espacio}' en esta fecha.<br><br>
                        <b>¿Te equivocaste o queres corregirla?</b> Activa la casilla de arriba que dice "Corregir datos" y volve a presionar el botón de guardar.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Error inesperado: {e}")

# ======================================================
# PESTAÑA: BUSCADOR DE LEGAJOS Y BITÁCORA
# ======================================================
def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Buscador de Legajos</h3>", unsafe_allow_html=True)
    
    if centro in ["Administración", "coordinacion"]:
        centro_seleccionado = st.selectbox("Filtrar padrón por centro barrial:", CENTROS, key="padrón_admin_select")
    else:
        centro_seleccionado = centro

    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    nombres = sorted(df_centro["nombre"].unique().tolist()) if not df_centro.empty else []

    seleccion = st.selectbox("Escribi el nombre para ver la ficha:", [""] + nombres)
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-gray'>Busca a alguien arriba para ver su carnet.</div>", unsafe_allow_html=True)
        if not df_centro.empty:
            st.markdown("#### Padrón Oficial del Centro")
            filtro_activo = st.radio("Filtrar padrón por estado:", ["Solo Activos", "Todos"], horizontal=True)
            df_mostrar_padrón = df_centro.copy()
            if filtro_activo == "Solo Activos":
                df_mostrar_padrón = df_mostrar_padrón[df_mostrar_padrón["activo"].astype(str).str.upper() == "SI"]
                
            st.dataframe(df_mostrar_padrón[["nombre", "dni", "telefono", "activo"]].sort_values("nombre"), use_container_width=True, hide_index=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            csv_padron = df_mostrar_padrón[["nombre", "dni", "telefono", "domicilio", "activo"]].sort_values("nombre").to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Padrón de este Centro a Excel/CSV", data=csv_padron, file_name=f"padron_{centro_seleccionado}.csv", mime="text/csv")
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    tags_str = str(datos_persona.get("etiquetas", ""))
    telefono = str(datos_persona.get("telefono", ""))
    wa_btn_html = f"<a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>Enviar WhatsApp</a>" if (telefono and telefono.lower() != "none") else ""
    
    is_active = str(datos_persona.get("activo")).upper() != "NO"
    status_class = "status-active" if is_active else "status-inactive"
    status_text = "• Activo" if is_active else "• Inactivo"
    
    dni_val = str(datos_persona.get('dni', '')).strip()
    dni_val = "S/D" if (not dni_val or dni_val.lower() == 'none') else dni_val
    
    nac_val = str(datos_persona.get('fecha_nacimiento', '')).strip()
    nacimiento_mostrar = "S/D" if (not nac_val or nac_val.lower() == 'none') else f"{nac_val} ({calculate_age(nac_val)} anos)"
    
    direccion_val = str(datos_persona.get('domicilio','')).strip()
    direccion_mostrar = "No registrada" if (not direccion_val or direccion_val.lower() == 'none') else direccion_val

    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-header">
            <div>
                <span class="profile-institution">Hogar de Cristo Bahía Blanca</span>
                <div class="profile-name">{seleccion}</div>
            </div>
            <span class="profile-status {status_class}">{status_text}</span>
        </div>
        <div class="profile-grid">
            <div class="profile-meta-item">
                <span class="profile-meta-label">Documento</span>
                <span class="profile-meta-value">{dni_val}</span>
            </div>
            <div class="profile-meta-item">
                <span class="profile-meta-label">Nacimiento / Edad</span>
                <span class="profile-meta-value">{nacimiento_mostrar}</span>
            </div>
            <div class="profile-meta-item" style="grid-column: span 2;">
                <span class="profile-meta-label">Direccion</span>
                <span class="profile-meta-value">{direccion_mostrar}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if tags_str and tags_str.lower() != "none" and tags_str.lower() != "nan":
        st.markdown(f"""
        <div class="profile-footer-data">
            <span class="profile-meta-label" style="font-size:0.55rem; opacity:0.8;">Datos Familiares / Referencia</span>
            <div style="font-size:0.85rem; font-weight:600; color:var(--text-primary); margin-top:2px;">{tags_str}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if wa_btn_html:
        st.markdown(wa_btn_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Registrar Intervención / Nota del Día")
    with st.form("form_bitacora_seguimiento", clear_on_submit=True):
        f_nota = st.date_input("Fecha de lo ocurrido", value=get_today_ar())
        cat_nota = st.selectbox("Categoría de Seguimiento", CATEGORIAS_SEGUIMIENTO)
        obs_nota = st.text_area("¿Qué pasó hoy?", placeholder="Ej: Se charló con el referente familiar...")
        
        if st.form_submit_button("Guardar en Bitácora (Supabase)", use_container_width=True):
            if not obs_nota.strip():
                st.error("La observación no puede quedar vacía.")
            else:
                with st.spinner("Asentando nota en la nube..."):
                    try:
                        st.cache_data.clear()
                        f_nota_str = f_nota.isoformat()
                        nueva_intervencion = {
                            "fecha": f_nota_str, "anio": year_of(f_nota_str), "centro": centro_seleccionado,
                            "nombre_persona": seleccion, "categoria": cat_nota,
                            "observacion": obs_nota.strip(), "usuario_registro": usuario
                        }
                        supabase.table("bitacora_seguimiento").insert(nueva_intervencion).execute()
                        st.toast(f"Nota registrada para {seleccion}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Error al registrar nota: {e}")

    st.markdown("<br>### Historial de Acompañamiento", unsafe_allow_html=True)
    df_chico = df_seg[df_seg["nombre_persona"] == seleccion].copy() if not df_seg.empty else pd.DataFrame()
    
    if df_chico.empty:
        st.markdown("<div class='alert-box alert-gray'>Todavía no hay notas asentadas en la bitácora para este participante.</div>", unsafe_allow_html=True)
    else:
        df_chico = df_chico.sort_values("fecha", ascending=False)
        for _, row in df_chico.iterrows():
            st.markdown(f"""
            <div class='note-card'>
                <div style='display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-secondary); margin-bottom:5px;'>
                    <span>Fecha: <b>{row['fecha']}</b> — Categoria: <i>{row['categoria']}</i></span>
                    <span>Por: {row['usuario_registro']}</span>
                </div>
                <div style='font-size:0.95rem; color:var(--text-primary); line-height:1.4;'>
                    {row['observacion']}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ======================================================
# PESTAÑA: ALTA DE PERSONA
# ======================================================
def page_alta_persona(df_personas, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Alta de Persona al Padrón</h3>", unsafe_allow_html=True)
    st.info("Completá este formulario para ingresar al sistema a alguien que ya participa del centro.")
    
    if centro in ["Administración", "coordinacion"]:
        centro_destino = st.selectbox("Asignar legajo al centro:", CENTROS, key="alta_admin_select")
    else:
        centro_destino = centro

    with st.form("alta_directa_form"):
        st.markdown("#### Datos Principales")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            new_nom = st.text_input("Nombre Completo *", placeholder="Ej: Juan Pérez")
            new_dni = st.text_input("DNI")
            new_nac = st.text_input("Fecha de Nacimiento (AAAA-MM-DD)", help="Ej: 1998-11-08")
        with col_a2:
            new_tel = st.text_input("Teléfono")
            new_em = st.text_input("Contacto de Emergencia")
            new_dom = st.text_input("Dirección / Barrio")
        
        st.markdown("#### Información Adicional")
        new_etq = st.text_input("Etiquetas (Separadas por coma)")
        new_notas = st.text_area("Notas Permanentes")
        
        if st.form_submit_button("Guardar en el Padrón (Supabase)", type="primary", use_container_width=True):
            if not new_nom.strip():
                st.error("El Nombre Completo es obligatorio.")
            else:
                with st.spinner("Guardando legajo en la nube..."):
                    try:
                        st.cache_data.clear()
                        check = supabase.table("personas").select("*").eq("centro", centro_destino).ilike("nombre", new_nom.strip()).execute()
                        if check.data:
                            st.warning(f"'{new_nom}' ya existe en este centro.")
                        else:
                            fecha_nac_valida = None
                            if new_nac.strip():
                                try: 
                                    fecha_nac_valida = pd.to_datetime(new_nac.strip()).date().isoformat()
                                except:
                                    st.error("Formato de fecha incorrecto. Usar AAAA-MM-DD.")
                                    st.stop()

                            fila_nueva = {
                                "nombre": new_nom.strip(), "dni": new_dni.strip() if new_dni.strip() else None,
                                "fecha_nacimiento": fecha_nac_valida, "telefono": new_tel.strip() if new_tel.strip() else None,
                                "domicilio": new_dom.strip() if new_dom.strip() else None, "contacto_emergencia": new_em.strip() if new_em.strip() else None,
                                "etiquetas": new_etq.strip() if new_etq.strip() else None, "notas": new_notas.strip() if new_notas.strip() else None,
                                "activo": "SI", "centro": centro_destino, "usuario_alta": usuario
                            }
                            supabase.table("personas").insert(fila_nueva).execute()
                            st.balloons()
                            st.success(f"¡{new_nom} ingresado correctamente!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e: st.error(f"Error al guardar: {e}")

# ======================================================
# PESTAÑA: REPORTES ANALÍTICOS AVANZADOS
# ======================================================
def page_reportes(df_asistencia, centro):
    st.markdown("<h3 style='margin-bottom:15px;'>Métricas y Tendencias Temporales</h3>", unsafe_allow_html=True)
    
    centro_seleccionado = st.selectbox("Filtrar reporte por centro barrial:", CENTROS, key="reportes_admin_select") if centro in ["Administración", "coordinacion"] else centro
    df_c = df_asistencia[df_asistencia["centro"] == centro_seleccionado].copy() if not df_asistencia.empty else pd.DataFrame()
    
    if df_c.empty:
        st.markdown("<div class='alert-box alert-gray'>Todavía no hay datos históricos suficientes en este centro para generar estadísticas avanzadas.</div>", unsafe_allow_html=True)
        return
        
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"]).dt.date
    df_c = df_c.sort_values("fecha_dt")

    hoy = get_today_ar()
    
    inicio_sem_actual = hoy - timedelta(days=6)
    inicio_sem_anterior = hoy - timedelta(days=13)
    inicio_mes_actual = hoy.replace(day=1)
    inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1)
    
    sum_sem_actual = df_c[(df_c["fecha_dt"] >= inicio_sem_actual) & (df_c["fecha_dt"] <= hoy)]["presentes_i"].sum()
    sum_sem_anterior = df_c[(df_c["fecha_dt"] >= inicio_sem_anterior) & (df_c["fecha_dt"] < inicio_sem_actual)]["presentes_i"].sum()
    sum_mes_actual = df_c[(df_c["fecha_dt"] >= inicio_mes_actual) & (df_c["fecha_dt"] <= hoy)]["presentes_i"].sum()
    sum_mes_anterior = df_c[(df_c["fecha_dt"] >= inicio_mes_anterior) & (df_c["fecha_dt"] < inicio_mes_actual)]["presentes_i"].sum()
    
    def delta_pct(act, ant):
        if ant == 0: return 0.0
        return ((act - ant) / ant) * 100

    wow_pct = delta_pct(sum_sem_actual, sum_sem_anterior)
    mom_pct = delta_pct(sum_mes_actual, sum_mes_anterior)
    
    m1, m2 = st.columns(2)
    with m1:
        c_wow = "#86EFAC" if wow_pct >= 0 else "#FCA5A5"
        st.markdown(f"""
        <div class='kpi'>
            <h3>Semana vs Semana Anterior (WoW)</h3>
            <div class='v'>{sum_sem_actual} <span style='font-size:1rem; color:{c_wow}; font-weight:700;'>({"+" if wow_pct>=0 else ""}{wow_pct:.1f}%)</span></div>
            <span style='font-size:0.7rem; color:var(--text-secondary);'>Últimos 7 días corridos vs período previo</span>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        c_mom = "#86EFAC" if mom_pct >= 0 else "#FCA5A5"
        st.markdown(f"""
        <div class='kpi'>
            <h3>Mes Actual vs Mes Anterior (MoM)</h3>
            <div class='v'>{sum_mes_actual} <span style='font-size:1rem; color:{c_mom}; font-weight:700;'>({"+" if mom_pct>=0 else ""}{mom_pct:.1f}%)</span></div>
            <span style='font-size:0.7rem; color:var(--text-secondary);'>Acumulado mensual vs mes cerrado anterior</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>#### Evolución Lineal de Concurrencia", unsafe_allow_html=True)
    df_linea = df_c.groupby("fecha")["presentes_i"].sum().reset_index()
    st.line_chart(df_linea.set_index("fecha")["presentes_i"], color="#60A5FA")

    st.markdown("<br>#### Análisis del Flujo por Día de la Semana", unsafe_allow_html=True)
    df_c["dia_nombre"] = pd.to_datetime(df_c["fecha"]).dt.day_name()
    map_dias = {'Monday':'Lunes','Tuesday':'Martes','Wednesday':'Miércoles','Thursday':'Jueves','Friday':'Viernes','Saturday':'Sábado','Sunday':'Domingo'}
    df_c["dia_nombre"] = df_c["dia_nombre"].map(map_dias)
    
    df_dias_agg = df_c.groupby("dia_nombre")["presentes_i"].mean().reindex(['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']).fillna(0)
    st.bar_chart(df_dias_agg, color="#A78BFA")

# ======================================================
# CONSOLE GLOBAL ADMIN (SUPERVISIÓN TOTAL DE COORDINADORES)
# ======================================================
def page_global(df_asistencia, df_personas, df_ap):
    st.markdown("<h3 style='margin-bottom:15px;'>Consola Central Institucional</h3>", unsafe_allow_html=True)
    st.caption("Panel de control unificado para de cargas generales de Hogar de Cristo Bahía Blanca.")
    
    t_pers = len(df_personas["nombre"].unique()) if not df_personas.empty else 0
    t_asist = df_asistencia["presentes"].apply(lambda x: clean_int(x, 0)).sum() if not df_asistencia.empty else 0
    
    k1, k2 = st.columns(2)
    k1.markdown(f"<div class='kpi'><h3>Padrón Total Institucional</h3><div class='v'>{t_pers}</div><span style='font-size:0.75rem; color:var(--text-secondary);'>Personas en la federación</span></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3>Total de Asistencias</h3><div class='v'>{t_asist}</div><span style='font-size:0.75rem; color:var(--text-secondary);'>Ingresos totales acumulados</span></div>", unsafe_allow_html=True)
    
    st.markdown("<br>#### Semáforo de Actividad de Hoy", unsafe_allow_html=True)
    
    hoy_str = get_today_ar().isoformat()
    sc1, sc2, sc3 = st.columns(3)
    
    with sc1:
        c_bel = df_asistencia[(df_asistencia["centro"] == C_BELEN) & (df_asistencia["fecha"] == hoy_str)]
        if c_bel.empty: st.markdown("<div class='alert-box alert-danger'>Calle Belén: Falta Cargar</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alert-box alert-success'>Calle Belén: Al Día</div>", unsafe_allow_html=True)
        
    with sc2:
        c_mar = df_asistencia[(df_asistencia["centro"] == C_MARANATHA) & (df_asistencia["fecha"] == hoy_str)]
        if c_mar.empty: st.markdown("<div class='alert-box alert-danger'>Casa Maranatha: Falta Cargar</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alert-box alert-success'>Casa Maranatha: Al Día</div>", unsafe_allow_html=True)
        
    with sc3:
        c_nud = df_asistencia[(df_asistencia["centro"] == C_NUDO) & (df_asistencia["fecha"] == hoy_str)]
        if c_nud.empty: st.markdown("<div class='alert-box alert-danger'>Nudo a Nudo: Falta Cargar</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alert-box alert-success'>Nudo a Nudo: Al Día</div>", unsafe_allow_html=True)

    st.markdown("<br>#### Auditoría y Registro de Planillas", unsafe_allow_html=True)
    if not df_asistencia.empty:
        df_audit = df_asistencia.copy().sort_values("created_at", ascending=False)
        
        df_audit_clean = df_audit[["fecha", "centro", "espacio", "presentes", "coordinador", "modo", "accion"]].rename(
            columns={"fecha": "Fecha", "centro": "Centro Barrial", "espacio": "Espacio", "presentes": "Asistentes", "coordinador": "Responsable", "modo": "Estado del Día", "accion": "Tipo Registro"}
        )
        st.dataframe(df_audit_clean, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        csv_historico = df_audit_clean.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Base de Datos Histórica Completa", data=csv_historico, file_name="historico_asistencias_federacion.csv", mime="text/csv")
    else:
        st.markdown("<div class='alert-box alert-gray'>No se registran planillas en la base de datos de asistencia.</div>", unsafe_allow_html=True)

# ======================================================
# CONTROLADOR PRINCIPAL
# ======================================================
def main():
    if not st.session_state.get("logged_in"): 
        show_login_screen()
    
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]
    
    if centro not in ["Administración", "coordinacion"]:
        centro_clean = clean_string(centro)
        match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
        if not match_centro:
            st.error(f"Error: El centro '{centro}' no está mapeado.")
            st.stop()
        centro = match_centro

    show_top_header(nombre, centro)
    df_asistencia, df_personas, df_ap, df_seg = load_all_data_supabase()

    list_tabs = ["Inicio", "Legajos", "Alta", "Reportes"]
    if centro in ["Administración", "coordinacion"] or u.lower() == "admin": 
        list_tabs.append("Global")
    
    tabs = st.tabs(list_tabs)
    
    with tabs[0]: 
        show_top_alerts(latest_asistencia(df_asistencia), df_personas, df_ap, centro)
        kpi_row_full(df_asistencia, centro)
        st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
        page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
        
    with tabs[1]: 
        page_personas_full(df_personas, df_ap, df_seg, centro, u)

    with tabs[2]: 
        page_alta_persona(df_personas, centro, u)
        
    with tabs[3]: 
        page_reportes(df_asistencia, centro)
        
    if "Global" in list_tabs and len(tabs) > 4:
        with tabs[4]: 
            page_global(df_asistencia, df_personas, df_ap)

if __name__ == "__main__":
    main()
