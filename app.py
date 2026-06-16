import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import pytz
import unicodedata
import re
from supabase import create_client, Client

# ======================================================
# CONFIGURACIÓN ESTÉTICA (Sin Emojis)
# ======================================================
st.set_page_config(page_title="Hogar de Cristo Bahía Blanca", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
:root { --primary: #60A5FA; --secondary: #A78BFA; --background: #121212; --surface: #1E1E1E; --text-primary: #FFFFFF; --text-secondary: #AAAAAA; }
.stApp { background-color: var(--background); color: var(--text-primary); font-family: sans-serif; }
.top-bar { background: var(--surface); padding: 15px; border-radius: 12px; border: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
.kpi { border-radius: 12px; padding: 15px; background: var(--surface); border: 1px solid #333; text-align: center; }
.kpi .v { font-size: 1.8rem; font-weight: 800; color: var(--primary); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# LÓGICA DE DATOS
# ======================================================
supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')

def get_today_ar(): return datetime.now(TZ_AR).date()
def clean_int(x): 
    try: return int(float(str(x).strip()))
    except: return 0

# ======================================================
# VISTAS (Login + Header)
# ======================================================
def show_login():
    st.markdown("### HOGAR DE CRISTO BAHÍA BLANCA")
    with st.form("login"):
        u = st.text_input("Usuario").strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.form_submit_button("Ingresar"):
            res = supabase.table("usuarios").select("*").execute().data
            for row in res:
                if row.get("usuario", "").lower() == u.lower() and row.get("password_text") == p:
                    st.session_state.update({"logged_in": True, "usuario": u, "centro": row["centro"], "nombre": row["nombre_visible"]})
                    st.rerun()
            st.error("Credenciales incorrectas")
    st.stop()

# ======================================================
# MAIN (Logica cargada completa)
# ======================================================
def main():
    if not st.session_state.get("logged_in"): show_login()
    
    centro = st.session_state["centro"]
    
    # Header
    col1, col2 = st.columns([3, 1])
    col1.markdown(f"### {st.session_state['nombre']} | {centro}")
    if col2.button("Salir"): st.session_state.clear(); st.rerun()
    
    # Carga de datos base
    try:
        res_a = supabase.table("asistencia_diaria").select("*").execute().data
        df_a = pd.DataFrame(res_a)
    except: df_a = pd.DataFrame()

    # Pestañas
    tabs = st.tabs(["Carga Diaria", "Reportes"] + (["Global"] if centro == "Administración" else []))
    
    with tabs[0]:
        st.markdown("#### Registro de Asistencia")
        fecha = st.date_input("Fecha", value=get_today_ar())
        # Carga GENERAL para TODOS (Sin talleres)
        presentes = st.number_input("Cantidad de presentes", min_value=0, value=0)
        notas = st.text_area("Notas")
        
        if st.button("Guardar"):
            data = {"fecha": fecha.isoformat(), "centro": centro, "espacio": "General", "presentes": presentes, "coordinador": st.session_state["nombre"], "notas": notas}
            supabase.table("asistencia_diaria").insert(data).execute()
            st.success("Guardado")
            st.rerun()
            
    with tabs[1]:
        st.markdown("### Reportes")
        df_a["presentes_i"] = df_a["presentes"].apply(clean_int)
        df_c = df_a[df_a["centro"] == centro] if centro != "Administración" else df_a
        st.bar_chart(df_c.groupby("fecha")["presentes_i"].sum())

    if len(tabs) > 2:
        with tabs[2]:
            st.markdown("### Auditoría Global")
            st.dataframe(df_a.sort_values("fecha", ascending=False))

if __name__ == "__main__":
    main()
