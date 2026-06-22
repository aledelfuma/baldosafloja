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

.profile-card { background-color: var(--surface); border-radius: var(--radius-lg); padding: 20px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 20px; }
.profile-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px; margin-bottom: 15px; }
.profile-institution { font-size: 0.65rem; font-weight: 700; letter-spacing: 1px; color: var(--primary); text-transform: uppercase; }
.profile-status { font-size: 0.75rem; font-weight: 600; }
.status-active { color: #86EFAC; }
.status-inactive { color: #FCA5A5; }
.profile-name { font-size: 1.4rem; font-weight: 800; line-height: 1.1; margin-top: 2px; color: var(--text-primary); }
.profile-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }
.profile-meta-item { display: flex; flex-direction: column; }
.profile-meta-label { font-size: 0.65rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
.profile-meta-value { font-size: 0.95rem; font-weight: 600; color: var(--text-primary); }
.profile-footer-data { background-color: rgba(0, 0, 0, 0.15); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.03); }

.stTabs [data-baseweb="tab-list"] { position: fixed; bottom: 50px !important; left: 15px !important; right: 15px !important; background-color: rgba(30, 30, 30, 0.95) !important; backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 20px !important; display: flex; justify-content: space-around; padding: 8px 5px !important; z-index: 999999 !important; box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important; }
.stTabs [data-baseweb="tab"] { flex-grow: 1; text-align: center; justify-content: center; font-size: 0.65rem !important; font-weight: 700; color: var(--text-secondary) !important; padding: 10px 0; border: none !important; background: transparent !important; }
.stTabs [aria-selected="true"] { color: var(--primary) !important; background-color: rgba(96, 165, 250, 0.12) !important; border-radius: 14px; }
.note-card { background-color: var(--surface); border-left: 4px solid var(--secondary); padding: 12px 15px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.02); }
.btn-wa { display: block; text-align: center; background-color: #25D366 !important; color: white !important; padding: 10px; border-radius: var(--radius-sm); text-decoration: none; font-weight: 700; font-size: 0.9rem; margin-top: 10px; }
.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONEXIÓN SEGURA A SUPABASE
# ======================================================
@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = get_supabase_client()
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')
def get_today_ar(): return datetime.now(TZ_AR).date()

# ======================================================
# METADATOS COMPLETA DE CALENDARIO DIARIO
# ======================================================
C_BELEN = "Calle Belén"
C_NUDO = "Nudo a Nudo"
C_MARANATHA = "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]

CALENDARIO_MARANATHA = {
    0: ["Taller Costura CFP", "Apoyo sec.", "Plan FinEs", "General"],
    1: ["Taller de Arte", "La Ronda", "Plan FinEs", "General"],
    2: ["Taller Costura CFP", "Apoyo sec.", "General"],
    3: ["Apoyo Esc. Primario", "Almuerzo", "Fútbol Calle Belén", "Espacio Joven", "General"],
    4: ["Pre-Juvenil", "Plan FinEs", "General"],
    5: ["General"],
    6: ["General"]
}
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

def calculate_age(born):
    try:
        born = pd.to_datetime(born).date()
        return get_today_ar().year - born.year - ((get_today_ar().month, get_today_ar().day) < (born.month, born.day))
    except: return 0

def format_wa_number(phone): return re.sub(r'\D', '', str(phone))
def clean_string(s): return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip().upper() if isinstance(s, str) else ""
def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default
def year_of(f_iso):
    try: return str(pd.to_datetime(f_iso).year)
    except: return str(get_today_ar().year)

# ======================================================
# CORE DE CARGA DE BASE DE DATOS
# ======================================================
@st.cache_data(ttl=10, show_spinner="Sincronizando...")
def load_all_data_supabase():
    try:
        res_a = supabase.table("asistencia_diaria").select("*").execute()
        res_p = supabase.table("personas").select("*").execute()
        res_ap = supabase.table("asistencia_personas").select("*").execute()
        res_seg = supabase.table("bitacora_seguimiento").select("*").execute()
        return pd.DataFrame(res_a.data), pd.DataFrame(res_p.data), pd.DataFrame(res_ap.data), pd.DataFrame(res_seg.data)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def latest_asistencia(df):
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["created_at"], errors="coerce")
    df2["k"] = (df2["anio"].astype(str)+"|"+df2["fecha"].astype(str)+"|"+df2["centro"].astype(str)+"|"+df2["espacio"].astype(str))
    return df2.sort_values("timestamp_dt").groupby("k", as_index=False).tail(1)

def get_today_asistencia_summary(df_a):
    if df_a.empty: return df_a.copy()
    hoy_str = get_today_ar().isoformat()
    d = df_a[df_a["fecha"] == hoy_str].copy()
    if d.empty: return d.copy()
    d["timestamp_dt"] = pd.to_datetime(d["created_at"], errors="coerce")
    return d.sort_values("timestamp_dt").groupby(["centro", "espacio"]).tail(1)

def filter_personas_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    if centro in ["Administración", "coordinacion"]: return df_personas.copy()
    centro_clean = clean_string(centro)
    df_temp = df_personas.copy()
    df_temp['centro_norm'] = df_temp['centro'].apply(clean_string)
    return df_temp[df_temp['centro_norm'] == centro_clean].copy()

# ======================================================
# COMPONENTES VISUALES INTERACTIVOS
# ======================================================
def show_login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### HOGAR DE CRISTO BAHIA BLANCA")
    with st.form("login_form_oficial"):
        u = st.text_input("Usuario", placeholder="Ej: rozeta").strip()
        p = st.text_input("Contraseña", type="password", placeholder="••••••••").strip()
        if st.form_submit_button("Ingresar al Sistema", use_container_width=True):
            try:
                query = supabase.table("usuarios").select("*").execute()
                for row in query.data:
                    db_user = row.get("usuario") or row.get("usuarios")
                    if db_user and str(db_user).strip().lower() == u.lower() and str(row.get("password_text")) == p:
                        st.session_state.update({"logged_in": True, "usuario": u, "centro_asignado": row["centro"].strip(), "nombre_visible": row["nombre_visible"]})
                        st.rerun()
                st.error("Credenciales incorrectas.")
            except Exception as e: st.error(f"Error: {e}")
    st.stop()

def show_top_header(nombre, centro):
    col_inf, col_out = st.columns([3, 1])
    with col_inf:
        st.markdown(f"<div class='top-bar'><div class='user-info'>{nombre}</div><div class='center-info'>Centro: {centro}</div></div>", unsafe_allow_html=True)
    with col_out:
        if st.button("Salir"): st.session_state.clear(); st.rerun()

def show_workshop_monitor(df_asistencia, centro_seleccionado, fecha_seleccionada):
    if centro_seleccionado != C_MARANATHA: return
    st.markdown("<h4 style='font-size:0.9rem; margin-bottom:10px; color:var(--text-secondary); text-transform:uppercase;'>Estado del Calendario (Hoy)</h4>", unsafe_allow_html=True)
    fecha_iso = fecha_seleccionada.isoformat()
    actividades = CALENDARIO_MARANATHA.get(fecha_seleccionada.weekday(), ["General"])
    df_hoy = df_asistencia[(df_asistencia["centro"] == centro_seleccionado) & (df_asistencia["fecha"] == fecha_iso)]
    cargados = df_hoy["espacio"].unique() if not df_hoy.empty else []
    
    html = "<div class='workshop-status-container'>"
    for t in actividades:
        badge = "badge-done'>(Cargado)" if t in cargados else "badge-pending'>(Pendiente)"
        html += f"<div class='workshop-row'><span class='workshop-name'>• {t}</span><span class='workshop-{badge}</span></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def show_top_alerts(df_latest, df_personas, df_ap, centro):
    if centro in ["Administración", "coordinacion"]: return
    df_c = filter_personas_centro(df_personas, centro)
    df_c_act = df_c[df_c["activo"].astype(str).str.upper() == "SI"] if not df_c.empty else pd.DataFrame()
    cumples, alertas = [], []
    today = get_today_ar()
    
    if not df_c_act.empty:
        for _, row in df_c_act.iterrows():
            fn = pd.to_datetime(str(row.get("fecha_nacimiento")), errors="coerce")
            if not pd.isna(fn) and fn.month == today.month and fn.day == today.day: cumples.append(row["nombre"])
        if not df_ap.empty:
            ultimas = sorted(df_ap["fecha"].unique(), reverse=True)[:4]
            if len(ultimas) >= 3:
                for p in df_c_act["nombre"].unique():
                    asist = df_ap[(df_ap["nombre"] == p) & (df_ap["fecha"].isin(ultimas))]
                    if len(asist) >= 3 and (asist["estado"] == "Ausente").all(): alertas.append(p)

    ac1, ac2, ac3 = st.columns(3)
    ac1.markdown("<div class='alert-box alert-success'>Sincronizado</div>", unsafe_allow_html=True)
    with ac2:
        if cumples: st.expander(f"Cumpleaños ({len(cumples)})", expanded=True).write(cumples)
        else: st.markdown("<div class='alert-box alert-gray'>Sin cumpleaños</div>", unsafe_allow_html=True)
    with ac3:
        if alertas: st.expander(f"Ausencias ({len(alertas)})", expanded=True).write(alertas)
        else: st.markdown("<div class='alert-box alert-gray'>Sin alertas</div>", unsafe_allow_html=True)

def kpi_row_full(df_asistencia, centro):
    hoy = get_today_ar()
    hace_7 = hoy - timedelta(days=6)
    ini_mes = hoy.replace(day=1)
    c1 = c2 = c3 = 0
    if not df_asistencia.empty:
        df_k = df_asistencia.copy()
        df_k["presentes_i"] = df_k["presentes"].apply(lambda x: clean_int(x, 0))
        df_k["f_dt"] = pd.to_datetime(df_k["fecha"]).dt.date
        df_centro = df_k if centro in ["Administración", "coordinacion"] else df_k[df_k["centro"] == centro]
        c1 = int(df_centro[df_centro["f_dt"] == hoy]["presentes_i"].sum())
        c2 = int(df_centro[(df_centro["f_dt"] >= hace_7) & (df_centro["f_dt"] <= hoy)]["presentes_i"].sum())
        c3 = int(df_centro[(df_centro["f_dt"] >= ini_mes) & (df_centro["f_dt"] <= hoy)]["presentes_i"].sum())
    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><h3>Mes Actual</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)

# ======================================================
# GESTIÓN OPERATIVA DE PESTAÑAS
# ======================================================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Carga Diaria</h3>", unsafe_allow_html=True)
    centro_seleccionado = st.selectbox("Centro a gestionar:", CENTROS) if centro in ["Administración", "coordinacion"] else centro
    fecha = st.date_input("Fecha de carga", value=get_today_ar())
    fecha_str = fecha.isoformat()
    
    show_workshop_monitor(df_asistencia, centro_seleccionado, fecha)
    
    col_e, col_m = st.columns(2)
    with col_e:
        if centro_seleccionado == C_MARANATHA:
            espacio = st.selectbox("Actividad del Taller", CALENDARIO_MARANATHA.get(fecha.weekday(), ["General"]))
        else:
            espacio = DEFAULT_ESPACIO
            st.info(f"Carga: {espacio}")
    with col_m:
        modo = st.selectbox("Modo / Actividad", ["Día habitual", "Actividad especial", "Cerrado"])
        
    notas = st.text_area("Notas generales", height=70)
    df_c = filter_personas_centro(df_personas, centro_seleccionado)
    df_act = df_c[df_c["activo"].astype(str).str.upper() == "SI"] if not df_c.empty else pd.DataFrame()
    nombres = sorted(list(set(df_act["nombre"].astype(str).tolist()))) if not df_act.empty else []
    
    presentes = st.multiselect("Marcar Asistencia", options=nombres)
    forrar_reemplazo = st.checkbox("Corregir datos (Sobreescribir)", value=False)
    
    if st.button("GUARDAR CARGA", type="primary", use_container_width=True):
        if len(presentes) <= 0 and modo != "Cerrado":
            st.error("Marque asistentes o asigne el modo Cerrado.")
            return
        with st.spinner("Guardando..."):
            try:
                st.cache_data.clear()
                if forrar_reemplazo:
                    supabase.table("asistencia_diaria").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                    supabase.table("asistencia_personas").delete().eq("fecha", fecha_str).eq("centro", centro_seleccionado).eq("espacio", espacio).execute()
                
                supabase.table("asistencia_diaria").insert({
                    "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado, "espacio": espacio,
                    "presentes": len(presentes), "coordinador": nombre_visible, "modo": modo, "notas": notas, "usuario": usuario, "accion": "replaced" if forrar_reemplazo else "append"
                }).execute()
                
                if presentes:
                    filas = [{"fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado, "espacio": espacio, "nombre": n, "estado": "Presente", "coordinador": nombre_visible, "usuario": usuario} for n in presentes]
                    for aus in [x for x in nombres if x not in presentes]:
                        filas.append({"fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro_seleccionado, "espacio": espacio, "nombre": aus, "estado": "Ausente", "coordinador": nombre_visible, "usuario": usuario})
                    supabase.table("asistencia_personas").insert(filas).execute()
                st.balloons(); st.toast("Guardado de forma exitosa"); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Error: {e}")

def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>Buscador de Legajos</h3>", unsafe_allow_html=True)
    centro_seleccionado = st.selectbox("Filtrar padrón por centro barrial:", CENTROS, key="pad_sel") if centro in ["Administración", "coordinacion"] else centro
    df_centro = filter_personas_centro(df_personas, centro_seleccionado)
    nombres = sorted(df_centro["nombre"].unique().tolist()) if not df_centro.empty else []
    seleccion = st.selectbox("Escribi el nombre para ver la ficha:", [""] + nombres)
    
    if not seleccion:
        if not df_centro.empty:
            df_m = df_centro[df_centro["activo"].astype(str).str.upper() == "SI"]
            st.dataframe(df_m[["nombre", "dni", "telefono"]].sort_values("nombre"), use_container_width=True, hide_index=True)
        return
        
    d_p = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    is_active = str(d_p.get("activo")).upper() != "NO"
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-header">
            <div><span class="profile-institution">Hogar de Cristo</span><div class="profile-name">{seleccion}</div></div>
            <span class="profile-status text-{"green" if is_active else "red"}-500">{"• Activo" if is_active else "• Inactivo"}</span>
        </div>
        <div class="profile-grid">
            <div class="profile-meta-item"><span class="profile-meta-label">Documento</span><span class="profile-meta-value">{d_p.get('dni','S/D')}</span></div>
            <div class="profile-meta-item"><span class="profile-meta-label">Edad</span><span class="profile-meta-value">{calculate_age(d_p.get('fecha_nacimiento'))} años</span></div>
            <div class="profile-meta-item" style="grid-column: span 2;"><span class="profile-meta-label">Dirección</span><span class="profile-meta-value">{d_p.get('domicilio','No registrada')}</span></div>
        </div>
    """, unsafe_allow_html=True)
    if str(d_p.get('etiquetas')) not in ["none","nan",""]: st.markdown(f"<div class='profile-footer-data'><span class='profile-meta-label'>Referencia</span><div>{d_p.get('etiquetas')}</div></div></div>", unsafe_allow_html=True)
    else: st.markdown("</div>", unsafe_allow_html=True)
    
    if d_p.get('telefono'): st.markdown(f"<a href='https://wa.me/{format_wa_number(d_p.get('telefono'))}' target='_blank' class='btn-wa'>WhatsApp</a>", unsafe_allow_html=True)

    with st.form("form_seg"):
        c_n = st.selectbox("Categoría", CATEGORIAS_SEGUIMIENTO)
        o_n = st.text_area("Observación")
        if st.form_submit_button("Guardar en Bitácora"):
            st.cache_data.clear()
            supabase.table("bitacora_seguimiento").insert({"fecha": get_today_ar().isoformat(), "anio": year_of(get_today_ar().isoformat()), "centro": centro_seleccionado, "nombre_persona": seleccion, "categoria": c_n, "observacion": o_n.strip(), "usuario_registro": usuario}).execute()
            st.toast("Intervención guardada"); time.sleep(0.5); st.rerun()

    df_ch = df_seg[df_seg["nombre_persona"] == seleccion].copy() if not df_seg.empty else pd.DataFrame()
    if not df_ch.empty:
        for _, row in df_ch.sort_values("fecha", ascending=False).iterrows():
            st.markdown(f"<div class='note-card'><div><b>{row['fecha']}</b> - {row['categoria']} (Por: {row['usuario_registro']})</div><div style='margin-top:5px;'>{row['observacion']}</div></div>", unsafe_allow_html=True)

def page_alta_persona(df_personas, centro, usuario):
    st.markdown("### Alta al Padrón")
    c_dest = st.selectbox("Centro destino:", CENTROS) if centro in ["Administración", "coordinacion"] else centro
    with st.form("alta_f"):
        nom = st.text_input("Nombre Completo *")
        dni = st.text_input("DNI")
        nac = st.text_input("Nacimiento (AAAA-MM-DD)")
        tel = st.text_input("Teléfono")
        dom = st.text_input("Dirección")
        etq = st.text_input("Familiares / Referencias")
        not_p = st.text_area("Notas")
        if st.form_submit_button("Registrar Legajo"):
            if nom.strip():
                st.cache_data.clear()
                # ✅ SOLUCIÓN AL SYNTAXERROR: Extraemos la fecha limpia antes de meterla en el diccionario plano
                fecha_nac_final = nac.strip() if nac.strip() else None
                
                supabase.table("personas").insert({
                    "nombre": nom.strip(), 
                    "dni": dni.strip() if dni.strip() else None, 
                    "fecha_nacimiento": fecha_nac_final, 
                    "telefono": tel.strip() if tel.strip() else None, 
                    "domicilio": dom.strip() if dom.strip() else None, 
                    "etiquetas": etq.strip() if etq.strip() else None, 
                    "notes": not_p.strip() if not_p.strip() else None, 
                    "activo": "SI", 
                    "centro": c_dest, 
                    "usuario_alta": usuario
                }).execute()
                st.success("Alta dada de forma exitosa"); time.sleep(0.5); st.rerun()

def page_reportes(df_asistencia, centro):
    st.markdown("### Métricas Avanzadas Comparativas")
    c_sel = st.selectbox("Centro reporte:", CENTROS, key="rep_c") if centro in ["Administración", "coordinacion"] else centro
    df_c = df_asistencia[df_asistencia["centro"] == c_sel].copy() if not df_asistencia.empty else pd.DataFrame()
    if df_c.empty: return
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c["f_str"] = df_c["fecha"].astype(str)
    
    hoy = get_today_ar()
    sem_act, sem_ant = hoy - timedelta(days=6), hoy - timedelta(days=13)
    mes_act, mes_ant = hoy.replace(day=1), (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    s_act = df_c[(df_c["f_str"] >= sem_act.isoformat()) & (df_c["f_str"] <= hoy.isoformat())]["presentes_i"].sum()
    s_ant = df_c[(df_c["f_str"] >= sem_ant.isoformat()) & (df_c["f_str"] < sem_act.isoformat())]["presentes_i"].sum()
    m_act = df_c[(df_c["f_str"] >= mes_act.isoformat()) & (df_c["f_str"] <= hoy.isoformat())]["presentes_i"].sum()
    m_ant = df_c[(df_c["f_str"] >= mes_ant.isoformat()) & (df_c["f_str"] < mes_act.isoformat())]["presentes_i"].sum()
    
    w_pct = ((s_act - s_ant) / s_ant * 100) if s_ant > 0 else 0.0
    m_pct = ((m_act - m_ant) / m_ant * 100) if m_ant > 0 else 0.0
    
    col1, col2 = st.columns(2)
    col1.markdown(f"<div class='kpi'><h3>Semana vs Anterior (WoW)</h3><div class='v'>{s_act} <span style='font-size:0.9rem; color:{'#86EFAC' if w_pct>=0 else '#FCA5A5'};'>({w_pct:+.1f}%)</span></div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi'><h3>Mes vs Anterior (MoM)</h3><div class='v'>{m_act} <span style='font-size:0.9rem; color:{'#86EFAC' if m_pct>=0 else '#FCA5A5'};'>({m_pct:+.1f}%)</span></div></div>", unsafe_allow_html=True)
    
    st.line_chart(df_c.groupby("fecha")["presentes_i"].sum(), color="#60A5FA")
    df_c["dia"] = pd.to_datetime(df_c["fecha"]).dt.day_name().map({'Monday':'Lunes','Tuesday':'Martes','Wednesday':'Miércoles','Thursday':'Jueves','Friday':'Viernes','Saturday':'Sábado','Sunday':'Domingo'})
    st.bar_chart(df_c.groupby("dia")["presentes_i"].mean().reindex(['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']), color="#A78BFA")

def page_global(df_asistencia, df_personas, df_ap):
    st.markdown("### Consola Central de Control")
    hoy_str = get_today_ar().isoformat()
    sc1, sc2, sc3 = st.columns(3)
    sc1.markdown(f"<div class='alert-box alert-{'success' if not df_asistencia[(df_asistencia['centro']==C_BELEN)&(df_asistencia['fecha']==hoy_str)].empty else 'danger'}'>Calle Belén</div>", unsafe_allow_html=True)
    sc2.markdown(f"<div class='alert-box alert-{'success' if not df_asistencia[(df_asistencia['centro']==C_MARANATHA)&(df_asistencia['fecha']==hoy_str)].empty else 'danger'}'>Casa Maranatha</div>", unsafe_allow_html=True)
    sc3.markdown(f"<div class='alert-box alert-{'success' if not df_asistencia[(df_asistencia['centro']==C_NUDO)&(df_asistencia['fecha']==hoy_str)].empty else 'danger'}'>Nudo a Nudo</div>", unsafe_allow_html=True)
    st.dataframe(df_asistencia[["fecha", "centro", "espacio", "presentes", "coordinador", "modo", "accion"]].sort_values("fecha", ascending=False), use_container_width=True, hide_index=True)

# ======================================================
# CONTROLADOR PRINCIPAL DEL SISTEMA
# ======================================================
def main():
    if not st.session_state.get("logged_in"): show_login_screen()
    u, centro, nombre = st.session_state["usuario"], st.session_state["centro_asignado"], st.session_state["nombre_visible"]
    
    if centro not in ["Administración", "coordinacion"]:
        centro = next((c for c in CENTROS if clean_string(c) == clean_string(centro)), CENTROS[0])
        
    show_top_header(nombre, centro)
    df_a, df_p, df_ap, df_seg = load_all_data_supabase()
    
    list_tabs = ["Inicio", "Legajos", "Alta", "Reportes"]
    if centro in ["Administración", "coordinacion"] or u.lower() == "admin": list_tabs.append("Global")
    tabs = st.tabs(list_tabs)
    
    with tabs[0]:
        show_top_alerts(latest_asistencia(df_a), df_p, df_ap, centro)
        kpi_row_full(df_a, centro)
        st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
        page_registrar_asistencia(df_p, df_a, centro, nombre, u)
    with tabs[1]: page_personas_full(df_p, df_ap, df_seg, centro, u)
    with tabs[2]: page_alta_persona(df_p, centro, u)
    with tabs[3]: page_reportes(df_a, centro)
    if "Global" in list_tabs:
        with tabs[4]: page_global(df_a, df_p, df_ap)

if __name__ == "__main__": main()
