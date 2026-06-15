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
# 🔄 FLUJO DE DATOS CONEXIÓN REAL A SUPABASE
# ======================================================
@st.cache_data(ttl=10, show_spinner="Sincronizando con Supabase...")
def load_all_data_supabase():
    try:
        # LECTURAS REALES DIRECTAS DESDE SUPABASE
        res_a = supabase.table("asistencia_diaria").select("*").execute()
        res_p = supabase.table("personas").select("*").execute()
        res_ap = supabase.table("asistencia_personas").select("*").execute()
        
        df_a = pd.DataFrame(res_a.data) if res_a.data else pd.DataFrame(columns=["created_at", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"])
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame(columns=["nombre", "centro", "domicilio", "notas", "activo", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"])
        df_ap = pd.DataFrame(res_ap.data) if res_ap.data else pd.DataFrame(columns=["created_at", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario"])
        
        # Estructura en blanco para bitácoras secundarias
        df_seg = pd.DataFrame(columns=["created_at", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"])
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
    d["timestamp_dt"] = pd.to_datetime(d["created_at"], errors="coerce")
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
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Ingresar", use_container_width=True):
                try:
                    query = supabase.table("usuarios").select("*").execute()
                    if query.data:
                        user_data = None
                        for row in query.data:
                            db_user = row.get("usuarios") or row.get("usuario")
                            if db_user and str(db_user).strip().lower() == u.strip().lower():
                                user_data = row
                                break
                        
                        if user_data:
                            if str(user_data["password_text"]) == p.strip():
                                st.session_state.update({
                                    "logged_in": True, 
                                    "usuario": u.strip(), 
                                    "centro_asignado": user_data["centro"].strip(), 
                                    "nombre_visible": user_data["nombre_visible"]
                                })
                                st.rerun()
                            else: st.error("🔒 Contraseña incorrecta.")
                        else:
                            nombres_reales = [str(r.get("usuarios") or r.get("usuario")) for r in query.data]
                            st.error(f"🔍 Encontrados en la DB: {nombres_reales}. Vos escribiste: '{u.strip()}'")
                    else: st.error("🔍 La tabla 'usuarios' está vacía en Supabase.")
                except Exception as e: st.error(f"❌ Error de conexión con Supabase: {e}")
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

    st.markdown("<h4 style='font-size:1rem; margin-bottom:10px;'>📊 Novedades del Centro</h4>", unsafe_allow_html=True)
    today_a = get_today_asistencia_summary(df_latest)
    c_a = today_a[today_a["centro"] == centro] if not today_a.empty else pd.DataFrame()

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if c_a.empty: st.markdown("<div class='alert-box alert-danger'>⚠️ Faltan Asistencias</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alert-box alert-success'>✅ Asistencias al día</div>", unsafe_allow_html=True)
    with ac2:
        if cumples:
            with st.expander(f"🎉 Cumpleaños ({len(cumples)})", expanded=True):
                for c in cumples: st.write(f"- {c}")
        else: st.markdown("<div class='alert-box alert-gray'>🎂 Sin cumples</div>", unsafe_allow_html=True)
    with ac3: st.markdown("<div class='alert-box alert-gray'>✔️ Sin Inasistencias</div>", unsafe_allow_html=True)

def kpi_row_full(df_latest, centro):
    hoy_date = get_today_ar()
    hoy = hoy_date.isoformat()
    week_ago = (hoy_date - timedelta(days=6)).isoformat()
    
    c1 = c2 = c3 = 0
    if not df_latest.empty:
        df_latest["presentes_i"] = df_latest["presentes"].apply(lambda x: clean_int(x, 0))
        c1 = int(df_latest[(df_latest["centro"] == centro) & (df_latest["fecha"].astype(str) == hoy)]["presentes_i"].sum())
        c2 = int(df_latest[(df_latest["centro"] == centro) & (df_latest["fecha"].astype(str) >= week_ago) & (df_latest["fecha"].astype(str) <= hoy)]["presentes_i"].sum())
        c3 = int(df_latest[(df_latest["centro"] == centro) & (df_latest["fecha"].astype(str) >= hoy_date.replace(day=1).isoformat()) & (df_latest["fecha"].astype(str) <= hoy)]["presentes_i"].sum())
        
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi'><h3>Mes actual</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)

# ======================================================
# 📝 PESTAÑA: CARGA DIARIA (CONEXIÓN SUPABASE EN BATCH)
# ======================================================
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
    df_activos = df_centro[df_centro["activo"].astype(str).str.upper() == "SI"] if not df_centro.empty else pd.DataFrame()
    nombres = sorted(list(set(df_activos["nombre"].astype(str).tolist()))) if not df_activos.empty else []
    
    st.markdown("#### 👥 Marcar Asistencia")
    presentes = st.multiselect("Buscador de personas", options=nombres, placeholder="Seleccionar asistentes...")
    total_presentes = len(presentes)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 GUARDAR ASISTENCIA (SUPABASE ⚡)", type="primary", use_container_width=True):
        if total_presentes <= 0 and modo != "Cerrado":
            st.error("⛔ Debes marcar asistentes o indicar 'Cerrado'.")
            return
            
        with st.spinner("Guardando en Supabase en lote..."):
            try:
                # 1. Guardamos la cabecera del día
                cabecera = {
                    "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro,
                    "espacio": espacio, "presentes": total_presentes, "coordinador": nombre_visible,
                    "modo": modo, "notas": notas, "usuario": usuario, "accion": "append"
                }
                supabase.table("asistencia_diaria").insert(cabecera).execute()
                
                # 2. OPTIMIZACIÓN COMPLEJA EN BATCH: Acumulamos las filas en memoria y hacemos 1 sola llamada SQL
                filas_personas = []
                for n in presentes:
                    filas_personas.append({
                        "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro,
                        "espacio": espacio, "nombre": n, "estado": "Presente", "es_nuevo": "NO",
                        "coordinador": nombre_visible, "usuario": usuario
                    })
                ausentes = [n for n in nombres if n not in presentes]
                for n in ausentes:
                    filas_personas.append({
                        "fecha": fecha_str, "anio": year_of(fecha_str), "centro": centro,
                        "espacio": espacio, "nombre": n, "estado": "Ausente", "es_nuevo": "NO",
                        "coordinador": nombre_visible, "usuario": usuario
                    })
                
                if filas_personas:
                    supabase.table("asistencia_personas").insert(filas_personas).execute()
                
                st.balloons()
                st.toast("✅ Asistencia Guardada de un Solo Viaje")
                time.sleep(1.5)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar la asistencia: {e}")

# ======================================================
# 👥 PESTAÑA: BUSCADOR DE LEGAJOS (REAL DE SUPABASE)
# ======================================================
def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>👥 Buscador de Legajos</h3>", unsafe_allow_html=True)
    
    df_centro = filter_personas_centro(df_personas, centro)
    nombres = sorted(df_centro["nombre"].unique()) if not df_centro.empty else []

    seleccion = st.selectbox("Escribí el nombre para ver su ficha:", [""] + nombres)
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-gray'>🔍 Buscá a alguien arriba para ver su carnet.</div>", unsafe_allow_html=True)
        if not df_centro.empty:
            st.markdown("#### 📋 Padrón Oficial del Centro")
            st.dataframe(df_centro[["nombre", "dni", "telefono", "activo"]].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    tags_str = str(datos_persona.get("etiquetas", ""))
    tags_html = ""
    if tags_str and tags_str.lower() != "none" and tags_str.lower() != "nan":
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

    telefono = str(datos_persona.get("telefono", ""))
    wa_btn_html = f"<div style='margin-top:5px;'><a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>💬 Enviar WhatsApp</a></div>" if (telefono and telefono.lower() != "none") else ""
    estado_badge = "🟢 ACTIVO" if str(datos_persona.get("activo")).upper() != "NO" else "🔴 INACTIVO"
    
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
<div style="background:var(--surface); padding:15px; border-radius:var(--radius-sm); border:1px solid rgba(255,255,255,0.05);">
    <div style="margin-bottom:10px;">
        <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">📱 Teléfono</div>
        <div style="font-size:1.1rem;">{telefono if (telefono and telefono.lower()!='none') else 'No registrado'}</div>
        {wa_btn_html}
    </div>
    <div>
        <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">🏠 Dirección</div>
        <div style="font-size:1.1rem;">{str(datos_persona.get('domicilio','')) if str(datos_persona.get('domicilio','')).lower()!='none' else 'No registrada'}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ======================================================
# ➕ PESTAÑA: ALTA DE PERSONA (YA REAL E INTEGRADA)
# ======================================================
def page_alta_persona(df_personas, centro, usuario):
    st.markdown("<h3 style='margin-bottom:15px;'>➕ Alta de Persona al Padrón</h3>", unsafe_allow_html=True)
    st.info("💡 Completá este formulario para ingresar al sistema a alguien que ya participa del centro.")
    
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
        
        if st.form_submit_button("💾 Guardar en el Padrón (Supabase ⚡)", type="primary", use_container_width=True):
            if not new_nom.strip():
                st.error("⚠️ El Nombre Completo es obligatorio.")
            else:
                with st.spinner("Guardando legajo en la nube..."):
                    try:
                        check = supabase.table("personas").select("*").eq("centro", centro).ilike("nombre", new_nom.strip()).execute()
                        if check.data:
                            st.warning(f"⚠️ '{new_nom}' ya existe en este centro.")
                        else:
                            fecha_nac_valida = None
                            if new_nac.strip():
                                try: fecha_nac_valida = pd.to_datetime(new_nac.strip()).date().isoformat()
                                catch:
                                    st.error("⛔ Formato de fecha incorrecto. Usar AAAA-MM-DD.")
                                    st.stop()

                            fila_nueva = {
                                "nombre": new_nom.strip(), "dni": new_dni.strip() if new_dni.strip() else None,
                                "fecha_nacimiento": fecha_nac_valida, "telefono": new_tel.strip() if new_tel.strip() else None,
                                "domicilio": new_dom.strip() if new_dom.strip() else None, "contacto_emergencia": new_em.strip() if new_em.strip() else None,
                                "etiquetas": new_etq.strip() if new_etq.strip() else None, "notas": new_notas.strip() if new_notas.strip() else None,
                                "activo": "SI", "centro": centro, "usuario_alta": usuario
                            }
                            supabase.table("personas").insert(fila_nueva).execute()
                            st.balloons()
                            st.success(f"✅ ¡{new_nom} ingresado correctamente!")
                            time.sleep(1.5)
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as e: st.error(f"❌ Error al guardar: {e}")

# ======================================================
# 📊 PESTAÑA: REPORTES Y CONSOLE GLOBAL
# ======================================================
def page_reportes(df_asistencia, centro):
    st.markdown("<h3 style='margin-bottom:15px;'>📊 Reportes</h3>", unsafe_allow_html=True)
    df_c = df_asistencia[df_asistencia["centro"] == centro].copy() if not df_asistencia.empty else pd.DataFrame()
    
    if df_c.empty:
        st.info("Sin datos históricos de asistencia en este centro aún.")
        return
        
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    st.markdown("#### Evolución de Asistencias")
    st.line_chart(df_c.set_index("fecha")["presentes_i"], color="#60A5FA")
    st.markdown(f"**Promedio de asistencia registrado:** {df_c['presentes_i'].mean():.1f} personas por día.")

def page_global(df_asistencia, df_personas, df_ap):
    st.markdown("<h3 style='margin-bottom:15px;'>🌍 Consola Central</h3>", unsafe_allow_html=True)
    st.caption("Métricas consolidadas institucionales del Hogar de Cristo.")
    
    t_pers = len(df_personas["nombre"].unique()) if not df_personas.empty else 0
    t_asist = df_asistencia["presentes"].apply(lambda x: clean_int(x, 0)).sum() if not df_asistencia.empty else 0
    
    k1, k2 = st.columns(2)
    k1.markdown(f"<div class='kpi'><h3>Padrón Total Institucional</h3><div class='v'>{t_pers}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3>Total de Asistencias</h3><div class='v'>{t_asist}</div></div>", unsafe_allow_html=True)

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
        st.error(f"Error: El centro '{centro}' no está mapeado.")
        st.stop()
    centro = match_centro

    if centro == C_BELEN and u.lower() != "natasha_test":
        st.error("🔒 ACCESO DENEGADO: El centro Calle Belén es de acceso exclusivo para la administración.")
        if st.button("⬅️ Salir de la cuenta", type="primary"):
            st.session_state.clear(); st.rerun()
        return

    show_top_header(nombre, centro)
    
    # ⚡ Carga unificada y sincrónica de Supabase
    df_asistencia, df_personas, df_ap, df_seg = load_all_data_supabase()

    list_tabs = ["🏠 Inicio", "👥 Legajos", "➕ Alta", "📊 Reportes"]
    if u.lower() == "natasha_test": 
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
