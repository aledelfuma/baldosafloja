import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="Asistencia – Hogar de Cristo",
    layout="wide"
)

PRIMARY = "#004E7B"
ACCENT = "#63296C"

st.markdown(
    f"""
    <style>
    h1, h2, h3 {{ color: {PRIMARY}; }}
    .stButton>button {{
        background-color: {PRIMARY};
        color: white;
        border-radius: 999px;
        font-weight: 600;
    }}
    .stButton>button:hover {{
        background-color: {ACCENT};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# =============================
# DATA FILES
# =============================
DATA_DIR = "data"
PERSONAS_FILE = f"{DATA_DIR}/personas.csv"
ASISTENCIA_FILE = f"{DATA_DIR}/asistencia.csv"

os.makedirs(DATA_DIR, exist_ok=True)

# =============================
# CONSTANTES
# =============================
CENTROS = ["Calle Belén", "Casa Maranatha", "Nudo a Nudo"]

COORDINADORES = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellán"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
}

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar primaria",
    "Apoyo escolar secundaria",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]

# =============================
# INIT CSV
# =============================
if not os.path.exists(PERSONAS_FILE):
    pd.DataFrame(columns=["nombre", "frecuencia", "centro"]).to_csv(PERSONAS_FILE, index=False)

if not os.path.exists(ASISTENCIA_FILE):
    pd.DataFrame(columns=[
        "id", "fecha", "centro", "espacio",
        "presentes", "coordinador", "notas", "timestamp"
    ]).to_csv(ASISTENCIA_FILE, index=False)

# =============================
# LOAD DATA
# =============================
df_personas = pd.read_csv(PERSONAS_FILE)
df_asistencia = pd.read_csv(ASISTENCIA_FILE)

# =============================
# SIDEBAR
# =============================
st.sidebar.title("Centro barrial")

centro = st.sidebar.selectbox("Centro", CENTROS)
coordinador = st.sidebar.selectbox("Quién carga", COORDINADORES[centro])

# =============================
# MAIN
# =============================
st.title("Sistema de Asistencia")
st.caption(f"Centro: **{centro}** · Coordinador/a: **{coordinador}**")

tab1, tab2, tab3 = st.tabs(["📌 Registrar", "👥 Personas", "📊 Reportes"])

# =============================
# TAB 1 – REGISTRAR
# =============================
with tab1:
    fecha = st.date_input("Fecha", value=date.today())

    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA)
    else:
        espacio = "General"
        st.info("Este centro registra asistencia general.")

    presentes = st.number_input("Cantidad de personas", min_value=0, step=1)
    notas = st.text_area("Notas")

    if st.button("Guardar asistencia"):
        nuevo = {
            "id": str(uuid.uuid4()),
            "fecha": fecha.isoformat(),
            "centro": centro,
            "espacio": espacio,
            "presentes": int(presentes),
            "coordinador": coordinador,
            "notas": notas,
            "timestamp": datetime.now().isoformat(),
        }
        df_asistencia = pd.concat([df_asistencia, pd.DataFrame([nuevo])])
        df_asistencia.to_csv(ASISTENCIA_FILE, index=False)
        st.success("Asistencia guardada")
        st.rerun()

# =============================
# TAB 2 – PERSONAS
# =============================
with tab2:
    st.subheader("Listado de personas")
    st.dataframe(df_personas[df_personas["centro"] == centro], use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona")

    nombre = st.text_input("Nombre completo")
    frecuencia = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual", "No asiste"])

    if st.button("Agregar persona"):
        if nombre.strip() == "":
            st.error("Ingresá un nombre.")
        else:
            nuevo = {
                "nombre": nombre.strip(),
                "frecuencia": frecuencia,
                "centro": centro
            }
            df_personas = pd.concat([df_personas, pd.DataFrame([nuevo])])
            df_personas.to_csv(PERSONAS_FILE, index=False)
            st.success("Persona agregada")
            st.rerun()

# =============================
# TAB 3 – REPORTES
# =============================
with tab3:
    st.subheader("Asistencia últimos 30 días")

    df = df_asistencia[df_asistencia["centro"] == centro].copy()
    if df.empty:
        st.info("Todavía no hay registros.")
    else:
        df["fecha"] = pd.to_datetime(df["fecha"])
        desde = date.today() - timedelta(days=30)
        df = df[df["fecha"].dt.date >= desde]

        if df.empty:
            st.info("No hay datos en los últimos 30 días.")
        else:
            serie = df.groupby(df["fecha"].dt.date)["presentes"].sum()
            st.line_chart(serie)

            st.download_button(
                "Descargar CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="asistencia.csv",
                mime="text/csv"
            )
