import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# =====================================================
# CONFIG UI
# =====================================================
st.set_page_config(page_title="Asistencia — Hogar de Cristo BB", layout="wide")

PRIMARY_COLOR = "#004E7B"
ACCENT_COLOR = "#63296C"
LOGO_FILE = "logo_hogar.png"

CUSTOM_CSS = f"""
<style>
html, body, [class*="css"] {{
    font-family: "Helvetica", "Arial", sans-serif;
}}
[data-testid="stSidebar"] {{
    background-color: #0b1220 !important;
    border-right: 3px solid {PRIMARY_COLOR};
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {PRIMARY_COLOR} !important;
}}
h1, h2, h3 {{
    color: {PRIMARY_COLOR} !important;
}}
.stMetric {{
    background-color: #121a2b !important;
    border-radius: 14px;
    padding: 0.85rem 1rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35);
    border-left: 6px solid {ACCENT_COLOR};
}}
.stTabs [role="tab"] {{
    border-radius: 999px;
    padding: 0.5rem 1.1rem;
    margin-right: 0.35rem;
    background-color: #121a2b;
    border: 1px solid rgba(255,255,255,0.12);
    font-weight: 600;
    color: #d1d5db;
}}
.stTabs [aria-selected="true"] {{
    background-color: {PRIMARY_COLOR};
    color: white !important;
    border-color: {PRIMARY_COLOR};
}}
.stButton>button {{
    border-radius: 999px;
    padding: 0.45rem 1.15rem;
    background-color: {PRIMARY_COLOR};
    color: white;
    font-weight: 700;
    border: none;
}}
.stButton>button:hover {{
    background-color: {ACCENT_COLOR};
    color: white;
}}
div[data-testid="stAlert"] {{
    border-radius: 14px;
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
    "Centro cerrado / no abrió",
]

ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
BACKUP_TAB = "asistencia_backup"

ASISTENCIA_COLS = [
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
]

PERSONAS_COLS = ["nombre", "frecuencia", "centro", "notas", "fecha_alta"]


# =====================================================
# USERS / ROLES (simple)
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
    # (Opcional) permitir override desde secrets
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
# HELPERS
# =====================================================
def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id():
    return str(uuid.uuid4())


def normalize_bool(v):
    s = str(v).strip().lower()
    return s in ["true", "1", "si", "sí", "yes"]


# =====================================================
# GOOGLE SHEETS API v4 (SIN gspread)
# =====================================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@st.cache_resource(show_spinner=False)
from googleapiclient.errors import HttpError
import json

def get_spreadsheet_meta(service, sid):
    try:
        return service.spreadsheets().get(spreadsheetId=sid).execute()
    except HttpError as e:
        st.error("❌ Google Sheets API devolvió error")
        st.write("Status:", getattr(e.resp, "status", None))
        try:
            body = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
            st.write("Body:", body)
        except Exception:
            st.write("Body: (no se pudo decodificar)")
        st.stop()


def spreadsheet_id():
    return st.secrets["sheets"]["spreadsheet_id"]


def get_spreadsheet_meta(service, sid):
    return service.spreadsheets().get(spreadsheetId=sid).execute()


def tab_exists(service, sid, title: str) -> bool:
    meta = get_spreadsheet_meta(service, sid)
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return True
    return False


def ensure_tab(service, sid, title: str):
    if tab_exists(service, sid, title):
        return
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    service.spreadsheets().batchUpdate(spreadsheetId=sid, body=body).execute()


def read_table(service, sid, tab_name: str) -> pd.DataFrame:
    rng = f"{tab_name}!A1:Z"
    res = service.spreadsheets().values().get(spreadsheetId=sid, range=rng).execute()
    values = res.get("values", [])
    if not values:
        return pd.DataFrame()
    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)
    return df


def write_table(service, sid, tab_name: str, df: pd.DataFrame):
    # limpia y reescribe
    clear_rng = f"{tab_name}!A:Z"
    service.spreadsheets().values().clear(spreadsheetId=sid, range=clear_rng, body={}).execute()

    values = [df.columns.tolist()] + df.astype(str).fillna("").values.tolist()
    start_rng = f"{tab_name}!A1"
    service.spreadsheets().values().update(
        spreadsheetId=sid,
        range=start_rng,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def append_row(service, sid, tab_name: str, row_list):
    rng = f"{tab_name}!A1"
    service.spreadsheets().values().append(
        spreadsheetId=sid,
        range=rng,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_list]},
    ).execute()


def ensure_headers(service, sid, tab_name: str, cols: list[str]):
    df = read_table(service, sid, tab_name)
    if df.empty:
        # crear con headers
        df0 = pd.DataFrame(columns=cols)
        write_table(service, sid, tab_name, df0)
        return

    # si no tiene headers correctos, normalizar: agrega faltantes y reordena
    current_cols = list(df.columns)
    changed = False
    for c in cols:
        if c not in current_cols:
            df[c] = ""
            changed = True
    df = df[cols]
    if changed or current_cols != cols:
        write_table(service, sid, tab_name, df)


# =====================================================
# LOGIN
# =====================================================
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
# SIDEBAR (LOGIN + CENTRO)
# =====================================================
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_container_width=True)

st.sidebar.title("Acceso")

if not st.session_state["logged_in"]:
    u_in = st.sidebar.text_input("Usuario", key="login_user")
    p_in = st.sidebar.text_input("Contraseña", type="password", key="login_pass")
    if st.sidebar.button("Ingresar", use_container_width=True):
        ok, meta = do_login(u_in.strip(), p_in)
        if ok:
            st.session_state["logged_in"] = True
            st.session_state["user"] = u_in.strip()
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
coordinador_logueado = st.sidebar.selectbox("¿Quién carga?", lista_coord, key="coord_sidebar")

st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")


# =====================================================
# CONNECT & BOOTSTRAP SHEETS
# =====================================================
service = get_sheets_service()
sid = spreadsheet_id()

# Debug visible (útil cuando algo raro pasa)
with st.expander("Debug Google Sheets", expanded=False):
    sa = dict(st.secrets["gcp_service_account"])
    st.write("client_email (bot):", sa.get("client_email"))
    st.write("spreadsheet_id:", sid)
    st.write("URL:", f"https://docs.google.com/spreadsheets/d/{sid}/edit")

# Asegura pestañas + headers
ensure_tab(service, sid, ASISTENCIA_TAB)
ensure_tab(service, sid, PERSONAS_TAB)
ensure_tab(service, sid, BACKUP_TAB)
ensure_headers(service, sid, ASISTENCIA_TAB, ASISTENCIA_COLS)
ensure_headers(service, sid, PERSONAS_TAB, PERSONAS_COLS)
ensure_headers(service, sid, BACKUP_TAB, ASISTENCIA_COLS)


# =====================================================
# LOAD DATA
# =====================================================
def load_asistencia() -> pd.DataFrame:
    df = read_table(service, sid, ASISTENCIA_TAB)
    if df.empty:
        return pd.DataFrame(columns=ASISTENCIA_COLS)
    # normalizaciones
    for c in ASISTENCIA_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[ASISTENCIA_COLS].copy()
    df["total_presentes"] = pd.to_numeric(df["total_presentes"], errors="coerce").fillna(0).astype(int)
    df["cerrado"] = df["cerrado"].apply(normalize_bool)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def load_personas() -> pd.DataFrame:
    df = read_table(service, sid, PERSONAS_TAB)
    if df.empty:
        return pd.DataFrame(columns=PERSONAS_COLS)
    for c in PERSONAS_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[PERSONAS_COLS].copy()
    return df


def backup_asistencia():
    df = read_table(service, sid, ASISTENCIA_TAB)
    if df.empty:
        df = pd.DataFrame(columns=ASISTENCIA_COLS)
    # asegura columnas
    for c in ASISTENCIA_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[ASISTENCIA_COLS]
    write_table(service, sid, BACKUP_TAB, df)


def restore_asistencia_backup():
    df = read_table(service, sid, BACKUP_TAB)
    if df.empty:
        return
    for c in ASISTENCIA_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[ASISTENCIA_COLS]
    write_table(service, sid, ASISTENCIA_TAB, df)


asistencia = load_asistencia()
personas = load_personas()


# =====================================================
# HEADER + ALERTAS
# =====================================================
st.markdown(
    f"## Sistema de Asistencia — Hogar de Cristo Bahía Blanca  \n"
    f"Estás trabajando sobre: **{centro_logueado}** — 👤 **{coordinador_logueado}**"
)

hoy = date.today()
hace_7 = hoy - timedelta(days=6)

def registros_por_fecha(df, centro, day: date):
    if df.empty:
        return df
    return df[(df["centro"] == centro) & (df["fecha"].dt.date == day)]

faltan_hoy = []
faltan_semana = []

for c in CENTROS:
    dfh = registros_por_fecha(asistencia, c, hoy)
    if dfh.empty:
        faltan_hoy.append(c)

    dfs = asistencia[(asistencia["centro"] == c) &
                     (asistencia["fecha"].dt.date >= hace_7) &
                     (asistencia["fecha"].dt.date <= hoy)]
    if dfs.empty:
        faltan_semana.append(c)

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Centros sin carga HOY", len(faltan_hoy))
with m2:
    st.metric("Centros sin carga (últimos 7 días)", len(faltan_semana))
with m3:
    dfc7 = asistencia[(asistencia["centro"] == centro_logueado) &
                      (asistencia["fecha"].dt.date >= hace_7) &
                      (asistencia["fecha"].dt.date <= hoy)]
    st.metric(f"{centro_logueado} (7 días)", int(dfc7["total_presentes"].sum()) if not dfc7.empty else 0)

if faltan_hoy:
    st.error("⚠️ Falta cargar HOY: " + ", ".join(faltan_hoy))
if faltan_semana:
    st.warning("ℹ️ Sin registros en los últimos 7 días: " + ", ".join(faltan_semana))


# =====================================================
# TABS
# =====================================================
tab_reg, tab_hist, tab_per, tab_rep, tab_admin = st.tabs(
    ["📌 Registrar asistencia", "🧾 Historial / Deshacer", "👥 Personas", "📊 Reportes / Base", "🛠️ Admin"]
)


# =====================================================
# TAB 1 — REGISTRAR ASISTENCIA
# =====================================================
with tab_reg:
    st.subheader("Registrar asistencia para este centro")

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        fecha = st.date_input("Fecha", value=hoy, key="reg_fecha")
    with c2:
        if centro_logueado == "Casa Maranatha":
            espacio = st.selectbox("Espacio (Maranatha)", ESPACIOS_MARANATHA, key="reg_espacio")
        else:
            espacio = "General"
            st.info("Este centro carga en modo General (sin espacios).")
    with c3:
        tipo = st.selectbox("Tipo de día", TIPOS_JORNADA, index=0, key="reg_tipo")

    presentes = st.number_input("Total presentes", min_value=0, step=1, value=0, key="reg_presentes")
    notas = st.text_area("Notas (opcional)", key="reg_notas")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Guardar asistencia", use_container_width=True):
            backup_asistencia()
            row = [
                new_id(),
                fecha.isoformat(),
                centro_logueado,
                espacio,
                str(int(presentes)),
                (notas or "").strip(),
                coordinador_logueado,
                tipo,
                "FALSE",
                now_ts(),
                user,
                "crear",
            ]
            append_row(service, sid, ASISTENCIA_TAB, row)
            st.success("Guardado ✅")
            st.rerun()

    with b2:
        if st.button("🚫 Marcar como CERRADO (0 presentes)", use_container_width=True):
            backup_asistencia()
            row = [
                new_id(),
                fecha.isoformat(),
                centro_logueado,
                espacio,
                "0",
                ((notas or "").strip() or "Centro cerrado / no abrió"),
                coordinador_logueado,
                "Centro cerrado / no abrió",
                "TRUE",
                now_ts(),
                user,
                "cerrado",
            ]
            append_row(service, sid, ASISTENCIA_TAB, row)
            st.success("Cerrado registrado ✅")
            st.rerun()

    st.markdown("---")
    st.write("### Últimos 14 días (este centro)")
    asistencia_now = load_asistencia()
    dfc = asistencia_now[asistencia_now["centro"] == centro_logueado].copy()
    if dfc.empty:
        st.info("Todavía no hay registros.")
    else:
        dfc = dfc.dropna(subset=["fecha"])
        dfc = dfc[dfc["fecha"].dt.date >= (hoy - timedelta(days=13))]
        serie = dfc.groupby("fecha")["total_presentes"].sum().sort_index()
        st.line_chart(serie)


# =====================================================
# TAB 2 — HISTORIAL + DESHACER
# =====================================================
with tab_hist:
    st.subheader("Historial del centro (editar)")
    st.caption("Antes de guardar cambios se hace backup en `asistencia_backup`. Si algo sale mal: Deshacer.")

    asistencia_now = load_asistencia()
    dfx = asistencia_now[asistencia_now["centro"] == centro_logueado].copy()
    dfx = dfx.dropna(subset=["fecha"]) if not dfx.empty else dfx
    dfx = dfx.sort_values("fecha", ascending=False).head(80) if not dfx.empty else dfx

    if dfx.empty:
        st.info("No hay registros todavía.")
    else:
        edited = st.data_editor(dfx, use_container_width=True, num_rows="fixed", key="hist_editor")

        s1, s2 = st.columns(2)
        with s1:
            if st.button("💾 Guardar cambios del historial", use_container_width=True):
                backup_asistencia()

                base = read_table(service, sid, ASISTENCIA_TAB)
                if base.empty:
                    base = pd.DataFrame(columns=ASISTENCIA_COLS)

                # normalizar columnas
                for c in ASISTENCIA_COLS:
                    if c not in base.columns:
                        base[c] = ""
                base = base[ASISTENCIA_COLS].copy()

                # la edición afecta solo ids presentes en edited
                ed = edited.copy()
                ed["timestamp"] = now_ts()
                ed["cargado_por"] = user
                ed["accion"] = "editar"

                # asegurar todas las cols
                for c in ASISTENCIA_COLS:
                    if c not in ed.columns:
                        ed[c] = ""

                # construir resultado
                ed_ids = set(ed["id_registro"].astype(str).tolist())
                base_not = base[~base["id_registro"].astype(str).isin(ed_ids)].copy()

                out = pd.concat([base_not, ed[ASISTENCIA_COLS]], ignore_index=True)
                write_table(service, sid, ASISTENCIA_TAB, out[ASISTENCIA_COLS])

                st.success("Cambios guardados ✅")
                st.rerun()

        with s2:
            if st.button("↩️ Deshacer (restaurar backup)", use_container_width=True):
                restore_asistencia_backup()
                st.success("Backup restaurado ✅")
                st.rerun()


# =====================================================
# TAB 3 — PERSONAS
# =====================================================
with tab_per:
    st.subheader(f"Personas — {centro_logueado}")

    personas_now = load_personas()
    dfp = personas_now[personas_now["centro"] == centro_logueado].copy()

    bus = st.text_input("Buscar nombre", placeholder="Escribí parte del nombre...", key="per_bus")
    if bus.strip():
        dfp = dfp[dfp["nombre"].fillna("").str.contains(bus.strip(), case=False, na=False)]

    if dfp.empty:
        st.info("No hay personas para mostrar con ese filtro.")
    else:
        st.dataframe(dfp, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona")
    p1, p2 = st.columns(2)
    with p1:
        nombre = st.text_input("Nombre completo", key="per_nombre")
    with p2:
        frecuencia = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual", "No asiste"], key="per_freq")
    notas_p = st.text_area("Notas (opcional)", key="per_notas")

    if st.button("➕ Agregar", use_container_width=True):
        if not nombre.strip():
            st.error("Escribí un nombre.")
        else:
            row = [
                nombre.strip(),
                frecuencia,
                centro_logueado,
                (notas_p or "").strip(),
                date.today().isoformat(),
            ]
            append_row(service, sid, PERSONAS_TAB, row)
            st.success("Persona agregada ✅")
            st.rerun()

    st.markdown("---")
    st.subheader("Editar personas (centro actual)")
    personas_now = load_personas()
    dfp2 = personas_now[personas_now["centro"] == centro_logueado].copy()

    if dfp2.empty:
        st.info("No hay personas para editar.")
    else:
        edited_p = st.data_editor(dfp2, use_container_width=True, num_rows="dynamic", key="per_editor")
        if st.button("💾 Guardar cambios de personas", use_container_width=True):
            # reemplaza solo el centro actual
            otras = personas_now[personas_now["centro"] != centro_logueado].copy()
            out = pd.concat([otras, edited_p], ignore_index=True)

            # asegurar columnas
            for c in PERSONAS_COLS:
                if c not in out.columns:
                    out[c] = ""
            out = out[PERSONAS_COLS]

            write_table(service, sid, PERSONAS_TAB, out)
            st.success("Cambios guardados ✅")
            st.rerun()


# =====================================================
# TAB 4 — REPORTES / BASE
# =====================================================
with tab_rep:
    st.subheader("Reportes / Base de datos")

    asistencia_now = load_asistencia()
    if asistencia_now.empty:
        st.info("Todavía no hay datos.")
    else:
        asistencia_now["dia"] = asistencia_now["fecha"].dt.date

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            centros_sel = st.multiselect("Centros", CENTROS, default=[centro_logueado], key="rep_centros")
        with f2:
            desde = st.date_input("Desde", value=(hoy - timedelta(days=28)), key="rep_desde")
        with f3:
            hasta = st.date_input("Hasta", value=hoy, key="rep_hasta")
        with f4:
            coord_all = sorted({c for lst in COORDINADORES.values() for c in lst})
            coord_sel = st.selectbox("Coordinador (opcional)", ["Todos"] + coord_all, key="rep_coord")

        dff = asistencia_now[(asistencia_now["centro"].isin(centros_sel)) &
                             (asistencia_now["dia"] >= desde) &
                             (asistencia_now["dia"] <= hasta)].copy()

        if coord_sel != "Todos":
            dff = dff[dff["coordinador"] == coord_sel]

        if dff.empty:
            st.info("No hay datos con esos filtros.")
        else:
            st.markdown("### Tendencia")
            serie = dff.groupby("fecha")["total_presentes"].sum().sort_index()
            st.line_chart(serie)

            st.markdown("---")
            st.markdown("### Tabla filtrada")
            st.dataframe(dff.sort_values("fecha", ascending=False), use_container_width=True)

            st.download_button(
                "⬇️ Descargar CSV (filtrado)",
                dff.sort_values("fecha", ascending=False).to_csv(index=False).encode("utf-8"),
                file_name="asistencia_filtrada.csv",
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
        asistencia_now = load_asistencia()
        if asistencia_now.empty:
            st.info("No hay registros.")
        else:
            asistencia_now = asistencia_now.sort_values("timestamp", ascending=False)
            st.markdown("### Auditoría (quién / cuándo / acción)")
            st.dataframe(
                asistencia_now[["timestamp","cargado_por","accion","centro","fecha","espacio","total_presentes","coordinador","notas","id_registro"]],
                use_container_width=True,
            )

        st.markdown("---")
        a1, a2 = st.columns(2)
        with a1:
            if st.button("🧾 Crear backup ahora", use_container_width=True):
                backup_asistencia()
                st.success("Backup creado ✅")
        with a2:
            if st.button("↩️ Restaurar backup", use_container_width=True):
                restore_asistencia_backup()
                st.success("Backup restaurado ✅")
                st.rerun()

