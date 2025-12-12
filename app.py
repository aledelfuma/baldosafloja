import os
import re
import unicodedata
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st
import altair as alt

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
from google.auth.exceptions import RefreshError


# =========================
# Config
# =========================
st.set_page_config(
    page_title="Sistema de Asistencia — Hogar de Cristo Bahía Blanca",
    page_icon="🧾",
    layout="wide",
)

APP_TITLE = "Sistema de Asistencia — Hogar de Cristo Bahía Blanca"

PRIMARY = "#004E7B"
ACCENT = "#63296C"

CENTROS_CANON = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar (Primaria)",
    "Apoyo escolar (Secundaria)",
    "Fines",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]

FRECUENCIAS_CANON = ["Diaria", "Semanal", "Mensual", "No asiste"]

ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"


# =========================
# Utils
# =========================
def clean_cell(x) -> str:
    if x is None:
        return ""
    s = str(x).replace("\u00a0", " ")
    return s.strip()

def strip_accents(s: str) -> str:
    s = clean_cell(s)
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_centro(s: str) -> str:
    k = norm_key(s)
    if k in ["calle belen", "calle bélen", "calle belén", "belen", "belén"]:
        return "Calle Belén"
    if k in ["nudo a nudo", "nudo", "nudo a  nudo"]:
        return "Nudo a Nudo"
    if k in ["casa maranatha", "maranatha", "casa maranata", "casa maranatá"]:
        return "Casa Maranatha"
    for c in CENTROS_CANON:
        if norm_key(c) == k:
            return c
    return clean_cell(s)

def normalize_frecuencia(s: str) -> str:
    k = norm_key(s)
    if k in ["diaria", "diario", "todos los dias", "todos los días"]:
        return "Diaria"
    if k in ["semanal", "por semana", "una vez por semana"]:
        return "Semanal"
    if k in ["mensual", "por mes", "una vez por mes"]:
        return "Mensual"
    if k in ["no asiste", "no", "no viene", "no viene mas", "no viene más"]:
        return "No asiste"
    for f in FRECUENCIAS_CANON:
        if norm_key(f) == k:
            return f
    return clean_cell(s)

def safe_int(x, default=0):
    try:
        return int(float(str(x).strip()))
    except Exception:
        return default


# =========================
# Dataframe hardening (clave para tu error)
# =========================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    - baja a minúsculas
    - trim espacios
    - reemplaza variantes a nombres canónicos
    """
    if df is None or df.empty:
        return df

    new_cols = []
    for c in df.columns:
        cc = clean_cell(c).lower()
        cc = re.sub(r"\s+", "_", cc)
        new_cols.append(cc)
    df = df.copy()
    df.columns = new_cols

    # alias -> canónico
    aliases = {
        "persona": "nombre",
        "personas": "nombre",
        "nombre_y_apellido": "nombre",
        "centros": "centro",
        "presente": "presentes",
        "asistentes": "presentes",
        "cantidad": "presentes",
        "total": "presentes",
        "total_presentes": "presentes",
        "coordinador_a": "coordinador",
        "coordinadora": "coordinador",
        "año": "anio",
        "ano": "anio",
        "fecha": "fecha",
        "espacio": "espacio",
        "modo": "modo",
        "notas": "notas",
        "timestamp": "timestamp",
        "frecuencia": "frecuencia",
    }
    for a, b in aliases.items():
        if a in df.columns and b not in df.columns:
            df = df.rename(columns={a: b})

    # asegurar columnas mínimas si faltan (evita crashes)
    for col in ["fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "timestamp"]:
        if col not in df.columns:
            df[col] = ""

    return df


# =========================
# CSV
# =========================
CSV_FALLBACKS = ["datapersonas.csv", "personas.csv"]

def find_csv_path():
    for p in CSV_FALLBACKS:
        if os.path.exists(p):
            return p
    return None

def load_personas_csv_fallback() -> pd.DataFrame:
    path = find_csv_path()
    if not path:
        return pd.DataFrame(columns=["nombre", "frecuencia", "centro"])

    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1")

    df = normalize_columns(df)

    # asegurar columnas
    for k in ["nombre", "frecuencia", "centro"]:
        if k not in df.columns:
            df[k] = ""

    df = df[["nombre", "frecuencia", "centro"]].copy()
    df["nombre"] = df["nombre"].map(clean_cell)
    df["frecuencia"] = df["frecuencia"].map(normalize_frecuencia)
    df["centro"] = df["centro"].map(normalize_centro)
    df = df[df["nombre"] != ""]
    df = df.drop_duplicates(subset=["nombre", "centro"], keep="first")
    return df


# =========================
# Google Sheets via AuthorizedSession
# =========================
def require_secrets():
    if "gcp_service_account" not in st.secrets:
        st.error("Falta [gcp_service_account] en secrets.toml")
        st.stop()
    if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
        st.error("Falta [sheets] spreadsheet_id en secrets.toml")
        st.stop()

@st.cache_resource(show_spinner=False)
def get_authed_session():
    require_secrets()
    sa = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = Credentials.from_service_account_info(sa, scopes=scopes)
        return AuthorizedSession(creds), sa.get("client_email", "")
    except RefreshError as e:
        st.error(f"RefreshError: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error credenciales: {type(e).__name__}: {e}")
        st.stop()

def sheets_base():
    sid = st.secrets["sheets"]["spreadsheet_id"]
    return sid, f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"

def sheets_get_meta(session: AuthorizedSession):
    sid, base = sheets_base()
    r = session.get(base, timeout=30)
    r.raise_for_status()
    return r.json()

def tab_exists(session: AuthorizedSession, title: str) -> bool:
    meta = sheets_get_meta(session)
    for s in meta.get("sheets", []):
        props = s.get("properties", {})
        if props.get("title") == title:
            return True
    return False

def ensure_tab(session: AuthorizedSession, title: str, headers: list[str]):
    sid, base = sheets_base()

    if tab_exists(session, title):
        # si A1 está vacío, escribo headers
        rng = f"{title}!A1:Z1"
        r = session.get(f"{base}/values/{rng}", timeout=30)
        r.raise_for_status()
        values = r.json().get("values", [])
        if not values:
            body = {"values": [headers]}
            put = session.put(
                f"{base}/values/{title}!A1:Z1?valueInputOption=RAW",
                json=body,
                timeout=30,
            )
            put.raise_for_status()
        return

    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    r = session.post(f"{base}:batchUpdate", json=body, timeout=30)
    r.raise_for_status()

    body2 = {"values": [headers]}
    put = session.put(
        f"{base}/values/{title}!A1:Z1?valueInputOption=RAW",
        json=body2,
        timeout=30,
    )
    put.raise_for_status()

def read_table(session: AuthorizedSession, tab: str) -> pd.DataFrame:
    sid, base = sheets_base()
    r = session.get(f"{base}/values/{tab}!A1:Z", timeout=30)
    r.raise_for_status()
    values = r.json().get("values", [])
    if not values:
        return pd.DataFrame()

    headers = [clean_cell(x) for x in values[0]]
    rows = values[1:]

    if not headers:
        return pd.DataFrame()

    fixed = []
    for row in rows:
        row = list(row)
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        fixed.append(row[: len(headers)])

    df = pd.DataFrame(fixed, columns=headers)
    for c in df.columns:
        df[c] = df[c].map(clean_cell)

    # 🔥 endurecer columnas (evita tu KeyError)
    df = normalize_columns(df)
    return df

def append_row(session: AuthorizedSession, tab: str, row: list):
    sid, base = sheets_base()
    body = {"values": [row]}
    r = session.post(
        f"{base}/values/{tab}!A1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
        json=body,
        timeout=30,
    )
    r.raise_for_status()


# =========================
# Usuarios
# =========================
def get_users():
    if "users" not in st.secrets:
        return {}
    try:
        return dict(st.secrets["users"])
    except Exception:
        return {}

def login_box():
    users = get_users()

    st.sidebar.markdown("## Acceso")
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    if st.session_state.auth_user:
        st.sidebar.success(f"Conectado como: {st.session_state.auth_user}")
        if st.sidebar.button("Salir"):
            st.session_state.auth_user = None
            st.session_state.user_nombre = ""
            st.session_state.user_centro = ""
            st.rerun()
        return

    if not users:
        st.sidebar.info("Modo DEMO (no hay [users] en secrets).")
        centro_demo = st.sidebar.selectbox("Centro asignado", CENTROS_CANON, index=0)
        nombre_demo = st.sidebar.text_input("Tu nombre", value="Demo")
        if st.sidebar.button("Entrar"):
            st.session_state.auth_user = "demo"
            st.session_state.user_nombre = nombre_demo
            st.session_state.user_centro = centro_demo
            st.rerun()
        return

    u = st.sidebar.text_input("Usuario")
    p = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        key = clean_cell(u).lower()
        if key not in users:
            st.sidebar.error("Usuario incorrecto.")
            return
        ud = users[key]
        if clean_cell(ud.get("password", "")) != clean_cell(p):
            st.sidebar.error("Contraseña incorrecta.")
            return
        st.session_state.auth_user = key
        st.session_state.user_nombre = clean_cell(ud.get("nombre", key))
        st.session_state.user_centro = normalize_centro(ud.get("centro", ""))
        st.rerun()


# =========================
# Seed personas CSV -> Sheets (si está vacío)
# =========================
def seed_personas_if_empty(session: AuthorizedSession) -> bool:
    df = read_table(session, PERSONAS_TAB)
    if df is not None and not df.empty:
        return False

    csv_path = find_csv_path()
    if not csv_path:
        return False

    df_csv = load_personas_csv_fallback()
    if df_csv.empty:
        return False

    now = datetime.now().isoformat(timespec="seconds")
    for _, r in df_csv.iterrows():
        append_row(session, PERSONAS_TAB, [r["nombre"], r["frecuencia"], r["centro"], now])
    return True


# =========================
# UI Styling
# =========================
def inject_css():
    st.markdown(
        f"""
        <style>
          .stApp {{
            background: radial-gradient(1200px 900px at 30% 10%, rgba(99,41,108,0.25), transparent 55%),
                        radial-gradient(1200px 900px at 80% 20%, rgba(0,78,123,0.25), transparent 55%),
                        #0b0f14;
            color: #e7eef7;
          }}
          .hc-pill {{
            display:inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            font-size: 12px;
          }}
          .hc-card {{
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 14px 16px;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def kpi(label: str, value: str):
    st.markdown(
        f"""
        <div class="hc-card">
          <div style="opacity:0.85;font-size:13px;margin-bottom:6px;">{label}</div>
          <div style="font-size:34px;font-weight:800;line-height:1;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Main
# =========================
def main():
    inject_css()
    login_box()

    if not st.session_state.get("auth_user"):
        st.stop()

    centro = normalize_centro(st.session_state.get("user_centro", ""))
    coordinador = clean_cell(st.session_state.get("user_nombre", ""))
    anio_actual = datetime.now().year

    session, client_email = get_authed_session()
    sid = st.secrets["sheets"]["spreadsheet_id"]

    ensure_tab(session, PERSONAS_TAB, ["nombre", "frecuencia", "centro", "timestamp"])
    ensure_tab(session, ASISTENCIA_TAB, ["fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "timestamp"])

    _ = seed_personas_if_empty(session)

    df_personas = read_table(session, PERSONAS_TAB)
    df_asistencia = read_table(session, ASISTENCIA_TAB)

    # normalizaciones de contenido
    if df_personas is None or df_personas.empty:
        df_personas = pd.DataFrame(columns=["nombre", "frecuencia", "centro", "timestamp"])
    else:
        df_personas["nombre"] = df_personas["nombre"].map(clean_cell)
        df_personas["frecuencia"] = df_personas["frecuencia"].map(normalize_frecuencia)
        df_personas["centro"] = df_personas["centro"].map(normalize_centro)

    if df_asistencia is None or df_asistencia.empty:
        df_asistencia = pd.DataFrame(columns=["fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "timestamp"])
    else:
        df_asistencia["centro"] = df_asistencia["centro"].map(normalize_centro)
        df_asistencia["presentes"] = df_asistencia["presentes"].map(lambda x: safe_int(x, 0))
        df_asistencia["anio"] = df_asistencia["anio"].map(lambda x: safe_int(x, anio_actual))

    # Header
    st.markdown(f"# {APP_TITLE}")
    st.markdown(
        f"Estás trabajando sobre: **{centro}** — 👤 **{coordinador}**  &nbsp;&nbsp; <span class='hc-pill'>Año: {anio_actual}</span>",
        unsafe_allow_html=True,
    )

    # DF por centro/año
    df_c = df_asistencia[(df_asistencia["centro"] == centro) & (df_asistencia["anio"] == anio_actual)].copy()

    # KPIs (robustos)
    hoy = date.today().isoformat()
    if "presentes" not in df_c.columns:
        df_c["presentes"] = 0

    hoy_total = int(df_c.loc[df_c["fecha"] == hoy, "presentes"].sum()) if not df_c.empty else 0
    ult7_fechas = [(date.today() - timedelta(days=i)).isoformat() for i in range(7)]
    ult7 = int(df_c.loc[df_c["fecha"].isin(ult7_fechas), "presentes"].sum()) if not df_c.empty else 0

    semana = [(date.today() - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    dias_cargados = set(df_c["fecha"].tolist()) if not df_c.empty else set()
    sin_cargar = sum(1 for d in semana if d not in dias_cargados)

    c1, c2, c3 = st.columns(3)
    with c1: kpi("Ingresos HOY", str(hoy_total))
    with c2: kpi("Ingresos últimos 7 días", str(ult7))
    with c3: kpi("Días sin cargar (últimos 7)", str(sin_cargar))

    st.divider()

    tabs = st.tabs(["🧾 Registrar asistencia", "👥 Personas", "📊 Reportes / Base de datos", "🌍 Global"])

    # TAB 1
    with tabs[0]:
        st.subheader("Registrar asistencia para este centro")

        colA, colB = st.columns([2, 1])
        with colA:
            fecha = st.date_input("Fecha", value=date.today())
        with colB:
            modo = st.selectbox("Tipo de día", ["Día habitual", "Actividad especial", "Salida", "Centro cerrado"], index=0)

        if centro == "Casa Maranatha":
            espacio = st.selectbox("Espacio (solo Casa Maranatha)", ESPACIOS_MARANATHA, index=0)
            if espacio == "Otro":
                espacio = st.text_input("Escribí el espacio", value="")
        else:
            st.info("Este centro no usa espacios internos.")
            espacio = ""

        col1, col2 = st.columns([1, 2])
        with col1:
            presentes = st.number_input("Total presentes", min_value=0, step=1, value=0)
        with col2:
            notas = st.text_input("Notas (opcional)", value="")

        if st.button("✅ Guardar asistencia", use_container_width=True):
            ts = datetime.now().isoformat(timespec="seconds")
            append_row(
                session,
                ASISTENCIA_TAB,
                [
                    fecha.isoformat(),
                    str(fecha.year),
                    centro,
                    clean_cell(espacio),
                    str(int(presentes)),
                    coordinador,
                    modo,
                    clean_cell(notas),
                    ts,
                ],
            )
            st.success("Guardado ✅")
            st.rerun()

        st.markdown("### Últimos registros (este centro / este año)")
        df_last = df_c.sort_values(by="timestamp", ascending=False) if (not df_c.empty and "timestamp" in df_c.columns) else df_c
        st.dataframe(df_last.head(30), use_container_width=True)

    # TAB 2
    with tabs[1]:
        st.subheader("Personas de este centro")

        colI, colJ = st.columns([1, 2])
        with colI:
            if st.button("📥 Importar CSV ahora (si está vacío)", use_container_width=True):
                ok = seed_personas_if_empty(session)
                if ok:
                    st.success("Importado ✅. Recargando…")
                else:
                    st.info("No importé: no hay CSV o la hoja ya tenía datos.")
                st.rerun()
        with colJ:
            st.caption("Busca `data/personas.csv` o `personas.csv`.")

        personas_centro = df_personas[df_personas["centro"] == centro].copy()
        st.markdown(f"<span class='hc-pill'>Personas visibles: {len(personas_centro)}</span>", unsafe_allow_html=True)
        st.dataframe(personas_centro[["nombre", "frecuencia", "centro"]], use_container_width=True)

        st.divider()
        st.markdown("### Agregar persona (opcional)")
        cA, cB, cC = st.columns([2, 1, 1])
        with cA:
            new_nombre = st.text_input("Nombre y apellido")
        with cB:
            new_freq = st.selectbox("Frecuencia", FRECUENCIAS_CANON, index=1)
        with cC:
            st.text_input("Centro", value=centro, disabled=True)

        if st.button("➕ Agregar a la base", use_container_width=True):
            if clean_cell(new_nombre) == "":
                st.error("Falta el nombre.")
            else:
                ts = datetime.now().isoformat(timespec="seconds")
                append_row(session, PERSONAS_TAB, [clean_cell(new_nombre), new_freq, centro, ts])
                st.success("Persona agregada ✅")
                st.rerun()

    # TAB 3
    with tabs[2]:
        st.subheader("Reportes (este centro)")

        if df_c.empty:
            st.info("Todavía no hay registros de asistencia para este centro.")
        else:
            tmp = df_c.copy()
            tmp["fecha_dt"] = pd.to_datetime(tmp["fecha"], errors="coerce")
            tmp = tmp.dropna(subset=["fecha_dt"])
            day = tmp.groupby("fecha_dt", as_index=False)["presentes"].sum()

            st.markdown("#### Asistencia por día")
            chart = (
                alt.Chart(day)
                .mark_line(point=True)
                .encode(
                    x=alt.X("fecha_dt:T", title="Fecha"),
                    y=alt.Y("presentes:Q", title="Presentes"),
                    tooltip=["fecha_dt:T", "presentes:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)

            st.markdown("#### Base de datos (asistencia — este centro / este año)")
            st.dataframe(df_c.sort_values(by="fecha", ascending=False), use_container_width=True)

            st.download_button(
                "⬇️ Descargar asistencia (CSV)",
                data=df_c.to_csv(index=False).encode("utf-8"),
                file_name=f"asistencia_{norm_key(centro)}_{anio_actual}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # TAB 4
    with tabs[3]:
        st.subheader("Tablero global (todos los centros / este año)")
        dfg = df_asistencia[df_asistencia["anio"] == anio_actual].copy()
        if dfg.empty:
            st.info("No hay registros globales para este año.")
        else:
            by_centro = dfg.groupby("centro", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            bar = (
                alt.Chart(by_centro)
                .mark_bar()
                .encode(
                    x=alt.X("centro:N", title="Centro"),
                    y=alt.Y("presentes:Q", title="Total"),
                    tooltip=["centro:N", "presentes:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(bar, use_container_width=True)
            st.dataframe(dfg.sort_values(by="fecha", ascending=False), use_container_width=True)

    with st.sidebar.expander("🔧 Diagnóstico", expanded=False):
        csv_path = find_csv_path()
        st.write("CSV encontrado:", csv_path if csv_path else "❌ NO")
        if csv_path:
            df_csv = load_personas_csv_fallback()
            st.write("Filas CSV:", len(df_csv))
            st.write("Centros detectados en CSV:", sorted(set(df_csv["centro"].tolist())))
        st.write("Filas PERSONAS (Sheets):", len(df_personas))
        st.write("Filas ASISTENCIA (Sheets):", len(df_asistencia))
        st.write("Centro usuario:", centro)
        st.write("Service Account:", client_email)
        st.write("Spreadsheet ID:", sid)


if __name__ == "__main__":
    main()

