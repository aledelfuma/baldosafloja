import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import unicodedata
import re
from supabase import create_client, Client

# ======================================================
# CONFIGURACIÓN Y ESTILOS
# ======================================================
st.set_page_config(page_title="Hogar de Cristo Bahía Blanca", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
:root { --primary: #60A5FA; --secondary: #A78BFA; --background: #121212; --surface: #1E1E1E; }
.stApp { background-color: var(--background) !important; font-family: sans-serif !important; }
.kpi { border-radius: 12px; padding: 12px; background: var(--surface); border: 1px solid #333; text-align: center; }
.kpi h3 { font-size: 0.6rem; color: #AAA; text-transform: uppercase; margin: 0; }
.kpi .v { font-size: 1.5rem; font-weight: 800; color: var(--primary); margin-top: 5px; }
.alert-box { padding: 8px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; text-align: center; }
.bg-done { background: #064e3b; color: #86EFAC; }
.bg-pending { background: #7f1d1d; color: #FCA5A5; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# LÓGICA Y HELPERS
# ======================================================
@st.cache_resource
def get_supabase(): return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
supabase = get_supabase()

C_BELEN = "Calle Belén"
C_NUDO = "Nudo a Nudo"
C_MARANATHA = "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]

# Configuración de talleres
MAPEO_ESPACIOS = {
    C_MARANATHA: ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"],
    C_BELEN: ["General"],
    C_NUDO: ["General"]
}

def get_today_ar(): return datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).date()

# ======================================================
# VISTA: MONITOR DE TALLERES (SIN CÓDIGO CRUDO)
# ======================================================
def show_workshop_monitor(df_asistencia, centro_seleccionado):
    if centro_seleccionado == "Administración": return
    
    st.markdown("#### Control de Carga (Hoy)")
    hoy_str = get_today_ar().isoformat()
    talleres_definidos = MAPEO_ESPACIOS.get(centro_seleccionado, ["General"])
    df_hoy = df_asistencia[(df_asistencia["centro"] == centro_seleccionado) & (df_asistencia["fecha"] == hoy_str)]
    talleres_cargados = df_hoy["espacio"].unique() if not df_hoy.empty else []
    
    # Renderizado seguro con columnas nativas de Streamlit
    cols = st.columns(len(talleres_definidos))
    for i, t in enumerate(talleres_definidos):
        is_done = t in talleres_cargados
        css_class = "bg-done" if is_done else "bg-pending"
        cols[i].markdown(f"<div class='alert-box {css_class}'>{t}<br>{'✅' if is_done else '❌'}</div>", unsafe_allow_html=True)

# ======================================================
# VISTA: CARGA DIARIA
# ======================================================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, usuario):
    st.markdown("### Carga Diaria")
    centro_sel = st.selectbox("Centro:", CENTROS) if centro == "Administración" else centro
    show_workshop_monitor(df_asistencia, centro_sel)
    
    fecha = st.date_input("Fecha", value=get_today_ar())
    espacio = st.selectbox("Espacio", MAPEO_ESPACIOS.get(centro_sel, ["General"]))
    presentes = st.number_input("Presentes", min_value=0)
    
    if st.button("Guardar"):
        data = {"fecha": fecha.isoformat(), "centro": centro_sel, "espacio": espacio, "presentes": presentes, "coordinador": nombre}
        supabase.table("asistencia_diaria").insert(data).execute()
        st.success("Guardado")
        st.rerun()

# ======================================================
# MAIN
# ======================================================
def main():
    if not st.session_state.get("logged_in"):
        # Login simplificado para testeo
        with st.form("login"):
            u = st.text_input("Usuario")
            if st.form_submit_button("Ingresar"):
                st.session_state.update({"logged_in": True, "usuario": u, "centro_asignado": "Casa Maranatha", "nombre_visible": "Alejandro"})
                st.rerun()
        st.stop()
    
    df_a, df_p, df_ap, df_seg = load_all_data_supabase()
    show_top_header(st.session_state["nombre_visible"], st.session_state["centro_asignado"])
    
    tabs = st.tabs(["Inicio", "Legajos", "Reportes"])
    with tabs[0]: page_registrar_asistencia(df_p, df_a, st.session_state["centro_asignado"], st.session_state["nombre_visible"], st.session_state["usuario"])

def load_all_data_supabase():
    # ... (tu función de carga existente) ...
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def show_top_header(nombre, centro):
    st.markdown(f"**{nombre}** | Centro: **{centro}**")

if __name__ == "__main__":
    main()
