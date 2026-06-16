import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import pytz
import unicodedata
import re
from supabase import create_client, Client

# ======================================================
# CONFIGURACIÓN DE TEMA Y ESTILO (MANTENIENDO EL DISEÑO QUE TE GUSTA)
# ======================================================
st.set_page_config(page_title="Hogar de Cristo Bahía Blanca", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
:root { --primary: #60A5FA; --secondary: #A78BFA; --background: #121212; --surface: #1E1E1E; --text-primary: #FFFFFF; --text-secondary: #AAAAAA; --radius-sm: 12px; --radius-lg: 18px; }
header {display: none !important;} footer {visibility: hidden;}
.stApp { background-color: var(--background) !important; font-family: 'Inter', sans-serif !important; color: var(--text-primary) !important; }
.block-container { padding-top: 2rem !important; max-width: 500px !important; margin: 0 auto; }
.top-bar { background-color: var(--surface); padding: 15px 20px; border-radius: var(--radius-lg); border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
.stButton>button { background-color: var(--primary) !important; color: #000000 !important; border-radius: var(--radius-sm) !important; border: none !important; font-weight: 800 !important; padding: 0.7rem 1rem !important; transition: 0.2s !important; width: 100% !important; }
.kpi { border-radius: var(--radius-lg); padding: 12px; background: var(--surface); border: 1px solid rgba(255,255,255,0.05); text-align: center; }
.kpi h3 { font-size: 0.6rem; color: var(--text-secondary); text-transform: uppercase; margin: 0; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary); margin-top: 5px; }
.profile-card { background-color: var(--surface); border-radius: var(--radius-lg); padding: 20px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 20px; }
.stTabs [data-baseweb="tab-list"] { position: fixed; bottom: 50px; left: 15px; right: 15px; background: rgba(30, 30, 30, 0.95); backdrop-filter: blur(10px); border-radius: 20px; display: flex; justify-content: space-around; padding: 10px; z-index: 999; box-shadow: 0 5px 20px rgba(0,0,0,0.5); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONEXIÓN Y HELPERS
# ======================================================
supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')
def get_today_ar(): return datetime.now(TZ_AR).date()
def clean_int(x): 
    try: return int(float(str(x).strip()))
    except: return 0

# Configuración fija de centros
CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

# ======================================================
# LÓGICA DE DATOS
# ======================================================
@st.cache_data(ttl=5)
def load_data():
    try:
        a = supabase.table("asistencia_diaria").select("*").execute().data
        p = supabase.table("personas").select("*").execute().data
        u = supabase.table("usuarios").select("*").execute().data
        return pd.DataFrame(a), pd.DataFrame(p), pd.DataFrame(u)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ======================================================
# VISTAS
# ======================================================
def show_login():
    st.markdown("### HOGAR DE CRISTO BAHÍA BLANCA")
    with st.form("login"):
        u = st.text_input("Usuario").strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.form_submit_button("Ingresar"):
            _, _, df_u = load_data()
            for _, row in df_u.iterrows():
                if row.get("usuario", "").lower() == u.lower() and row.get("password_text") == p:
                    st.session_state.update({"logged_in": True, "usuario": u, "centro": row["centro"], "nombre": row["nombre_visible"]})
                    st.rerun()
            st.error("Credenciales incorrectas")
    st.stop()

def main():
    if not st.session_state.get("logged_in"): show_login()
    
    centro = st.session_state["centro"]
    
    # Header
    col1, col2 = st.columns([3, 1])
    col1.markdown(f"**{st.session_state['nombre']}** | Centro: {centro}")
    if col2.button("Salir"): st.session_state.clear(); st.rerun()
    
    df_a, df_p, _ = load_data()
    
    # Inicio / Carga Diaria (Simplificada, General para todos)
    st.markdown("### Carga Diaria")
    fecha = st.date_input("Fecha", value=get_today_ar())
    
    # Todos usan "General"
    presentes = st.number_input("Presentes", min_value=0, value=0)
    notas = st.text_area("Notas")
    
    if st.button("Guardar"):
        try:
            data = {"fecha": fecha.isoformat(), "centro": centro, "espacio": "General", "presentes": presentes, "coordinador": st.session_state["nombre"], "notas": notas}
            supabase.table("asistencia_diaria").insert(data).execute()
            st.success("Guardado correctamente")
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")

    # Visualización de KPIs simples
    df_hoy = df_a[pd.to_datetime(df_a["fecha"]).dt.date == get_today_ar()]
    hoy_total = df_hoy[df_hoy["centro"] == centro]["presentes"].apply(clean_int).sum()
    st.markdown(f"<div class='kpi'><h3>Ingresos hoy en {centro}</h3><div class='v'>{hoy_total}</div></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
