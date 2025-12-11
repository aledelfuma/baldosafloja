import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta

# -----------------------------------------
# CONFIGURACIÓN BÁSICA Y ESTILO
# -----------------------------------------
st.set_page_config(page_title="Asistencia Centros Barriales", layout="wide")

# Colores institucionales Hogar de Cristo
PRIMARY_COLOR = "#004E7B"   # Azul Hogar
ACCENT_COLOR = "#63296C"    # Violeta Hogar
BG_COLOR = "#EAF2F6"        # Fondo azul muy claro
CARD_BG = "#F5EFF7"         # Fondo violeta muy claro
TEXT_DARK = "#1A1A1A"

# Inyectar CSS para hacerlo más elegante y con identidad
CUSTOM_CSS = f"""
<style>
/* ----- Fondo general de la app ----- */
[data-testid="stAppViewContainer"] {{
    background-color: {BG_COLOR} !important;  /* celestito Hogar */
    color: {TEXT_DARK} !important;
}}

[data-testid="stHeader"] {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_DARK} !important;
    border-bottom: 1px solid rgba(0,0,0,0.06);
}}

/* Para algunos temas oscuros */
html, body {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_DARK} !important;
}}

/* ----- Sidebar ----- */
[data-testid="stSidebar"] {{
    background-color: #F4F6FB !important;   /* clarito, no blanco puro */
    border-right: 3px solid {PRIMARY_COLOR};
    color: {TEXT_DARK};
}}

[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3 {{
    color: {PRIMARY_COLOR} !important;
}}

/* ----- Títulos ----- */
h1, h2, h3, h4 {{
    color: {PRIMARY_COLOR};
    font-family: "Helvetica", "Arial", sans-serif;
}}

/* ----- Métricas (tarjetitas) ----- */
.stMetric {{
    background-color: {CARD_BG} !important;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    border-left: 6px solid {ACCENT_COLOR};
}}

/* ----- Tabs ----- */
.stTabs [role="tab"] {{
    border-radius: 999px;
    padding: 0.5rem 1.1rem;
    margin-right: 0.3rem;
    background-color: #FFFFFF;
    border: 1px solid rgba(0,0,0,0.12);
    font-weight: 500;
    color: {PRIMARY_COLOR};
}}
.stTabs [aria-selected="true"] {{
    background-color: {PRIMARY_COLOR};
    color: white !important;
    border-color: {PRIMARY_COLOR};
}}

/* ----- Botones ----- */
.stButton>button {{
    border-radius: 999px;
    border: none;
    padding: 0.45rem 1.2rem;
    font-weight: 600;
    background-color: {PRIMARY_COLOR};
    color: white;
}}
.stButton>button:hover {{
    background-color: {ACCENT_COLOR};
    color: white;
}}

/* ----- Inputs ----- */
input, select, textarea {{
    border-radius: 6px !important;
}}

/* ----- Tablas / dataframes ----- */
[data-testid="stDataFrame"] {{
    background-color: #FFFFFF;
    border-radius: 8px;
    padding: 0.6rem;
}}

/* Evitar textos grises raros */
[data-testid="stMarkdownContainer"] {{
    color: {TEXT_DARK};
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------
# CONSTANTES
# -----------------------------------------
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
LOGO_FILE = "logo_hogar.png"


# -----------------------------------------
# PERSONAS: nombre, frecuencia, centro, notas, fecha_alta
# -----------------------------------------
def cargar_personas():
    """
    Carga personas.csv admitiendo distintos encabezados/sep.
    Devuelve SIEMPRE columnas: nombre, frecuencia, centro, notas, fecha_alta
    """
    if not os.path.exists(PERSONAS_FILE):
        df_vacio = pd.DataFrame(
            columns=["nombre", "frecuencia", "centro", "notas", "fecha_alta"]
        )
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

    if df.empty:
        df = pd.DataFrame()

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
        elif c in ["notas", "observaciones"]:
            rename_map[c] = "notas"
        elif c in ["fecha_alta", "alta", "fechaingreso", "fecha_ingreso"]:
            rename_map[c] = "fecha_alta"

    df = df.rename(columns=rename_map)

    # 5) Asegurar columnas
    for col in ["nombre", "frecuencia", "centro", "notas", "fecha_alta"]:
        if col not in df.columns:
            df[col] = ""

    # 6) Dejar solo esas 5 en orden
    df = df[["nombre", "frecuencia", "centro", "notas", "fecha_alta"]]

    # 7) Guardar limpio
    df.to_csv(PERSONAS_FILE, index=False)

    # 8) Aviso si no había centro
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
# columnas: fecha, centro, espacio, total_presentes, notas,
#           coordinador, tipo_jornada, cerrado
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
                "cerrado",
            ]
        )
        df.to_csv(RESUMEN_FILE, index=False)
        return df

    df = pd.read_csv(RESUMEN_FILE)

    # Agregar columnas nuevas si faltan
    if "coordinador" not in df.columns:
        df["coordinador"] = ""
    if "tipo_jornada" not in df.columns:
        df["tipo_jornada"] = "Día habitual"
    if "cerrado" not in df.columns:
        df["cerrado"] = False

    df.to_csv(RESUMEN_FILE, index=False)
    return df


def guardar_resumen(df: pd.DataFrame):
    df.to_csv(RESUMEN_FILE, index=False)


# -----------------------------------------
# INICIALIZACIÓN
# -----------------------------------------
personas = cargar_personas()
resumen = cargar_resumen()

# Logo en la barra lateral (si existe)
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_column_width=True)

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

# Encabezado principal
st.markdown(
    f"## Sistema de Asistencia — Hogar de Cristo Bahía Blanca  \n"
    f"Estás trabajando sobre: **{centro_logueado}** — 👤 **{coordinador_logueado}**"
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
    total_sem = int(serie_sem.sum())

    # días con algún registro (aunque sea cerrado y 0)
    fechas_con_reg = set(df_sem["fecha"].dt.date.unique())
    dias_sin = 0
    for d in idx_sem:
        if d.date() not in fechas_con_reg:
            dias_sin += 1
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
tab_registro, tab_personas, tab_reportes, tab_global = st.tabs(
    [
        "📅 Registrar asistencia",
        "👥 Personas",
        "📊 Reportes / Base de datos",
        "🌍 Tablero global",
    ]
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

    fecha = st.date_input("Fecha", value=hoy, key="reg_fecha")

    col3, col4 = st.columns(2)
    with col3:
        if centro == "Casa Maranatha":
            espacio = st.selectbox(
                "Espacio",
                ESPACIOS_MARANATHA,
                key="reg_espacio",
            )
        else:
            espacio = "General"
            st.info("Este centro no usa espacios internos.")
    with col4:
        total_presentes = st.number_input(
            "Total presentes",
            min_value=0,
            step=1,
            key="reg_presentes",
        )

    col5, col6 = st.columns(2)
    with col5:
        tipo_jornada = st.selectbox(
            "Tipo de día",
            TIPOS_JORNADA,
            key="reg_tipo_jornada",
        )
    with col6:
        cerrado = st.checkbox(
            "Hoy el centro estuvo cerrado / no abrió",
            key="reg_cerrado",
        )

    if cerrado:
        st.info("Marcado como día cerrado: se registrará con 0 presentes.")
        total_presentes_val = 0
    else:
        total_presentes_val = int(total_presentes)

    notas = st.text_area("Notas (opcional)", key="reg_notas")

    if st.button(
        "💾 Guardar asistencia",
        use_container_width=True,
        key="reg_btn_guardar",
    ):
        nueva = {
            "fecha": fecha.isoformat(),
            "centro": centro,
            "espacio": espacio,
            "total_presentes": total_presentes_val,
            "notas": notas.strip(),
            "coordinador": coordinador,
            "tipo_jornada": tipo_jornada
            if not cerrado
            else "Centro cerrado / no abrió",
            "cerrado": cerrado,
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

        with st.expander("Ver últimos registros", expanded=False):
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
    personas_centro = personas[personas["centro"] == centro_p].copy()

    # Buscador rápido
    buscador = st.text_input(
        "Buscar por nombre",
        key="per_buscador",
        placeholder="Escribí parte del nombre...",
    )

    if buscador.strip():
        personas_centro_filtro = personas_centro[
            personas_centro["nombre"]
            .fillna("")
            .str.contains(buscador.strip(), case=False, na=False)
        ]
    else:
        personas_centro_filtro = personas_centro

    st.markdown("### Lista de personas")
    if personas_centro_filtro.empty:
        st.info("No se encontraron personas para este centro con ese filtro.")
    else:
        with st.expander("Ver lista filtrada", expanded=True):
            st.dataframe(
                personas_centro_filtro[
                    ["nombre", "frecuencia", "centro", "fecha_alta", "notas"]
                ],
                use_container_width=True,
            )

    # -------- Ficha simple de persona --------
    st.markdown("---")
    st.subheader("Ficha de persona")

    nombres_unicos = sorted(personas_centro["nombre"].dropna().unique().tolist())
    if nombres_unicos:
        persona_sel = st.selectbox(
            "Elegí una persona para ver su ficha",
            ["(Elegir)"] + nombres_unicos,
            key="per_ficha_sel",
        )
        if persona_sel != "(Elegir)":
            ficha = personas_centro[personas_centro["nombre"] == persona_sel].iloc[0]
            st.markdown(f"**Nombre:** {ficha['nombre']}")
            st.markdown(f"**Centro:** {ficha['centro']}")
            st.markdown(f"**Frecuencia:** {ficha['frecuencia']}")
            st.markdown(f"**Fecha de alta:** {ficha['fecha_alta'] or '-'}")
            st.markdown("**Notas / observaciones:**")
            st.write(ficha["notas"] or "—")
    else:
        st.info("Todavía no hay personas cargadas en este centro.")

    # -------- Agregar persona nueva --------
    st.markdown("---")
    st.subheader("Agregar persona nueva")

    col1, col2 = st.columns(2)
    with col1:
        nombre_nuevo = st.text_input("Nombre completo", key="per_nombre_nuevo")
    with col2:
        frecuencia_nueva = st.selectbox(
            "Frecuencia",
            ["Diaria", "Semanal", "Mensual", "No asiste"],
            key="per_frecuencia_nueva",
        )

    notas_nueva = st.text_area(
        "Notas / observaciones (opcional)",
        key="per_notas_nueva",
    )

    if st.button(
        "➕ Agregar persona",
        use_container_width=True,
        key="per_btn_agregar",
    ):
        if nombre_nuevo.strip() == "":
            st.error("Escribí un nombre.")
        else:
            nueva = {
                "nombre": nombre_nuevo.strip(),
                "frecuencia": frecuencia_nueva,
                "centro": centro_p,
                "notas": notas_nueva.strip(),
                "fecha_alta": hoy.isoformat(),
            }
            personas = pd.concat(
                [personas, pd.DataFrame([nueva])], ignore_index=True
            )
            guardar_personas(personas)
            st.success("Persona agregada correctamente")

    # -------- Editar personas --------
    st.markdown("---")
    st.subheader("Editar personas de este centro")

    personas_centro = personas[personas["centro"] == centro_p].copy()  # recargar
    if personas_centro.empty:
        st.info("Todavía no hay personas para editar en este centro.")
    else:
        edit = st.data_editor(
            personas_centro,
            use_container_width=True,
            num_rows="dynamic",
            key="per_editor_personas",
        )

        if st.button(
            "💾 Guardar cambios",
            use_container_width=True,
            key="per_btn_guardar_cambios",
        ):
            otras = personas[personas["centro"] != centro_p]
            personas = pd.concat([otras, edit], ignore_index=True)
            guardar_personas(personas)
            st.success("Cambios guardados")


# =====================================================
# TAB 3 — REPORTES / BASE DE DATOS (con filtro por año)
# =====================================================
with tab_reportes:
    st.subheader("Reportes y base de datos")

    if resumen.empty:
        st.info("No hay datos cargados todavía.")
    else:
        df = resumen.copy()
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = df["fecha"].dt.year

        años_disponibles = (
            df["anio"].dropna().unique().astype(int).tolist()
            if not df.empty
            else []
        )
        años_disponibles = sorted(años_disponibles, reverse=True)

        vista = st.radio(
            "¿Qué querés ver?",
            ["📅 Hoy / por día", "📆 Esta semana", "📚 Base de datos completa"],
            horizontal=True,
            key="rep_vista",
        )

        # ------------------- VISTA POR DÍA -------------------
        if vista == "📅 Hoy / por día":
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fecha_sel = st.date_input(
                    "Fecha", value=hoy, key="rep_dia_fecha"
                )
            with col_f2:
                centros_sel = st.multiselect(
                    "Centros",
                    CENTROS,
                    default=CENTROS,
                    key="rep_dia_centros",
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

            # Resumen por tipo de jornada
            st.markdown("#### Resumen por tipo de jornada")
            if not df_dia.empty:
                tipos = (
                    df_dia.groupby("tipo_jornada")["total_presentes"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(tipos)

            # Botón para saltar a vista semanal cuando hay un solo centro
            if len(centros_sel) == 1:
                if st.button(
                    "Ver semana de este centro",
                    key="rep_dia_btn_ir_semana",
                ):
                    st.session_state["rep_vista"] = "📆 Esta semana"
                    st.session_state["rep_sem_centro"] = centros_sel[0]

        # ------------------- VISTA SEMANAL -------------------
        elif vista == "📆 Esta semana":
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                centro_sem = st.selectbox(
                    "Centro",
                    CENTROS,
                    index=CENTROS.index(
                        st.session_state.get("rep_sem_centro", centro_logueado)
                    ),
                    key="rep_sem_centro",
                )

                # Filtro coordinador
                coords_centro = COORDINADORES.get(centro_sem, [])
                coord_sem = st.selectbox(
                    "Coordinador (opcional)",
                    ["Todos"] + coords_centro,
                    key="rep_sem_coord",
                )

            with col_w2:
                fin_semana = st.date_input(
                    "Hasta (inclusive)",
                    value=hoy,
                    key="rep_sem_fin",
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

                # días con al menos un registro (aunque sea cerrado)
                fechas_con_reg = set(df_sem["fecha"].dt.date.unique())
                dias_sin = 0
                for d in idx:
                    if d.date() not in fechas_con_reg:
                        dias_sin += 1

                dias_con = len(idx) - dias_sin
                prom_dia = total_sem / len(idx) if len(idx) > 0 else 0

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

                # Resumen por tipo de jornada en la semana
                st.markdown("#### Resumen por tipo de jornada (semana)")
                tipos_sem = (
                    df_sem.groupby("tipo_jornada")["total_presentes"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(tipos_sem)

        # ------------------- VISTA BASE COMPLETA (con filtro por año) -------------------
        else:  # "📚 Base de datos completa"
            st.markdown("### Base de datos de asistencia")

            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            with col_b1:
                centros_sel = st.multiselect(
                    "Centros",
                    CENTROS,
                    default=CENTROS,
                    key="rep_base_centros",
                )
            with col_b2:
                fecha_desde = st.date_input(
                    "Desde",
                    value=date(2025, 1, 1),
                    key="rep_base_desde",
                )
                fecha_hasta = st.date_input(
                    "Hasta",
                    value=hoy,
                    key="rep_base_hasta",
                )
            with col_b3:
                # Filtro coordinador global
                coords_globales = sorted(
                    [c for sub in COORDINADORES.values() for c in sub]
                )
                coord_base = st.selectbox(
                    "Coordinador (opcional)",
                    ["Todos"] + coords_globales,
                    key="rep_base_coord",
                )
            with col_b4:
                if años_disponibles:
                    año_sel = st.selectbox(
                        "Año (opcional)",
                        ["Todos"] + [str(a) for a in años_disponibles],
                        key="rep_base_year",
                    )
                else:
                    año_sel = "Todos"

            df_base = df[
                (df["centro"].isin(centros_sel))
                & (df["fecha"].dt.date >= fecha_desde)
                & (df["fecha"].dt.date <= fecha_hasta)
            ].copy()

            if coord_base != "Todos":
                df_base = df_base[df_base["coordinador"] == coord_base]

            if año_sel != "Todos":
                df_base = df_base[df_base["anio"] == int(año_sel)]

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
                    key="rep_base_btn_descargar_asistencia",
                )

                st.markdown("#### Resumen por tipo de jornada (periodo seleccionado)")
                tipos_base = (
                    df_base.groupby("tipo_jornada")["total_presentes"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(tipos_base)

            st.markdown("---")
            st.markdown("### Base de datos de personas")

            centro_personas_bd = st.selectbox(
                "Centro para ver personas",
                ["Todos"] + CENTROS,
                index=(["Todos"] + CENTROS).index(centro_logueado),
                key="rep_base_centro_personas",
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
                key="rep_base_btn_descargar_personas",
            )


# =====================================================
# TAB 4 — TABLERO GLOBAL (por año)
# =====================================================
with tab_global:
    st.subheader("Tablero global Hogar de Cristo Bahía Blanca")

    if resumen.empty:
        st.info("Todavía no hay datos cargados.")
    else:
        df = resumen.copy()
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = df["fecha"].dt.year

        años_disponibles = (
            df["anio"].dropna().unique().astype(int).tolist()
            if not df.empty
            else []
        )
        años_disponibles = sorted(años_disponibles, reverse=True)

        if años_disponibles:
            año_global = st.selectbox(
                "Año",
                años_disponibles,
                index=0,
                key="global_year",
            )
        else:
            año_global = hoy.year

        df_year = df[df["anio"] == año_global].copy()

        if df_year.empty:
            st.info(f"No hay datos para el año {año_global}.")
        else:
            # Serie anual diaria
            inicio = date(año_global, 1, 1)
            fin = date(año_global, 12, 31)
            idx = pd.date_range(inicio, fin, freq="D")

            serie_global = (
                df_year.groupby("fecha")["total_presentes"]
                .sum()
                .reindex(idx, fill_value=0)
            )

            total_año = int(serie_global.sum())
            dias_con_reg = int((serie_global > 0).sum())
            dias_totales = len(idx)
            prom_diario = total_año / dias_totales if dias_totales > 0 else 0

            # Centro con más ingresos en el año
            tot_por_centro = (
                df_year.groupby("centro")["total_presentes"]
                .sum()
                .sort_values(ascending=False)
            )
            if not tot_por_centro.empty:
                centro_top = tot_por_centro.index[0]
                centro_top_val = int(tot_por_centro.iloc[0])
            else:
                centro_top = "-"
                centro_top_val = 0

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(f"Total año {año_global}", total_año)
            with c2:
                st.metric("Promedio diario (año)", f"{prom_diario:.1f}")
            with c3:
                st.metric(
                    "Centro con más ingresos (año)",
                    f"{centro_top} ({centro_top_val})",
                )

            st.markdown(f"### Evolución diaria — año {año_global}")
            st.line_chart(serie_global)

            st.markdown("### Comparación por centro en el año")
            if not tot_por_centro.empty:
                st.bar_chart(tot_por_centro)

            st.markdown("### Resumen global por tipo de jornada en el año")
            tipos_año = (
                df_year.groupby("tipo_jornada")["total_presentes"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(tipos_año)

            with st.expander("Ver registros crudos del año"):
                st.dataframe(
                    df_year.sort_values("fecha", ascending=False),
                    use_container_width=True,
                )
