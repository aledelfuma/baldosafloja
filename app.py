import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="Asistencia Centros Barriales", layout="wide")

CENTROS = ["Nudo a Nudo", "Casa Maranatha", "Calle Belén"]

# Espacios por centro (podés agregar/sacar tranquilo)
ESPACIOS_POR_CENTRO = {
    "Casa Maranatha": [
        "Taller de costura",
        "Apoyo escolar primaria",
        "Apoyo escolar secundaria",
        "FINES",
        "Espacio Joven",
        "La Ronda",
        "Otros"
    ],
    "Calle Belén": [
        "Centro abierto",
        "Talleres",
        "Apoyo escolar",
        "Otros"
    ],
    "Nudo a Nudo": [
        "Espacio general",
        "Talleres",
        "Otros"
    ]
}

TURNOS = ["Mañana", "Tarde", "Noche", "Continuo"]

PERSONAS_FILE = "personas.csv"
RESUMEN_FILE = "resumen_diario.csv"


# ---------- AUXILIARES ----------
def cargar_personas():
    if os.path.exists(PERSONAS_FILE):
        return pd.read_csv(PERSONAS_FILE)
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
    df = pd.DataFrame(columns=[
        "id_registro", "fecha", "centro", "espacio",
        "turno", "total_presentes", "notas"
    ])
    df.to_csv(RESUMEN_FILE, index=False)
    return df


def guardar_resumen(df: pd.DataFrame):
    df.to_csv(RESUMEN_FILE, index=False)


def generar_nuevo_id(df: pd.DataFrame, col: str) -> int:
    if df.empty:
        return 1
    return int(df[col].max()) + 1


# ---------- CARGA ----------
personas = cargar_personas()
resumen = cargar_resumen()

st.sidebar.title("Centros Barriales")
centro_logueado = st.sidebar.selectbox(
    "Centro (referente/coordinador)",
    CENTROS
)
st.sidebar.markdown("---")
st.sidebar.caption("App interna de registro de asistencia\nHogar de Cristo Bahía Blanca")

tab_registro, tab_personas, tab_reportes = st.tabs(
    ["📅 Registrar día / espacio", "👤 Personas del centro", "📊 Reportes"]
)

# ======================================================
# TAB 1: REGISTRAR DÍA / ESPACIO
# ======================================================
with tab_registro:
    st.subheader("Registrar asistencia de un espacio")

    col1, col2 = st.columns(2)
    with col1:
        centro = st.selectbox(
            "Centro barrial",
            CENTROS,
            index=CENTROS.index(centro_logueado),
            key="centro_registro"
        )
    with col2:
        fecha = st.date_input("Fecha", value=date.today())

    col3, col4, col5 = st.columns(3)
    with col3:
        espacios = ESPACIOS_POR_CENTRO.get(centro, ["General"])
        espacio = st.selectbox("Espacio / taller", espacios)
    with col4:
        turno = st.selectbox("Turno", TURNOS, index=1)  # por defecto Tarde
    with col5:
        total_presentes = st.number_input(
            "Total presentes en ese espacio",
            min_value=0,
            step=1
        )

    notas = st.text_area(
        "Notas (opcional)",
        placeholder="Ej: vinieron 3 nuevos, faltó tal chico, salida, etc."
    )

    if st.button("💾 Guardar registro de este espacio", use_container_width=True):
        id_registro = generar_nuevo_id(resumen, "id_registro")
        nueva_fila = {
            "id_registro": id_registro,
            "fecha": fecha.isoformat(),
            "centro": centro,
            "espacio": espacio,
            "turno": turno,
            "total_presentes": int(total_presentes),
            "notas": notas.strip()
        }
        resumen = pd.concat([resumen, pd.DataFrame([nueva_fila])], ignore_index=True)
        guardar_resumen(resumen)
        st.success("Asistencia del espacio guardada correctamente ✅")

    st.markdown("---")
    st.markdown("### Últimos registros de este centro")

    if resumen.empty:
        st.info("Todavía no hay registros.")
    else:
        df_centro = resumen[resumen["centro"] == centro].copy()
        df_centro["fecha"] = pd.to_datetime(df_centro["fecha"])
        df_centro = df_centro.sort_values(["fecha", "espacio"], ascending=[False, True])

        if df_centro.empty:
            st.info("Todavía no hay registros para este centro.")
        else:
            st.dataframe(df_centro.head(15), use_container_width=True)

            st.markdown("#### Evolución de la asistencia total del centro")
            df_agr = (
                df_centro.groupby("fecha")["total_presentes"]
                .sum()
                .reset_index()
                .set_index("fecha")
            )
            st.line_chart(df_agr)


# ======================================================
# TAB 2: PERSONAS DEL CENTRO
# ======================================================
with tab_personas:
    st.subheader("Personas del centro barrial")

    centro_p = st.selectbox(
        "Centro",
        CENTROS,
        index=CENTROS.index(centro_logueado),
        key="centro_personas"
    )

    personas_centro = personas[personas["centro"] == centro_p]

    col_m1, col_m2, col_m3 = st.columns(3)
    total_personas = len(personas_centro)
    activas = len(personas_centro[personas_centro["activo"] == "si"])
    inactivas = total_personas - activas

    with col_m1:
        st.metric("Total personas cargadas", total_personas)
    with col_m2:
        st.metric("Personas activas", activas)
    with col_m3:
        st.metric("Inactivas", inactivas)

    st.markdown("### Lista general")
    if personas_centro.empty:
        st.info("Todavía no hay personas cargadas en este centro.")
    else:
        st.dataframe(
            personas_centro[
                ["id_persona", "nombre", "apellido", "edad", "anio_llegada", "activo"]
            ],
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("### Agregar nueva persona")

    with st.form("form_nueva_persona"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre")
        with c2:
            apellido = st.text_input("Apellido")

        c3, c4 = st.columns(2)
        with c3:
            edad = st.number_input("Edad (aprox.)", min_value=0, max_value=120, step=1)
        with c4:
            anio_llegada = st.number_input(
                "Año estimado de llegada",
                min_value=1980,
                max_value=date.today().year,
                value=date.today().year,
                step=1
            )

        enviar = st.form_submit_button("➕ Agregar")

        if enviar:
            if not nombre.strip() and not apellido.strip():
                st.error("Poné al menos nombre o apellido.")
            else:
                id_persona = generar_nuevo_id(personas, "id_persona")
                nueva = {
                    "id_persona": id_persona,
                    "nombre": nombre.strip(),
                    "apellido": apellido.strip(),
                    "edad": int(edad),
                    "anio_llegada": int(anio_llegada),
                    "centro": centro_p,
                    "activo": "si"
                }
                personas = pd.concat([personas, pd.DataFrame([nueva])], ignore_index=True)
                guardar_personas(personas)
                st.success("Persona agregada ✅")

    st.markdown("---")
    st.markdown("### Editar datos / activar o desactivar")

    if not personas_centro.empty:
        edit_df = personas_centro[
            ["id_persona", "nombre", "apellido", "edad", "anio_llegada", "activo"]
        ].copy()

        edit_df = st.data_editor(edit_df, num_rows="fixed", hide_index=True, use_container_width=True)

        if st.button("💾 Guardar cambios en personas"):
            for _, row in edit_df.iterrows():
                mask = personas["id_persona"] == row["id_persona"]
                personas.loc[mask, "edad"] = row["edad"]
                personas.loc[mask, "anio_llegada"] = row["anio_llegada"]
                personas.loc[mask, "activo"] = row["activo"]
            guardar_personas(personas)
            st.success("Cambios guardados ✅")


# ======================================================
# TAB 3: REPORTES
# ======================================================
with tab_reportes:
    st.subheader("Reportes generales de asistencia")

    if resumen.empty:
        st.info("Todavía no hay datos cargados.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            centros_sel = st.multiselect(
                "Centros",
                options=CENTROS,
                default=CENTROS
            )
        with c2:
            fecha_desde = st.date_input("Desde", value=date(2025, 1, 1))
        with c3:
            fecha_hasta = st.date_input("Hasta", value=date.today())

        df = resumen.copy()
        df["fecha"] = pd.to_datetime(df["fecha"])

        df = df[(df["fecha"] >= pd.to_datetime(fecha_desde)) &
                (df["fecha"] <= pd.to_datetime(fecha_hasta))]

        df = df[df["centro"].isin(centros_sel)]

        if df.empty:
            st.info("No hay datos para ese filtro.")
        else:
            # Métricas generales (todo junto)
            total_dias = df["fecha"].nunique()
            total_presentes = df["total_presentes"].sum()
            promedio_dia = total_presentes / total_dias if total_dias > 0 else 0

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Días con registros", total_dias)
            with m2:
                st.metric("Total de personas (suma de todos los espacios)", int(total_presentes))
            with m3:
                st.metric("Promedio por día", f"{promedio_dia:.1f}")

            st.markdown("---")
            g1, g2 = st.columns(2)

            # Totales por centro
            with g1:
                st.markdown("#### Total por centro")
                tot_centro = df.groupby("centro")["total_presentes"].sum()
                st.bar_chart(tot_centro)

            # Totales por espacio
            with g2:
                st.markdown("#### Total por espacio (todos los centros elegidos)")
                tot_espacio = df.groupby("espacio")["total_presentes"].sum().sort_values(ascending=False)
                st.bar_chart(tot_espacio)

            st.markdown("---")
            st.markdown("### Detalle por día y espacio")

            df_det = df.sort_values(["fecha", "centro", "espacio"], ascending=[False, True, True])
            st.dataframe(df_det, use_container_width=True)

            # Descarga
            csv = df_det.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar reporte (CSV)",
                data=csv,
                file_name="reporte_asistencia_centros_y_espacios.csv",
                mime="text/csv",
            )
