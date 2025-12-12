import streamlit as st
import pandas as pd
import os
import uuid
from datetime import date, timedelta, datetime

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Asistencia Centros Barriales", layout="wide")

PRIMARY_COLOR = "#004E7B"
ACCENT_COLOR = "#63296C"

CUSTOM_CSS = f"""
<style>
/* ----- Sidebar ----- */
[data-testid="stSidebar"] {{
    background-color: #111827 !important;
    border-right: 3px solid {PRIMARY_COLOR};
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {PRIMARY_COLOR} !important;
}}

/* ----- Títulos ----- */
h1, h2, h3, h4 {{
    color: {PRIMARY_COLOR} !important;
    font-family: "Helvetica", "Arial", sans-serif;
}}

/* ----- Métricas ----- */
.stMetric {{
    background-color: #1f2633 !important;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    border-left: 6px solid {ACCENT_COLOR};
}}

/* ----- Tabs ----- */
.stTabs [role="tab"] {{
    border-radius: 999px;
    padding: 0.5rem 1.1rem;
    margin-right: 0.3rem;
    background-color: #1f2633;
    border: 1px solid rgba(255,255,255,0.15);
    font-weight: 500;
    color: #d1d5db;
}}
.stTabs [aria-selected="true"] {{
    background-color: {PRIMARY_COLOR};
    color: white !important;
    border-color: {PRIMARY_COLOR};
}}

/* ----- Botones ----- */
.stButton>button {{
    border-radius: 999px;
    padding: 0.45rem 1.2rem;
    background-color: {PRIMARY_COLOR};
    color: white;
    font-weight: 600;
    border: none;
}}
.stButton>button:hover {{
    background-color: {ACCENT_COLOR};
    color: white;
}}

/* ----- Tablas ----- */
[data-testid="stDataFrame"] {{
    background-color: #111827 !important;
    border-radius: 8px;
    padding: 0.6rem;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =====================================================
# CONSTANTES
# =====================================================
CENTROS = ["Nudo a Nudo", "Casa Maranatha", "Calle Belén"]

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar primaria",
    "Apoyo escolar secundaria",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otros",
]

COORDINADORES = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellán"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

TIPOS_JORNADA = [
    "Día habitual",
    "Jornada especial",
    "Reunión",
    "Misa / Celebración",
    "Otra",
]

PERSONAS_FILE = "personas.csv"
RESUMEN_FILE = "resumen_diario.csv"
RESUMEN_BACKUP_FILE = "resumen_diario_backup.csv"
LOGO_FILE = "logo_hogar.png"

# =====================================================
# USUARIOS / ROLES (1)
# - Si tenés secrets.toml, lo toma.
# - Si no, usa defaults.
# =====================================================
DEFAULT_USERS = {
    "admin": {"password": "hogar", "role": "admin", "centers": ["*"]},
    # Coordinadores (password simple por defecto: "hogar")
    "natasha": {"password": "hogar", "role": "coord", "centers": ["Calle Belén"]},
    "estefania": {"password": "hogar", "role": "coord", "centers": ["Calle Belén"]},
    "martin": {"password": "hogar", "role": "coord", "centers": ["Calle Belén"]},
    "camila": {"password": "hogar", "role": "coord", "centers": ["Nudo a Nudo"]},
    "julieta": {"password": "hogar", "role": "coord", "centers": ["Nudo a Nudo"]},
    "florencia": {"password": "hogar", "role": "coord", "centers": ["Casa Maranatha"]},
    "guillermina": {"password": "hogar", "role": "coord", "centers": ["Casa Maranatha"]},
}

def load_users():
    try:
        # secrets.toml esperado:
        # [users]
        # admin = {password="...", role="admin", centers=["*"]}
        # ...
        if "users" in st.secrets:
            raw = st.secrets["users"]
            users = {}
            for k in raw:
                users[k] = {
                    "password": raw[k].get("password", ""),
                    "role": raw[k].get("role", "coord"),
                    "centers": raw[k].get("centers", []),
                }
            return users
    except Exception:
        pass
    return DEFAULT_USERS

USERS = load_users()

# =====================================================
# HELPERS CSV
# =====================================================
def ensure_personas_file():
    if not os.path.exists(PERSONAS_FILE):
        df = pd.DataFrame(columns=["nombre", "frecuencia", "centro", "notas", "fecha_alta"])
        df.to_csv(PERSONAS_FILE, index=False)

def ensure_resumen_file():
    if not os.path.exists(RESUMEN_FILE):
        df = pd.DataFrame(columns=[
            "id_registro",
            "fecha",
            "centro",
            "espacio",
            "total_presentes",
            "notas",
            "coordinador",
            "tipo_jornada",
            "cerrado",
            "timestamp",
            "cargado_por",
            "accion",
        ])
        df.to_csv(RESUMEN_FILE, index=False)

def cargar_personas():
    ensure_personas_file()
    try:
        df = pd.read_csv(PERSONAS_FILE)
    except Exception:
        df = pd.DataFrame(columns=["nombre", "frecuencia", "centro", "notas", "fecha_alta"])

    df.columns = [c.strip().lower() for c in df.columns]
    # normalizar
    if "nombre" not in df.columns:
        # intenta mapear si venía como "personas"
        if "personas" in df.columns:
            df = df.rename(columns={"personas": "nombre"})
        else:
            df["nombre"] = ""

    for col in ["frecuencia", "centro", "notas", "fecha_alta"]:
        if col not in df.columns:
            df[col] = ""

    df = df[["nombre", "frecuencia", "centro", "notas", "fecha_alta"]]
    df.to_csv(PERSONAS_FILE, index=False)
    return df

def guardar_personas(df: pd.DataFrame):
    df.to_csv(PERSONAS_FILE, index=False)

def cargar_resumen():
    ensure_resumen_file()
    try:
        df = pd.read_csv(RESUMEN_FILE)
    except Exception:
        df = pd.DataFrame(columns=[
            "id_registro","fecha","centro","espacio","total_presentes","notas",
            "coordinador","tipo_jornada","cerrado","timestamp","cargado_por","accion"
        ])

    # asegurar columnas nuevas (8 auditoría)
    needed = [
        "id_registro","fecha","centro","espacio","total_presentes","notas",
        "coordinador","tipo_jornada","cerrado","timestamp","cargado_por","accion"
    ]
    for c in needed:
        if c not in df.columns:
            df[c] = ""

    # tipos
    df["total_presentes"] = pd.to_numeric(df["total_presentes"], errors="coerce").fillna(0).astype(int)
    df["cerrado"] = df["cerrado"].astype(str).str.lower().isin(["true", "1", "yes", "si", "sí"])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # guardar limpio
    df.to_csv(RESUMEN_FILE, index=False)
    return df

def backup_resumen():
    if os.path.exists(RESUMEN_FILE):
        try:
            with open(RESUMEN_FILE, "rb") as fsrc:
                data = fsrc.read()
            with open(RESUMEN_BACKUP_FILE, "wb") as fdst:
                fdst.write(data)
            return True
        except Exception:
            return False
    return False

def restore_backup():
    if os.path.exists(RESUMEN_BACKUP_FILE):
        try:
            with open(RESUMEN_BACKUP_FILE, "rb") as fsrc:
                data = fsrc.read()
            with open(RESUMEN_FILE, "wb") as fdst:
                fdst.write(data)
            return True
        except Exception:
            return False
    return False

def guardar_resumen(df: pd.DataFrame):
    df_out = df.copy()
    # estandarizar a CSV
    df_out.to_csv(RESUMEN_FILE, index=False)

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def new_id():
    return str(uuid.uuid4())

# =====================================================
# LOGIN / SESIÓN (1)
# =====================================================
def is_logged_in():
    return st.session_state.get("logged_in", False)

def do_login(username, password):
    u = USERS.get(username)
    if not u:
        return False, None
    if str(u.get("password", "")) != str(password):
        return False, None
    return True, u

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["user_meta"] = None

# =====================================================
# LOAD DATA
# =====================================================
personas = cargar_personas()
resumen = cargar_resumen()

# =====================================================
# SIDEBAR: LOGO + LOGIN
# =====================================================
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_column_width=True)

st.sidebar.title("Acceso")

if not is_logged_in():
    username = st.sidebar.text_input("Usuario", value="", key="login_user")
    password = st.sidebar.text_input("Contraseña", type="password", value="", key="login_pass")
    if st.sidebar.button("Ingresar", use_container_width=True):
        ok, meta = do_login(username.strip(), password)
        if ok:
            st.session_state["logged_in"] = True
            st.session_state["user"] = username.strip()
            st.session_state["user_meta"] = meta
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos.")
    st.stop()

# logout
st.sidebar.success(f"Conectado como: {st.session_state['user']}")
if st.sidebar.button("Salir", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["user_meta"] = None
    st.rerun()

user = st.session_state["user"]
user_meta = st.session_state["user_meta"] or {}
role = user_meta.get("role", "coord")
allowed_centers = user_meta.get("centers", [])

st.sidebar.markdown("---")
st.sidebar.subheader("Centro / Coordinador")

# Centro: admin puede elegir cualquiera, coordinador queda bloqueado
if role == "admin":
    centro_logueado = st.sidebar.selectbox("Centro", CENTROS, key="centro_sidebar")
else:
    # primer centro permitido
    centro_logueado = allowed_centers[0] if allowed_centers else CENTROS[0]
    st.sidebar.write(f"Centro asignado: **{centro_logueado}**")

# Coordinador: lista por centro (admin y coord eligen dentro del centro)
lista_coord = COORDINADORES.get(centro_logueado, [])
if not lista_coord:
    lista_coord = ["(sin coordinadores cargados)"]

# si no es admin, default a uno coherente con usuario (si coincide)
default_coord = lista_coord[0]
if role != "admin":
    # pequeño intento: si el user está en la lista por nombre parecido
    for c in lista_coord:
        if user.lower() in c.lower().replace(" ", "") or user.lower() in c.lower():
            default_coord = c
            break

coordinador_logueado = st.sidebar.selectbox(
    "¿Quién carga?",
    lista_coord,
    index=lista_coord.index(default_coord) if default_coord in lista_coord else 0,
    key="coord_sidebar",
)

st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

# =====================================================
# HEADER
# =====================================================
st.markdown(
    f"## Sistema de Asistencia — Hogar de Cristo Bahía Blanca  \n"
    f"Centro: **{centro_logueado}** — 👤 **{coordinador_logueado}** — Rol: **{role}**"
)

# =====================================================
# (2) ALERTAS DE OLVIDO: HOY + ÚLTIMOS 7 DÍAS
# =====================================================
hoy = date.today()
hace_una_semana = hoy - timedelta(days=6)

def registros_por_fecha(df, centro, day: date):
    if df.empty:
        return df
    dfx = df[(df["centro"] == centro) & (df["fecha"].dt.date == day)]
    return dfx

faltan_hoy = []
faltan_semana = []

for c in CENTROS:
    dfh = registros_por_fecha(resumen, c, hoy)
    if dfh.empty:
        faltan_hoy.append(c)

    # para semana: consideramos “faltante” si NO tiene NINGÚN registro en los 7 días
    dfs = resumen[(resumen["centro"] == c) &
                  (resumen["fecha"].dt.date >= hace_una_semana) &
                  (resumen["fecha"].dt.date <= hoy)]
    if dfs.empty:
        faltan_semana.append(c)

a1, a2, a3 = st.columns(3)
with a1:
    st.metric("Centros sin carga HOY", len(faltan_hoy))
with a2:
    st.metric("Centros sin carga (7 días)", len(faltan_semana))
with a3:
    # mini resumen centro actual (últimos 7 días)
    dfc = resumen[(resumen["centro"] == centro_logueado) &
                  (resumen["fecha"].dt.date >= hace_una_semana) &
                  (resumen["fecha"].dt.date <= hoy)]
    total_7 = int(dfc["total_presentes"].sum()) if not dfc.empty else 0
    st.metric(f"{centro_logueado} (7 días)", total_7)

if faltan_hoy:
    st.error("⚠️ Falta cargar HOY: " + ", ".join(faltan_hoy))
if faltan_semana:
    st.warning("ℹ️ Sin registros en los últimos 7 días: " + ", ".join(faltan_semana))

# =====================================================
# TABS
# =====================================================
tab_registro, tab_historial, tab_personas, tab_reportes, tab_admin = st.tabs(
    [
        "⚡ Carga rápida (día)",
        "🧾 Historial (editar / deshacer)",
        "👥 Personas",
        "📊 Reportes pro + Export",
        "🛠️ Admin / Auditoría",
    ]
)

# =====================================================
# TAB 1 — (3) CARGA RÁPIDA + (2) MARCAR CERRADO RÁPIDO
# =====================================================
with tab_registro:
    st.subheader("Carga rápida")

    colx1, colx2, colx3 = st.columns([1.2, 1.2, 1])

    with colx1:
        fecha = st.date_input("Fecha", value=hoy, key="quick_fecha")

    with colx2:
        if centro_logueado == "Casa Maranatha":
            espacio = st.selectbox("Espacio (Maranatha)", ESPACIOS_MARANATHA, key="quick_espacio")
        else:
            espacio = "General"
            st.info("Este centro carga en modo General (sin espacios).")

    with colx3:
        tipo_jornada = st.selectbox("Tipo de día", TIPOS_JORNADA, key="quick_tipo")

    presentes = st.number_input("Total presentes", min_value=0, step=1, value=0, key="quick_presentes")
    notas = st.text_area("Notas (opcional)", key="quick_notas")

    cbtn1, cbtn2 = st.columns(2)
    with cbtn1:
        if st.button("💾 Guardar asistencia", use_container_width=True, key="quick_guardar"):
            # Permiso: coordinador SOLO su centro (ya bloqueado), admin puede todo
            ok_backup = backup_resumen()

            nueva = {
                "id_registro": new_id(),
                "fecha": pd.to_datetime(fecha),
                "centro": centro_logueado,
                "espacio": espacio,
                "total_presentes": int(presentes),
                "notas": (notas or "").strip(),
                "coordinador": coordinador_logueado,
                "tipo_jornada": tipo_jornada,
                "cerrado": False,
                "timestamp": pd.to_datetime(now_ts()),
                "cargado_por": user,
                "accion": "crear",
            }

            resumen2 = pd.concat([resumen, pd.DataFrame([nueva])], ignore_index=True)
            guardar_resumen(resumen2)
            resumen = cargar_resumen()
            st.success("Guardado ✅" + (" (backup ok)" if ok_backup else " (sin backup)"))

    with cbtn2:
        if st.button("🚫 Marcar como CERRADO (0 presentes)", use_container_width=True, key="quick_cerrado"):
            ok_backup = backup_resumen()

            nueva = {
                "id_registro": new_id(),
                "fecha": pd.to_datetime(fecha),
                "centro": centro_logueado,
                "espacio": espacio,
                "total_presentes": 0,
                "notas": (notas or "").strip() or "Centro cerrado / no abrió",
                "coordinador": coordinador_logueado,
                "tipo_jornada": "Centro cerrado / no abrió",
                "cerrado": True,
                "timestamp": pd.to_datetime(now_ts()),
                "cargado_por": user,
                "accion": "cerrado",
            }

            resumen2 = pd.concat([resumen, pd.DataFrame([nueva])], ignore_index=True)
            guardar_resumen(resumen2)
            resumen = cargar_resumen()
            st.success("Registrado como cerrado ✅" + (" (backup ok)" if ok_backup else " (sin backup)"))

    st.markdown("---")
    st.write("### Vista rápida: últimos 14 días (este centro)")
    dfc = resumen[resumen["centro"] == centro_logueado].copy()
    dfc = dfc.dropna(subset=["fecha"])
    dfc = dfc[dfc["fecha"].dt.date >= (hoy - timedelta(days=13))]
    dfc = dfc.sort_values("fecha", ascending=True)

    if dfc.empty:
        st.info("Todavía no hay registros para mostrar.")
    else:
        serie = dfc.groupby("fecha")["total_presentes"].sum().sort_index()
        st.line_chart(serie)

# =====================================================
# TAB 2 — (4) HISTORIAL EDITABLE + BACKUP + DESHACER
# =====================================================
with tab_historial:
    st.subheader("Historial del centro (editar)")

    st.caption("Tip: antes de guardar cambios, la app crea un backup automático. Podés deshacer con 1 click.")

    # historial del centro
    dfx = resumen[resumen["centro"] == centro_logueado].copy()
    dfx = dfx.dropna(subset=["fecha"])
    dfx = dfx.sort_values("fecha", ascending=False).head(60)

    if dfx.empty:
        st.info("No hay registros todavía.")
    else:
        # columnas editables básicas (no tocar auditoría ni id)
        cols_show = [
            "id_registro","fecha","centro","espacio","total_presentes","notas",
            "coordinador","tipo_jornada","cerrado","timestamp","cargado_por","accion"
        ]
        dfx = dfx[cols_show]

        st.write("### Editar últimos 60 registros")
        edited = st.data_editor(
            dfx,
            use_container_width=True,
            num_rows="fixed",
            key="hist_editor",
        )

        csave, cundo = st.columns(2)

        with csave:
            if st.button("💾 Guardar cambios del historial", use_container_width=True, key="hist_save"):
                ok_backup = backup_resumen()

                # Permisos: coord solo puede editar registros de su centro (ya filtrado)
                # Guardamos cambios haciendo merge por id_registro
                base = resumen.copy()
                base_ids = set(edited["id_registro"].astype(str).tolist())

                # actualizamos filas editadas por id
                base["id_registro"] = base["id_registro"].astype(str)
                ed = edited.copy()
                ed["id_registro"] = ed["id_registro"].astype(str)

                # set auditoría para "editar"
                ed["timestamp"] = pd.to_datetime(now_ts())
                ed["cargado_por"] = user
                ed["accion"] = "editar"

                # merge: reemplazar filas que coinciden
                base_not = base[~base["id_registro"].isin(base_ids)]
                merged = pd.concat([base_not, ed], ignore_index=True)

                # normalizar tipos
                merged["fecha"] = pd.to_datetime(merged["fecha"], errors="coerce")
                merged["timestamp"] = pd.to_datetime(merged["timestamp"], errors="coerce")
                merged["total_presentes"] = pd.to_numeric(merged["total_presentes"], errors="coerce").fillna(0).astype(int)
                merged["cerrado"] = merged["cerrado"].astype(str).str.lower().isin(["true","1","yes","si","sí"])

                guardar_resumen(merged)
                resumen = cargar_resumen()
                st.success("Cambios guardados ✅" + (" (backup ok)" if ok_backup else " (sin backup)"))
                st.rerun()

        with cundo:
            if st.button("↩️ Deshacer (restaurar backup)", use_container_width=True, key="hist_undo"):
                ok = restore_backup()
                if ok:
                    resumen = cargar_resumen()
                    st.success("Backup restaurado ✅")
                    st.rerun()
                else:
                    st.error("No hay backup para restaurar (o falló la restauración).")

# =====================================================
# TAB 3 — PERSONAS (simple, sin el punto 6)
# =====================================================
with tab_personas:
    st.subheader(f"Personas — {centro_logueado}")

    dfp = personas[personas["centro"] == centro_logueado].copy()

    bus = st.text_input("Buscar nombre", placeholder="Escribí parte del nombre...", key="per_bus")
    if bus.strip():
        dfp = dfp[dfp["nombre"].fillna("").str.contains(bus.strip(), case=False, na=False)]

    if dfp.empty:
        st.info("No hay personas para mostrar con ese filtro.")
    else:
        st.dataframe(dfp[["nombre","frecuencia","centro","fecha_alta","notas"]], use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona")

    c1, c2 = st.columns(2)
    with c1:
        nombre_nuevo = st.text_input("Nombre completo", key="per_nombre")
    with c2:
        frecuencia = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual", "No asiste"], key="per_freq")

    notas = st.text_area("Notas (opcional)", key="per_notas")
    if st.button("➕ Agregar", use_container_width=True, key="per_add"):
        if not nombre_nuevo.strip():
            st.error("Escribí un nombre.")
        else:
            nueva = {
                "nombre": nombre_nuevo.strip(),
                "frecuencia": frecuencia,
                "centro": centro_logueado,
                "notas": (notas or "").strip(),
                "fecha_alta": date.today().isoformat(),
            }
            personas2 = pd.concat([personas, pd.DataFrame([nueva])], ignore_index=True)
            guardar_personas(personas2)
            personas = cargar_personas()
            st.success("Persona agregada ✅")
            st.rerun()

    st.markdown("---")
    st.subheader("Editar personas (centro actual)")
    dfp2 = personas[personas["centro"] == centro_logueado].copy()
    if dfp2.empty:
        st.info("No hay personas para editar.")
    else:
        edited_p = st.data_editor(dfp2, use_container_width=True, num_rows="dynamic", key="per_editor")
        if st.button("💾 Guardar cambios de personas", use_container_width=True, key="per_save"):
            otras = personas[personas["centro"] != centro_logueado].copy()
            personas_out = pd.concat([otras, edited_p], ignore_index=True)
            guardar_personas(personas_out)
            personas = cargar_personas()
            st.success("Cambios guardados ✅")
            st.rerun()

# =====================================================
# TAB 4 — (5) REPORTES PRO + (7) EXPORTACIONES
# =====================================================
with tab_reportes:
    st.subheader("Reportes pro")

    if resumen.empty or resumen["fecha"].isna().all():
        st.info("Todavía no hay datos cargados.")
    else:
        df = resumen.dropna(subset=["fecha"]).copy()
        df["anio"] = df["fecha"].dt.year
        df["dia"] = df["fecha"].dt.date

        # filtros
        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1:
            centros_sel = st.multiselect("Centros", CENTROS, default=[centro_logueado], key="rep_centros")
        with colf2:
            desde = st.date_input("Desde", value=(hoy - timedelta(days=28)), key="rep_desde")
        with colf3:
            hasta = st.date_input("Hasta", value=hoy, key="rep_hasta")
        with colf4:
            coord_all = sorted({c for lst in COORDINADORES.values() for c in lst})
            coord_sel = st.selectbox("Coordinador (opcional)", ["Todos"] + coord_all, key="rep_coord")

        dff = df[(df["centro"].isin(centros_sel)) &
                 (df["dia"] >= desde) &
                 (df["dia"] <= hasta)].copy()

        if coord_sel != "Todos":
            dff = dff[dff["coordinador"] == coord_sel]

        if dff.empty:
            st.info("No hay datos con esos filtros.")
        else:
            # --- Reporte 28 días tendencia ---
            st.markdown("### Tendencia (periodo seleccionado)")
            serie = dff.groupby("fecha")["total_presentes"].sum().sort_index()
            st.line_chart(serie)

            # --- Semana vs semana pasada ---
            st.markdown("### Semana vs semana pasada")
            fin = hoy
            ini = hoy - timedelta(days=6)
            fin_prev = hoy - timedelta(days=7)
            ini_prev = hoy - timedelta(days=13)

            w = df[(df["centro"].isin(centros_sel)) &
                   (df["dia"] >= ini) & (df["dia"] <= fin)]
            wp = df[(df["centro"].isin(centros_sel)) &
                    (df["dia"] >= ini_prev) & (df["dia"] <= fin_prev)]

            if coord_sel != "Todos":
                w = w[w["coordinador"] == coord_sel]
                wp = wp[wp["coordinador"] == coord_sel]

            tot_w = int(w["total_presentes"].sum()) if not w.empty else 0
            tot_wp = int(wp["total_presentes"].sum()) if not wp.empty else 0
            delta = (tot_w - tot_wp)
            delta_pct = (delta / tot_wp * 100) if tot_wp > 0 else None

            cA, cB, cC = st.columns(3)
            with cA:
                st.metric("Últimos 7 días", tot_w, delta=delta)
            with cB:
                st.metric("Semana pasada", tot_wp)
            with cC:
                st.metric("Δ %", f"{delta_pct:.1f}%" if delta_pct is not None else "—")

            # --- Comparación por centro (barras) ---
            st.markdown("### Comparación por centro (periodo)")
            by_center = dff.groupby("centro")["total_presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_center)

            # --- Ranking días pico ---
            st.markdown("### Top 10 días (periodo)")
            top_days = (
                dff.groupby("dia")["total_presentes"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            st.dataframe(top_days, use_container_width=True)

            # --- Por tipo de jornada ---
            st.markdown("### Por tipo de jornada (periodo)")
            by_tipo = dff.groupby("tipo_jornada")["total_presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_tipo)

            st.markdown("---")
            st.subheader("Exportaciones (1 click)")

            # Export 1: dataset filtrado
            st.download_button(
                "⬇️ Descargar asistencia FILTRADA (CSV)",
                dff.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                file_name="asistencia_filtrada.csv",
                mime="text/csv",
                use_container_width=True,
            )

            # Export 2: Centro actual semana
            df_centro_week = df[(df["centro"] == centro_logueado) &
                                (df["dia"] >= (hoy - timedelta(days=6))) &
                                (df["dia"] <= hoy)].copy()
            st.download_button(
                f"⬇️ Descargar {centro_logueado} (últimos 7 días)",
                df_centro_week.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                file_name=f"{centro_logueado}_7dias.csv".replace(" ", "_"),
                mime="text/csv",
                use_container_width=True,
            )

            # Export 3: Todo (solo admin)
            if role == "admin":
                st.download_button(
                    "⬇️ Descargar TODO (CSV)",
                    df.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                    file_name="asistencia_todo.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

# =====================================================
# TAB 5 — ADMIN / AUDITORÍA (8)
# =====================================================
with tab_admin:
    st.subheader("Admin / Auditoría")

    if role != "admin":
        st.info("Esta sección es solo para Admin.")
    else:
        st.markdown("### Auditoría (quién / cuándo / acción)")
        if resumen.empty:
            st.info("No hay registros.")
        else:
            dfa = resumen.copy()
            dfa = dfa.dropna(subset=["fecha"])
            dfa = dfa.sort_values("timestamp", ascending=False)
            st.dataframe(
                dfa[["timestamp","cargado_por","accion","centro","fecha","espacio","total_presentes","coordinador","notas","id_registro"]],
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("### Herramientas Admin")

        coladm1, coladm2, coladm3 = st.columns(3)

        with coladm1:
            if st.button("🧹 Re-guardar CSV limpio", use_container_width=True):
                # re-guardar asegurando columnas y tipos
                df_clean = cargar_resumen()
                guardar_resumen(df_clean)
                st.success("Listo ✅")

        with coladm2:
            if st.button("↩️ Restaurar backup global", use_container_width=True):
                ok = restore_backup()
                if ok:
                    resumen = cargar_resumen()
                    st.success("Backup restaurado ✅")
                    st.rerun()
                else:
                    st.error("No hay backup (o falló).")

        with coladm3:
            if st.button("⚠️ Crear backup manual", use_container_width=True):
                ok = backup_resumen()
                st.success("Backup creado ✅" if ok else "No pude crear backup.")

        st.markdown("---")
        st.markdown("### Resumen de “olvidos” (hoy)")
        if faltan_hoy:
            st.error("Faltan hoy: " + ", ".join(faltan_hoy))
        else:
            st.success("Hoy están todos cargados ✅")
