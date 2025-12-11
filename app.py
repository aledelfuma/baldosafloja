import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta

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
    "Otros",
]

# Coordinadores por centro
COORDINADORES = {
    "Calle Belén": [
        "Natasha Carrari",
        "Estefanía Eberle",
        "Martín Pérez Santellán",
    ],
    "Nudo a Nudo": [
        "Camila Prada",
        "Julieta",
    ],
    "Casa Maranatha": [
        "Florencia",
        "Guillermina Cazenave",
    ],
}

# Tipos de día / jornada
TIPOS_JORNADA = [
    "Día habitual",
    "Jornada especial",
    "Reunión",
    "Misa / Celebración",
    "Otra",
]

# Archivos
PERSONAS_FILE = "personas.csv"
RESUMEN_FILE = "resumen_diario.csv"


# -----------------------------------------
# PERSONAS: nombre, frecuencia, centro
# -----------------------------------------
def cargar_personas():
    """Carga personas.csv admitiendo distintos encabezados/sep.
    Devuelve SIEMPRE columnas: nombre, frecuencia, centro
    """
    if not os.path.exists(PERSONAS_FILE):
        df_vacio = pd.DataFrame(columns=["nombre", "frecuencia", "centro"])
        df_vacio.to_csv(PERSONAS_FILE, index=False)
        return df_vacio

    # 1) Intento normal: separador coma
    try:
        df = pd.read_csv(PERSONAS_FILE)
    except Exception:
        df = pd.DataFrame()

    # 2) Si no encuentra 'centro', pruebo con separador ;
    if "centro" not in df.columns:
        try:
            df2 = pd.read_csv(PERSONAS_FILE, sep=";")
            if "centro" in df2.columns:
                df = df2
        except Exception:
            pass

    # 3) Normalizo nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # 4) Mapear columnas conocidas
    rename_map = {}
    for c in df.columns:
        if c in ["nombre", "persona", "personas"]:
            rename_map[c] = "nombre"
        elif c == "frecuencia":
            rename_map[c] = "frecuencia"
        elif "centro" in c:
            rename_map[c] = "centro"
    df = df.rename(columns=rename_map)

    # 5) Asegurar columnas
    for col in ["nombre", "frecuencia", "centro"]:
        if col not in df.columns:
            df[col] = ""

    # 6) Dejar solo esas 3
    df = df[["nombre", "frecuencia", "centro"]]

    # 7) Guardar limpio
    df.to_csv(PERSONAS_FILE, index=False)

    # 8) Avisar si no había centro
    if df["centro"].eq("").all():
        st.warning(
            "El archivo personas.csv no tenía una columna 'centro' clara. "
            "Se creó en blanco. Revisá que la primera fila diga algo como: "
            "nombre,frecuencia,centro"
        )

    return df


def guardar_personas(df: pd.DataFrame):
    df.to_csv(PERSONAS_FILE, index=False)


# -----------------------------------------
# RESUMEN DIARIO
# columnas: fecha, centro, espacio, total_presentes, notas, coordinador, tipo_jornada
# -----------------------------------------
def cargar_resumen():
    """Carga resumen_diario.csv y se asegura que tenga columnas nuevas."""
    if not os.path.exists(RESUMEN_FILE):
        df = pd.DataFrame(
            columns=[
                "fecha",
                "centro",
                "espacio",
                "total_presentes",
                "notas",
                "coordinador",
                "tipo_jornada",
            ]
        )
        df.to_csv(RESUMEN_FILE, index=False)
        return df

    df = pd.read_csv(RESUMEN_FILE)

    # Si es un archivo viejo sin columnas nuevas, las agrego
    if "coordinador" not in df.columns:
        df["coordinador"] = ""
    if "tipo_jornada" not in df.columns:
        df["tipo_jornada"] = "Día habitual"

    df.to_csv(RESUMEN_FILE, index=False)
    return df


def guardar_resumen(df: pd.DataFrame):
    df.to_csv(RESUMEN_FILE, index=False)


# -----------------------------------------
# INICIALIZACIÓN
# -----------------------------------------
personas = cargar_personas()
resumen = cargar_resumen()

# ----- Barra lateral: centro + coordinador -----
st.sidebar.title("Centros Barriales")
centro_logueado = st.sidebar.selectbox(
    "Soy referente de...",
    CENTROS,
    key="centro_sidebar",
)

# según centro, elegimos coordinador
lista_coord = COORDINADORES.get(centro_logueado, ["(sin coordinadores cargados)"])
coordinador_logueado = st.sidebar.selectbox(
    "¿Quién está cargando?",
    lista_coord,
    key="coord_sidebar",
)

st.sidebar.markdown("---")
st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

st.markdown(
    f"### Estás trabajando sobre: **{centro_logueado}**  \n"
    f"👤 Coordinador/a: **{coordinador_logueado}**"
)

# ---------- Mini tablero del centro logueado ----------
hoy = date.today()
hace_una_semana = hoy - timedelta(days=6)

df_centro_summary = resumen.copy()
if not df_centro_summary.empty:
    df_centro_summary["fecha"] = pd.to_datetime(
        df_centro_summary["fecha"], errors="coerce"
    )
    df_centro_summary = df_centro_summary[
        df_centro_summary["centro"] == centro_logueado
    ]

    df_hoy = df_centro_summary[df_centro_summary["fecha"].dt.date == hoy]
    df_sem = df_centro_summary[
        (df_centro_summary["fecha"].dt.date >= hace_una_semana)
        & (df_centro_summary["fecha"].dt.date <= hoy)
    ]

    total_hoy = int(df_hoy["total_presentes"].sum())
    idx_sem = pd.date_range(hace_una_semana, hoy, freq="D")
    serie_sem = (
        df_sem.groupby("fecha")["total_presentes"].sum().reindex(idx_sem, fill_value=0)
    )
    dias_sin = int((serie_sem == 0).sum())
    total_sem = int(serie_sem.sum())
else:
    total_hoy = 0
    total_sem = 0
    dias_sin = 7

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Ingresos HOY", total_hoy)
with c2:
    st.metric("Ingresos últimos 7 días", total_sem)
with c3:
    st.metric("Días sin cargar esta semana", dias_sin)

# ---------- Tabs principales ----------
tab_registro, tab_personas, tab_reportes = st.tabs(
    ["📅 Registrar asistencia", "👥 Personas", "📊 Reportes / Base de datos"]
)


# =====================================================
# TAB 1 — REGISTRO DE ASISTENCIA
# =====================================================
with tab_registro:
    st.subheader("Registrar asistencia para este centro")

    centro = centro_logueado  # siempre el de la barra lateral
    coordinador = coordinador_logueado

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Centro:** {centro}")
    with col2:
        st.write(f"**Coordinador/a:** {coordinador}")

    fecha = st.date_input("Fecha", value=hoy, key="fecha_registro")

    col3, col4 = st.columns(2)
    with col3:
        if centro == "Casa Maranatha":
            espacio = st.selectbox(
                "Espacio",
                ESPACIOS_MARANATHA,
                key="espacio_maranatha",
            )
        else:
            espacio = "General"
            st.info("Este centro no usa espacios internos.")
    with col4:
        total_presentes = st.number_input(
            "Total presentes",
            min_value=0,
            step=1,
            key="presentes_registro",
        )

    col5, col6 = st.columns(2)
    with col5:
        tipo_jornada = st.selectbox(
            "Tipo de día",
            TIPOS_JORNADA,
            key="tipo_jornada",
        )
    with col6:
        notas = st.text_area("Notas (opcional)", key="notas_registro")

    if st.button(
        "💾 Guardar asistencia",
        use_container_width=True,
        key="btn_guardar_asistencia",
    ):
        nueva = {
            "fecha": fecha.isoformat(),
            "centro": centro,
            "espacio": espacio,
            "total_presentes": int(total_presentes),
            "notas": notas.strip(),
            "coordinador": coordinador,
            "tipo_jornada": tipo_jornada,
        }
        resumen = pd.concat([resumen, pd.DataFrame([nueva])], ignore_index=True)
        guardar_resumen(resumen)
        st.success("Registro guardado exitosamente ✅")

    st.markdown("---")
    st.subheader("Últimos registros de este centro")

    if resumen.empty:
        st.info("Todavía no hay registros.")
    else:
        dfc = resumen[resumen["centro"] == centro].copy()
        dfc["fecha"] = pd.to_datetime(dfc["fecha"], errors="coerce")
        dfc = dfc.sort_values("fecha", ascending=False)

        with st.expander("Ver últimos registros"):
            st.dataframe(dfc.head(30), use_container_width=True)

        if not dfc.empty:
            st.write("### Evolución de asistencia (ingresos diarios)")
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
    st.subheader("Personas de este centro")

    centro_p = centro_logueado  # bloqueado al centro elegido en el costado

    personas_centro = personas[personas["centro"] == centro_p]

    st.markdown("### Lista de personas")
    if personas_centro.empty:
        st.info("Todavía no hay personas cargadas para este centro.")
    else:
        with st.expander("Ver lista completa", expanded=True):
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
            key="frecuencia_nueva",
        )

    if st.button(
        "➕ Agregar persona",
        use_container_width=True,
        key="btn_agregar_persona",
    ):
        if nombre_nuevo.strip() == "":
            st.error("Escribí un nombre.")
        else:
            nueva = {
                "nombre": nombre_nuevo.strip(),
                "frecuencia": frecuencia_nueva,
                "centro": centro_p,
            }
            personas = pd.concat(
                [personas, pd.DataFrame([nueva])], ignore_index=True
            )
            guardar_personas(personas)
            st.success("Persona agregada correctamente")

    st.markdown("---")
    st.subheader("Editar personas de este centro")

    personas_centro = personas[personas["centro"] == centro_p]  # recargar
    edit = st.data_editor(
        personas_centro,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_personas",
    )

    if st.button(
        "💾 Guardar cambios",
        use_container_width=True,
        key="btn_guardar_personas",
    ):
        otras = personas[personas["centro"] != centro_p]
        personas = pd.concat([otras, edit], ignore_index=True)
        guardar_personas(personas)
        st.success("Cambios guardados")


# =====================================================
# TAB 3 — REPORTES / BASE DE DATOS
# =====================================================
with tab_reportes:
    st.subheader("Reportes y base de datos")

    if resumen.empty:
        st.info("No hay datos cargados todavía.")
    else:
        vista = st.radio(
            "¿Qué querés ver?",
            ["📅 Hoy / por día", "📆 Esta semana", "📚 Base de datos completa"],
            horizontal=True,
            key="radio_vista_reportes",
        )

        df = resumen.copy()
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

        # ------------------- VISTA POR DÍA -------------------
        if vista == "📅 Hoy / por día":
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fecha_sel = st.date_input(
                    "Fecha", value=hoy, key="fecha_reportes_dia"
                )
            with col_f2:
                centros_sel = st.multiselect(
                    "Centros",
                    CENTROS,
                    default=CENTROS,
                    key="centros_reportes_dia",
                )

            df_dia = df[
                (df["fecha"].dt.date == fecha_sel)
                & (df["centro"].isin(centros_sel))
            ]

            st.markdown(f"### Resumen del día {fecha_sel.strftime('%d/%m/%Y')}")

            # Métricas por centro
            resumen_centros = (
                df_dia.groupby("centro")["total_presentes"]
                .sum()
                .reindex(centros_sel)
                .fillna(0)
            )

            col_m1, col_m2, col_m3 = st.columns(3)
            total_hoy = resumen_centros.sum()
            centros_con_reg = (resumen_centros > 0).sum()
            centros_sin_reg = len(centros_sel) - centros_con_reg

            with col_m1:
                st.metric("Total de personas (todos los centros)", int(total_hoy))
            with col_m2:
                st.metric("Centros con registro", int(centros_con_reg))
            with col_m3:
                st.metric("Centros SIN registro", int(centros_sin_reg))

            st.markdown("#### Detalle por centro")
            st.dataframe(
                resumen_centros.rename("total_presentes").reset_index(),
                use_container_width=True,
            )

            st.markdown("#### Centros sin registro (posible olvido)")
            faltantes = resumen_centros[resumen_centros == 0].index.tolist()
            if faltantes:
                st.error(", ".join(faltantes))
            else:
                st.success(
                    "Todos los centros seleccionados cargaron algo para este día."
                )

            with st.expander("Ver registros detallados del día"):
                st.dataframe(df_dia, use_container_width=True)

            # Botón para saltar a vista semanal cuando hay un solo centro
            if len(centros_sel) == 1:
                if st.button(
                    "Ver semana de este centro",
                    key="btn_ir_semana_desde_dia",
                ):
                    st.session_state["radio_vista_reportes"] = "📆 Esta semana"
                    st.session_state["centro_semana"] = centros_sel[0]

        # ------------------- VISTA SEMANAL -------------------
        elif vista == "📆 Esta semana":
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                centro_sem = st.selectbox(
                    "Centro",
                    CENTROS,
                    index=CENTROS.index(
                        st.session_state.get("centro_semana", centro_logueado)
                    ),
                    key="centro_semana",
                )

                # Filtro coordinador
                coords_centro = COORDINADORES.get(centro_sem, [])
                coord_sem = st.selectbox(
                    "Coordinador (opcional)",
                    ["Todos"] + coords_centro,
                    key="coord_semana",
                )

            with col_w2:
                fin_semana = st.date_input(
                    "Hasta (inclusive)",
                    value=hoy,
                    key="fin_semana",
                )

            inicio_semana = fin_semana - timedelta(days=6)

            df_sem = df[
                (df["centro"] == centro_sem)
                & (df["fecha"].dt.date >= inicio_semana)
                & (df["fecha"].dt.date <= fin_semana)
            ].copy()

            if coord_sem != "Todos":
                df_sem = df_sem[df_sem["coordinador"] == coord_sem]

            st.markdown(
                f"### {centro_sem} — últimos 7 días "
                f"({inicio_semana.strftime('%d/%m/%Y')} al {fin_semana.strftime('%d/%m/%Y')})"
            )

            if df_sem.empty:
                st.info("No hay registros en esos días.")
            else:
                # Reindexar para ver también días sin registro
                idx = pd.date_range(inicio_semana, fin_semana, freq="D")
                serie = (
                    df_sem.groupby("fecha")["total_presentes"]
                    .sum()
                    .reindex(idx, fill_value=0)
                )

                total_sem = int(serie.sum())
                dias_con = int((serie > 0).sum())
                dias_sin = int((serie == 0).sum())
                prom_dia = total_sem / 7

                cm1, cm2, cm3, cm4 = st.columns(4)
                with cm1:
                    st.metric("Total semana", total_sem)
                with cm2:
                    st.metric("Promedio por día", f"{prom_dia:.1f}")
                with cm3:
                    st.metric("Días con registro", dias_con)
                with cm4:
                    st.metric("Días sin registro", dias_sin)

                st.markdown("#### Evolución en la semana")
                st.line_chart(serie)

                st.markdown("#### Tabla por día")
                tabla_sem = serie.rename("total_presentes").reset_index()
                tabla_sem = tabla_sem.rename(columns={"index": "fecha"})
                with st.expander("Ver tabla detallada por día", expanded=True):
                    st.dataframe(tabla_sem, use_container_width=True)

                with st.expander("Ver registros crudos de la semana"):
                    st.dataframe(df_sem.sort_values("fecha"), use_container_width=True)

        # ------------------- VISTA BASE COMPLETA -------------------
        else:  # "📚 Base de datos completa"
            st.markdown("### Base de datos de asistencia")

            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                centros_sel = st.multiselect(
                    "Centros",
                    CENTROS,
                    default=CENTROS,
                    key="centros_base",
                )
            with col_b2:
                fecha_desde = st.date_input(
                    "Desde",
                    value=date(2025, 1, 1),
                    key="fecha_desde_base",
                )
                fecha_hasta = st.date_input(
                    "Hasta",
                    value=hoy,
                    key="fecha_hasta_base",
                )
            with col_b3:
                # Filtro coordinador global
                coords_globales = sorted(
                    [c for sub in COORDINADORES.values() for c in sub]
                )
                coord_base = st.selectbox(
                    "Coordinador (opcional)",
                    ["Todos"] + coords_globales,
                    key="coord_base",
                )

            df_base = df[
                (df["centro"].isin(centros_sel))
                & (df["fecha"].dt.date >= fecha_desde)
                & (df["fecha"].dt.date <= fecha_hasta)
            ].copy()

            if coord_base != "Todos":
                df_base = df_base[df_base["coordinador"] == coord_base]

            if df_base.empty:
                st.info("No hay datos para esos filtros.")
            else:
                with st.expander("Ver registros de asistencia", expanded=True):
                    st.dataframe(
                        df_base.sort_values("fecha", ascending=False),
                        use_container_width=True,
                    )

                st.download_button(
                    "⬇️ Descargar asistencia (CSV)",
                    df_base.to_csv(index=False).encode("utf-8"),
                    "base_asistencia.csv",
                    "text/csv",
                    key="btn_descargar_asistencia_base",
                )

            st.markdown("---")
            st.markdown("### Base de datos de personas")

            centro_personas_bd = st.selectbox(
                "Centro para ver personas",
                ["Todos"] + CENTROS,
                index=(["Todos"] + CENTROS).index(centro_logueado),
                key="centro_personas_base",
            )

            if centro_personas_bd == "Todos":
                df_personas_bd = personas.copy()
            else:
                df_personas_bd = personas[personas["centro"] == centro_personas_bd]

            with st.expander("Ver personas", expanded=True):
                st.dataframe(df_personas_bd, use_container_width=True)

            st.download_button(
                "⬇️ Descargar personas (CSV)",
                df_personas_bd.to_csv(index=False).encode("utf-8"),
                "base_personas.csv",
                "text/csv",
                key="btn_descargar_personas_base",
            )
