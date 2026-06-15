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
}
.kpi h3 { margin: 0; font-size: 0.6rem; color: var(--text-secondary) !important; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary) !important; line-height: 1; margin-top: 5px; }

/* MINI CONTROLADOR DE TALLERES (ESTILO SEMÁFORO GEOMÉTRICO) */
.workshop-status-container {
    background: #1E1E1E;
    border-radius: 18px;
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

.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; }
.alert-danger { background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.3); }
.alert-success { background-color: rgba(34, 197, 94, 0.15); color: #86EFAC !important; border: 1px solid rgba(34, 197, 94, 0.3); }
.alert-warning { background-color: rgba(245, 158, 11, 0.15); color: #FDE047 !important; border: 1px solid rgba(245, 158, 11, 0.3); }
.alert-gray { background-color: var(--surface); color: var(--text-secondary) !important; border: 1px solid rgba(255,255,255,0.05); }

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

/* BOTÓN DE WHATSAPP DIRECTO */
.btn-wa {
    display: block; text-align: center; background-color: #25D366 !important; color: white !important;
    padding: 10px; border-radius: var(--radius-sm); text-decoration: none; font-weight: 700; font-size: 0.9rem; margin-top: 10px;
}

/* MENÚ FLOTANTE ELEVADO */
.stTabs [data-baseweb="tab-list"] {
    position: fixed; bottom: 50px !important; left: 15px !important; right: 15px !important;
    background-color: rgba(30, 30, 30, 0.95) !important; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 20px !important; display: flex; justify-content: space-around; padding: 8px 5px !important; z-index: 999999 !important; box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
}
.stTabs [data-baseweb="tab"] {
    flex-grow: 1; text-align: center; justify-content: center; font-size: 0.65rem !important; font-weight: 700; color: var(--text-secondary) !important; padding: 10px 0; border: none !important; background: transparent !important;
}
.stTabs [aria-selected="true"] { color: var(--primary) !important; background-color: rgba(96, 165, 250, 0.12) !important; border-radius: 14px; }
.stTabs [aria-selected="true"]::after { display: none; }

.note-card {
    background-color: var(--surface); border-left: 4px solid var(--secondary); padding: 12px 15px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; margin-bottom: 12px; border-top: 1px solid rgba(255,255,255,0.02); border-right: 1px solid rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);
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
# MAPEO ESTRUCTURADO DE TALLERES POR CENTRO BARRIAL
# ======================================================
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')

def get_today_ar(): return datetime.now(TZ_AR).date()

C_BELEN = "Calle Belén"
C_NUDO = "Nudo a Nudo"
C_MARANATHA = "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]

MAPEO_ESPACIOS = {
    C_MARANATHA: ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"],
    C_BELEN: ["General", "Comedor / Merendero", "Apoyo Escolar"],
    C_NUDO: ["General", "Comedor / Merendero", "Taller Recreativo"]
}

CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

def calculate_age(born):
    try:
        born = pd.to_datetime(born).date()
        today = get_today_ar()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except: return 0

def format_wa_number(phone): return re.sub(r'\D', '', str(phone))
def clean_string(s): return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip().upper() if isinstance(s, str) else ""
def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default

# ======================================================
# FLUJO DE DATOS CONEXIÓN REAL A SUPABASE
# ======================================================
@st.cache_data(ttl=5, show_spinner="Sincronizando...")
def load_all_data_supabase():
    try:
        res_a = supabase.table("asistencia_diaria").select("*").execute()
        res_p = supabase.table("personas").select("*").execute()
        res_ap = supabase.table("asistencia_personas").select("*").execute()
        res_seg = supabase.table("bitacora_seguimiento").select("*").execute()
        
        df_a = pd.DataFrame(res_a.data) if res_a.data else pd.DataFrame(columns=["fecha", "centro", "espacio", "presentes", "coordinador"])
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame(columns=["nombre", "centro", "domicilio", "activo", "dni", "fecha_nacimiento", "telefono", "etiquetas"])
        df_ap = pd.DataFrame(res_ap.data) if res_ap.data else pd.DataFrame(columns=["fecha", "centro", "espacio", "nombre", "estado"])
        df_seg = pd.DataFrame(res_seg.data) if res_seg.data else pd.DataFrame(columns=["fecha", "centro", "nombre_persona", "categoria", "observacion", "usuario_registro"])
        
        return df_a, df_p, df_ap, df_seg
    except Exception as e:
        st.error(f"Error de sincronización con la nube: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### HOGAR DE CRISTO BAHIA BLANCA")
    st.markdown("<p style='color:var(--text-secondary); font-size:0.9rem; margin-top:-10px; margin-bottom:25px;'>Ingreso de Coordinadores.</p>", unsafe_allow_html=True)
    
    with st.form("login_form_oficial"):
        u = st.text_input("Usuario", placeholder="Ej: guillermina").strip()
        p = st.text_input("Contraseña", type="password", placeholder="••••••••").strip()
        
        if st.form_submit_button("Ingresar al Sistema", use_container_width=True):
            if not u or not p: st.error("Completá ambos campos.")
            else:
                try:
                    query = supabase.table("usuarios").select("*").execute()
                    if query.data:
                        user_data = None
                        for row in query.data:
                            db_user = row.get("usuarios") or row.get("usuario")
                            if db_user and str(db_user).strip().lower() == u.lower():
                                user_data = row
                                break
                        if user_data and str(user_data["password_text"]) == p:
                            st.session_state.update({
                                "logged_in": True, "usuario": u, 
                                "centro_asignado": user_data["centro"].strip(), 
                                "nombre_visible": user_data["nombre_visible"]
                            })
                            st.rerun()
                        else: st.error("Credenciales incorrectas.")
                except Exception as e: st.error(f"Error: {e}")
    st.stop()

def show_top_header(nombre, centro):
    col_inf, col_out = st.columns([3, 1])
    with col_inf:
        st.markdown(f"""
        <div style='display:flex; align-items:center; gap:12px; background-color: var(--surface); padding: 10px 15px; border-radius: var(--radius-lg); border: 1px solid rgba(255,255,255,0.05);'>
            <div style='background-color: var(--primary); width: 35px; height: 35px; border-radius: 50%; display:flex; align-items:center; justify-content:center; color:black; font-weight:bold;'>
                {nombre[0].upper() if nombre else 'U'}
            </div>
            <div>
                <div class='user-info'>{nombre}</div>
                <div class='center-info'>{centro}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_out:
        if st.button("Salir"):
            st.session_state.clear()
            st.rerun()

# ======================================================
# PANEL CONTROLADOR CORREGIDO (EVITA TEXTO CRUDO HTML)
# ======================================================
def show_workshop_monitor(df_asistencia, centro_seleccionado):
    if centro_seleccionado == "Administración":
        return
        
    st.markdown("<h4 style='font-size:0.9rem; margin-bottom:10px; color:var(--text-secondary); text-transform:uppercase;'>Control de Carga por Talleres (Hoy)</h4>", unsafe_allow_html=True)
    
    hoy_str = get_today_ar().isoformat()
    talleres_definidos = MAPEO_ESPACIOS.get(centro_seleccionado, ["General"])
    
    df_hoy = df_asistencia[(df_asistencia["centro"] == centro_seleccionado) & (df_asistencia["fecha"] == hoy_str)]
    talleres_cargados = df_hoy["espacio"].unique() if not df_hoy.empty else []
    
    # ✅ SOLUCIÓN: Concatenación limpia pura para que Streamlit renderice el HTML sin confusiones
    html_monitor = "<div class='workshop-status-container'>"
    for t in talleres_definidos:
        if t in talleres_cargados:
            html_monitor += "<div class='workshop-row'><span class='workshop-name'>• " + str(t) + "</span><span class='workshop-badge badge-done'>Cargado</span></div>"
        else:
            html_monitor += "<div class='workshop-row'><span class='workshop-name'>• " + str(t) + "</span><span class='workshop-badge badge-pending'>Falta Cargar</span></div>"
    html_monitor += "</div>"
    
    st.markdown(html_monitor, unsafe_allow_html=True)

# ======================================================
# PESTAÑA: CARGA DIARIA POR TALLERES
# ======================================================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.markdown("<h3 style='margin-bottom:5px;'>Carga Diaria</h3>", unsafe_allow_html=True)
    
    if centro == "Administración":
        centro_seleccionado = st.selectbox("Seleccionar Centro Barrial:", CENTROS)
    else:
        centro_seleccionado = centro

    show_workshop_monitor(df_asistencia, centro_seleccionado)

    fecha = st.date_input("Fecha de trabajo", value=get_today_ar())
    fecha_str = fecha.isoformat()
    
    talleres_disponibles = MAPEO_ESPACIOS.get(centro_seleccionado, ["General"])
    
    col_e, col_m = st.columns(2)
    with col_e: espacio = st.selectbox("Taller / Espacio a cargar", talleres_disponibles)
    with col_m: modo = st.selectbox("Estado del Espacio", ["Día habitual", "Actividad especial", "No abrió / Suspendido"])
    
    notas = st.text_area("Notas generales del día (Opcional)", height=70, placeholder="Ej: Se trabajó herrería inicial con buena convocatoria.")

    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    df_activos = df_centro[df_centro["activo"].astype(str).str.upper() == "SI"] if not df_centro.empty else pd.DataFrame()
    nombres = sorted(list(set(df_activos["nombre"].astype(str).tolist()))) if not df_activos.empty else []
    
    st.markdown(f"#### Participantes del Centro ({len(nombres)})")
    presentes = st.multiselect("Marcar quiénes asistieron a este taller:", options=nombres, placeholder="Buscar y seleccionar...")
    total_presentes = len(presentes)
    
    st.markdown("<br>", unsafe_allow_html=True)
    forrar_reemplazo = st.checkbox("Corregir datos: tildar acá si estás re-subiendo o editando este taller específico.", value=False)
    
    if st.button("GUARDAR CARGA DEL TALLER", type="primary", use_container_width=True):
        if total_presentes <= 0 and modo == "Día habitual":
            st.error("Debes seleccionar asistentes o marcar el espacio como 'No abrió'.")
            return
            
        with st.spinner("Procesando en Supabase..."):
            try:
                if forzar_reemplazo:
                    supabase.table("asistencia_diaria").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                    supabase.table("asistencia_personas").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                
                cabecera = {
                    "fecha": fecha_str, "anio": str(fecha.year), "centro": centro_seleccionado,
                    "espacio": espacio, "presentes": total_presentes, "coordinador": nombre_visible,
                    "modo": modo, "notas": notas, "usuario": usuario, "accion": "append"
                }
                supabase.table("asistencia_diaria").insert(cabecera).execute()
                
                filas_personas = []
                for n in presentes:
                    filas_personas.append({
                        "fecha": fecha_str, "anio": str(fecha.year), "centro": centro_seleccionado,
                        "espacio": espacio, "nombre": n, "estado": "Presente", "es_nuevo": "NO",
                        "coordinador": nombre_visible, "usuario": usuario
                    })
                ausentes = [n for n in nombres if n not in presentes]
                for n in ausentes:
                    filas_personas.append({
                        "fecha": fecha_str, "anio": str(fecha.year), "centro": centro_seleccionado,
                        "espacio": espacio, "nombre": n, "estado": "Ausente", "es_nuevo": "NO",
                        "coordinador": nombre_visible, "usuario": usuario
                    })
                
                if filas_personas:
                    supabase.table("asistencia_personas").insert(filas_personas).execute()
                
                st.balloons()
                st.toast("Taller guardado de forma segura.")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
                
            except Exception as e:
                err_str = str(e)
                if "23505" in err_str or "already exists" in err_str.lower():
                    st.markdown(f"""
                    <div class='alert-box alert-warning'>
                        <b>Taller ya registrado hoy:</b> Ya se guardó la asistencia de '{espacio}' para la fecha elegida.<br><br>
                        <b>¿Querés modificarla?</b> Tildá la casilla de "Corregir datos" de arriba y volvé a presionar el botón.
                    </div>
                    """, unsafe_allow_html=True)
                else: st.error(f"Error: {e}")

# ======================================================
# PESTAÑA: BUSCADOR DE LEGAJOS Y BITÁCORA
# ======================================================
def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Legajos</h3>", unsafe_allow_html=True)
    
    if centro == "Administración":
        centro_seleccionado = st.selectbox("Filtrar padrón por centro barrial:", CENTROS, key="padrón_admin_select")
    else:
        centro_seleccionado = centro

    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    nombres = sorted(df_centro["nombre"].unique().tolist()) if not df_centro.empty else []

    seleccion = st.selectbox("Buscar participante:", [""] + nombres)
    
    if not seleccion:
        if not df_centro.empty:
            st.markdown("#### Padrón de la Comunidad")
            df_mostrar = df_centro[df_centro["activo"].astype(str).str.upper() == "SI"]
            st.dataframe(df_mostrar[["nombre", "dni", "telefono"]].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    tags_str = str(datos_persona.get("etiquetas", ""))
    telefono = str(datos_persona.get("telefono", ""))
    
    is_active = str(datos_persona.get("activo")).upper() != "NO"
    status_class = "status-active" if is_active else "status-inactive"
    status_text = "• Activo" if is_active else "• Inactivo"
    
    dni_val = str(datos_persona.get('dni', '')).strip()
    dni_val = "S/D" if (not dni_val or dni_val.lower() == 'none') else dni_val
    
    nac_val = str(datos_persona.get('fecha_nacimiento', '')).strip()
    nacimiento_mostrar = "S/D" if (not nac_val or nac_val.lower() == 'none') else f"{nac_val} ({calculate_age(nac_val)} años)"
    
    direccion_mostrar = str(datos_persona.get('domicilio','')).strip()
    if not direccion_mostrar or direccion_mostrar.lower() == 'none': direccion_mostrar = "No registrada"

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
                <span class="profile-meta-label">Dirección</span>
                <span class="profile-meta-value">{direccion_mostrar}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if tags_str and tags_str.lower() not in ["none", "nan", ""]:
        st.markdown(f"""
        <div class="profile-footer-data">
            <span class="profile-meta-label" style="font-size:0.55rem; opacity:0.8;">Datos Familiares / Referencia</span>
            <div style="font-size:0.85rem; font-weight:600; color:var(--text-primary); margin-top:2px;">{tags_str}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if telefono and telefono.lower() != "none":
        st.markdown(f"<a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>Enviar WhatsApp</a>", unsafe_allow_html=True)

    st.markdown("<br>### Registrar Intervención en Bitácora", unsafe_allow_html=True)
    with st.form("form_bitacora_seguimiento", clear_on_submit=True):
        f_nota = st.date_input("Fecha", value=get_today_ar())
        cat_nota = st.selectbox("Categoría", CATEGORIAS_SEGUIMIENTO)
        obs_nota = st.text_area("Observaciones de la intervención")
        
        if st.form_submit_button("Guardar en Bitácora", use_container_width=True):
            if obs_nota.strip():
                try:
                    supabase.table("bitacora_seguimiento").insert({
                        "fecha": f_nota.isoformat(), "anio": str(f_nota.year), "centro": centro_seleccionado,
                        "nombre_persona": seleccion, "categoria": cat_nota, "observacion": obs_nota.strip(), "usuario_registro": usuario
                    }).execute()
                    st.toast("Intervención guardada.")
                    time.sleep(0.5)
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    df_chico = df_seg[df_seg["nombre_persona"] == seleccion].copy() if not df_seg.empty else pd.DataFrame()
    if not df_chico.empty:
        st.markdown("#### Historial Clínico / Institucional")
        for _, row in df_chico.sort_values("fecha", ascending=False).iterrows():
            st.markdown(f"""
            <div class='note-card'>
                <div style='display:flex; justify-content:space-between; font-size:0.7rem; color:var(--text-secondary);'>
                    <span><b>{row['fecha']}</b> — {row['categoria']}</span>
                    <span>Por: {row['usuario_registro']}</span>
                </div>
                <div style='font-size:0.9rem; margin-top:5px;'>{row['observacion']}</div>
            </div>
            """, unsafe_allow_html=True)

# ======================================================
# PESTAÑA: ALTA DE PERSONA
# ======================================================
def page_alta_persona(df_personas, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Alta al Padrón</h3>", unsafe_allow_html=True)
    
    if centro == "Administración":
        centro_destino = st.selectbox("Asignar al centro:", CENTROS, key="alta_admin_select")
    else: centro_destino = centro

    with st.form("alta_directa_form"):
        new_nom = st.text_input("Nombre Completo *")
        new_dni = st.text_input("DNI")
        new_nac = st.text_input("Fecha Nacimiento (AAAA-MM-DD)")
        new_tel = st.text_input("Teléfono")
        new_dom = st.text_input("Dirección / Referencia de Vivienda")
        new_etq = st.text_input("Familiares / Referentes (Etiquetas)")
        
        if st.form_submit_button("Ingresar Legajo", type="primary", use_container_width=True):
            if new_nom.strip():
                try:
                    supabase.table("personas").insert({
                        "nombre": new_nom.strip(), "dni": new_dni.strip() if new_dni.strip() else None,
                        "fecha_nacimiento": new_nac.strip() if new_nac.strip() else None, "telefono": new_tel.strip() if new_tel.strip() else None,
                        "domicilio": new_dom.strip() if new_dom.strip() else None, "etiquetas": new_etq.strip() if new_etq.strip() else None,
                        "activo": "SI", "centro": centro_destino, "usuario_alta": usuario
                    }).execute()
                    st.success("Ingresado con éxito.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

def page_reportes(df_asistencia, centro):
    st.markdown("<h3 style='margin-bottom:15px;'>Estadísticas de Asistencia</h3>", unsafe_allow_html=True)
    
    centro_sel = st.selectbox("Filtrar por centro:", CENTROS) if centro == "Administración" else centro
    
    df_c = df_asistencia[df_asistencia["centro"] == centro_sel].copy() if not df_asistencia.empty else pd.DataFrame()
    if df_c.empty:
        st.info("Sin registros históricos para este centro.")
        return
        
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    
    st.markdown("#### Promedio de Asistentes por Taller / Espacio")
    df_taller = df_c.groupby("espacio")["presentes_i"].mean().reset_index().sort_values("presentes_i", ascending=False)
    st.bar_chart(df_taller.set_index("espacio")["presentes_i"], color="#60A5FA")

# ======================================================
# CONSOLE GLOBAL ADMIN
# ======================================================
def page_global(df_asistencia, df_personas):
    st.markdown("<h3 style='margin-bottom:15px;'>Consola Central Federación</h3>", unsafe_allow_html=True)
    
    hoy_str = get_today_ar().isoformat()
    
    st.markdown("#### Estado de carga de Talleres hoy:")
    for c in CENTROS:
        df_c = df_asistencia[(df_asistencia["centro"] == c) & (df_asistencia["fecha"] == hoy_str)]
        cargados = df_c["espacio"].tolist() if not df_c.empty else []
        definidos = MAPEO_ESPACIOS.get(c, ["General"])
        
        faltan = [t for t in definidos if t not in cargados]
        if not faltan:
            st.markdown(f"✅ **{c}**: Todos los talleres cargados.")
        else:
            st.markdown(f"⚠️ **{c}**: Falta cargar -> *{', '.join(faltan)}*")

    st.markdown("<br>#### Registro Completo de Cargas Recientes", unsafe_allow_html=True)
    if not df_asistencia.empty:
        st.dataframe(df_asistencia[["fecha", "centro", "espacio", "presentes", "coordinador"]].sort_values("fecha", ascending=False), use_container_width=True, hide_index=True)

# ======================================================
# CONTROLADOR PRINCIPAL
# ======================================================
def main():
    if not st.session_state.get("logged_in"): show_login_screen()
    
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]
    
    show_top_header(nombre, centro)
    df_asistencia, df_personas, df_ap, df_seg = load_all_data_supabase()

    list_tabs = ["Inicio", "Legajos", "Alta", "Reportes"]
    if centro == "Administración" or u.lower() == "admin": list_tabs.append("Global")
    
    tabs = st.tabs(list_tabs)
    
    with tabs[0]: page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
    with tabs[1]: page_personas_full(df_personas, df_ap, df_seg, centro, u)
    with tabs[2]: page_alta_persona(df_personas, centro, u)
    with tabs[3]: page_reportes(df_asistencia, centro)
    if "Global" in list_tabs and len(tabs) > 4:
        with tabs[4]: page_global(df_asistencia, df_personas)

if __name__ == "__main__":
    main()
