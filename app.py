import streamlit as st
import pandas as pd
import os
import uuid
from datetime import date, timedelta, datetime

import gspread
from google.oauth2.service_account import Credentials


# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Asistencia Centros Barriales", layout="wide")

PRIMARY_COLOR = "#004E7B"
ACCENT_COLOR = "#63296C"

CUSTOM_CSS = f"""
<style>
[data-testid="stSidebar"] {{
    background-color: #111827 !important;
    border-right: 3px solid {PRIMARY_COLOR};
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {PRIMARY_COLOR} !important;
}}
h1, h2, h3, h4 {{
    color: {PRIMARY_COLOR} !important;
    font-family: "Helvetica", "Arial", sans-serif;
}}
.stMetric {{
    background-color: #1f2633 !important;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    border-left: 6px solid {ACCENT_COLOR};
}}
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
[data-testid="stDataFrame"] {{
    background-color: #111827 !important;
    border-radius: 8px;
    padding: 0.6rem;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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

LOGO_FILE = "logo_hogar.png"


# =====================================================
# USERS / ROLES (si no ponés secrets users, usa defaults)
# =====================================================
DEFAULT_USERS = {
    "admin": {"password": "hogar", "role": "admin", "centers": ["*"]},
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
# GOOGLE SHEETS (DB)
# =====================================================
ASISTENCIA_SHEET = "asistencia"
PERSONAS_SHEET = "personas"
ASISTENCIA_BACKUP_SHEET = "asistencia_backup"

ASISTENCIA_COLS = [
    "id_registro","fecha","centro","espacio","total_presentes","notas","coordinador",
    "tipo_jornada","cerrado","timestamp","cargado_por","accion"
]
PERSONAS_COLS = ["nombre","frecuencia","centro","notas","fecha_alta"]


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """
    Crea el cliente de Google Sheets desde secrets.
    Incluye FIX robusto para private_key (evita errores pyasn1).
    """
    sa = dict(st.secrets["gcp_service_account"])

    pk = sa.get("private_key", "")
    if not pk:
        raise ValueError("Falta 'private_key' en secrets[gcp_service_account].")

    # FIX: convertir "\\n" -> "\n" (muy común en Streamlit Secrets)
    pk = pk.replace("\\n", "\n").strip()

    # asegurar encabezados
    if "-----BEGIN PRIVATE KEY-----" not in pk or "-----END PRIVATE KEY-----" not in pk:
        raise ValueError(
            "La 'private_key' no contiene BEGIN/END PRIVATE KEY. "
            "Pegala desde el JSON original del service account."
        )

    # asegurar que termina en salto de línea
    if not pk.endswith("\n"):
        pk += "\n"

    sa["private_key"] = pk

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)


def get_spreadsheet():
    gc = get_gspread_client()
    spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
    return gc.open_by_key(spreadsheet_id)


def get_ws(name: str):
    sh = get_spreadsheet()
    try:
        return sh.worksheet(name)
    except Exception:
        return sh.add_worksheet(title=name, rows="2000", cols="30")


def df_from_ws(ws, required_cols):
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=required_cols)
    df = pd.DataFrame(records)
    df.columns = [c.strip() for c in df.columns]
    for c in required_cols:
        if c not in df.columns:
            df[c] = ""
    df = df[required_cols]
    return df


def write_df_to_ws(ws, df: pd.DataFrame, cols_order):
    df2 = df.copy()
    for c in cols_order:
        if c not in df2.columns:
            df2[c] = ""
    df2 = df2[cols_order]

    values = [cols_order] + df2.astype(str).fillna("").values.tolist()
    ws.clear()
    ws.update("A1", values)


def append_row_ws(ws, row_dict, cols_order):
    row = []
    for c in cols_order:
        v = row_dict.get(c, "")
        row.append("" if v is None else str(v))
    ws.append_row(row, value_input_option="USER_ENTERED")


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id():
    return str(uuid.uuid4())


def backup_asistencia_to_sheet():
    ws_main = get_ws(ASISTENCIA_SHEET)
    ws_bak = get_ws(ASISTENCIA_BACKUP_SHEET)
    df_main = df_from_ws(ws_main, ASISTENCIA_COLS)
    write_df_to_ws(ws_bak, df_main, ASISTENCIA_COLS)


def restore_asistencia_from_backup():
    ws_main = get_ws(ASISTENCIA_SHEET)
    ws_bak = get_ws(ASISTENCIA_BACKUP_SHEET)
    df_bak = df_from_ws(ws_bak, ASISTENCIA_COLS)
    write_df_to_ws(ws_main, df_bak, ASISTENCIA_COLS)


# =====================================================
# LOGIN
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

user = st.session_state["user"]
user_meta = st.session_state["user_meta"] or {}
role = user_meta.get("role", "coord")
allowed_centers = user_meta.get("centers", [])

st.sidebar.success(f"Conectado como: {user}")
if st.sidebar.button("Salir", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["user_meta"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Centro / Coordinador")

if role == "admin":
    centro_logueado = st.sidebar.selectbox("Centro", CENTROS, key="centro_sidebar")
else:
    centro_logueado = allowed_centers[0] if allowed_centers else CENTROS[0]
    st.sidebar.write(f"Centro asignado: **{centro_logueado}**")

lista_coord = COORDINADORES.get(centro_logueado, []) or ["(sin coordinadores cargados)"]

default_coord = lista_coord[0]
if role != "admin":
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
# LOAD DATA (desde Sheets)
# =====================================================
ws_asistencia = get_ws(ASISTENCIA_SHEET)
ws_personas = get_ws(PERSONAS_SHEET)
ws_backup = get_ws(ASISTENCIA_BACKUP_SHEET)

asistencia = df_from_ws(ws_asistencia, ASISTENCIA_COLS)
personas = df_from_ws(ws_personas, PERSONAS_COLS)

if not asistencia.empty:
    asistencia["total_presentes"] = pd.to_numeric(asistencia["total_presentes"], errors="coerce").fillna(0).astype(int)
    asistencia["cerrado"] = asistencia["cerrado"].astype(str).str.lower().isin(["true","1","yes","si","sí"])
    asistencia["fecha"] = pd.to_datetime(asistencia["fecha"], errors="coerce")
    asistencia["timestamp"] = pd.to_datetime(asistencia["timestamp"], errors="coerce")


# =====================================================
# HEADER + ALERTAS OLVIDO
# =====================================================
st.markdown(
    f"## Sistema de Asistencia — Hogar de Cristo Bahía Blanca  \n"
    f"Centro: **{centro_logueado}** — 👤 **{coordinador_logueado}** — Rol: **{role}**"
)

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
    dfh = registros_por_fecha(asistencia, c, hoy)
    if dfh.empty:
        faltan_hoy.append(c)

    dfs = asistencia[(asistencia["centro"] == c) &
                     (asistencia["fecha"].dt.date >= hace_una_semana) &
                     (asistencia["fecha"].dt.date <= hoy)]
    if dfs.empty:
        faltan_semana.append(c)

a1, a2, a3 = st.columns(3)
with a1:
    st.metric("Centros sin carga HOY", len(faltan_hoy))
with a2:
    st.metric("Centros sin carga (7 días)", len(faltan_semana))
with a3:
    dfc = asistencia[(asistencia["centro"] == centro_logueado) &
                     (asistencia["fecha"].dt.date >= hace_una_semana) &
                     (asistencia["fecha"].dt.date <= hoy)]
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
# TAB 1 — CARGA RÁPIDA + CERRADO
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
            backup_asistencia_to_sheet()
            nueva = {
                "id_registro": new_id(),
                "fecha": fecha.isoformat(),
                "centro": centro_logueado,
                "espacio": espacio,
                "total_presentes": int(presentes),
                "notas": (notas or "").strip(),
                "coordinador": coordinador_logueado,
                "tipo_jornada": tipo_jornada,
                "cerrado": "FALSE",
                "timestamp": now_ts(),
                "cargado_por": user,
                "accion": "crear",
            }
            append_row_ws(ws_asistencia, nueva, ASISTENCIA_COLS)
            st.success("Guardado ✅")
            st.rerun()

    with cbtn2:
        if st.button("🚫 Marcar como CERRADO (0 presentes)", use_container_width=True, key="quick_cerrado"):
            backup_asistencia_to_sheet()
            nueva = {
                "id_registro": new_id(),
                "fecha": fecha.isoformat(),
                "centro": centro_logueado,
                "espacio": espacio,
                "total_presentes": 0,
                "notas": (notas or "").strip() or "Centro cerrado / no abrió",
                "coordinador": coordinador_logueado,
                "tipo_jornada": "Centro cerrado / no abrió",
                "cerrado": "TRUE",
                "timestamp": now_ts(),
                "cargado_por": user,
                "accion": "cerrado",
            }
            append_row_ws(ws_asistencia, nueva, ASISTENCIA_COLS)
            st.success("Registrado como cerrado ✅")
            st.rerun()

    st.markdown("---")
    st.write("### Vista rápida: últimos 14 días (este centro)")
    asistencia2 = df_from_ws(ws_asistencia, ASISTENCIA_COLS)
    if not asistencia2.empty:
        asistencia2["fecha"] = pd.to_datetime(asistencia2["fecha"], errors="coerce")
        asistencia2["total_presentes"] = pd.to_numeric(asistencia2["total_presentes"], errors="coerce").fillna(0).astype(int)

    dfc = asistencia2[asistencia2["centro"] == centro_logueado].copy() if not asistencia2.empty else pd.DataFrame()
    if dfc.empty:
        st.info("Todavía no hay registros para mostrar.")
    else:
        dfc = dfc.dropna(subset=["fecha"])
        dfc = dfc[dfc["fecha"].dt.date >= (hoy - timedelta(days=13))]
        serie = dfc.groupby("fecha")["total_presentes"].sum().sort_index()
        st.line_chart(serie)

# =====================================================
# TAB 2 — HISTORIAL EDITABLE + DESHACER
# =====================================================
with tab_historial:
    st.subheader("Historial del centro (editar)")
    st.caption("Antes de guardar cambios, se hace backup en la hoja `asistencia_backup`. Podés deshacer con 1 click.")

    asistencia2 = df_from_ws(ws_asistencia, ASISTENCIA_COLS)
    if not asistencia2.empty:
        asistencia2["fecha"] = pd.to_datetime(asistencia2["fecha"], errors="coerce")
        asistencia2["timestamp"] = pd.to_datetime(asistencia2["timestamp"], errors="coerce")
        asistencia2["total_presentes"] = pd.to_numeric(asistencia2["total_presentes"], errors="coerce").fillna(0).astype(int)
        asistencia2["cerrado"] = asistencia2["cerrado"].astype(str).str.lower().isin(["true","1","yes","si","sí"])

    dfx = asistencia2[asistencia2["centro"] == centro_logueado].copy() if not asistencia2.empty else pd.DataFrame()
    dfx = dfx.dropna(subset=["fecha"]) if not dfx.empty else dfx
    dfx = dfx.sort_values("fecha", ascending=False).head(60) if not dfx.empty else dfx

    if dfx.empty:
        st.info("No hay registros todavía.")
    else:
        edited = st.data_editor(dfx, use_container_width=True, num_rows="fixed", key="hist_editor")

        csave, cundo = st.columns(2)
        with csave:
            if st.button("💾 Guardar cambios del historial", use_container_width=True, key="hist_save"):
                backup_asistencia_to_sheet()

                base = asistencia2.copy()
                base["id_registro"] = base["id_registro"].astype(str)
                ed = edited.copy()
                ed["id_registro"] = ed["id_registro"].astype(str)

                ed["timestamp"] = now_ts()
                ed["cargado_por"] = user
                ed["accion"] = "editar"

                base_ids = set(ed["id_registro"].tolist())
                base_not = base[~base["id_registro"].isin(base_ids)].copy()
                merged = pd.concat([base_not, ed], ignore_index=True)

                merged = merged[ASISTENCIA_COLS].copy()
                write_df_to_ws(ws_asistencia, merged, ASISTENCIA_COLS)

                st.success("Cambios guardados ✅")
                st.rerun()

        with cundo:
            if st.button("↩️ Deshacer (restaurar backup)", use_container_width=True, key="hist_undo"):
                restore_asistencia_from_backup()
                st.success("Backup restaurado ✅")
                st.rerun()

# =====================================================
# TAB 3 — PERSONAS
# =====================================================
with tab_personas:
    st.subheader(f"Personas — {centro_logueado}")

    personas2 = df_from_ws(ws_personas, PERSONAS_COLS)

    dfp = personas2[personas2["centro"] == centro_logueado].copy()
    bus = st.text_input("Buscar nombre", placeholder="Escribí parte del nombre...", key="per_bus")
    if bus.strip():
        dfp = dfp[dfp["nombre"].fillna("").str.contains(bus.strip(), case=False, na=False)]

    if dfp.empty:
        st.info("No hay personas para mostrar con ese filtro.")
    else:
        st.dataframe(dfp, use_container_width=True)

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
            append_row_ws(ws_personas, nueva, PERSONAS_COLS)
            st.success("Persona agregada ✅")
            st.rerun()

    st.markdown("---")
    st.subheader("Editar personas (centro actual)")
    personas2 = df_from_ws(ws_personas, PERSONAS_COLS)
    dfp2 = personas2[personas2["centro"] == centro_logueado].copy()

    if dfp2.empty:
        st.info("No hay personas para editar.")
    else:
        edited_p = st.data_editor(dfp2, use_container_width=True, num_rows="dynamic", key="per_editor")
        if st.button("💾 Guardar cambios de personas", use_container_width=True, key="per_save"):
            otras = personas2[personas2["centro"] != centro_logueado].copy()
            out = pd.concat([otras, edited_p], ignore_index=True)
            write_df_to_ws(ws_personas, out, PERSONAS_COLS)
            st.success("Cambios guardados ✅")
            st.rerun()

# =====================================================
# TAB 4 — REPORTES PRO + EXPORT
# =====================================================
with tab_reportes:
    st.subheader("Reportes pro")

    asistencia2 = df_from_ws(ws_asistencia, ASISTENCIA_COLS)
    if asistencia2.empty:
        st.info("Todavía no hay datos.")
    else:
        asistencia2["fecha"] = pd.to_datetime(asistencia2["fecha"], errors="coerce")
        asistencia2["total_presentes"] = pd.to_numeric(asistencia2["total_presentes"], errors="coerce").fillna(0).astype(int)
        asistencia2["dia"] = asistencia2["fecha"].dt.date

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

        dff = asistencia2[(asistencia2["centro"].isin(centros_sel)) &
                          (asistencia2["dia"] >= desde) &
                          (asistencia2["dia"] <= hasta)].copy()

        if coord_sel != "Todos":
            dff = dff[dff["coordinador"] == coord_sel]

        if dff.empty:
            st.info("No hay datos con esos filtros.")
        else:
            st.markdown("### Tendencia (periodo seleccionado)")
            serie = dff.groupby("fecha")["total_presentes"].sum().sort_index()
            st.line_chart(serie)

            st.markdown("### Semana vs semana pasada")
            fin = hoy
            ini = hoy - timedelta(days=6)
            fin_prev = hoy - timedelta(days=7)
            ini_prev = hoy - timedelta(days=13)

            w = asistencia2[(asistencia2["centro"].isin(centros_sel)) &
                            (asistencia2["dia"] >= ini) & (asistencia2["dia"] <= fin)]
            wp = asistencia2[(asistencia2["centro"].isin(centros_sel)) &
                             (asistencia2["dia"] >= ini_prev) & (asistencia2["dia"] <= fin_prev)]
            if coord_sel != "Todos":
                w = w[w["coordinador"] == coord_sel]
                wp = wp[wp["coordinador"] == coord_sel]

            tot_w = int(w["total_presentes"].sum()) if not w.empty else 0
            tot_wp = int(wp["total_presentes"].sum()) if not wp.empty else 0
            delta = tot_w - tot_wp
            delta_pct = (delta / tot_wp * 100) if tot_wp > 0 else None

            cA, cB, cC = st.columns(3)
            with cA:
                st.metric("Últimos 7 días", tot_w, delta=delta)
            with cB:
                st.metric("Semana pasada", tot_wp)
            with cC:
                st.metric("Δ %", f"{delta_pct:.1f}%" if delta_pct is not None else "—")

            st.markdown("### Comparación por centro (periodo)")
            by_center = dff.groupby("centro")["total_presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_center)

            st.markdown("### Top 10 días (periodo)")
            top_days = (
                dff.groupby("dia")["total_presentes"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            st.dataframe(top_days, use_container_width=True)

            st.markdown("### Por tipo de jornada (periodo)")
            by_tipo = dff.groupby("tipo_jornada")["total_presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_tipo)

            st.markdown("---")
            st.subheader("Exportaciones (1 click)")

            st.download_button(
                "⬇️ Descargar asistencia FILTRADA (CSV)",
                dff.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                file_name="asistencia_filtrada.csv",
                mime="text/csv",
                use_container_width=True,
            )

            df_centro_week = asistencia2[(asistencia2["centro"] == centro_logueado) &
                                         (asistencia2["dia"] >= (hoy - timedelta(days=6))) &
                                         (asistencia2["dia"] <= hoy)].copy()
            st.download_button(
                f"⬇️ Descargar {centro_logueado} (últimos 7 días)",
                df_centro_week.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                file_name=f"{centro_logueado}_7dias.csv".replace(" ", "_"),
                mime="text/csv",
                use_container_width=True,
            )

            if role == "admin":
                st.download_button(
                    "⬇️ Descargar TODO (CSV)",
                    asistencia2.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                    file_name="asistencia_todo.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

# =====================================================
# TAB 5 — ADMIN / AUDITORÍA
# =====================================================
with tab_admin:
    st.subheader("Admin / Auditoría")

    if role != "admin":
        st.info("Esta sección es solo para Admin.")
    else:
        asistencia2 = df_from_ws(ws_asistencia, ASISTENCIA_COLS)
        if not asistencia2.empty:
            asistencia2["fecha"] = pd.to_datetime(asistencia2["fecha"], errors="coerce")
            asistencia2["timestamp"] = pd.to_datetime(asistencia2["timestamp"], errors="coerce")
            asistencia2 = asistencia2.sort_values("timestamp", ascending=False)

        st.markdown("### Auditoría (quién / cuándo / acción)")
        if asistencia2.empty:
            st.info("No hay registros.")
        else:
            st.dataframe(
                asistencia2[["timestamp","cargado_por","accion","centro","fecha","espacio","total_presentes","coordinador","notas","id_registro"]],
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("### Herramientas Admin")

        coladm1, coladm2, coladm3 = st.columns(3)
        with coladm1:
            if st.button("↩️ Restaurar backup (sheet)", use_container_width=True):
                restore_asistencia_from_backup()
                st.success("Backup restaurado ✅")
                st.rerun()

        with coladm2:
            if st.button("🧾 Crear backup ahora", use_container_width=True):
                backup_asistencia_to_sheet()
                st.success("Backup creado ✅")

        with coladm3:
            if st.button("🔄 Recargar todo", use_container_width=True):
                st.rerun()
