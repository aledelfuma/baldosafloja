from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

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

# Maranatha: quién puede cargar qué espacio (ajustalo a tu realidad)
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

TAB_ASISTENCIA = "asistencia"
TAB_PERSONAS = "personas"

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
PERSONAS_HEADERS = ["nombre", "frecuencia", "centro"]

LOCAL_ASISTENCIA_PATH = Path("/tmp/asistencia_local.csv")
LOCAL_PERSONAS_PATH = Path("/tmp/personas_local.csv")

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
.hc-card {{
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(10, 13, 18, 0.70);
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
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
hr {{
  border:none;
  border-top: 1px solid rgba(255,255,255,0.08);
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
    if "no as" in k or k in ["no", "noasiste", "no asiste"]:
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
        return int(ds[:4])
    except Exception:
        return date.today().year


# =========================
# Backend abstraction
# =========================
@dataclass
class BackendStatus:
    mode: str  # "sheets" or "local"
    details: str


class StorageBackend:
    def read_personas(self) -> pd.DataFrame:
        raise NotImplementedError

    def write_personas(self, df: pd.DataFrame) -> None:
        raise NotImplementedError

    def read_asistencia(self) -> pd.DataFrame:
        raise NotImplementedError

    def append_asistencia(self, row: List[Any]) -> None:
        raise NotImplementedError

    def ensure_ready(self) -> BackendStatus:
        raise NotImplementedError


# ---------- Local CSV backend (no se cae nunca) ----------
class LocalCSVBackend(StorageBackend):
    def ensure_ready(self) -> BackendStatus:
        # asegurar archivos con header
        if not LOCAL_PERSONAS_PATH.exists():
            pd.DataFrame(columns=PERSONAS_HEADERS).to_csv(LOCAL_PERSONAS_PATH, index=False, encoding="utf-8")
        if not LOCAL_ASISTENCIA_PATH.exists():
            pd.DataFrame(columns=ASISTENCIA_HEADERS).to_csv(LOCAL_ASISTENCIA_PATH, index=False, encoding="utf-8")
        return BackendStatus("local", f"Guardando localmente en {LOCAL_ASISTENCIA_PATH}")

    def read_personas(self) -> pd.DataFrame:
        try:
            return pd.read_csv(LOCAL_PERSONAS_PATH)
        except Exception:
            return pd.DataFrame(columns=PERSONAS_HEADERS)

    def write_personas(self, df: pd.DataFrame) -> None:
        df.to_csv(LOCAL_PERSONAS_PATH, index=False, encoding="utf-8")

    def read_asistencia(self) -> pd.DataFrame:
        try:
            return pd.read_csv(LOCAL_ASISTENCIA_PATH)
        except Exception:
            return pd.DataFrame(columns=ASISTENCIA_HEADERS)

    def append_asistencia(self, row: List[Any]) -> None:
        df = self.read_asistencia()
        add = pd.DataFrame([row], columns=ASISTENCIA_HEADERS)
        out = pd.concat([df, add], ignore_index=True)
        out.to_csv(LOCAL_ASISTENCIA_PATH, index=False, encoding="utf-8")


# ---------- Google Sheets backend ----------
class SheetsBackend(StorageBackend):
    def __init__(self):
        self._gc = None
        self._sh = None
        self._sa_email = ""

    def ensure_ready(self) -> BackendStatus:
        # Importa perezoso y con error controlado
        try:
            import gspread  # noqa
            from google.oauth2.service_account import Credentials  # noqa
        except Exception as e:
            return BackendStatus("local", f"No se pudo importar gspread/google-auth: {e}")

        # Validación secrets
        if "gcp_service_account" not in st.secrets or "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
            return BackendStatus("local", "Faltan secrets [gcp_service_account] o [sheets].spreadsheet_id")

        sa = dict(st.secrets["gcp_service_account"])
        pk = sa.get("private_key", "")
        if isinstance(pk, str) and "\\n" in pk:
            sa["private_key"] = pk.replace("\\n", "\n")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        try:
            creds = Credentials.from_service_account_info(sa, scopes=scopes)
            import gspread
            self._gc = gspread.authorize(creds)
            self._sa_email = sa.get("client_email", "")
            sid = st.secrets["sheets"]["spreadsheet_id"]
            self._sh = self._gc.open_by_key(sid)
        except Exception as e:
            return BackendStatus("local", f"No se pudo abrir Google Sheets (permiso/clave/red): {e}")

        # asegurar tabs + headers
        self._ensure_tab(TAB_PERSONAS, PERSONAS_HEADERS)
        self._ensure_tab(TAB_ASISTENCIA, ASISTENCIA_HEADERS)

        return BackendStatus("sheets", f"Conectado a Sheets como {self._sa_email}")

    def _ensure_tab(self, title: str, headers: List[str]):
        assert self._sh is not None
        names = [w.title for w in self._sh.worksheets()]
        if title not in names:
            self._sh.add_worksheet(title=title, rows=5000, cols=40)
        ws = self._sh.worksheet(title)
        values = ws.get_all_values()
        if not values:
            ws.append_row(headers, value_input_option="RAW")
        else:
            first = values[0]
            if [clean_cell(x) for x in first] != headers:
                ws.update("A1", [headers])

    def _read_tab(self, title: str) -> pd.DataFrame:
        assert self._sh is not None
        ws = self._sh.worksheet(title)
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
        return df

    def read_personas(self) -> pd.DataFrame:
        df = self._read_tab(TAB_PERSONAS)
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def write_personas(self, df: pd.DataFrame) -> None:
        assert self._sh is not None
        ws = self._sh.worksheet(TAB_PERSONAS)
        ws.clear()
        ws.update("A1", [df.columns.tolist()] + df.astype(str).fillna("").values.tolist())

    def read_asistencia(self) -> pd.DataFrame:
        df = self._read_tab(TAB_ASISTENCIA)
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def append_asistencia(self, row: List[Any]) -> None:
        assert self._sh is not None
        ws = self._sh.worksheet(TAB_ASISTENCIA)
        ws.append_row([str(x) for x in row], value_input_option="USER_ENTERED")


def get_backend() -> Tuple[StorageBackend, BackendStatus]:
    # Intentar Sheets; si falla, caer a local sin romper.
    sheets = SheetsBackend()
    status = sheets.ensure_ready()
    if status.mode == "sheets":
        return sheets, status
    local = LocalCSVBackend()
    return local, local.ensure_ready()


backend, backend_status = get_backend()


# =========================
# Users desde secrets
# =========================
def get_users() -> Dict[str, Dict[str, Any]]:
    users: Dict[str, Dict[str, Any]] = {}
    try:
        if "users" in st.secrets:
            for username, info in st.secrets["users"].items():
                u = str(username).lower().strip()
                users[u] = {
                    "password": str(info.get("password", "")),
                    "centro": clean_cell(info.get("centro", "")) or None,
                    "nombre": clean_cell(info.get("nombre", u)) or u,
                }
    except Exception:
        users = {}

    # fallback mínimo (para que nunca se quede sin acceso)
    if not users:
        users = {"admin": {"password": "admin", "centro": None, "nombre": "Admin"}}
    return users


def login():
    users = get_users()

    st.sidebar.markdown("## Acceso")
    if "auth" not in st.session_state:
        st.session_state.auth = {"user": None, "nombre": "", "centro": None}

    auth = st.session_state.auth
    if auth["user"]:
        st.sidebar.success(f"Conectado: {auth['nombre']}")
        st.sidebar.caption(f"Modo almacenamiento: {backend_status.mode} — {backend_status.details}")
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
# Personas: CSV robusto
# =========================
def find_csv_path() -> Optional[str]:
    candidates = ["datapersonas.csv", "personas.csv", "data/datapersonas.csv", "data/personas.csv"]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def _parse_line_persona(line: str):
    ln = line.strip()
    if not ln:
        return None

    # TAB
    if "\t" in ln and ln.count("\t") >= 2:
        parts = [p.strip() for p in ln.split("\t")]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]

    # ;
    if ";" in ln and ln.count(";") >= 2:
        parts = [p.strip() for p in ln.split(";")]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]

    # CSV con comillas o normal (si hay comas en el nombre, tomamos las últimas 2 como freq/centro)
    try:
        parts = next(csv.reader([ln], delimiter=",", quotechar='"', skipinitialspace=True))
        parts = [p.strip() for p in parts if p.strip() != ""]
        if len(parts) >= 3:
            centro = parts[-1]
            frecuencia = parts[-2]
            nombre = ",".join(parts[:-2]).strip()
            if nombre:
                return nombre, frecuencia, centro
    except Exception:
        pass

    # 2+ espacios (copiado de planilla)
    parts = [p.strip() for p in re.split(r"\s{2,}", ln) if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]

    return None


def normalize_personas_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=PERSONAS_HEADERS)

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    if "personas" in df.columns and "nombre" not in df.columns:
        df.rename(columns={"personas": "nombre"}, inplace=True)

    for c in ["nombre", "frecuencia", "centro"]:
        if c not in df.columns:
            df[c] = ""

    out = df[["nombre", "frecuencia", "centro"]].copy()
    out["nombre"] = out["nombre"].astype(str).map(clean_cell)
    out["frecuencia"] = out["frecuencia"].astype(str).map(normalize_frecuencia)
    out["centro"] = out["centro"].astype(str).map(normalize_centro)

    out = out[out["nombre"] != ""]
    out = out.drop_duplicates(subset=["nombre", "centro"], keep="first").reset_index(drop=True)
    return out


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
    data_lines = lines[1:] if ("nombre" in first and "frecuencia" in first) else lines

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


def seed_personas_from_csv(force: bool = False) -> Dict[str, Any]:
    df_sheet = normalize_personas_df(backend.read_personas())
    df_csv, meta = load_personas_csv_robusto()

    if df_csv.empty:
        meta["imported"] = 0
        meta["final_total"] = len(df_sheet)
        meta["reason"] = "CSV vacío o no encontrado"
        return meta

    if force or df_sheet.empty:
        df_final = df_csv if df_sheet.empty else normalize_personas_df(pd.concat([df_sheet, df_csv], ignore_index=True))
        backend.write_personas(df_final)
        meta["imported"] = len(df_csv)
        meta["final_total"] = len(df_final)
        meta["reason"] = "OK"
        return meta

    meta["imported"] = 0
    meta["final_total"] = len(df_sheet)
    meta["reason"] = "Ya había datos (usá FORZAR para reimportar)"
    return meta


# =========================
# Asistencia: reglas
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

    # Maranatha
    if not espacio:
        return False, "En Casa Maranatha tenés que elegir un espacio."
    allowed = MARANATHA_PERMISOS_POR_ESPACIO.get(espacio, [])
    if coordinador not in allowed:
        return False, f"{coordinador} no puede cargar el espacio: {espacio}."
    return True, ""


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


def is_duplicate(df_asistencia: pd.DataFrame, centro: str, fecha_str: str, espacio: str) -> bool:
    if df_asistencia is None or df_asistencia.empty:
        return False
    df = df_asistencia.copy()
    centro = normalize_centro(centro)
    espacio = clean_cell(espacio)

    if centro != "Casa Maranatha":
        return ((df["centro"] == centro) & (df["fecha"] == fecha_str)).any()

    return ((df["centro"] == centro) & (df["fecha"] == fecha_str) & (df["espacio"] == espacio)).any()


def compute_metrics(df: pd.DataFrame, year: int, centro: Optional[str] = None) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "hoy": 0, "semana": 0, "mes": 0,
            "df_diario": pd.DataFrame(columns=["fecha", "presentes"]),
            "df_por_centro": pd.DataFrame(columns=["centro", "total_anual"]),
        }

    d = df.copy()
    d = d[d["anio"] == year].copy()
    if centro:
        d = d[d["centro"] == centro].copy()
    if d.empty:
        return {
            "hoy": 0, "semana": 0, "mes": 0,
            "df_diario": pd.DataFrame(columns=["fecha", "presentes"]),
            "df_por_centro": pd.DataFrame(columns=["centro", "total_anual"]),
        }

    d["_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    d = d.dropna(subset=["_dt"]).copy()

    today = pd.Timestamp(date.today())
    start_week = today - pd.Timedelta(days=today.weekday())
    start_month = today.replace(day=1)

    hoy = int(d[d["_dt"].dt.date == today.date()]["presentes"].sum())
    semana = int(d[d["_dt"] >= start_week]["presentes"].sum())
    mes = int(d[d["_dt"] >= start_month]["presentes"].sum())

    df_diario = d.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")

    df_por_centro = pd.DataFrame(columns=["centro", "total_anual"])
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
st.sidebar.caption(f"Modo almacenamiento: **{backend_status.mode}** — {backend_status.details}")

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

# Coordinador restringido
if CENTRO == "Casa Maranatha":
    allowed_coords = MARANATHA_PERMISOS_POR_ESPACIO.get(ESPACIO, COORDINADORES_POR_CENTRO["Casa Maranatha"])
else:
    allowed_coords = COORDINADORES_POR_CENTRO.get(CENTRO, [])

COORDINADOR = st.sidebar.selectbox("¿Quién carga?", allowed_coords, index=0)

with st.sidebar.expander("🔧 Diagnóstico", expanded=False):
    st.write("Usuario:", st.session_state.auth["user"])
    st.write("Nombre:", st.session_state.auth["nombre"])
    st.write("Centro fijo:", assigned_center or "(admin)")
    st.write("Año:", YEAR)


# =========================
# Load data
# =========================
df_personas = normalize_personas_df(backend.read_personas())
df_asistencia = parse_asistencia_df(backend.read_asistencia())

# Header
st.markdown(f"# {APP_TITLE}")
st.markdown(
    f"Trabajando sobre: **{CENTRO}**"
    + (f" / **{ESPACIO}**" if CENTRO == "Casa Maranatha" and ESPACIO else "")
    + f" — 👤 **{COORDINADOR}**  &nbsp;&nbsp; <span class='hc-pill'>Año: {YEAR}</span>",
    unsafe_allow_html=True,
)

# KPIs Centro + Global
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

# Tabs
t1, t2, t3, t4 = st.tabs(["🧾 Cargar asistencia", "👥 Personas", "📊 Reportes", "🌍 Global"])


# =========================
# TAB 1: Cargar asistencia
# =========================
with t1:
    st.subheader("Cargar asistencia (con control de duplicados y permisos)")

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
        # recargar asistencia para evitar “doble click”
        df_now = parse_asistencia_df(backend.read_asistencia())
        if is_duplicate(df_now, CENTRO, fecha_str, espacio_guardar):
            if CENTRO != "Casa Maranatha":
                st.warning(f"Ya se cargó asistencia para **{CENTRO}** el **{fecha_str}**. (1 por día)")
            else:
                st.warning(f"Ya se cargó **{CENTRO} / {espacio_guardar}** el **{fecha_str}**. (1 por día por espacio)")
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
            backend.append_asistencia(row)
            st.success("Asistencia guardada ✅")
            st.rerun()

    st.markdown("### Últimos registros (este centro / este año)")
    df_c = df_asistencia[(df_asistencia["centro"] == CENTRO) & (df_asistencia["anio"] == YEAR)].copy()
    if df_c.empty:
        st.info("Todavía no hay registros.")
    else:
        st.dataframe(df_c.sort_values("fecha", ascending=False).head(30), use_container_width=True)


# =========================
# TAB 2: Personas
# =========================
with t2:
    st.subheader("Personas")
    left, right = st.columns([1, 1])
    with left:
        if st.button("📥 Importar datapersonas.csv (FORZAR)", use_container_width=True):
            meta = seed_personas_from_csv(force=True)
            st.success(f"Importadas: {meta.get('imported', 0)} | Total final: {meta.get('final_total', '?')}")
            st.write(meta)
            st.rerun()
    with right:
        p = find_csv_path()
        st.caption(f"CSV detectado: **{p or 'NO'}** (nombre esperado: `datapersonas.csv`)")

    # mostrar por centro actual
    df_p = df_personas[df_personas["centro"] == CENTRO].copy()
    st.markdown(f"<span class='hc-pill'>Personas visibles en {CENTRO}: <b>{len(df_p)}</b></span>", unsafe_allow_html=True)

    q = st.text_input("Buscar (nombre)", value="")
    if q:
        df_p = df_p[df_p["nombre"].str.contains(q, case=False, na=False)]

    st.dataframe(df_p, use_container_width=True, height=420)

    st.divider()
    st.markdown("### Agregar persona (manual)")
    a, b = st.columns([2, 1])
    with a:
        nombre_new = st.text_input("Nombre (ej: Apellido, Nombre)", value="")
    with b:
        frec_new = st.selectbox("Frecuencia", FRECUENCIAS_CANON, index=2)

    if st.button("➕ Guardar persona", use_container_width=True):
        if not nombre_new.strip():
            st.error("Falta el nombre.")
        else:
            df_all = df_personas.copy()
            add = pd.DataFrame([{"nombre": clean_cell(nombre_new), "frecuencia": frec_new, "centro": CENTRO}])
            df_all = normalize_personas_df(pd.concat([df_all, add], ignore_index=True))
            backend.write_personas(df_all)
            st.success("Persona agregada ✅")
            st.rerun()


# =========================
# TAB 3: Reportes centro
# =========================
with t3:
    st.subheader("Reportes del centro")
    df_c = df_asistencia[(df_asistencia["centro"] == CENTRO) & (df_asistencia["anio"] == YEAR)].copy()

    if df_c.empty:
        st.info("No hay datos para este centro en este año.")
    else:
        st.markdown("### Evolución diaria (suma)")
        diario = df_c.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
        st.line_chart(diario.set_index("fecha")["presentes"])

        st.markdown("### Por coordinador (suma)")
        por_coord = df_c.groupby("coordinador", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
        st.bar_chart(por_coord.set_index("coordinador")["presentes"])

        if CENTRO == "Casa Maranatha":
            st.markdown("### Por espacio (Maranatha)")
            por_esp = df_c.groupby("espacio", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            st.bar_chart(por_esp.set_index("espacio")["presentes"])

        st.markdown("### Base de datos (registros)")
        st.dataframe(df_c.sort_values("fecha", ascending=False), use_container_width=True)

        st.download_button(
            "⬇️ Descargar CSV (este centro / año)",
            data=df_c.to_csv(index=False).encode("utf-8"),
            file_name=f"asistencia_{CENTRO.replace(' ','_')}_{YEAR}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# =========================
# TAB 4: Global
# =========================
with t4:
    st.subheader("Tablero Global (todos los centros)")

    df_y = df_asistencia[df_asistencia["anio"] == YEAR].copy()
    if df_y.empty:
        st.info("No hay datos globales para este año.")
    else:
        st.markdown("### Totales por centro (año)")
        st.dataframe(m_global["df_por_centro"], use_container_width=True)

        st.markdown("### Evolución diaria global")
        gd = m_global["df_diario"].copy()
        if not gd.empty:
            gd = gd.tail(120)
            st.line_chart(gd.set_index("fecha")["presentes"])

        st.markdown("### Últimos registros (global)")
        st.dataframe(df_y.sort_values("fecha", ascending=False).head(50), use_container_width=True)

        st.download_button(
            "⬇️ Descargar CSV (global / año)",
            data=df_y.to_csv(index=False).encode("utf-8"),
            file_name=f"asistencia_GLOBAL_{YEAR}.csv",
            mime="text/csv",
            use_container_width=True,
        )
