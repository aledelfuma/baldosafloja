import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import pytz
import io
import unicodedata
import re
from supabase import create_client, Client # <-- METEMOS ESTO NUEVO ACÁ

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
... TODO TU BLOQUE DE CSS GIGANTE SE QUEDA ACÁ ADENTRO IGUAL ...
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ======================================================
# 🔌 ACÁ ENCHUFÁS EL NUEVO MOTOR (Pega esto justo acá)
# ======================================================
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase_client()


# ======================================================
# 🌑 ZONA HORARIA Y HELPERS (Esto ya lo tenías, sigue abajo)
# ======================================================
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')

def get_now_ar_str(): return datetime.now(TZ_AR).strftime("%Y-%m-%d %H:%M:%S")
def get_today_ar(): return datetime.now(TZ_AR).date()
