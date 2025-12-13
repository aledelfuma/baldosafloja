from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# Imports Google (requiere requirements.txt)
import gspread
from google.oauth2.service_account import Credentials


# =========================
# Config
# =========================
APP_TITLE = "Sistema de Asistencia — Hogar de Cristo Bahía Blanca"
PRIMARY = "#004E7B"
ACCENT = "#63296C"

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar (primaria)",
    "Apoyo escolar (secundaria)",
    "FinEs",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]

COORDINADORES_POR_CENTRO = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellan"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

MARANATHA_PERMISOS_POR_ESPACIO = {
    "Taller de costura": ["Florencia", "Guillermina Cazenave"],
    "Apoyo escolar (primaria)": ["Florencia", "Guillermina Cazenave"],
    "Apoyo escolar (secundaria)": ["Florencia", "Guillermina Cazenave"],
    "FinEs": ["Florencia", "Guillermina Cazenave"],
    "Espacio Joven": ["Florencia", "Guillermina Cazenave"],
    "La Ronda": ["Florencia", "Guillermina Cazenave"],
    "Otro": ["Florencia", "Guillermina Cazenave"],
}

FRECUENCIAS_CANON = ["Diaria", "Semanal", "Mensual", "No asiste"]

TAB_PERSONAS = "personas"
TAB_ASISTENCIA = "asistencia"

PERSONAS_HEADERS = ["nombre", "frecuencia", "centro"]
ASISTENCIA_HEADERS = [
    "timestamp",
    "fecha",
    "anio",
    "centro",
    "espacio",
    "presentes",
    "coordinador",
    "modo",
    "notas",
    "usuario",
]

st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="wide")


# =========================
# UI
# =========================
def inject_css():
    st.markdown(
        f"""
<style>
.stApp {{
  background: radial-gradient(1200px 800px at 20% 10%, rgba(99,41,108,0.28), transparent 55%),
              radial-gradient(1200px 900px at 75% 35%, rgba(0,78,123,0.25), transparent 55%),
              linear-gradient(180deg, #0B0F14 0%, #070A0D 100%);
  color: #EAF0F6;
}}
section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, rgba(0,78,123,0.25), rgba(99,41,108,0.20));
  border-right: 1px solid rgba(255,255,255,0.06);
}}
.hc-kpi {{
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(10, 13, 18, 0.75);
  border-radius: 16px;
  padding: 14px 16px;
}}
.hc-pill {{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04);
  font-size: 12px;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(items: List[Tuple[str, str]]):
    cols = st.columns(len(items))
    for c, (label, value) in zip(cols, items):
        c.markdown(
            f"""
            <div class="hc-kpi">
              <div style="opacity:.78;font-size:12px;margin-bottom:6px;">{label}</div>
              <div style="font-size:34px;font-weight:800;letter-spacing:-0.5px;line-height:1;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


inject_css()


# =========================
# Helpers
# =========================
def clean_cell(x) -> str:
    if x is None:
        return ""
    return str(x).replace("\u00a0", " ").strip()


def normalize_centro(s: str) -> str:
    s = clean_cell(s)
    k = s.lower()
    if "belen" in k or "belén" in k:
        return "Calle Belén"
    if "nudo" in k:
        return "Nudo a Nudo"
    if "maran" in k:
        return "Casa Maranatha"
    for c in CENTROS:
        if c.lower() == k:
            return c
    return s


def normalize_frecuencia(s: str) -> str:
    s = clean_cell(s)
    k = s.lower()
    if "diar" in k:
        return "Diaria"
    if "seman" in k:
        return "Semanal"
    if "mens" in k:
        return "Mensual"
    if "no as" in k:
        return "No asiste"
    return s


def safe_int(x, default=0) -> int:
    try:
        if x is None:
            return default
        return int(float(str(x).replace(",", ".")))
    except Exception:
        return default


def datestr(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def year_from_datestr(ds: str) -> int:
    try:
        return int(str(ds)[:4])
    except Exception:
        return date.today().year


def normalize_personas_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=PERSONAS_HEADERS)
    d = df.copy()
    d.columns = [c.strip().lower() for c in d.columns]
    if "personas" in d.columns and "nombre" not in d.columns:
        d.rename(columns={"personas": "nombre"}, inplace=True)
    for c in PERSONAS_HEADERS:
        if c not in d.columns:
            d[c] = ""
    out = d[PERSONAS_HEADERS].copy()
    out["nombre"] = out["nombre"].astype(str).map(clean_cell)
    out["frecuencia"] = out["frecuencia"].astype(str).map(normalize_frecuencia)
    out["centro"] = out["centro"].astype(str).map(normalize_centro)
    out = out[out["nombre"] != ""]
    out = out.drop_duplicates(subset=["nombre", "centro"], keep="first").reset_index(drop=True)
    return out


def parse_asistencia_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=[c.lower() for c in ASISTENCIA_HEADERS])
    d = df.copy()
    d.columns = [c.strip().lower() for c in d.columns]
    for c in [x.lower() for x in ASISTENCIA_HEADERS]:
        if c not in d.columns:
            d[c] = ""
    d["centro"] = d["centro"].astype(str).map(normalize_centro)
    d["espacio"] = d["espacio"].astype(str).map(clean_cell)
    d["coordinador"] = d["coordinador"].astype(str).map(clean_cell)
    d["presentes"] = d["presentes"].map(lambda x: safe_int(x, 0))
    d["fecha"] = d["fecha"].astype(str).map(lambda x: clean_cell(x)[:10])
    d["anio"] = d["anio"].map(lambda x: safe_int(x, year_from_datestr(datestr(date.today()))))
    return d[[c.lower() for c in ASISTENCIA_HEADERS]]


# =========================
# Google Sheets (estable)
# =========================
@dataclass
class SheetCtx:
    sh: gspread.Spreadsheet
    ws_personas: gspread.Worksheet
    ws_asistencia: gspread.Worksheet
    service_email: str
    spreadsheet_id: str


def validate_secrets_or_stop():
    if "gcp_service_account" not in st.secrets:
        st.error("Falta [gcp_service_account] en Secrets.")
        st.stop()
    if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
        st.error("Falta [sheets].spreadsheet_id en Secrets.")
        st.stop()
    if "users" not in st.secrets:
        st.error("Falta [users] en Secrets.")
        st.stop()


@st.cache_resource(show_spinner=False)
def get_sheet_ctx() -> SheetCtx:
    validate_secrets_or_stop()

    sa = dict(st.secrets["gcp_service_account"])
    pk = sa.get("private_key", "")
    if isinstance(pk, str) and "\\n" in pk:
        sa["private_key"] = pk.replace("\\n", "\n")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    gc = gspread.authorize(creds)

    sid = st.secrets["sheets"]["spreadsheet_id"]
    sh = gc.open_by_key(sid)

    service_email = clean_cell(sa.get("client_email", ""))

    def ensure_tab(title: str, headers: List[str]) -> gspread.Worksheet:
        names = [w.title for w in sh.worksheets()]
        if title not in names:
            sh.add_worksheet(title=title, rows=8000, cols=40)
        ws = sh.worksheet(title)
        values = ws.get_all_values()
        if not values:
            ws.append_row(headers, value_input_option="RAW")
        else:
            first = [clean_cell(x) for x in values[0]]
            if first != headers:
                ws.update("A1", [headers])
        return ws

    ws_personas = ensure_tab(TAB_PERSONAS, PERSONAS_HEADERS)
    ws_asistencia = ensure_tab(TAB_ASISTENCIA, ASISTENCIA_HEADERS)

    return SheetCtx(sh=sh, ws_personas=ws_personas, ws_asistencia=ws_asistencia, service_email=service_email, spreadsheet_id=sid)


def read_ws(ws: gspread.Worksheet) -> pd.DataFrame:
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    header = [clean_cell(h) for h in values[0]]
    rows = values[1:]
    fixed = []
    for r in rows:
        r = list(r)
        if len(r) < len(header):
            r += [""] * (len(header) - len(r))
        fixed.append(r[: len(header)])
    df = pd.DataFrame(fixed, columns=header)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def overwrite_ws(ws: gspread.Worksheet, df: pd.DataFrame):
    ws.clear()
    ws.update("A1", [df.columns.tolist()] + df.astype(str).fillna("").values.tolist())


def append_ws(ws: gspread.Worksheet, row: List[Any]):
    ws.append_row([str(x) for x in row], value_input_option="USER_ENTERED")


# Conectar sí o sí
try:
    ctx = get_sheet_ctx()
except Exception as e:
    st.error("❌ No se pudo conectar a Google Sheets.")
    st.write("Detalle:", str(e))
    st.stop()


# =========================
# Auth
# =========================
def get_users() -> Dict[str, Dict[str, Any]]:
    users: Dict[str, Dict[str, Any]] = {}
    for username, info in st.secrets["users"].items():
        u = str(username).lower().strip()
        users[u] = {
            "password": str(info.get("password", "")),
            "centro": clean_cell(info.get("centro", "")) or None,
            "nombre": clean_cell(info.get("nombre", u)) or u,
        }
    return users


def login():
    users = get_users()
    st.sidebar.markdown("## Acceso")

    if "auth" not in st.session_state:
        st.session_state.auth = {"user": None, "nombre": "", "centro": None}

    auth = st.session_state.auth
    if auth["user"]:
        st.sidebar.success(f"Conectado: {auth['nombre']}")
        st.sidebar.caption(f"Google Sheets OK — {ctx.service_email}")
        if st.sidebar.button("Salir"):
            st.session_state.auth = {"user": None, "nombre": "", "centro": None}
            st.rerun()
        return

    u = st.sidebar.text_input("Usuario")
    p = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        key = clean_cell(u).lower()
        if key not in users:
            st.sidebar.error("Usuario incorrecto.")
            return
        info = users[key]
        if clean_cell(info.get("password")) != clean_cell(p):
            st.sidebar.error("Contraseña incorrecta.")
            return
        st.session_state.auth = {
            "user": key,
            "nombre": info.get("nombre", key),
            "centro": normalize_centro(info.get("centro")) if info.get("centro") else None,
        }
        st.rerun()


login()
if not st.session_state.auth["user"]:
    st.stop()


# =========================
# CSV personas: robusto + import estable
# =========================
def find_csv_path() -> Optional[str]:
    for p in ["datapersonas.csv", "personas.csv", "data/datapersonas.csv", "data/personas.csv"]:
        if Path(p).exists():
            return p
    return None


def _parse_line_persona(line: str):
    ln = line.strip()
    if not ln:
        return None

    if "\t" in ln and ln.count("\t") >= 2:
        parts = [p.strip() for p in ln.split("\t")]
        return parts[0], parts[1], parts[2]

    if ";" in ln and ln.count(";") >= 2:
        parts = [p.strip() for p in ln.split(";")]
        return parts[0], parts[1], parts[2]

    # CSV: toma las últimas 2 columnas como freq/centro, el resto es nombre (aunque tenga comas)
    try:
        parts = next(csv.reader([ln], delimiter=",", quotechar='"', skipinitialspace=True))
        parts = [p.strip() for p in parts if p.strip() != ""]
        if len(parts) >= 3:
            centro = parts[-1]
            frecuencia = parts[-2]
            nombre = ",".join(parts[:-2]).strip()
            return nombre, frecuencia, centro
    except Exception:
        pass

    parts = [p.strip() for p in re.split(r"\s{2,}", ln) if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]

    return None


def load_personas_csv_robusto() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    path = find_csv_path()
    meta = {"path": path, "lines": 0, "parsed": 0, "skipped": 0}
    if not path:
        return pd.DataFrame(columns=PERSONAS_HEADERS), meta

    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    lines = [ln for ln in lines if ln.strip()]
    meta["lines"] = len(lines)
    if not lines:
        return pd.DataFrame(columns=PERSONAS_HEADERS), meta

    first = lines[0].lower()
    data_lines = lines[1:] if ("nombre" in first and "frecuencia" in first and "centro" in first) else lines

    rows = []
    for ln in data_lines:
        parsed = _parse_line_persona(ln)
        if not parsed:
            meta["skipped"] += 1
            continue
        nombre, freq, centro = parsed
        rows.append([nombre, freq, centro])
        meta["parsed"] += 1

    df = pd.DataFrame(rows, columns=PERSONAS_HEADERS)
    df = normalize_personas_df(df)
    return df, meta


# =========================
# Reglas de carga + métricas
# =========================
def can_user_load(centro: str, coordinador: str, espacio: str) -> Tuple[bool, str]:
    centro = normalize_centro(centro)
    coordinador = clean_cell(coordinador)
    espacio = clean_cell(espacio)

    if centro != "Casa Maranatha":
        allowed = COORDINADORES_POR_CENTRO.get(centro, [])
        if coordinador not in allowed:
            return False, f"Este coordinador no está habilitado para cargar en {centro}."
        return True, ""

    if not espacio:
        return False, "En Casa Maranatha tenés que elegir un espacio."
    allowed = MARANATHA_PERMISOS_POR_ESPACIO.get(espacio, [])
    if coordinador not in allowed:
        return False, f"{coordinador} no puede cargar el espacio: {espacio}."
    return True, ""


def is_duplicate(df_asistencia: pd.DataFrame, centro: str, fecha_str: str, espacio: str) -> bool:
    if df_asistencia is None or df_asistencia.empty:
        return False
    centro = normalize_centro(centro)
    espacio = clean_cell(espacio)

    if centro != "Casa Maranatha":
        return ((df_asistencia["centro"] == centro) & (df_asistencia["fecha"] == fecha_str)).any()

    return (
        (df_asistencia["centro"] == centro)
        & (df_asistencia["fecha"] == fecha_str)
        & (df_asistencia["espacio"] == espacio)
    ).any()


def compute_metrics(df: pd.DataFrame, year: int, centro: Optional[str] = None) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"hoy": 0, "semana": 0, "mes": 0, "df_diario": pd.DataFrame(), "df_por_centro": pd.DataFrame()}

    d = df[df["anio"] == year].copy()
    if centro:
        d = d[d["centro"] == centro].copy()
    if d.empty:
        return {"hoy": 0, "semana": 0, "mes": 0, "df_diario": pd.DataFrame(), "df_por_centro": pd.DataFrame()}

    d["_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    d = d.dropna(subset=["_dt"]).copy()

    today = pd.Timestamp(date.today())
    start_week = today - pd.Timedelta(days=today.weekday())
    start_month = today.replace(day=1)

    hoy = int(d[d["_dt"].dt.date == today.date()]["presentes"].sum())
    semana = int(d[d["_dt"] >= start_week]["presentes"].sum())
    mes = int(d[d["_dt"] >= start_month]["presentes"].sum())

    df_diario = d.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")

    df_por_centro = pd.DataFrame()
    if centro is None:
        df_por_centro = (
            d.groupby("centro", as_index=False)["presentes"].sum()
            .rename(columns={"presentes": "total_anual"})
            .sort_values("total_anual", ascending=False)
        )

    return {"hoy": hoy, "semana": semana, "mes": mes, "df_diario": df_diario, "df_por_centro": df_por_centro}


# =========================
# Sidebar contexto
# =========================
st.sidebar.markdown("## Contexto")
st.sidebar.caption(f"Sheets OK — {ctx.service_email}")

current_year = date.today().year
YEAR = st.sidebar.selectbox("Año", [current_year, current_year - 1, current_year - 2], index=0)

assigned_center = st.session_state.auth["centro"]
if assigned_center:
    CENTRO = assigned_center
    st.sidebar.markdown(f"<span class='hc-pill'>Centro asignado: <b>{CENTRO}</b></span>", unsafe_allow_html=True)
else:
    CENTRO = st.sidebar.selectbox("Centro", CENTROS, index=0)

if CENTRO == "Casa Maranatha":
    ESPACIO = st.sidebar.selectbox("Espacio", ESPACIOS_MARANATHA, index=0)
    if ESPACIO == "Otro":
        ESPACIO = st.sidebar.text_input("Especificar espacio", value="").strip()
else:
    ESPACIO = ""

if CENTRO == "Casa Maranatha":
    allowed_coords = MARANATHA_PERMISOS_POR_ESPACIO.get(ESPACIO, COORDINADORES_POR_CENTRO["Casa Maranatha"])
else:
    allowed_coords = COORDINADORES_POR_CENTRO.get(CENTRO, [])

COORDINADOR = st.sidebar.selectbox("¿Quién carga?", allowed_coords, index=0)

with st.sidebar.expander("🔧 Diagnóstico", expanded=False):
    st.write("Spreadsheet ID:", ctx.spreadsheet_id)
    st.write("Tabs:", [w.title for w in ctx.sh.worksheets()])


# =========================
# Load data (siempre desde Sheets)
# =========================
df_personas = normalize_personas_df(read_ws(ctx.ws_personas))
df_asistencia = parse_asistencia_df(read_ws(ctx.ws_asistencia))

# Header
st.markdown(f"# {APP_TITLE}")
st.markdown(
    f"Trabajando sobre: **{CENTRO}**"
    + (f" / **{ESPACIO}**" if CENTRO == "Casa Maranatha" and ESPACIO else "")
    + f" — 👤 **{COORDINADOR}**  &nbsp;&nbsp; <span class='hc-pill'>Año: {YEAR}</span>",
    unsafe_allow_html=True,
)

m_centro = compute_metrics(df_asistencia, YEAR, centro=CENTRO)
m_global = compute_metrics(df_asistencia, YEAR, centro=None)

kpi_row([
    ("HOY (Centro)", str(m_centro["hoy"])),
    ("Semana (Centro)", str(m_centro["semana"])),
    ("Mes (Centro)", str(m_centro["mes"])),
    ("HOY (Global)", str(m_global["hoy"])),
    ("Semana (Global)", str(m_global["semana"])),
    ("Mes (Global)", str(m_global["mes"])),
])

st.divider()

t1, t2, t3, t4 = st.tabs(["🧾 Cargar asistencia", "👥 Personas", "📊 Reportes", "🌍 Global"])


# =========================
# TAB 1: Cargar asistencia
# =========================
with t1:
    st.subheader("Cargar asistencia")

    colA, colB, colC = st.columns([1, 1, 2])
    with colA:
        FECHA = st.date_input("Fecha", value=date.today())
    with colB:
        MODO = st.selectbox("Tipo de día", ["Día habitual", "Evento especial", "Salida", "Centro cerrado"], index=0)
    with colC:
        NOTAS = st.text_input("Notas (opcional)", value="")

    cerrado = (MODO == "Centro cerrado")
    PRESENTES = st.number_input("Presentes", min_value=0, step=1, value=0, disabled=cerrado)

    fecha_str = datestr(FECHA)
    espacio_guardar = ESPACIO if CENTRO == "Casa Maranatha" else ""

    ok_perm, msg_perm = can_user_load(CENTRO, COORDINADOR, espacio_guardar)
    if not ok_perm:
        st.error(msg_perm)

    if st.button("✅ Guardar", use_container_width=True, disabled=not ok_perm):
        df_now = parse_asistencia_df(read_ws(ctx.ws_asistencia))
        if is_duplicate(df_now, CENTRO, fecha_str, espacio_guardar):
            st.warning("Ya existe una carga para ese día (según la regla).")
        else:
            row = [
                datetime.now().isoformat(timespec="seconds"),
                fecha_str,
                year_from_datestr(fecha_str),
                CENTRO,
                espacio_guardar,
                int(PRESENTES) if not cerrado else 0,
                COORDINADOR,
                MODO,
                clean_cell(NOTAS),
                st.session_state.auth["user"],
            ]
            append_ws(ctx.ws_asistencia, row)
            st.success("Guardado en Google Sheets ✅")
            st.rerun()

    st.markdown("### Últimos registros (este centro / este año)")
    df_c = df_asistencia[(df_asistencia["centro"] == CENTRO) & (df_asistencia["anio"] == YEAR)].copy()
    if df_c.empty:
        st.info("Todavía no hay registros.")
    else:
        st.dataframe(df_c.sort_values("fecha", ascending=False).head(40), use_container_width=True)


# =========================
# TAB 2: Personas
# =========================
with t2:
    st.subheader("Personas (Google Sheets)")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("📥 Importar datapersonas.csv a Google", use_container_width=True):
            df_csv, meta = load_personas_csv_robusto()
            if df_csv.empty:
                st.error("No pude leer datapersonas.csv. Revisá el archivo en el repo.")
                st.write(meta)
            else:
                df_sheet = normalize_personas_df(read_ws(ctx.ws_personas))
                df_final = normalize_personas_df(pd.concat([df_sheet, df_csv], ignore_index=True))
                overwrite_ws(ctx.ws_personas, df_final)
                st.success(f"Importadas {len(df_csv)} — Total ahora: {len(df_final)} ✅")
                st.write(meta)
                st.rerun()
    with c2:
        p = find_csv_path()
        st.caption(f"CSV detectado: **{p or 'NO'}** (esperado: `datapersonas.csv` en el repo)")

    df_personas = normalize_personas_df(read_ws(ctx.ws_personas))
    df_p = df_personas[df_personas["centro"] == CENTRO].copy()
    st.markdown(f"<span class='hc-pill'>Personas en {CENTRO}: <b>{len(df_p)}</b></span>", unsafe_allow_html=True)

    q = st.text_input("Buscar (nombre)", value="")
    if q:
        df_p = df_p[df_p["nombre"].str.contains(q, case=False, na=False)]
    st.dataframe(df_p, use_container_width=True, height=440)


# =========================
# TAB 3: Reportes
# =========================
with t3:
    st.subheader("Reportes del centro")
    df_c = df_asistencia[(df_asistencia["centro"] == CENTRO) & (df_asistencia["anio"] == YEAR)].copy()
    if df_c.empty:
        st.info("No hay datos para este centro en este año.")
    else:
        diario = df_c.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
        st.line_chart(diario.set_index("fecha")["presentes"])

        por_coord = df_c.groupby("coordinador", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
        st.bar_chart(por_coord.set_index("coordinador")["presentes"])

        if CENTRO == "Casa Maranatha":
            por_esp = df_c.groupby("espacio", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            st.bar_chart(por_esp.set_index("espacio")["presentes"])

        st.dataframe(df_c.sort_values("fecha", ascending=False), use_container_width=True)


# =========================
# TAB 4: Global
# =========================
with t4:
    st.subheader("Global (todos los centros)")
    df_y = df_asistencia[df_asistencia["anio"] == YEAR].copy()
    if df_y.empty:
        st.info("No hay datos globales para este año.")
    else:
        st.dataframe(m_global["df_por_centro"], use_container_width=True)

        gd = m_global["df_diario"].copy()
        if not gd.empty:
            st.line_chart(gd.tail(120).set_index("fecha")["presentes"])

        st.dataframe(df_y.sort_values("fecha", ascending=False).head(60), use_container_width=True)
