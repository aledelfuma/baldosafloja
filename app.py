import streamlit as st
import pandas as pd
import os
from datetime import date

# --------------------------------------------------
# CONFIGURACIÓN BÁSICA
# --------------------------------------------------
st.set_page_config(
    page_title="Asistencia Centros Barriales",
    layout="wide",
)

CENTROS = ["Nudo a Nudo", "Casa Maranatha", "Calle Belén"]
PERSONAS_FILE = "personas.csv"
RESUMEN_FILE = "resumen_diario.csv"


# --------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------
def cargar_personas():
    if os.path.exists(PERSONAS_FILE):
        return pd.read_csv(PERSONAS_FILE)
    else:
        df = pd.DataFrame(columns=[
            "id_persona", "nombre", "apellido", "edad",
            "anio_llegada", "centro", "activo"
        ])
        df.to_csv(PERSONAS_FILE, index=False)
        return df


def guardar_personas(df: pd.DataFrame):
    df.to_csv(PERSONAS_FILE, index=False)


def cargar_resumen():
    if os.path.exists(RESUMEN_FILE):
        return pd.read_csv(RESUMEN_FILE)
    else:
        df = pd.DataFrame(columns=[
            "id_registro", "fecha", "centro",
            "total_presentes", "notas"
        ])
        df.to_csv(RESUMEN_FILE, index=False)
        return df


def guardar_resumen(df: pd.DataFrame):
    df.to_csv(RESUMEN_FILE, index=False)


def generar_nuevo_id(df: pd.DataFrame, columna_id: str) -> int:
    if df.empty:
        return 1
    return int(df[columna_id].max()) + 1


# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
personas = cargar_personas()
resumen = cargar_resumen()

st.sidebar.title("Centros Barriales")
centro_logueado = st.sidebar.selectbox(
    "Centro (referente/coordinador)",
    CENTROS,
    help="Elegí tu centro barrial para que aparezca por defecto."
)

st.sidebar.markdown("---")
st.sidebar.write("App interna de registro de asistencia\nHogar de Cristo Bahía Blanca")


# --------------------------------------------------
# TABS PRINCIPALES
# --------------------------------------------------
tab_registro, tab_personas, tab_reportes = st.tabs(
    ["📅 Registrar día", "👤 Personas del centro", "📊 Reportes"]
)


# ==================================================
# TAB 1: REGISTRAR DÍA
# ==================================================
with tab_registro:
    st.subheader("Registrar día de asistencia")

    col1, col2, col3 = st.columns(3)
    with col1:
        centro = st.selectbox(
            "Centro barrial",
            CENTROS,
            index=CENTROS.index(centro_logueado),
        )
    with col2:
        fecha = st.date_input("Fecha", value=date.today())
    with col3:
        total_presentes = st.number_input(
            "Total de personas presentes",
            min_value=0,
            step=1
        )

    notas = st.text_area(
        "Notas (opcional)",
        placeholder="Ej: vinieron 3 vecinos nuevos, salida al parque, etc."
    )

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("💾 Guardar día", use_container_width=True):
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
                resumen = pd.concat(
                    [resumen, pd.DataFrame([nueva_fila])],
                    ignore_index=True
                )
                guardar_resumen(resumen)
                st.success("Día de asistencia guardado correctamente ✅")

    st.markdown("---")

    # Vista rápida del último mes para ese centro
    st.markdown("### Últimos registros de este centro")

    if not resumen.empty:
        df_centro = resumen[resumen["centro"] == centro].copy()
        df_centro["fecha"] = pd.to_datetime(df_centro["fecha"])
        df_centro = df_centro.sort_values("fecha", ascending=False)

        if df_centro.empty:
            st.info("Todavía no hay registros para este centro.")
        else:
            st.dataframe(df_centro.head(10))

            # Gráfico simple de la evolución reciente
            st.markdown("#### Evolución reciente de la asistencia")
            df_plot = df_centro.sort_values("fecha")
            df_plot = df_plot.set_index("fecha")["total_presentes"]
            st.line_chart(df_plot)


# ==================================================
# TAB 2: PERSONAS DEL CENTRO
# ==================================================
with tab_personas:
    st.subheader("Personas del centro barrial")

    centro_personas = st.selectbox(
        "Centro",
        CENTROS,
        index=CENTROS.index(centro_logueado),
        key="centro_personas_select"
    )

    personas_centro = personas[personas["centro"] == centro_personas]

    # Métricas arriba
    col_m1, col_m2, col_m3 = st.columns(3)
    total_personas = len(personas_centro)
    activas = len(personas_centro[personas_centro["activo"] == "si"])
    inactivas = total_personas - activas

    with col_m1:
        st.metric("Total personas cargadas", total_personas)
    with col_m2:
        st.metric("Personas activas", activas)
    with col_m3:
        st.metric("Personas inactivas", inactivas)

    st.markdown("### Lista general de personas")

    if personas_centro.empty:
        st.info("Todavía no hay personas cargadas en este centro.")
    else:
        st.dataframe(
            personas_centro[
                ["id_persona", "nombre", "apellido",
                 "edad", "anio_llegada", "activo"]
            ],
            use_container_width=True
        )

        with st.expander("Ver pequeños gráficos de este centro"):
            # Distribución de edades
            if personas_centro["edad"].notna().any():
                st.markdown("**Distribución de edades**")
                st.bar_chart(personas_centro["edad"].value_counts().sort_index())

            # Personas por año de llegada
            if personas_centro["anio_llegada"].notna().any():
                st.markdown("**Personas por año de llegada**")
                st.bar_chart(
                    personas_centro["anio_llegada"].value_counts().sort_index()
                )

    st.markdown("---")
    st.markdown("### Agregar nueva persona")

    with st.form("nueva_persona_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            nombre = st.text_input("Nombre")
        with col_b:
            apellido = st.text_input("Apellido")

        col_c, col_d = st.columns(2)
        with col_c:
            edad = st.number_input(
                "Edad (aprox.)",
                min_value=0,
                max_value=120,
                step=1
            )
        with col_d:
            anio_llegada = st.number_input(
                "Año estimado de llegada",
                min_value=1980,
                max_value=date.today().year,
                step=1,
                value=date.today().year
            )

        enviado = st.form_submit_button("➕ Agregar persona")

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
                personas = pd.concat(
                    [personas, pd.DataFrame([nueva_persona])],
                    ignore_index=True
                )
                guardar_personas(personas)
                st.success("Persona agregada correctamente ✅")

    st.markdown("---")
    st.markdown("### Editar datos / activar o desactivar personas")

    if not personas_centro.empty:
        edit_df = personas_centro[
            ["id_persona", "nombre", "apellido",
             "edad", "anio_llegada", "activo"]
        ].copy()

        edit_df = st.data_editor(
            edit_df,
            num_rows="fixed",
            hide_index=True,
            use_container_width=True
        )

        if st.button("💾 Guardar cambios en personas"):
            for _, row in edit_df.iterrows():
                mask = personas["id_persona"] == row["id_persona"]
                personas.loc[mask, "edad"] = row["edad"]
                personas.loc[mask, "anio_llegada"] = row["anio_llegada"]
                personas.loc[mask, "activo"] = row["activo"]

            guardar_personas(personas)
            st.success("Cambios guardados ✅")


# ==================================================
# TAB 3: REPORTES
# ==================================================
with tab_reportes:
    st.subheader("Reportes generales de asistencia")

    if resumen.empty:
        st.info("Todavía no hay datos de asistencia cargados.")
    else:
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            centros_sel = st.multiselect(
                "Centros",
                options=CENTROS,
                default=CENTROS,
                help="Podés elegir uno o varios centros."
            )
        with colf2:
            fecha_desde = st.date_input("Desde", value=date(2025, 1, 1))
        with colf3:
            fecha_hasta = st.date_input("Hasta", value=date.today())

        df = resumen.copy()
        df["fecha"] = pd.to_datetime(df["fecha"])

        # Filtro de fechas
        df = df[(df["fecha"] >= pd.to_datetime(fecha_desde)) &
                (df["fecha"] <= pd.to_datetime(fecha_hasta))]

        # Filtro de centros
        df = df[df["centro"].isin(centros_sel)]

        if df.empty:
            st.info("No hay datos para ese filtro.")
        else:
            # Métricas generales
            total_dias = df["fecha"].nunique()
            total_presentes_sum = df["total_presentes"].sum()
            promedio_por_dia = total_presentes_sum / total_dias if total_dias > 0 else 0

            # Totales por centro
            totales_por_centro = df.groupby("centro")["total_presentes"].sum()
            promedio_por_centro = df.groupby("centro")["total_presentes"].mean()

            colm1, colm2, colm3 = st.columns(3)
            with colm1:
                st.metric("Días registrados", total_dias)
            with colm2:
                st.metric("Total de personas (suma de todos los días)",
                          int(total_presentes_sum))
            with colm3:
                st.metric("Promedio de presentes por día",
                          f"{promedio_por_dia:.1f}")

            st.markdown("---")
            col_g1, col_g2 = st.columns(2)

            # Gráfico 1: evolución en el tiempo
            with col_g1:
                st.markdown("#### Evolución de la asistencia en el tiempo")
                df_line = df.sort_values("fecha")
                df_line2 = df_line.pivot_table(
                    index="fecha",
                    columns="centro",
                    values="total_presentes",
                    aggfunc="sum"
                )
                st.line_chart(df_line2)

            # Gráfico 2: totales por centro
            with col_g2:
                st.markdown("#### Total de presentes por centro")
                st.bar_chart(totales_por_centro)

            st.markdown("---")
            st.markdown("### Detalle por día")
            st.dataframe(df.sort_values("fecha", ascending=False),
                         use_container_width=True)

            # Descargar CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar reporte (CSV)",
                data=csv,
                file_name="reporte_asistencia_centros.csv",
                mime="text/csv",
            )
