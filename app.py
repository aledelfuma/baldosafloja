import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import pytz
import unicodedata
import re
from supabase import create_client, Client

# ======================================================
# CONFIGURACIÓN DE TEMA
# ======================================================
st.set_page_config(page_title="Hogar de Cristo Bahía Blanca", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
:root { --primary: #60A5FA; --secondary: #A78BFA; --background: #121212; --surface: #1E1E1E; --text-primary: #FFFFFF; --text-secondary: #AAAAAA; }
header {display: none !important;} footer {visibility: hidden;}
.stApp { background-color: var(--background) !important; font-family: sans-serif !important; color: var(--text-primary) !important; }
.block-container { padding-top: 2rem !important; max-width: 500px !important; margin: 0 auto; }
.top-bar { background-color: var(--surface); padding: 15px; border-radius: 12px; border: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
.kpi { border-radius: 12px; padding: 12px; background: var(--surface); border: 1px solid #333; text-align: center; }
.kpi h3 { font-size: 0.6rem; color: var(--text-secondary); text-transform: uppercase; margin: 0; }
.kpi .v { font-size: 1.5rem; font-weight: 800; color: var(--primary); margin-top: 5px; }
.workshop-status-container { background: var(--surface); border-radius: 12px; padding: 15px; border: 1px solid #333; margin-bottom: 20px; }
.workshop-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; }
.badge-done { color: #86EFAC; font-weight: bold; font-size: 0.7rem; }
.badge-pending { color: #FCA5A5; font-weight: bold; font-size: 0.7rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONEXIÓN Y HELPERS
# ======================================================
@st.cache_resource
def get_supabase(): return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
supabase = get_supabase()

TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')
def get_today_ar(): return datetime.now(TZ_AR).date()
def clean_int(x): 
    try: return int(float(str(x).strip()))
    except: return 0

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]
MAPEO_ESPACIOS = {
    "Casa Maranatha": ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"],
    "Calle Belén": ["General"],
    "Nudo a Nudo": ["General"]
}

# ======================================================
# LÓGICA DE DATOS
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

# ======================================================
# VISTAS
# ======================================================
def show_login():
    st.markdown("### HOGAR DE CRISTO BAHÍA BLANCA")
    with st.form("login"):
        u = st.text_input("Usuario").strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.form_submit_button("Ingresar"):
            query = supabase.table("usuarios").select("*").execute().data
            for row in query:
                if row.get("usuario", "").lower() == u.lower() and row.get("password_text") == p:
                    st.session_state.update({"logged_in": True, "usuario": u, "centro": row["centro"], "nombre": row["nombre_visible"]})
                    st.rerun()
            st.error("Credenciales incorrectas.")
    st.stop()

def main():
    if not st.session_state.get("logged_in"): show_login()
    
    centro = st.session_state["centro"]
    
    # Header
    col1, col2 = st.columns([3,1])
    col1.markdown(f"**Usuario:** {st.session_state['nombre']} | **Centro:** {centro}")
    if col2.button("Salir"): st.session_state.clear(); st.rerun()
    
    df_a, df_p, df_ap, df_seg = load_all_data()
    
    tabs = st.tabs(["Inicio", "Legajos", "Alta", "Reportes"] + (["Global"] if centro == "Administración" else []))
    
    with tabs[0]:
        st.markdown("### Resumen")
        # Monitor de talleres
        if centro != "Administración":
            st.markdown("#### Control de Carga (Hoy)")
            hoy = get_today_ar().isoformat()
            cargados = df_a[(df_a["centro"] == centro) & (df_a["fecha"] == hoy)]["espacio"].unique()
            for t in MAPEO_ESPACIOS.get(centro, ["General"]):
                status = "Cargado" if t in cargados else "Falta Cargar"
                badge = "badge-done" if t in cargados else "badge-pending"
                st.markdown(f"<div class='workshop-row'><span>• {t}</span><span class='{badge}'>{status}</span></div>", unsafe_allow_html=True)
        
        # KPIs
        df_hoy = df_a[pd.to_datetime(df_a["fecha"]).dt.date == get_today_ar()]
        presentes_hoy = df_hoy[df_hoy["centro"] == centro]["presentes"].apply(clean_int).sum() if centro != "Administración" else df_hoy["presentes"].apply(clean_int).sum()
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{presentes_hoy}</div></div>", unsafe_allow_html=True)
        c2.markdown("<div class='kpi'><h3>Semana</h3><div class='v'>--</div></div>", unsafe_allow_html=True)
        c3.markdown("<div class='kpi'><h3>Mes</h3><div class='v'>--</div></div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("### Legajos")
        # buscador y lógica...

if __name__ == "__main__":
    main()
