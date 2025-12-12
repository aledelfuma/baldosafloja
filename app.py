# app.py
from __future__ import annotations

import os
import re
import json
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import pandas as pd
import streamlit as st

# -----------------------------
# Config visual (Hogar de Cristo)
# -----------------------------
PRIMARY = "#004E7B"
SECONDARY = "#63296C"

st.set_page_config(
    page_title="Sistema de Asistencia — Hogar de Cristo Bahía Blanca",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = f"""
<style>
:root {{
  --hc-primary: {PRIMARY};
  --hc-secondary: {SECONDARY};
}}
/* Fondo oscuro (no blanco) */
.stApp {{
  background: radial-gradient(1200px 700px at 15% 10%, rgba(99,41,108,0.30), transparent 55%),
              radial-gradient(1200px 700px at 80% 25%, rgba(0,78,123,0.28), transparent 55%),
              linear-gradient(180deg, #0b0f16, #0a0d12);
  color: #e9eef6;
}}
/* Sidebar */
section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, rgba(0,78,123,0.22), rgba(99,41,108,0.18));
  border-right: 1px solid rgba(255,255,255,0.06);
}}
/* Cards */
.hc-card {{
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 14px 16px;
}}
.hc-kpi {{
  font-size: 36px;
  font-weight: 800;
  letter-spacing: -0.02em;
}}
.hc-label {{
  opacity: 0.85;
  font-size: 13px;
}}
.hc-pill {{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(0,78,123,0.25);
  border: 1px solid rgba(0,78,123,0.40);
}}
/* Botones */
.stButton > button {{
  border-radius: 999px !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
}}
/* Tabs */
button[data-baseweb="tab"] > div {{
  font-size: 15px !important;
}}
/* Dataframe */
[data-testid="stDataFrame"] {{
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  overflow: hidden;
}}
/* Alertas */
.hc-warn {{
  background: rgba(99,41,108,0.20);
  border: 1px solid rgba(99,41,108,0.35);
  padding: 10px 12px;
  border-radius: 12px;
}}
.hc-ok {{
  background: rgba(0,78,123,0.20);
  border: 1px solid rgba(0,78,123,0.35);
  padding: 10px 12px;
  border-radius: 12px;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# -----------------------------
# Centros / Coordinadores
# -----------------------------
CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

COORDINADORES = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellán"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

# Solo Casa Maranatha usa espacios internos
ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar (Primaria)",
    "Apoyo escolar (Secundaria)",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]

ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"

# -----------------------------
# Utilidades
# -----------------------------
def today_str() -> str:
    return date.today().isoformat()

def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")

def safe_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def clean_cell(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_centro(s: str) -> str:
    s = clean_cell(s)
    s_low = s.lower()
    if "belen" in s_low or "belén" in s_low:
        return "Calle Belén"
    if "nudo" in s_low:
        return "Nudo a Nudo"
    if "maran" in s_low:
        return "Casa Maranatha"
    # si ya coincide exacto
    if s in CENTROS:
        return s
    return s

def normalize_frecuencia(s: str) -> str:
    s = clean_cell(s)
    s_low = s.lower()
    if "diar" in s_low:
        return "Diaria"
    if "seman" in s_low:
        return "Semanal"
    if "mens" in s_low:
        return "Mensual"
    if "no as" in s_low or "noas" in s_low:
        return "No asiste"
    # permitir vacío u otros
    return s if s else ""

def enforce_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]

def data_dir() -> Path:
    d = Path("data")
    d.mkdir(exist_ok=True)
    return d

# -----------------------------
# Backend: Local CSV
# -----------------------------
@dataclass
class LocalBackend:
    asistencia_path: Path
    personas_path: Path

    def read_asistencia(self) -> pd.DataFrame:
        if not self.asistencia_path.exists():
            return pd.DataFrame(columns=[
                "fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"
            ])
        try:
            df = pd.read_csv(self.asistencia_path, dtype=str, encoding="utf-8")
        except Exception:
            df = pd.read_csv(self.asistencia_path, dtype=str, encoding="latin-1")
        df = enforce_columns(df, ["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
        df["presentes"] = df["presentes"].map(lambda x: safe_int(x, 0))
        df["anio"] = df["anio"].map(lambda x: safe_int(x, 0))
        return df

    def append_asistencia(self, row: Dict) -> None:
        df = self.read_asistencia()
        df2 = pd.DataFrame([row])
        df = pd.concat([df, df2], ignore_index=True)
        df = enforce_columns(df, ["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
        df.to_csv(self.asistencia_path, index=False, encoding="utf-8")

    def read_personas(self) -> pd.DataFrame:
        if not self.personas_path.exists():
            return pd.DataFrame(columns=["nombre","frecuencia","centro"])
        try:
            df = pd.read_csv(self.personas_path, dtype=str, encoding="utf-8")
        except Exception:
            df = pd.read_csv(self.personas_path, dtype=str, encoding="latin-1")
        df = normalize_personas_df(df)
        return df

    def write_personas(self, df: pd.DataFrame) -> None:
        df = normalize_personas_df(df)
        df.to_csv(self.personas_path, index=False, encoding="utf-8")

# -----------------------------
# Backend: Google Sheets (opcional)
# -----------------------------
@dataclass
class SheetsBackend:
    spreadsheet_id: str

    def _ok(self) -> bool:
        return bool(self.spreadsheet_id)

    def _get_client(self):
        import gspread
        from google.oauth2.service_account import Credentials

        sa = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa, scopes=scopes)
        return gspread.authorize(creds)

    def _open(self):
        gc = self._get_client()
        return gc.open_by_key(self.spreadsheet_id)

    def ensure_tabs(self):
        sh = self._open()
        titles = [ws.title for ws in sh.worksheets()]
        if ASISTENCIA_TAB not in titles:
            sh.add_worksheet(title=ASISTENCIA_TAB, rows=1000, cols=20)
            ws = sh.worksheet(ASISTENCIA_TAB)
            ws.append_row(["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
        if PERSONAS_TAB not in titles:
            sh.add_worksheet(title=PERSONAS_TAB, rows=2000, cols=10)
            ws = sh.worksheet(PERSONAS_TAB)
            ws.append_row(["nombre","frecuencia","centro"])

    def read_tab(self, tab: str) -> pd.DataFrame:
        sh = self._open()
        ws = sh.worksheet(tab)
        values = ws.get_all_values()
        if not values:
            return pd.DataFrame()
        header = [clean_cell(h) for h in values[0]]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=header)
        return df

    def append_row(self, tab: str, row: List):
        sh = self._open()
        ws = sh.worksheet(tab)
        ws.append_row(row, value_input_option="USER_ENTERED")

    def write_df(self, tab: str, df: pd.DataFrame):
        sh = self._open()
        ws = sh.worksheet(tab)
        ws.clear()
        ws.update([df.columns.tolist()] + df.astype(str).fillna("").values.tolist())

# -----------------------------
# Selección backend
# -----------------------------
@st.cache_resource
def get_backend():
    # Si hay secrets de Sheets, usamos Sheets. Si no, local.
    sid = ""
    try:
        sid = st.secrets.get("sheets", {}).get("spreadsheet_id", "")
    except Exception:
        sid = ""

    if sid:
        try:
            b = SheetsBackend(spreadsheet_id=sid)
            b.ensure_tabs()
            return b
        except Exception as e:
            # fallback
            st.sidebar.markdown(
                f"<div class='hc-warn'>Google Sheets no disponible. Uso CSV local.<br><small>{type(e).__name__}: {e}</small></div>",
                unsafe_allow_html=True
            )

    d = data_dir()
    return LocalBackend(
        asistencia_path=d / "asistencia.csv",
        personas_path=d / "personas_app.csv",
    )

backend = get_backend()

# -----------------------------
# Personas CSV externo (IMPORT)
# -----------------------------
def find_csv_path() -> Optional[str]:
    candidates = [
        "datapersonas.csv",
        "personas.csv",
        str(data_dir() / "datapersonas.csv"),
        str(data_dir() / "personas.csv"),
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None

def normalize_personas_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["nombre","frecuencia","centro"])
    # mapear columnas posibles
    cols = {c.lower().strip(): c for c in df.columns}
    # posibles nombres de columna
    nombre_col = cols.get("nombre") or cols.get("persona") or cols.get("personas") or cols.get("name")
    frec_col = cols.get("frecuencia") or cols.get("freq") or cols.get("asistencia") or cols.get("frec")
    centro_col = cols.get("centro") or cols.get("centro ") or cols.get("cb")

    out = pd.DataFrame()
    out["nombre"] = df[nombre_col] if nombre_col else ""
    out["frecuencia"] = df[frec_col] if frec_col else ""
    out["centro"] = df[centro_col] if centro_col else ""

    out["nombre"] = out["nombre"].map(clean_cell)
    out["frecuencia"] = out["frecuencia"].map(normalize_frecuencia)
    out["centro"] = out["centro"].map(normalize_centro)

    out = out[out["nombre"] != ""]
    out = out.drop_duplicates(subset=["nombre","centro"], keep="first")
    out = out.reset_index(drop=True)
    return out

def load_personas_csv_robusto() -> Tuple[pd.DataFrame, Dict]:
    """
    Lee datapersonas.csv/personas.csv incluso si:
    - está separado por tabs
    - está separado por comas PERO el nombre tiene comas sin comillas (ej: 'Apellido, Nombre')
      En ese caso, tomamos los ÚLTIMOS 2 campos como frecuencia y centro, y todo lo anterior como nombre.
    """
    path = find_csv_path()
    meta = {"path": path, "lines": 0, "parsed": 0, "skipped": 0, "mode": ""}

    if not path:
        return pd.DataFrame(columns=["nombre","frecuencia","centro"]), meta

    raw_lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    raw_lines = [ln.strip() for ln in raw_lines if ln.strip()]
    meta["lines"] = len(raw_lines)
    if not raw_lines:
        return pd.DataFrame(columns=["nombre","frecuencia","centro"]), meta

    # Si primera línea parece header, la saltamos
    first = raw_lines[0].lower()
    data_lines = raw_lines[1:] if ("nombre" in first or "persona" in first or "frecuencia" in first) else raw_lines

    rows = []
    for ln in data_lines:
        # TAB
        if "\t" in ln and ln.count("\t") >= 2:
            meta["mode"] = "tab"
            parts = [p.strip() for p in ln.split("\t")]
            nombre = parts[0] if len(parts) > 0 else ""
            frecuencia = parts[1] if len(parts) > 1 else ""
            centro = parts[2] if len(parts) > 2 else ""
            if nombre:
                rows.append([nombre, frecuencia, centro])
                meta["parsed"] += 1
            else:
                meta["skipped"] += 1
            continue

        # COMA (nombre puede tener comas)
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) >= 3:
            meta["mode"] = "comma_last2"
            centro = parts[-1]
            frecuencia = parts[-2]
            nombre = ",".join(parts[:-2]).strip()
            if nombre:
                rows.append([nombre, frecuencia, centro])
                meta["parsed"] += 1
            else:
                meta["skipped"] += 1
        else:
            meta["skipped"] += 1

    df = pd.DataFrame(rows, columns=["nombre","frecuencia","centro"])
    df = normalize_personas_df(df)
    return df, meta

def import_personas_from_csv(force: bool = False) -> Dict:
    """
    Importa CSV externo hacia el backend (Sheets o local).
    - Si force=False: solo importa si personas está vacío
    - Si force=True: reemplaza/mergea sin duplicados
    """
    df_csv, meta = load_personas_csv_robusto()
    if df_csv.empty:
        meta["imported"] = 0
        meta["reason"] = "CSV vacío o no encontrado"
        return meta

    # leer actuales
    df_now = read_personas()
    if (not force) and (df_now is not None) and (not df_now.empty):
        meta["imported"] = 0
        meta["reason"] = "Ya hay personas cargadas (no force)"
        return meta

    if df_now is None or df_now.empty:
        df_final = df_csv
    else:
        df_final = pd.concat([df_now, df_csv], ignore_index=True)
        df_final = normalize_personas_df(df_final)

    write_personas(df_final)
    meta["imported"] = len(df_csv)
    meta["final_total"] = len(df_final)
    meta["reason"] = "OK"
    return meta

# -----------------------------
# Lectura / escritura por backend (Asistencia + Personas)
# -----------------------------
def read_asistencia() -> pd.DataFrame:
    if isinstance(backend, SheetsBackend):
        df = backend.read_tab(ASISTENCIA_TAB)
        df = enforce_columns(df, ["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
        # cast seguros
        df["presentes"] = df["presentes"].map(lambda x: safe_int(x, 0))
        df["anio"] = df["anio"].map(lambda x: safe_int(x, 0))
        df["centro"] = df["centro"].map(normalize_centro)
        df["coordinador"] = df["coordinador"].map(clean_cell)
        df["espacio"] = df["espacio"].map(clean_cell)
        df["modo"] = df["modo"].map(clean_cell)
        df["notas"] = df["notas"].map(clean_cell)
        df["fecha"] = df["fecha"].map(clean_cell)
        df["timestamp"] = df["timestamp"].map(clean_cell)
        return df
    else:
        return backend.read_asistencia()

def append_asistencia(row: Dict) -> None:
    if isinstance(backend, SheetsBackend):
        backend.append_row(ASISTENCIA_TAB, [
            row.get("fecha",""),
            row.get("anio",""),
            row.get("centro",""),
            row.get("espacio",""),
            row.get("presentes",""),
            row.get("coordinador",""),
            row.get("modo",""),
            row.get("notas",""),
            row.get("timestamp",""),
        ])
    else:
        backend.append_asistencia(row)

def read_personas() -> pd.DataFrame:
    if isinstance(backend, SheetsBackend):
        df = backend.read_tab(PERSONAS_TAB)
        df = normalize_personas_df(df)
        return df
    else:
        return backend.read_personas()

def write_personas(df: pd.DataFrame) -> None:
    df = normalize_personas_df(df)
    if isinstance(backend, SheetsBackend):
        backend.write_df(PERSONAS_TAB, df)
    else:
        backend.write_personas(df)

# -----------------------------
# Login simple (opcional)
# -----------------------------
def get_users_config() -> Dict:
    """
    Podés definir usuarios en secrets.toml:
    [users]
    natasha = {password="1234", centro="Calle Belén"}
    camila  = {password="1234", centro="Nudo a Nudo"}
    """
    default = {
        "natasha": {"password": "1234", "centro": "Calle Belén"},
        "estefania": {"password": "1234", "centro": "Calle Belén"},
        "martin": {"password": "1234", "centro": "Calle Belén"},
        "camila": {"password": "1234", "centro": "Nudo a Nudo"},
        "julieta": {"password": "1234", "centro": "Nudo a Nudo"},
        "florencia": {"password": "1234", "centro": "Casa Maranatha"},
        "guillermina": {"password": "1234", "centro": "Casa Maranatha"},
        "admin": {"password": "admin", "centro": "Calle Belén"},
    }
    try:
        users = st.secrets.get("users", None)
        if users:
            # st.secrets puede devolverte dict ya armado
            return dict(users)
    except Exception:
        pass
    return default

USERS = get_users_config()

def do_login():
    st.sidebar.markdown("## Acceso")
    if st.session_state.get("logged_in"):
        st.sidebar.markdown(
            f"<div class='hc-ok'>Conectado como: <b>{st.session_state['username']}</b></div>",
            unsafe_allow_html=True
        )
        if st.sidebar.button("Salir"):
            st.session_state.clear()
            st.rerun()
        return

    u = st.sidebar.text_input("Usuario", key="login_user")
    p = st.sidebar.text_input("Contraseña", type="password", key="login_pass")
    if st.sidebar.button("Entrar"):
        if not u or not p:
            st.sidebar.error("Completá usuario y contraseña.")
            return
        u_low = u.strip().lower()
        if u_low in USERS and str(USERS[u_low].get("password","")) == str(p):
            st.session_state["logged_in"] = True
            st.session_state["username"] = u_low
            st.session_state["centro_asignado"] = normalize_centro(USERS[u_low].get("centro","Calle Belén"))
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos.")

do_login()

def require_login() -> bool:
    return bool(st.session_state.get("logged_in"))

# -----------------------------
# Sidebar: centro + coordinador (bloqueado por centro)
# -----------------------------
def sidebar_context() -> Tuple[str, str, int]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Centro / Coordinador")

    anio = st.sidebar.selectbox("Año", options=list(range(date.today().year - 2, date.today().year + 1))[::-1], index=0)

    if require_login():
        centro = st.session_state.get("centro_asignado","Calle Belén")
        st.sidebar.markdown(f"<div class='hc-pill'>Centro asignado: <b>{centro}</b></div>", unsafe_allow_html=True)
    else:
        centro = st.sidebar.selectbox("Centro", CENTROS, index=0)

    coords = COORDINADORES.get(centro, [])
    if require_login():
        # si el usuario coincide con coordinador, lo preseleccionamos
        u = st.session_state.get("username","")
        default_coord = None
        for c in coords:
            if c.strip().lower().replace(" ", "") in u.replace(" ", ""):
                default_coord = c
                break
        if default_coord and default_coord in coords:
            idx = coords.index(default_coord)
        else:
            idx = 0
        coordinador = st.sidebar.selectbox("¿Quién carga?", coords, index=idx)
    else:
        coordinador = st.sidebar.selectbox("¿Quién carga?", coords, index=0)

    st.sidebar.markdown("<div style='opacity:.7;margin-top:12px'>App interna — Hogar de Cristo Bahía Blanca</div>", unsafe_allow_html=True)
    return centro, coordinador, int(anio)

CENTRO_ACTUAL, COORD_ACTUAL, ANIO_ACTUAL = sidebar_context()

# -----------------------------
# Header
# -----------------------------
def header():
    cols = st.columns([0.18, 0.82], vertical_alignment="center")
    with cols[0]:
        # Si tenés logo: ponelo en "assets/logo.png" y descomentá
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown(f"<div class='hc-pill'>Hogar de Cristo</div>", unsafe_allow_html=True)

    with cols[1]:
        st.markdown("# Sistema de Asistencia — Hogar de Cristo Bahía Blanca")
        st.markdown(
            f"Estás trabajando sobre: **{CENTRO_ACTUAL}** — 👤 **{COORD_ACTUAL}**"
        )

header()

# -----------------------------
# KPIs (este centro / este año)
# -----------------------------
def kpis(df_asistencia: pd.DataFrame):
    df = df_asistencia.copy()
    if df.empty:
        hoy_total = 0
        ult7 = 0
        dias_sin = 7
    else:
        df = df[df["centro"] == CENTRO_ACTUAL]
        df = df[df["anio"] == ANIO_ACTUAL]
        hoy = today_str()
        # OJO: no caer si falta columna
        if "fecha" not in df.columns:
            df["fecha"] = ""
        if "presentes" not in df.columns:
            df["presentes"] = 0

        hoy_total = int(df.loc[df["fecha"] == hoy, "presentes"].sum()) if not df.empty else 0

        d7 = date.today() - timedelta(days=6)
        df7 = df.copy()
        # filtrar fechas parseables
        def to_date(x):
            try:
                return datetime.fromisoformat(str(x)).date()
            except Exception:
                return None
        df7["_d"] = df7["fecha"].map(to_date)
        df7 = df7[df7["_d"].notna()]
        df7 = df7[df7["_d"] >= d7]
        ult7 = int(df7["presentes"].sum()) if not df7.empty else 0

        # días sin cargar esta semana (lun-dom)
        start = date.today() - timedelta(days=date.today().weekday())
        days = [start + timedelta(days=i) for i in range(7)]
        fechas_cargadas = set(df["fecha"].astype(str).tolist())
        dias_sin = sum(1 for d in days if d.isoformat() not in fechas_cargadas)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='hc-card'><div class='hc-label'>Ingresos HOY</div><div class='hc-kpi'>{hoy_total}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='hc-card'><div class='hc-label'>Ingresos últimos 7 días</div><div class='hc-kpi'>{ult7}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='hc-card'><div class='hc-label'>Días sin cargar esta semana</div><div class='hc-kpi'>{dias_sin}</div></div>", unsafe_allow_html=True)

df_asistencia_all = read_asistencia()
kpis(df_asistencia_all)

# -----------------------------
# Tabs
# -----------------------------
tab_reg, tab_personas, tab_reportes, tab_global = st.tabs(
    ["🧾 Registrar asistencia", "👥 Personas", "📊 Reportes / Base de datos", "🌍 Global"]
)

# -----------------------------
# TAB: Registrar asistencia
# -----------------------------
with tab_reg:
    st.subheader("Registrar asistencia para este centro")

    left, right = st.columns([0.7, 0.3], vertical_alignment="top")

    with left:
        fecha = st.date_input("Fecha", value=date.today())
        fecha_s = fecha.isoformat()

        if CENTRO_ACTUAL == "Casa Maranatha":
            espacio = st.selectbox("Espacio (solo Maranatha)", ESPACIOS_MARANATHA)
            if espacio == "Otro":
                espacio = st.text_input("Especificá el espacio", value="")
        else:
            espacio = ""

        modo = st.selectbox("Tipo de día", ["Día habitual", "Evento especial", "Otro"])
        cerrado = st.checkbox("Hoy el centro estuvo cerrado / no abrió", value=False)
        presentes = st.number_input("Total presentes", min_value=0, value=0, step=1, disabled=cerrado)

        notas = st.text_area("Notas (opcional)", height=90)

        if st.button("✅ Guardar registro", use_container_width=True):
            row = {
                "fecha": fecha_s,
                "anio": int(fecha.year),
                "centro": CENTRO_ACTUAL,
                "espacio": clean_cell(espacio),
                "presentes": int(presentes) if not cerrado else 0,
                "coordinador": COORD_ACTUAL,
                "modo": "Cerrado" if cerrado else clean_cell(modo),
                "notas": clean_cell(notas),
                "timestamp": now_ts(),
            }
            append_asistencia(row)
            st.success("Listo. Registro guardado.")
            st.rerun()

    with right:
        st.markdown("<div class='hc-card'><b>Ayuda</b><br><small>"
                    "• En Maranatha podés cargar por espacio.<br>"
                    "• En los otros centros se carga total del día.<br>"
                    "• Si estás en Streamlit Cloud, sin Google Sheets los CSV pueden perderse al reiniciar.</small></div>",
                    unsafe_allow_html=True)

# -----------------------------
# TAB: Personas
# -----------------------------
with tab_personas:
    st.subheader("Personas de este centro")

    dfp = read_personas()
    dfp_centro = dfp[dfp["centro"] == CENTRO_ACTUAL].copy() if not dfp.empty else pd.DataFrame(columns=["nombre","frecuencia","centro"])

    top = st.columns([0.5, 0.5], vertical_alignment="center")
    with top[0]:
        st.markdown(f"<div class='hc-pill'>Personas visibles: <b>{len(dfp_centro)}</b></div>", unsafe_allow_html=True)
    with top[1]:
        q = st.text_input("Buscar (nombre)", value="")
        if q:
            dfp_centro = dfp_centro[dfp_centro["nombre"].str.contains(q, case=False, na=False)]

    # Import CSV (forzar)
    cA, cB = st.columns([0.35, 0.65], vertical_alignment="center")
    with cA:
        if st.button("📥 Importar CSV ahora (FORZAR)", use_container_width=True):
            meta = import_personas_from_csv(force=True)
            st.success(f"Import OK. CSV importadas: {meta.get('imported',0)} | Total final: {meta.get('final_total','?')}")
            st.rerun()
    with cB:
        p = find_csv_path()
        st.caption(f"Busca `datapersonas.csv` / `personas.csv` en raíz o en `data/`. Detectado: **{p or 'NO ENCONTRADO'}**")

    # Mostrar tabla
    st.dataframe(dfp_centro, use_container_width=True, height=420)

    st.markdown("### Agregar / editar (simple)")
    col1, col2, col3 = st.columns([0.55, 0.25, 0.2], vertical_alignment="center")
    with col1:
        nombre_new = st.text_input("Nombre (ej: Apellido, Nombre)", value="")
    with col2:
        frec_new = st.selectbox("Frecuencia", ["Diaria","Semanal","Mensual","No asiste",""], index=2)
    with col3:
        if st.button("➕ Guardar persona", use_container_width=True):
            if not nombre_new.strip():
                st.error("Falta el nombre.")
            else:
                # upsert por (nombre, centro)
                df_all = dfp.copy()
                if df_all.empty:
                    df_all = pd.DataFrame(columns=["nombre","frecuencia","centro"])
                n = clean_cell(nombre_new)
                f = normalize_frecuencia(frec_new)
                c = CENTRO_ACTUAL
                mask = (df_all["nombre"].astype(str) == n) & (df_all["centro"].astype(str) == c)
                if mask.any():
                    df_all.loc[mask, "frecuencia"] = f
                else:
                    df_all = pd.concat([df_all, pd.DataFrame([{"nombre": n, "frecuencia": f, "centro": c}])], ignore_index=True)
                df_all = normalize_personas_df(df_all)
                write_personas(df_all)
                st.success("Persona guardada.")
                st.rerun()

# -----------------------------
# TAB: Reportes / Base de datos
# -----------------------------
with tab_reportes:
    st.subheader("Reportes (este centro)")

    df = df_asistencia_all.copy()
    df = enforce_columns(df, ["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
    df = df[(df["centro"] == CENTRO_ACTUAL) & (df["anio"] == ANIO_ACTUAL)].copy()

    if df.empty:
        st.markdown("<div class='hc-warn'>Todavía no hay registros de asistencia para este centro (este año).</div>", unsafe_allow_html=True)
    else:
        # Tabla últimos registros
        st.markdown("#### Últimos registros (este centro / este año)")
        df_show = df.sort_values("fecha", ascending=False).head(30)
        st.dataframe(df_show, use_container_width=True, height=240)

        # Gráfico por día (suma)
        st.markdown("#### Asistencia por día (sumatoria)")
        df_day = df.copy()
        df_day["fecha"] = df_day["fecha"].astype(str)
        g = df_day.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
        g = g.tail(40)
        st.line_chart(g.set_index("fecha")["presentes"])

        # Por coordinador
        st.markdown("#### Por coordinador (suma)")
        gc = df.groupby("coordinador", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
        st.bar_chart(gc.set_index("coordinador")["presentes"])

        # Maranatha por espacio
        if CENTRO_ACTUAL == "Casa Maranatha":
            st.markdown("#### Maranatha por espacio (suma)")
            ge = df.groupby("espacio", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            st.bar_chart(ge.set_index("espacio")["presentes"])

        # Descargar CSV
        st.download_button(
            "⬇️ Descargar registros de este centro (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"asistencia_{CENTRO_ACTUAL.replace(' ','_')}_{ANIO_ACTUAL}.csv",
            mime="text/csv",
            use_container_width=True
        )

# -----------------------------
# TAB: Global
# -----------------------------
with tab_global:
    st.subheader("Tablero global (todos los centros)")

    dfg = df_asistencia_all.copy()
    dfg = enforce_columns(dfg, ["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
    dfg = dfg[dfg["anio"] == ANIO_ACTUAL].copy()

    if dfg.empty:
        st.markdown("<div class='hc-warn'>No hay datos globales para este año todavía.</div>", unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([0.55, 0.45], vertical_alignment="top")

        with c1:
            st.markdown("#### Total por centro (año)")
            g1 = dfg.groupby("centro", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            st.bar_chart(g1.set_index("centro")["presentes"])

            st.markdown("#### Evolución general por día (sumatoria)")
            g2 = dfg.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
            g2 = g2.tail(60)
            st.line_chart(g2.set_index("fecha")["presentes"])

        with c2:
            st.markdown("#### Últimos registros (global)")
            st.dataframe(dfg.sort_values("timestamp", ascending=False).head(25), use_container_width=True, height=420)

# -----------------------------
# Auto-import inicial si personas está vacío (una vez)
# -----------------------------
if "boot_import_done" not in st.session_state:
    st.session_state["boot_import_done"] = True
    try:
        dfp_now = read_personas()
        if dfp_now.empty:
            meta = import_personas_from_csv(force=True)
            # no rerun agresivo, solo info
            st.toast(f"Import inicial personas: {meta.get('imported',0)} filas", icon="✅")
    except Exception:
        pass
