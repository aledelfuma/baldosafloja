import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import pytz
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
.stApp { background-color: var(--background) !important; font-family: 'Inter', sans-serif !important; color: var(--text-primary) !important; }
.block-container { padding-top: 2rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; padding-bottom: 160px !important; max-width: 500px !important; margin: 0 auto; overflow-x: hidden; }
.stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label { color: var(--text-primary) !important; }
.top-bar { background-color: var(--surface); padding: 15px 20px; border-radius: var(--radius-lg); margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
div.user-info { font-size: 1.1rem; font-weight: 700; line-height: 1.2; }
div.center-info { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary) !important; margin-top: 2px; }
.stButton>button, .stDownloadButton>button { background-color: var(--primary) !important; color: #000000 !important; border-radius: var(--radius-sm) !important; border: none !important; font-weight: 800 !important; padding: 0.7rem 1rem !important; transition: 0.2s !important; width: 100% !important; }
.stButton>button:active { transform: scale(0.98); } 
div.logout-wrapper > div > button { background-color: rgba(239, 68, 68, 0.15) !important; color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.2) !important; padding: 0.4rem 0.8rem !important; font-size: 0.8rem !important; font-weight: 700 !important; border-radius: 10px !important; width: auto !important; }
.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stMultiSelect>div>div>div { border-radius: var(--radius-sm) !important; border: 1px solid rgba(255,255,255,0.08) !important; background-color: #1A1A1A !important; color: var(--text-primary) !important; padding: 0.6rem; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }
.kpi { border-radius: var(--radius-lg); padding: 12px; background: var(--surface); border: 1px solid rgba(255,255,255,0.05); text-align: center; }
.kpi h3 { margin: 0; font-size: 0.6rem; color: var(--text-secondary) !important; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary) !important; line-height: 1; margin-top: 5px; }
.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; }
.alert-box.alert-warning { background-color: rgba(245, 158, 11, 0.15); color: #FDE047 !important; border: 1px solid rgba(245, 158, 11, 0.3); }
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
.btn-wa { display: block; text-align: center; background-color: #25D366 !important; color: white !important; padding: 10px; border-radius: var(--radius-sm); text-decoration: none; font-weight: 700; font-size: 0.9rem; margin-top: 10px; }
.stTabs [data-baseweb="tab-list"] { position: fixed; bottom: 50px !important; left: 15px !important; right: 15px !important; background-color: rgba(30, 30, 30, 0.95) !important; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 20px !important; display: flex; justify-content: space-around; padding: 8px 5px !important; z-index: 999999 !important; box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important; }
.stTabs [data-baseweb="tab"] { flex-grow: 1; text-align: center; justify-content: center; font-size: 0.65rem !important; font-weight: 700; color: var(--text-secondary) !important; padding: 10px 0; border: none !important; background: transparent !important; }
.stTabs [aria-selected="true"] { color: var(--primary) !important; background-color: rgba(96, 165, 250, 0.12) !important; border-radius: 14px; }
.stTabs [aria-selected="true"]::after { display: none; }
.note-card { background-color: var(--surface); border-left: 4px solid var(--secondary); padding: 12px 15px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; margin-bottom: 12px; border-top: 1px solid rgba(255,255,255,0.02); border-right: 1px solid rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONEXIÓN Y HELPERS
# ======================================================
supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')
def get_today_ar(): return datetime.now(TZ_AR).date()
def clean_int(x, default=0): 
    try: return int(float(str(x).strip()))
    except: return default

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# ======================================================
# FUNCIONES DE DATOS
# ======================================================
@st.cache_data(ttl=5)
def load_all_data():
    try:
        a = supabase.table("asistencia_diaria").select("*").execute().data
        p = supabase.table("personas").select("*").execute().data
        ap = supabase.table("asistencia_personas").select("*").execute().data
        seg = supabase.table("bitacora_seguimiento").select("*").execute().data
        return pd.DataFrame(a), pd.DataFrame(p), pd.DataFrame(ap), pd.DataFrame(seg)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def filter_personas_centro(df, centro):
    return df if centro == "Administración" else df[df['centro'] == centro]

# ======================================================
# VISTAS
# ======================================================
def show_login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### HOGAR DE CRISTO BAHÍA BLANCA")
    with st.form("login_form_oficial"):
        u = st.text_input("Usuario").strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.form_submit_button("Ingresar"):
            query = supabase.table("usuarios").select("*").execute().data
            for row in query:
                if row.get("usuario", "").lower() == u.lower() and row.get("password_text") == p:
                    st.session_state.update({"logged_in": True, "usuario": u, "centro_asignado": row["centro"], "nombre_visible": row["nombre_visible"]})
                    st.rerun()
            st.error("Credenciales incorrectas.")
    st.stop()

def page_registrar_asistencia(df_p, centro, nombre, usuario):
    st.markdown("### Carga Diaria")
    centro_sel = st.selectbox("Centro:", CENTROS) if centro == "Administración" else centro
    fecha = st.date_input("Fecha", value=get_today_ar())
    
    # TODOS cargan como "General"
    espacio = "General"
    modo = st.selectbox("Estado", ["Día habitual", "Actividad especial", "Cerrado"])
    
    df_c = filter_personas_centro(df_p, centro_sel)
    presentes = st.multiselect("Asistentes", options=df_c["nombre"].tolist())
    
    if st.button("Guardar"):
        data = {"fecha": fecha.isoformat(), "centro": centro_sel, "espacio": espacio, "presentes": len(presentes), "coordinador": nombre, "usuario": usuario, "modo": modo}
        supabase.table("asistencia_diaria").insert(data).execute()
        st.success("Guardado")
        st.rerun()

def main():
    if not st.session_state.get("logged_in"): show_login_screen()
    
    u, centro, nombre = st.session_state["usuario"], st.session_state["centro_asignado"], st.session_state["nombre_visible"]
    
    # Header
    col1, col2 = st.columns([3, 1])
    col1.markdown(f"**{nombre}** | {centro}")
    if col2.button("Salir"): st.session_state.clear(); st.rerun()
    
    df_a, df_p, df_ap, df_seg = load_all_data()
    
    tabs = st.tabs(["Inicio", "Legajos", "Alta", "Reportes"] + (["Global"] if centro == "Administración" else []))
    with tabs[0]: page_registrar_asistencia(df_p, df_a, centro, nombre, u)
    # ... resto de las tabs ...

if __name__ == "__main__":
    main()
