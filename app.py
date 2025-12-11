import streamlit as st
import pandas as pd
import os
from datetime import date

# -----------------------------------------
# CONFIGURACIÓN BÁSICA
# -----------------------------------------
st.set_page_config(page_title="Asistencia Centros Barriales", layout="wide")

CENTROS = ["Nudo a Nudo", "Casa Maranatha", "Calle Belén"]

# Espacios solo para Casa Maranatha
ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar primaria",
    "Apoyo escolar secundaria",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otros"
]

# Archivos
PERSONAS_FILE = "personas.csv"
RESUMEN_FILE = "resumen_diario.csv"


# -----------------------------------------
# CARGA DE PERSONAS (nombre, frecuencia, centro)
# -----------------------------------------
def cargar_personas():
    if os.path.exists(PERSONAS_FILE):
        return pd.read_csv(PERSONAS_FILE)
    df = pd.DataFrame(columns=[
        "nombre", "frecuencia", "centro"
    ])
    df.to_csv(PERSONAS_FILE, index=False)
    return df


def guardar_personas(df: pd.DataFrame):
    df.to_csv(PERSONAS_FILE, index=False)


# -----------------------------------------
# CARGA DEL RESUMEN DIARIO
# -----------------------------------------
def cargar_resumen():
    if os.path.exists(RESUMEN_FILE):
        return pd.read_csv(RESUMEN_FILE)
    df = pd.DataFrame(columns=[
        "fecha", "centro", "espacio", "total_presentes", "notas"
    ])
    df.to_csv(RESUMEN_FILE, index=False)
    return df


def guardar_resumen(df: pd.DataFrame):
    df.to_csv(RESUMEN_FILE, index=False)


# -----------------------------------------
# INICIALIZACIÓN
# -----------------------------------------
personas = cargar_personas()
resumen = cargar_resumen()

st.sidebar.title("Centros Barriales")
centro_logueado = st.sidebar.selectbox(
    "Seleccioná tu centro",
    CENTROS
)

st.sidebar.markdown("---")
st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

tabs = st.tabs(["📅 Registrar asistencia", "👥 Personas", "📊 Reportes"])

# =====================================================
# TAB 1 — REGISTRO DE ASISTENCIA
# =====================================================
with tabs[0]:
    st.subheader("Registrar asistencia por centro / espacio")

    col1, col2 = st.columns(2)
    with col1:
        centro = st.selectbox("Centro", CENTROS, index=CENTROS.index(centro_logueado))
    with col2:
        fecha = st.date_input("Fecha", value=date.today())

    col3, col4 = st.columns(2)
    with col3:
        if centro == "Casa Maranatha":
            espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA)
        else:
            espacio = "General"
            st.info("Este centro no usa espacios internos.")
    with col4:
        total_presentes = st.number_input("Total presentes", min_value=0, step=1)

    notas = st.text_area("Notas (opcional)")

    if st.button("💾 Guardar asistencia", use_container_width=True):
        nueva = {
            "fecha": fecha.isoformat(),
            "centro": centro,
            "espacio": espacio,
            "total_presentes": int(total_presentes),
            "notas": notas.strip()
        }
        resumen = pd.concat([resumen, pd.DataFrame([nueva])], ignore_index=True)
        guardar_resumen(resumen)
        st.success("Registro guardado exitosamente ✅")

    st.markdown("---")
    st.subheader("Últimos registros")

    if resumen.empty:
        st.info("Todavía no hay registros.")
    else:
        dfc = resumen[resumen["centro"] == centro].copy()
        dfc["fecha"] = pd.to_datetime(dfc["fecha"])
        dfc = dfc.sort_values("fecha", ascending=False)
        st.dataframe(dfc.head(20), use_container_width=True)

        st.write("### Evolución de asistencia")
        df_chart = dfc.groupby("fecha")["total_presentes"].sum()
        st.line_chart(df_chart)


# =====================================================
# TAB 2 — PERSONAS
# =====================================================
with tabs[1]:
    st.subheader("Personas por centro")

    centro_p = st.selectbox("Centro", CENTROS, index=CENTROS.index(centro_logueado))

    personas_centro = personas[personas["centro"] == centro_p]

    st.markdown("### Lista de personas")

    st.dataframe(personas_centro, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona nueva")

    col1, col2 = st.columns(2)
    with col1:
        nombre_nuevo = st.text_input("Nombre completo")
    with col2:
        frecuencia_nueva = st.selectbox(
            "Frecuencia",
            ["Diaria", "Semanal", "Mensual", "No asiste"]
        )

    if st.button("➕ Agregar persona", use_container_width=True):
        nueva = {
            "nombre": nombre_nuevo.strip(),
            "frecuencia": frecuencia_nueva,
            "centro": centro_p
        }
        personas = pd.concat([personas, pd.DataFrame([nueva])], ignore_index=True)
        guardar_personas(personas)
        st.success("Persona agregada correctamente")

    st.markdown("---")
    st.subheader("Editar personas")

    edit = st.data_editor(
        personas_centro,
        use_container_width=True,
        num_rows="dynamic"
    )

    if st.button("💾 Guardar cambios", use_container_width=True):
        # Reemplazamos solo las filas de ese centro
        personas = personas[personas["centro"] != centro_p]
        personas = pd.concat([personas, edit], ignore_index=True)
        guardar_personas(personas)
        st.success("Cambios guardados")


# =====================================================
# TAB 3 — REPORTES
# =====================================================
with tabs[2]:
    st.subheader("Reportes de asistencia")

    if resumen.empty:
        st.info("No hay datos cargados todavía.")
    else:
        centros_sel = st.multiselect("Seleccionar centros", CENTROS, default=CENTROS)

        df = resumen[resumen["centro"].isin(centros_sel)].copy()
        df["fecha"] = pd.to_datetime(df["fecha"])

        st.markdown("### Totales por centro")
        totales = df.groupby("centro")["total_presentes"].sum()
        st.bar_chart(totales)

        st.markdown("### Evolución total")
        linea = df.groupby("fecha")["total_presentes"].sum()
        st.line_chart(linea)

        st.markdown("---")
        st.markdown("### Casa Maranatha — Totales por espacio")
        df_mara = df[df["centro"] == "Casa Maranatha"]
        if not df_mara.empty:
            por_espacio = df_mara.groupby("espacio")["total_presentes"].sum()
            st.bar_chart(por_espacio)

        st.markdown("---")
        st.subheader("Exportar datos")
        st.download_button(
            "⬇️ Descargar CSV para Google Sheets",
            df.to_csv(index=False).encode("utf-8"),
            "reporte_asistencia.csv",
            "text/csv"
        )
