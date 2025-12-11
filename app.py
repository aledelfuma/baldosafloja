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
# PERSONAS: nombre, frecuencia, centro
# -----------------------------------------
def cargar_personas():
    if os.path.exists(PERSONAS_FILE):
        return pd.read_csv(PERSONAS_FILE)
    df = pd.DataFrame(columns=["nombre", "frecuencia", "centro"])
    df.to_csv(PERSONAS_FILE, index=False)
    return df


def guardar_personas(df: pd.DataFrame):
    df.to_csv(PERSONAS_FILE, index=False)


# -----------------------------------------
# RESUMEN DIARIO: fecha, centro, espacio, total_presentes, notas
# -----------------------------------------
def cargar_resumen():
    if os.path.exists(RESUMEN_FILE):
        return pd.read_csv(RESUMEN_FILE)
    df = pd.DataFrame(columns=["fecha", "centro", "espacio", "total_presentes", "notas"])
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
    CENTROS,
    key="centro_sidebar"
)

st.sidebar.markdown("---")
st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

tab_registro, tab_personas, tab_reportes = st.tabs(
    ["📅 Registrar asistencia", "👥 Personas", "📊 Reportes"]
)

# =====================================================
# TAB 1 — REGISTRO DE ASISTENCIA
# =====================================================
with tab_registro:
    st.subheader("Registrar asistencia por centro / espacio")

    col1, col2 = st.columns(2)
    with col1:
        centro = st.selectbox(
            "Centro",
            CENTROS,
            index=CENTROS.index(centro_logueado),
            key="centro_registro"
        )
    with col2:
        fecha = st.date_input("Fecha", value=date.today(), key="fecha_registro")

    col3, col4 = st.columns(2)
    with col3:
        if centro == "Casa Maranatha":
            espacio = st.selectbox(
                "Espacio",
                ESPACIOS_MARANATHA,
                key="espacio_maranatha"
            )
        else:
            espacio = "General"
            st.info("Este centro no usa espacios internos.")
    with col4:
        total_presentes = st.number_input(
            "Total presentes",
            min_value=0,
            step=1,
            key="presentes_registro"
        )

    notas = st.text_area("Notas (opcional)", key="notas_registro")

    if st.button("💾 Guardar asistencia", use_container_width=True, key="btn_guardar_asistencia"):
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
        dfc["fecha"] = pd.to_datetime(dfc["fecha"], errors="coerce")
        dfc = dfc.sort_values("fecha", ascending=False)
        st.dataframe(dfc.head(20), use_container_width=True)

        if not dfc.empty:
            st.write("### Evolución de asistencia")
            df_chart = (
                dfc.groupby("fecha")["total_presentes"]
                .sum()
                .sort_index()
            )
            st.line_chart(df_chart)


# =====================================================
# TAB 2 — PERSONAS
# =====================================================
with tab_personas:
    st.subheader("Personas por centro")

    centro_p = st.selectbox(
        "Centro",
        CENTROS,
        index=CENTROS.index(centro_logueado),
        key="centro_personas"
    )

    personas_centro = personas[personas["centro"] == centro_p]

    st.markdown("### Lista de personas")
    if personas_centro.empty:
        st.info("Todavía no hay personas cargadas para este centro.")
    else:
        st.dataframe(personas_centro, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona nueva")

    col1, col2 = st.columns(2)
    with col1:
        nombre_nuevo = st.text_input("Nombre completo", key="nombre_nuevo")
    with col2:
        frecuencia_nueva = st.selectbox(
            "Frecuencia",
            ["Diaria", "Semanal", "Mensual", "No asiste"],
            key="frecuencia_nueva"
        )

    if st.button("➕ Agregar persona", use_container_width=True, key="btn_agregar_persona"):
        if nombre_nuevo.strip() == "":
            st.error("Escribí un nombre.")
        else:
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

    personas_centro = personas[personas["centro"] == centro_p]  # recargar
    edit = st.data_editor(
        personas_centro,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_personas"
    )

    if st.button("💾 Guardar cambios", use_container_width=True, key="btn_guardar_personas"):
        # Sacamos las filas de ese centro y reemplazamos por el editado
        otras = personas[personas["centro"] != centro_p]
        personas = pd.concat([otras, edit], ignore_index=True)
        guardar_personas(personas)
        st.success("Cambios guardados")


# =====================================================
# TAB 3 — REPORTES
# =====================================================
with tab_reportes:
    st.subheader("Reportes de asistencia")

    if resumen.empty:
        st.info("No hay datos cargados todavía.")
    else:
        centros_sel = st.multiselect(
            "Seleccionar centros",
            CENTROS,
            default=CENTROS,
            key="centros_reportes"
        )

        df = resumen[resumen["centro"].isin(centros_sel)].copy()
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

        if df.empty:
            st.info("No hay datos para esos filtros.")
        else:
            st.markdown("### Totales por centro")
            totales = df.groupby("centro")["total_presentes"].sum()
            st.bar_chart(totales)

            st.markdown("### Evolución total")
            linea = (
                df.groupby("fecha")["total_presentes"]
                .sum()
                .sort_index()
            )
            st.line_chart(linea)

            st.markdown("---")
            st.markdown("### Casa Maranatha — Totales por espacio")
            df_mara = df[df["centro"] == "Casa Maranatha"]
            if not df_mara.empty:
                por_espacio = df_mara.groupby("espacio")["total_presentes"].sum()
                st.bar_chart(por_espacio)
            else:
                st.info("No hay datos de Casa Maranatha en este rango.")

            st.markdown("---")
            st.subheader("Exportar datos")
            st.download_button(
                "⬇️ Descargar CSV para Google Sheets",
                df.to_csv(index=False).encode("utf-8"),
                "reporte_asistencia.csv",
                "text/csv",
                key="btn_descargar_csv"
            )
