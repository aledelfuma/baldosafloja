import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
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
:root { --primary: #60A5FA; --secondary: #A78BFA; --background: #121212; --surface: #1E1E1E; --text-primary: #FFFFFF; --text-secondary: #AAAAAA; --radius-sm: 12px; --radius-lg: 18px; }
header {display: none !important;} footer {visibility: hidden;}
.stApp { background-color: var(--background) !important; font-family: sans-serif !important; color: var(--text-primary) !important; }
.block-container { padding-top: 2rem !important; max-width: 500px !important; margin: 0 auto; }
.kpi { border-radius: 12px; padding: 12px; background: var(--surface); border: 1px solid #333; text-align: center; }
.kpi h3 { font-size: 0.6rem; color: var(--text-secondary); text-transform: uppercase; margin: 0; }
.kpi .v { font-size: 1.5rem; font-weight: 800; color: var(--primary); margin-top: 5px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONEXIÓN Y HELPERS
# ======================================================
@st.cache_resource
def get_supabase(): return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
supabase = get_supabase()

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

def get_today_ar(): return datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).date()

def clean_int(x):
    try:
        return int(float(str(x).strip()))
    except:
        return 0

# ======================================================
# LÓGICA DE DATOS
# ======================================================
@st.cache_data(ttl=5)
def load_all_data():
    try:
        a = supabase.table("asistencia_diaria").select("*").execute().data
        p = supabase.table("personas").select("*").execute().data
        return pd.DataFrame(a), pd.DataFrame(p)
    except: return pd.DataFrame(), pd.DataFrame()

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
    st.markdown(f"**{st.session_state['nombre']}** | Centro: {centro}")
    if st.button("Salir"): st.session_state.clear(); st.rerun()
    
    df_a, df_p = load_all_data()
    
    st.markdown("### Carga Diaria")
    fecha = st.date_input("Fecha", value=get_today_ar())
    espacio = "General" # Todos cargan igual, sin talleres
    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    presentes = st.number_input("Presentes", min_value=0, value=0)
    
    if st.button("Guardar"):
        try:
            data = {"fecha": fecha.isoformat(), "centro": centro, "espacio": espacio, "presentes": presentes, "modo": modo, "coordinador": st.session_state["nombre"]}
            supabase.table("asistencia_diaria").insert(data).execute()
            st.success("Guardado")
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
