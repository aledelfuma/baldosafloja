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
    padding-bottom: 160px !important; 
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
}
.kpi h3 { margin: 0; font-size: 0.6rem; color: var(--text-secondary) !important; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary) !important; line-height: 1; margin-top: 5px; }

.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; }
.alert-danger { background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.3); }
.alert-success { background-color: rgba(34, 197, 94, 0.15); color: #86EFAC !important; border: 1px solid rgba(34, 197, 94, 0.3); }
.alert-warning { background-color: rgba(245, 158, 11, 0.15); color: #FDE047 !important; border: 1px solid rgba(245, 158, 11, 0.3); }
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

.login-box {
    background-color: var(--surface);
    padding: 30px 25px;
    border-radius: var(--radius-lg);
    border: 1px solid rgba(255,255,255,0.05);
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

ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# ======================================================
# FLUJO DE DATOS CONEXIÓN REAL A SUPABASE
# ======================================================
@st.cache_data(ttl=10, show_spinner="Sincronizando con Supabase...")
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
    if centro == "Administración": return df_personas.copy()
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
    
    st.markdown("### Bienvenido")
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
        Federación de Hogares de Cristo <br>
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
                <div class='user-info'>Hola, {nombre}</div>
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

def show_top_alerts(df_latest, df_personas, df_ap, centro):
    if centro == "Administración":
        return
    cumples = []
    if not df_personas.empty:
        df_c = filter_personas_centro(df_personas, centro)
        df_c_act = df_c[df_c["activo"].astype(str).str.upper() == "SI"]
        today = get_today_ar()
        for _, row in df_c_act.iterrows():
            try:
                fn = pd.to_datetime(str(row.get("fecha_nacimiento")), errors="coerce")
                if not pd.isna(fn) and fn.month == today.month and fn.day == today.day:
                    cumples.append(row["nombre"])
            except: pass

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
    with ac3: st.markdown("<div class='alert-box alert-gray'>Sin Inasistencias</div>", unsafe_allow_html=True)

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
        
        if centro == "Administración":
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
# PESTAÑA: CARGA DIARIA
# ======================================================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Carga Diaria</h3>", unsafe_allow_html=True)
    
    # El administrador puede simular la carga de cualquier centro barrial
    if centro == "Administración":
        centro_seleccionado = st.selectbox("Seleccionar Centro a gestionar:", CENTROS)
    else:
        centro_seleccionado = centro

    fecha = st.date_input("Fecha de carga", value=get_today_ar())
    if fecha > get_today_ar():
        st.error("No se puede cargar asistencia de días futuros.")
        return
    fecha_str = fecha.isoformat()
    
    col_e, col_m = st.columns(2)
    with col_e: espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA) if centro_seleccionado == C_MARANATHA else DEFAULT_ESPACIO
    with col_m: modo = st.selectbox("Modo / Actividad", ["Día habitual", "Actividad especial", "Cerrado"])
    
    notas = st.text_area("Notas generales del día (Opcional)", height=70)

    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    df_activos = df_centro[df_centro["activo"].astype(str).str.upper() == "SI"] if not df_centro.empty else pd.DataFrame()
    nombres = sorted(list(set(df_activos["nombre"].astype(str).tolist()))) if not df_activos.empty else []
    
    st.markdown("#### Marcar Asistencia")
    presentes = st.multiselect("Buscador de personas", options=nombres, placeholder="Seleccionar asistentes...")
    total_presentes = len(presentes)
    
    st.markdown("<br>", unsafe_allow_html=True)
    forzar_reemplazo = st.checkbox("Corregir datos: tildar aca para reemplazar la planilla anterior.", value=False)
    
    if st.button("GUARDAR ASISTENCIA (SUPABASE)", type="primary", use_container_width=True):
        if total_presentes <= 0 and modo != "Cerrado":
            st.error("Debes marcar asistentes o indicar 'Cerrado'.")
            return
            
        with st.spinner("Procesando en Supabase..."):
            try:
                if forzar_reemplazo:
                    supabase.table("asistencia_diaria").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                    supabase.table("asistencia_personas").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                
                cabecera = {
                    "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado,
                    "espacio": espacio, "presentes": total_presentes, "coordinador": nombre_visible,
                    "modo": modo, "notas": notas, 
                    "usuario": usuario, "accion": "append"
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
                time.sleep(1.5)
                st.cache_data.clear()
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
    
    if centro == "Administración":
        centro_seleccionado = st.selectbox("Filtrar padrón por centro barrial:", CENTROS, key="padrón_admin_select")
    else:
        centro_seleccionado = centro

    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    nombres = sorted(df_centro["nombre"].unique()) if not df_centro.empty else []

    seleccion = st.selectbox("Escribi el nombre para ver su ficha:", [""] + nombres)
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-gray'>Busca a alguien arriba para ver su carnet.</div>", unsafe_allow_html=True)
        if not df_centro.empty:
            st.markdown("#### Padrón Oficial del Centro")
            filtro_activo = st.radio("Filtrar padrón por estado:", ["Solo Activos", "Todos"], horizontal=True)
            df_mostrar_padrón = df_centro.copy()
            if filtro_activo == "Solo Activos":
                df_mostrar_padrón = df_mostrar_padrón[df_mostrar_padrón["activo"].astype(str).str.upper() == "SI"]
                
            st.dataframe(df_mostrar_padrón[["nombre", "dni", "telefono", "activo"]].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    tags_str = str(datos_persona.get("etiquetas", ""))
    tags_html = ""
    if tags_str and tags_str.lower() != "none" and tags_str.lower() != "nan":
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

    telefono = str(datos_persona.get("telefono", ""))
    wa_btn_html = f"<div style='margin-top:5px;'><a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>Enviar WhatsApp</a></div>" if (telefono and telefono.lower() != "none") else ""
    estado_badge = "ACTIVO" if str(datos_persona.get("activo")).upper() != "NO" else "INACTIVO"
    
    import urllib.parse
    avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(seleccion)}&backgroundColor=004e7b&textColor=ffffff"

    dni_val = str(datos_persona.get('dni', '')).strip()
    dni_val = "S/D" if (not dni_val or dni_val.lower() == 'none') else dni_val
    
    nac_val = str(datos_persona.get('fecha_nacimiento', '')).strip()
    nacimiento_mostrar = "S/D" if (not nac_val or nac_val.lower() == 'none') else f"{nac_val} ({calculate_age(nac_val)} años)"

    html_carnet = f"""
<div class="id-card">
<div style="display:flex; justify-content: space-between; align-items:flex-start; margin-bottom: 5px;">
<div class="id-title">HOGAR DE CRISTO</div>
<span style="font-weight:800; background: rgba(255,255,255,0.25); padding: 5px 12px; border-radius: 12px; font-size: 0.70rem; letter-spacing:1px;">{estado_badge}</span>
</div>
<div style="display:flex; gap: 15px; align-items: center; margin-bottom: 20px;">
<img src="{avatar_url}" style="width: 60px; height: 60px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.8);"/>
<div class="id-name" style="margin-bottom:0;">{seleccion}</div>
</div>
<div class="id-data-row">
<div class="id-data-col"><span class="id-label">Documento</span><span class="id-value">{dni_val}</span></div>
<div class="id-data-col"><span class="id-label">Nacimiento</span><span class="id-value">{nacimiento_mostrar}</span></div>
</div>
<div class="tag-container">{tags_html}</div>
</div>
"""
    st.markdown(html_carnet, unsafe_allow_html=True)
    
    st.markdown(f"""
<div style="background:var(--surface); padding:15px; border-radius:var(--radius-sm); border:1px solid rgba(255,255,255,0.05); margin-bottom:25px;">
    <div style="margin-bottom:10px;">
        <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">Telefono</div>
        <div style="font-size:1.1rem;">{telefono if (telefono and telefono.lower()!='none') else 'No registrado'}</div>
        {wa_btn_html}
    </div>
    <div>
        <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">Direccion</div>
        <div style="font-size:1.1rem;">{str(datos_persona.get('domicilio','')) if str(datos_persona.get('domicilio','')).lower()!='none' else 'No registrada'}</div>
    </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### Registrar Intervención / Nota del Día")
    with st.form("form_bitacora_seguimiento", clear_on_submit=True):
        f_nota = st.date_input("Fecha de lo ocurrido", value=get_today_ar())
        cat_nota = st.selectbox("Categoría de Seguimiento", CATEGORIAS_SEGUIMIENTO)
        obs_nota = st.text_area("¿Qué pasó hoy?", placeholder="Ej: Se lo acompañó a sacar el DNI...")
        
        if st.form_submit_button("Guardar en Bitácora (Supabase)", use_container_width=True):
            if not obs_nota.strip():
                st.error("La observación no puede quedar vacía.")
            else:
                with st.spinner("Asentando nota en la nube..."):
                    try:
                        f_nota_str = f_nota.isoformat()
                        nueva_intervencion = {
                            "fecha": f_nota_str, "anio": year_of(f_nota_str), "centro": centro_seleccionado,
                            "nombre_persona": seleccion, "categoria": cat_nota,
                            "observacion": obs_nota.strip(), "usuario_registro": usuario
                        }
                        supabase.table("bitacora_seguimiento").insert(nueva_intervencion).execute()
                        st.toast(f"Nota registrada para {seleccion}")
                        time.sleep(1)
                        st.cache_data.clear()
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
    
    if centro == "Administración":
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
                            time.sleep(1.5)
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as e: st.error(f"Error al guardar: {e}")

def page_reportes(df_asistencia, centro):
    st.markdown("<h3 style='margin-bottom:15px;'>Reportes Analíticos</h3>", unsafe_allow_html=True)
    
    if centro == "Administración":
        centro_seleccionado = st.selectbox("Filtrar reporte por centro barrial:", CENTROS, key="reportes_admin_select")
        df_c = df_asistencia[df_asistencia["centro"] == centro_seleccionado].copy() if not df_asistencia.empty else pd.DataFrame()
    else:
        df_c = df_asistencia[df_asistencia["centro"] == centro].copy() if not df_asistencia.empty else pd.DataFrame()
        centro_seleccionado = centro
    
    if df_c.empty:
        st.markdown("<div class='alert-box alert-gray'>Todavía no hay datos históricos suficientes en este centro para generar estadísticas.</div>", unsafe_allow_html=True)
        return
        
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"])
    df_c = df_c.sort_values("fecha_dt")

    avg_asistencia = df_c["presentes_i"].mean()
    record_concurrencia = df_c["presentes_i"].max()

    rc1, rc2 = st.columns(2)
    rc1.markdown(f"<div class='kpi'><h3>Promedio de Asistencia</h3><div class='v'>{avg_asistencia:.1f}</div><span style='font-size:0.75rem; color:var(--text-secondary);'>participantes / dia</span></div>", unsafe_allow_html=True)
    rc2.markdown(f"<div class='kpi'><h3>Récord Histórico</h3><div class='v'>{record_concurrencia}</div><span style='font-size:0.75rem; color:var(--text-secondary);'>Maxima concurrencia individual</span></div>", unsafe_allow_html=True)
    
    st.markdown("<br><hr style='opacity:0.1;'><br>", unsafe_allow_html=True)

    st.markdown("#### Evolución Temporal Concurrencia")
    df_linea = df_c.groupby("fecha")["presentes_i"].sum().reset_index()
    st.line_chart(df_linea.set_index("fecha")["presentes_i"], color="#60A5FA")

    if centro_seleccionado == C_MARANATHA:
        st.markdown("<br>#### Concurrencia Promedio por Taller / Espacio", unsafe_allow_html=True)
        df_espacio = df_c.groupby("espacio")["presentes_i"].mean().reset_index().sort_values("presentes_i", ascending=False)
        st.bar_chart(df_espacio.set_index("espacio")["presentes_i"], color="#A78BFA")

# ======================================================
# CONSOLE GLOBAL ADMIN (SUPERVISIÓN TOTAL DE ALEJANDRO)
# ======================================================
def page_global(df_asistencia, df_personas, df_ap):
    st.markdown("<h3 style='margin-bottom:15px;'>Consola Central Institucional</h3>", unsafe_allow_html=True)
    st.caption("Panel de control unificado de la federación para auditoría de cargas y métricas generales.")
    
    t_pers = len(df_personas["nombre"].unique()) if not df_personas.empty else 0
    t_asist = df_asistencia["presentes"].apply(lambda x: clean_int(x, 0)).sum() if not df_asistencia.empty else 0
    
    k1, k2 = st.columns(2)
    k1.markdown(f"<div class='kpi'><h3>Padrón Total Institucional</h3><div class='v'>{t_pers}</div><span style='font-size:0.75rem; color:var(--text-secondary);'>Personas en la federación</span></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3>Total de Asistencias</h3><div class='v'>{t_asist}</div><span style='font-size:0.75rem; color:var(--text-secondary);'>Ingresos totales acumulados</span></div>", unsafe_allow_html=True)
    
    st.markdown("<br>#### Auditoría y Estado de Cargas en los Centros", unsafe_allow_html=True)
    
    # Tabla de auditoría en tiempo real para verificar qué sube cada coordinador
    if not df_asistencia.empty:
        df_audit = df_asistencia.copy().sort_values("created_at", ascending=False)
        df_audit_clean = df_audit[["fecha", "centro", "espacio", "presentes", "coordinador", "modo"]].rename(
            columns={"fecha": "Fecha", "centro": "Centro Barrial", "espacio": "Espacio", "presentes": "Asistentes", "coordinador": "Responsable", "modo": "Estado del Día"}
        )
        st.dataframe(df_audit_clean, use_container_width=True, hide_index=True)
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
    
    if centro != "Administración":
        centro_clean = clean_string(centro)
        match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
        if not match_centro:
            st.error(f"Error: El centro '{centro}' no está mapeado.")
            st.stop()
        centro = match_centro

    show_top_header(nombre, centro)
    df_asistencia, df_personas, df_ap, df_seg = load_all_data_supabase()

    list_tabs = ["Inicio", "Legajos", "Alta", "Reportes"]
    if centro == "Administración" or u.lower() == "admin": 
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
