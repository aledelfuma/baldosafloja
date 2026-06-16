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
st.set_page_config(
    page_title="Hogar de Cristo Bahía Blanca",
    layout="wide",
    initial_sidebar_state="collapsed"
)

CSS = """
<style>
:root { --primary: #60A5FA; --secondary: #A78BFA; --background: #121212; --surface: #1E1E1E; --text-primary: #FFFFFF; --text-secondary: #AAAAAA; --radius-sm: 12px; --radius-lg: 18px; }
header {display: none !important;} footer {visibility: hidden;}
.stApp { background-color: var(--background) !important; font-family: 'Inter', sans-serif !important; color: var(--text-primary) !important; }
.block-container { padding-top: 2rem !important; max-width: 500px !important; margin: 0 auto; }
.top-bar { background-color: var(--surface); padding: 15px 20px; border-radius: var(--radius-lg); border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
.kpi { border-radius: var(--radius-lg); padding: 12px; background: var(--surface); border: 1px solid rgba(255,255,255,0.05); text-align: center; }
.kpi h3 { font-size: 0.6rem; color: var(--text-secondary); text-transform: uppercase; margin: 0; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary); margin-top: 5px; }
.alert-box { padding: 12px 15px; border-radius: var(--radius-sm); font-size: 0.9rem; font-weight: 600; margin-bottom: 10px; }
.alert-danger { background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.3); }
.alert-success { background-color: rgba(34, 197, 94, 0.15); color: #86EFAC; border: 1px solid rgba(34, 197, 94, 0.3); }
.profile-card { background-color: var(--surface); border-radius: var(--radius-lg); padding: 20px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 20px; }
.stTabs [data-baseweb="tab-list"] { position: fixed; bottom: 50px; left: 15px; right: 15px; background: rgba(30, 30, 30, 0.95); backdrop-filter: blur(10px); border-radius: 20px; display: flex; justify-content: space-around; padding: 10px; z-index: 999; box-shadow: 0 5px 20px rgba(0,0,0,0.5); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONFIGURACIÓN Y HELPERS
# ======================================================
supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')
def get_today_ar(): return datetime.now(TZ_AR).date()
def clean_int(x): try: return int(float(str(x).strip())); except: return 0
def filter_personas_centro(df, centro): return df if centro == "Administración" else df[df['centro'] == centro]

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]
CATEGORIAS = ["Escucha", "Salud", "Trámite", "Educación", "Familiar", "Crisis", "Otro"]

# ======================================================
# VISTAS
# ======================================================
def show_login_screen():
    st.markdown("### HOGAR DE CRISTO BAHÍA BLANCA")
    with st.form("login"):
        u = st.text_input("Usuario").strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.form_submit_button("Ingresar"):
            res = supabase.table("usuarios").select("*").execute().data
            for row in res:
                if row.get("usuario", "").lower() == u.lower() and row.get("password_text") == p:
                    st.session_state.update({"logged_in": True, "usuario": u, "centro_asignado": row["centro"], "nombre_visible": row["nombre_visible"]})
                    st.rerun()
            st.error("Credenciales incorrectas")
    st.stop()

def page_registrar_asistencia(df_personas, centro, nombre, usuario):
    st.markdown("### Carga Diaria")
    centro_sel = st.selectbox("Centro:", CENTROS) if centro == "Administración" else centro
    fecha = st.date_input("Fecha", value=get_today_ar())
    
    # Todos los centros cargan como "General"
    espacio = "General" 
    
    presentes = st.multiselect("Asistentes", options=filter_personas_centro(df_personas, centro_sel)["nombre"].tolist())
    
    if st.button("Guardar"):
        data = {"fecha": fecha.isoformat(), "centro": centro_sel, "espacio": espacio, "presentes": len(presentes), "coordinador": nombre, "usuario": usuario}
        supabase.table("asistencia_diaria").insert(data).execute()
        st.success("Guardado")
        st.rerun()

def main():
    if not st.session_state.get("logged_in"): show_login_screen()
    
    u, centro, nombre = st.session_state["usuario"], st.session_state["centro_asignado"], st.session_state["nombre_visible"]
    
    # Header simple
    st.markdown(f"**{nombre}** | {centro}")
    if st.button("Salir"): st.session_state.clear(); st.rerun()
    
    # Carga de datos
    res_p = supabase.table("personas").select("*").execute().data
    df_p = pd.DataFrame(res_p)
    res_a = supabase.table("asistencia_diaria").select("*").execute().data
    df_a = pd.DataFrame(res_a)

    tabs = st.tabs(["Inicio", "Legajos", "Alta", "Reportes"] + (["Global"] if centro == "Administración" or u.lower()=="admin" else []))
    with tabs[0]: page_registrar_asistencia(df_p, df_a, centro, nombre, u)
    # ... resto de las pestañas ...

if __name__ == "__main__":
    main()
