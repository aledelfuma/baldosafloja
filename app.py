import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="Asistencia Centros Barriales", layout="wide")

CENTROS = ["Nudo a Nudo", "Casa Maranatha", "Calle Belén"]

PERSONAS_FILE = "personas.csv"
RESUMEN_FILE = "resumen_diario.csv"


# ---------- FUNCIONES AUXILIARES ----------

def cargar_personas():
    if os.path.exists(PERSONAS_FILE):
        return pd.read_csv(PERSONAS_FILE)
    else:
        df = pd.DataFrame(columns=[
            "id_persona", "nombre", "apellido", "edad", "anio_llegada",
            "centro", "activo"
        ])
        df.to_csv(PERSONAS_FILE, index=False)
        return df


def guardar_personas(df):
    df.to_csv(PERSONAS_FILE, index=False)


def cargar_resumen():
    if os.path.exists(RESUMEN_FILE):
        return pd.read_csv(RESUMEN_FILE)
    else:
        df = pd.DataFrame(columns=[
            "id_registro", "fecha", "centro", "total_presentes", "notas"
        ])
        df.to_csv(RESUMEN_FILE, index=False)
        return df


def guardar_resumen(df):
    df.to_csv(RESUMEN_FILE, index=False)


def generar_nuevo_id(df, columna_id):
    if df.empty:
        return 1
    else:
        return int(df[columna_id].max()) + 1


# ---------- CARGA DE DATOS ----------
personas = cargar_personas()
resumen = cargar_resumen()


# ---------- SIDEBAR ----------
st.sidebar.title("Centros Barriales")
modo = st.sidebar.radio(
    "Seleccioná sección",
    ["Registrar día", "Personas del centro", "Reportes"]
)

# Podés agregar algo tipo “login” sencillito:
centro_logueado = st.sidebar.selectbox("Centro (coordinador)", CENTROS)


# ---------- MODO 1: REGISTRAR DÍA ----------
if modo == "Registrar día":
    st.title("Registrar día de asistencia")

    col1, col2, col3 = st.columns(3)
    with col1:
        centro = st.selectbox("Centro barrial", CENTROS, index=CENTROS.index(centro_logueado))
    with col2:
        fecha = st.date_input("Fecha", value=date.today())
    with col3:
        total_presentes = st.number_input("Total de personas presentes", min_value=0, step=1)

    notas = st.text_area("Notas (opcional)", placeholder="Ej: vinieron 3 vecinos nuevos...")

    if st.button("Guardar día"):
        if total_presentes < 0:
            st.error("El total de presentes no puede ser negativo.")
        else:
            id_registro = generar_nuevo_id(resumen, "id_registro")
            nueva_fila = {
                "id_registro": id_registro,
                "fecha": fecha.isoformat(),
                "centro": centro,
                "total_presentes": int(total_presentes),
                "notas": notas.strip()
            }
            resumen = pd.concat([resumen, pd.DataFrame([nueva_fila])], ignore_index=True)
            guardar_resumen(resumen)
            st.success("Día de asistencia guardado correctamente.")


# ---------- MODO 2: PERSONAS DEL CENTRO ----------
elif modo == "Personas del centro":
    st.title("Personas del centro barrial")

    centro_personas = st.selectbox("Centro", CENTROS, index=CENTROS.index(centro_logueado))

    # Filtrar personas del centro
    personas_centro = personas[personas["centro"] == centro_personas]

    st.subheader(f"Lista de personas - {centro_personas}")

    if personas_centro.empty:
        st.info("Todavía no hay personas cargadas en este centro.")
    else:
        st.dataframe(personas_centro[["id_persona", "nombre", "apellido", "edad", "anio_llegada", "activo"]])

    st.markdown("---")
    st.subheader("Agregar nueva persona")

    with st.form("nueva_persona_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            nombre = st.text_input("Nombre")
        with col_b:
            apellido = st.text_input("Apellido")

        col_c, col_d = st.columns(2)
        with col_c:
            edad = st.number_input("Edad (aprox.)", min_value=0, max_value=120, step=1)
        with col_d:
            anio_llegada = st.number_input("Año estimado de llegada", min_value=1980, max_value=date.today().year, step=1, value=date.today().year)

        enviado = st.form_submit_button("Agregar persona")

        if enviado:
            if nombre.strip() == "" and apellido.strip() == "":
                st.error("Poné al menos nombre o apellido.")
            else:
                id_persona = generar_nuevo_id(personas, "id_persona")
                nueva_persona = {
                    "id_persona": id_persona,
                    "nombre": nombre.strip(),
                    "apellido": apellido.strip(),
                    "edad": int(edad),
                    "anio_llegada": int(anio_llegada),
                    "centro": centro_personas,
                    "activo": "si"
                }
                personas = pd.concat([personas, pd.DataFrame([nueva_persona])], ignore_index=True)
                guardar_personas(personas)
                st.success("Persona agregada correctamente.")

    st.markdown("---")
    st.subheader("Editar estado de personas")

    if not personas_centro.empty:
        edit_df = personas_centro[["id_persona", "nombre", "apellido", "edad", "anio_llegada", "activo"]].copy()
        edit_df = st.data_editor(edit_df, num_rows="fixed", hide_index=True)

        if st.button("Guardar cambios en personas"):
            # Actualizar personas original
            for _, row in edit_df.iterrows():
                personas.loc[personas["id_persona"] == row["id_persona"], "edad"] = row["edad"]
                personas.loc[personas["id_persona"] == row["id_persona"], "anio_llegada"] = row["anio_llegada"]
                personas.loc[personas["id_persona"] == row["id_persona"], "activo"] = row["activo"]
            guardar_personas(personas)
            st.success("Cambios guardados.")


# ---------- MODO 3: REPORTES ----------
elif modo == "Reportes":
    st.title("Reportes generales")

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        centro_filtro = st.selectbox("Centro", ["Todos"] + CENTROS)
    with colf2:
        fecha_desde = st.date_input("Desde", value=date(2025, 1, 1))
    with colf3:
        fecha_hasta = st.date_input("Hasta", value=date.today())

    if resumen.empty:
        st.info("Todavía no hay datos de asistencia cargados.")
    else:
        df = resumen.copy()
        df["fecha"] = pd.to_datetime(df["fecha"])

        # Filtro de fechas
        df = df[(df["fecha"] >= pd.to_datetime(fecha_desde)) &
                (df["fecha"] <= pd.to_datetime(fecha_hasta))]

        # Filtro de centro
        if centro_filtro != "Todos":
            df = df[df["centro"] == centro_filtro]

        if df.empty:
            st.info("No hay datos para ese filtro.")
        else:
            # Métricas generales
            total_dias = df["fecha"].nunique()
            total_presentes_sum = df["total_presentes"].sum()
            promedio_por_dia = total_presentes_sum / total_dias if total_dias > 0 else 0

            colm1, colm2, colm3 = st.columns(3)
            with colm1:
                st.metric("Días registrados", total_dias)
            with colm2:
                st.metric("Total de personas (suma de todos los días)", int(total_presentes_sum))
            with colm3:
                st.metric("Promedio de presentes por día", f"{promedio_por_dia:.1f}")

            st.markdown("### Detalle por día")
            st.dataframe(df.sort_values("fecha", ascending=False))

            # Descargar CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar reporte (CSV)",
                data=csv,
                file_name="reporte_asistencia_centros.csv",
                mime="text/csv",
            )
