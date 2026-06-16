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
.kpi { border-radius: 12px; padding: 12px; background: var(--surface); border: 1px solid #333; text-align: center; }
.kpi h3 { font-size: 0.6rem; color: var(--text-secondary); text-transform: uppercase; margin: 0; }
.kpi .v { font-size: 1.5rem; font-weight: 800; color: var(--primary); margin-top: 5px; }
.alert-box { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 0.8rem; }
.alert-success { background: rgba(34, 197, 94, 0.1); color: #86EFAC; border: 1px solid #166534; }
.alert-danger { background: rgba(239, 68, 68, 0.1); color: #FCA5A5; border: 1px solid #991b1b; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# CONFIGURACIONES Y HELPERS
# ======================================================
@st.cache_resource
def get_supabase(): return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
supabase = get_supabase()

C_MARANATHA = "Casa Maranatha"
ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]

def get_today_ar(): return datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).date()

# ======================================================
# VISTA: REGISTRO DE ASISTENCIA
# ======================================================
def page_registrar_asistencia(centro, nombre_visible, usuario):
    st.markdown("### Carga Diaria")
    fecha = st.date_input("Fecha", value=get_today_ar())
    
    # Lógica condicional de talleres
    if centro == C_MARANATHA:
        espacio = st.selectbox("Taller / Espacio", ESPACIOS_MARANATHA)
    else:
        espacio = "General"
        st.info(f"Centro: {centro} (Carga General)")

    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    presentes = st.number_input("Cantidad de presentes", min_value=0, value=0)

    if st.button("Guardar Asistencia"):
        try:
            data = {
                "fecha": fecha.isoformat(),
                "centro": centro,
                "espacio": espacio,
                "presentes": presentes,
                "modo": modo,
                "coordinador": nombre_visible
            }
            supabase.table("asistencia_diaria").insert(data).execute()
            st.success("Guardado correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# ======================================================
# CONTROLADOR PRINCIPAL
# ======================================================
def main():
    if not st.session_state.get("logged_in"):
        # (Lógica de login simplificada)
        if st.button("Simular Login"): st.session_state.update({"logged_in": True, "centro": C_MARANATHA, "nombre": "Alejandro"})
        st.stop()
    
    centro = st.session_state["centro"]
    
    # Navegación
    tab1, tab2 = st.tabs(["Carga", "Reportes"])
    with tab1:
        page_registrar_asistencia(centro, st.session_state["nombre"], "admin")

if __name__ == "__main__":
    main()
