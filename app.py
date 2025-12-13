# app.py — Sistema de Asistencia (Hogar de Cristo Bahía Blanca)
# ✅ Google Sheets como base (persistente)
# ✅ Import robusto de datapersonas.csv (coma / tab / ; / 2+ espacios / comillas)
# ✅ Reglas anti-duplicado:
#    - Calle Belén y Nudo a Nudo: 1 carga por día por centro
#    - Casa Maranatha: 1 carga por día por espacio
# ✅ Permisos:
#    - En centros no Maranatha: cada coordinador solo carga su centro
#    - En Maranatha: cada coordinador solo puede cargar los espacios habilitados
# ✅ Tablero: métricas HOY / semana / mes por centro + GLOBAL (todos los centros)
# ✅ Separación por año
#
# requirements.txt:
# streamlit
# pandas
# gspread
# google-auth

streamlit
pandas
gspread==6.1.2
google-auth==2.33.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
httplib2==0.22.0
requests==2.32.3


# =========================
# Config visual
# =========================
APP_TITLE = "Sistema de Asistencia — Hogar de Cristo Bahía Blanca"
PRIMARY = "#004E7B"
ACCENT = "#63296C"

st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="wide")


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


def kpi(label: str, value: str):
    st.markdown(
        f"""
        <div class="hc-card">
          <div style="opacity:.78;font-size:12px;margin-bottom:6px;">{label}</div>
          <div style="font-size:34px;font-weight:800;letter-spacing:-0.5px;line-height:1;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# =========================
# Dominio (centros / permisos)
# =========================
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

# Coordinadores por centro
COORDINADORES_POR_CENTRO = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellan"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

# Permisos de Maranatha por espacio (ajustalo a tu realidad)
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


# =========================
# Sheets
# =========================
ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"

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


def clean_cell(x) -> str:
    if x is None:
        return ""
    return str(x).replace("\u00a0", " ").strip()


def normalize_centro(s: str) -> str:
    s = clean_cell(s)
    s_low = s.lower()
    # variantes típicas
    if "belen" in s_low or "belén" in s_low:
        return "Calle Belén"
    if "nudo" in s_low:
        return "Nudo a Nudo"
    if "maran" in s_low:
        return "Casa Maranatha"
    # match exacto
    for c in CENTROS:
        if c.lower() == s_low:
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
    if s in FRECUENCIAS_CANON:
        return s
    return s


def safe_int(x, default=0) -> int:
    try:
        if x is None:
            return default
        return int(float(str(x).replace(",", ".")))
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Falta [gcp_service_account] en .streamlit/secrets.toml")
        st.stop()

    sa = dict(st.secrets["gcp_service_account"])

    # private_key: aceptar tanto con \\n como con saltos reales
    pk = sa.get("private_key", "")
    if isinstance(pk, str) and "\\n" in pk:
        sa["private_key"] = pk.replace("\\n", "\n")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds), sa.get("client_email", "")


def get_spreadsheet():
    if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
        st.error("Falta [sheets] spreadsheet_id en .streamlit/secrets.toml")
        st.stop()
    sid = st.secrets["sheets"]["spreadsheet_id"]
    gc, _ = get_gspread_client()
    return gc.open_by_key(sid)


def ensure_tab(title: str, headers: List[str]):
    sh = get_spreadsheet()
    names = [w.title for w in sh.worksheets()]
    if title not in names:
        sh.add_worksheet(title=title, rows=2000, cols=30)
    ws = sh.worksheet(title)
    values = ws.get_all_values()
    if not values:
        ws.append_row(headers, value_input_option="RAW")
    else:
        # si header vacío o mal
        first = values[0]
        if len(first) < len(headers) or any(h.strip() == "" for h in first):
            ws.update("A1", [headers])


def read_table(tab: str) -> pd.DataFrame:
    sh = get_spreadsheet()
    ws = sh.worksheet(tab)
    vals = ws.get_all_values()
    if not vals:
        return pd.DataFrame()
    header = [clean_cell(h) for h in vals[0]]
    rows = vals[1:]
    if not header:
        return pd.DataFrame()
    # normalizar largo
    fixed = []
    for r in rows:
        r = list(r)
        if len(r) < len(header):
            r += [""] * (len(header) - len(r))
        fixed.append(r[: len(header)])
    df = pd.DataFrame(fixed, columns=header)
    # limpiar
    for c in df.columns:
        df[c] = df[c].map(clean_cell)
    # bajar a snake-ish
    df.columns = [re.sub(r"\s+", "_", c.strip().lower()) for c in df.columns]
    return df


def append_row(tab: str, row: List[Any]):
    sh = get_spreadsheet()
    ws = sh.worksheet(tab)
    ws.append_row([str(x) for x in row], value_input_option="USER_ENTERED")


def overwrite_df(tab: str, df: pd.DataFrame):
    sh = get_spreadsheet()
    ws = sh.worksheet(tab)
    ws.clear()
    ws.update("A1", [df.columns.tolist()] + df.astype(str).fillna("").values.tolist())


# Inicializar tabs
ensure_tab(PERSONAS_TAB, PERSONAS_HEADERS)
ensure_tab(ASISTENCIA_TAB, ASISTENCIA_HEADERS)


# =========================
# Login simple (opcional)
# =========================
# Podés reemplazar esto por users en secrets si querés:
# [users]
# natasha = {password="...", centro="Calle Belén", nombre="Natasha Carrari"}


def get_users():
    try:
        if "users" in st.secrets:
            return dict(st.secrets["users"])
    except Exception:
        pass
    return USERS_DEFAULT


def login():
    users = get_users()
    st.sidebar.markdown("## Acceso")

    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
        st.session_state.auth_name = ""
        st.session_state.auth_centro = None

    if st.session_state.auth_user:
        st.sidebar.success(f"Conectado: {st.session_state.auth_name}")
        if st.sidebar.button("Salir"):
            st.session_state.auth_user = None
            st.session_state.auth_name = ""
            st.session_state.auth_centro = None
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
        if clean_cell(info.get("password", "")) != clean_cell(p):
            st.sidebar.error("Contraseña incorrecta.")
            return
        st.session_state.auth_user = key
        st.session_state.auth_name = clean_cell(info.get("nombre", key))
        st.session_state.auth_centro = normalize_centro(info.get("centro", "")) if info.get("centro") else None
        st.rerun()


login()
if not st.session_state.auth_user:
    st.stop()


# =========================
# CSV Personas (robusto)
# =========================
def find_csv_path() -> Optional[str]:
    candidates = [
        "datapersonas.csv",
        "personas.csv",
        "data/datapersonas.csv",
        "data/personas.csv",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def _parse_line_persona(line: str):
    """
    Devuelve (nombre, frecuencia, centro) o None.
    Soporta:
      - TAB
      - ;
      - CSV con comillas (csv.reader)
      - "separado por 2+ espacios" (copiado de planilla)
      - nombre con comas sin comillas: toma últimas 2 columnas como frecuencia/centro
    """
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

    # CSV real (con comillas)
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

    # 2+ espacios
    parts = [p.strip() for p in re.split(r"\s{2,}", ln) if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]

    return None


def normalize_personas_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["nombre", "frecuencia", "centro"])

    # normalizar columnas
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # aliases
    if "personas" in df.columns and "nombre" not in df.columns:
        df.rename(columns={"personas": "nombre"}, inplace=True)
    if "persona" in df.columns and "nombre" not in df.columns:
        df.rename(columns={"persona": "nombre"}, inplace=True)

    for col in ["nombre", "frecuencia", "centro"]:
        if col not in df.columns:
            df[col] = ""

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
        return pd.DataFrame(columns=["nombre", "frecuencia", "centro"]), meta

    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    lines = [ln for ln in lines if ln.strip()]
    meta["lines"] = len(lines)
    if not lines:
        return pd.DataFrame(columns=["nombre", "frecuencia", "centro"]), meta

    # header?
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

    df = pd.DataFrame(rows, columns=["nombre", "frecuencia", "centro"])
    df = normalize_personas_df(df)
    return df, meta


def seed_personas_from_csv_if_needed(force: bool = False) -> Dict[str, Any]:
    df_sheet = read_table(PERSONAS_TAB)
    df_sheet = normalize_personas_df(df_sheet)

    df_csv, meta = load_personas_csv_robusto()
    if df_csv.empty:
        meta["imported"] = 0
        meta["final_total"] = len(df_sheet)
        meta["reason"] = "CSV vacío o no encontrado"
        return meta

    if df_sheet.empty or force:
        df_final = df_csv if df_sheet.empty else normalize_personas_df(pd.concat([df_sheet, df_csv], ignore_index=True))
        overwrite_df(PERSONAS_TAB, df_final)
        meta["imported"] = len(df_csv)
        meta["final_total"] = len(df_final)
        meta["reason"] = "OK"
        return meta

    meta["imported"] = 0
    meta["final_total"] = len(df_sheet)
    meta["reason"] = "Ya había datos en Sheets (usá FORZAR para reimportar)"
    return meta


# =========================
# Reglas de permisos y duplicados
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

    # Maranatha por espacio
    if not espacio:
        return False, "En Casa Maranatha tenés que elegir un espacio."
    allowed = MARANATHA_PERMISOS_POR_ESPACIO.get(espacio, [])
    if coordinador not in allowed:
        return False, f"{coordinador} no puede cargar el espacio: {espacio}."
    return True, ""


def is_duplicate(df_asistencia: pd.DataFrame, centro: str, fecha_str: str, espacio: str) -> bool:
    if df_asistencia is None or df_asistencia.empty:
        return False

    df = df_asistencia.copy()
    df["fecha"] = df.get("fecha", "").astype(str).str.slice(0, 10)
    df["centro"] = df.get("centro", "").astype(str).map(normalize_centro)
    df["espacio"] = df.get("espacio", "").astype(str).map(clean_cell)

    centro = normalize_centro(centro)
    espacio = clean_cell(espacio)

    if centro != "Casa Maranatha":
        # 1 carga por día por centro
        return ((df["centro"] == centro) & (df["fecha"] == fecha_str)).any()

    # 1 carga por día por espacio
    return ((df["centro"] == centro) & (df["fecha"] == fecha_str) & (df["espacio"] == espacio)).any()


# =========================
# Métricas y agregaciones
# =========================
def parse_asistencia(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=ASISTENCIA_HEADERS)

    df = df.copy()
    # asegurar columnas snake
    df.columns = [c.strip().lower() for c in df.columns]
    for c in [c.lower() for c in ASISTENCIA_HEADERS]:
        if c not in df.columns:
            df[c] = ""

    df["centro"] = df["centro"].map(normalize_centro)
    df["espacio"] = df["espacio"].map(clean_cell)
    df["coordinador"] = df["coordinador"].map(clean_cell)
    df["presentes"] = df["presentes"].map(lambda x: safe_int(x, 0))
    df["anio"] = df["anio"].map(lambda x: safe_int(x, 0))
    df["fecha"] = df["fecha"].map(lambda x: clean_cell(x)[:10])
    return df[[c.lower() for c in ASISTENCIA_HEADERS]]


def compute_metrics(df: pd.DataFrame, year: int, centro: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna: hoy, semana, mes, df_diario, df_por_centro (si centro=None), df_por_coordinador, df_por_espacio
    """
    if df is None or df.empty:
        return {
            "hoy": 0,
            "semana": 0,
            "mes": 0,
            "df_diario": pd.DataFrame(columns=["fecha", "presentes"]),
            "df_por_centro": pd.DataFrame(columns=["centro", "total_anual"]),
            "df_por_coordinador": pd.DataFrame(columns=["coordinador", "total"]),
            "df_por_espacio": pd.DataFrame(columns=["espacio", "total"]),
        }

    d = df.copy()
    d = d[d["anio"] == year].copy()
    if centro:
        d = d[d["centro"] == centro].copy()

    if d.empty:
        return {
            "hoy": 0,
            "semana": 0,
            "mes": 0,
            "df_diario": pd.DataFrame(columns=["fecha", "presentes"]),
            "df_por_centro": pd.DataFrame(columns=["centro", "total_anual"]),
            "df_por_coordinador": pd.DataFrame(columns=["coordinador", "total"]),
            "df_por_espacio": pd.DataFrame(columns=["espacio", "total"]),
        }

    # fechas
    d["_fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    d = d.dropna(subset=["_fecha_dt"]).copy()

    today = pd.Timestamp(date.today())
    start_week = today - pd.Timedelta(days=today.weekday())  # lunes
    start_month = today.replace(day=1)

    hoy = int(d[d["_fecha_dt"].dt.date == today.date()]["presentes"].sum())
    semana = int(d[d["_fecha_dt"] >= start_week]["presentes"].sum())
    mes = int(d[d["_fecha_dt"] >= start_month]["presentes"].sum())

    df_diario = d.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")

    df_por_centro = pd.DataFrame(columns=["centro", "total_anual"])
    if centro is None:
        df_por_centro = (
            d.groupby("centro", as_index=False)["presentes"].sum()
            .rename(columns={"presentes": "total_anual"})
            .sort_values("total_anual", ascending=False)
        )

    df_por_coordinador = (
        d.groupby("coordinador", as_index=False)["presentes"].sum()
        .rename(columns={"presentes": "total"})
        .sort_values("total", ascending=False)
    )

    df_por_espacio = (
        d[d["centro"] == "Casa Maranatha"]
        .groupby("espacio", as_index=False)["presentes"].sum()
        .rename(columns={"presentes": "total"})
        .sort_values("total", ascending=False)
    )

    return {
        "hoy": hoy,
        "semana": semana,
        "mes": mes,
        "df_diario": df_diario,
        "df_por_centro": df_por_centro,
        "df_por_coordinador": df_por_coordinador,
        "df_por_espacio": df_por_espacio,
    }


# =========================
# Sidebar: contexto usuario
# =========================
st.sidebar.markdown("## Contexto")

# Año
current_year = date.today().year
year_options = list(range(current_year - 2, current_year + 1))[::-1]
YEAR = st.sidebar.selectbox("Año", year_options, index=0)

# Centro asignado por usuario (si existe)
user_assigned_center = st.session_state.get("auth_centro", None)
if user_assigned_center:
    CENTRO = user_assigned_center
    st.sidebar.markdown(f"<span class='hc-pill'>Centro asignado: <b>{CENTRO}</b></span>", unsafe_allow_html=True)
else:
    CENTRO = st.sidebar.selectbox("Centro", CENTROS, index=0)

# Espacio (solo Maranatha)
if CENTRO == "Casa Maranatha":
    ESPACIO = st.sidebar.selectbox("Espacio (Maranatha)", ESPACIOS_MARANATHA, index=0)
    if ESPACIO == "Otro":
        ESPACIO = st.sidebar.text_input("Especificar espacio", value="").strip()
else:
    ESPACIO = ""

# Coordinador (se restringe según centro/espacio)
if CENTRO == "Casa Maranatha":
    allowed_coords = MARANATHA_PERMISOS_POR_ESPACIO.get(ESPACIO, COORDINADORES_POR_CENTRO["Casa Maranatha"])
else:
    allowed_coords = COORDINADORES_POR_CENTRO.get(CENTRO, [])

COORDINADOR = st.sidebar.selectbox("¿Quién carga?", allowed_coords, index=0)

st.sidebar.markdown("---")

# Diagnóstico Sheet
with st.sidebar.expander("🔧 Diagnóstico Google", expanded=False):
    _, sa_email = get_gspread_client()
    sid = st.secrets["sheets"]["spreadsheet_id"]
    st.write("Service Account:", sa_email)
    st.write("Spreadsheet ID:", sid)
    st.write("Usuario:", st.session_state.get("auth_user"))


# =========================
# Header
# =========================
st.markdown(f"# {APP_TITLE}")
st.markdown(
    f"Trabajando sobre: **{CENTRO}**"
    + (f" / **{ESPACIO}**" if CENTRO == "Casa Maranatha" and ESPACIO else "")
    + f" — 👤 **{COORDINADOR}**  &nbsp;&nbsp; <span class='hc-pill'>Año: {YEAR}</span>",
    unsafe_allow_html=True,
)

# =========================
# Carga data (Sheets)
# =========================
df_personas = normalize_personas_df(read_table(PERSONAS_TAB))
df_asistencia = parse_asistencia(read_table(ASISTENCIA_TAB))


# =========================
# KPIs (Centro + Global)
# =========================
m_centro = compute_metrics(df_asistencia, YEAR, centro=CENTRO)
m_global = compute_metrics(df_asistencia, YEAR, centro=None)

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: kpi("HOY (Centro)", str(m_centro["hoy"]))
with k2: kpi("Semana (Centro)", str(m_centro["semana"]))
with k3: kpi("Mes (Centro)", str(m_centro["mes"]))
with k4: kpi("HOY (Global)", str(m_global["hoy"]))
with k5: kpi("Semana (Global)", str(m_global["semana"]))
with k6: kpi("Mes (Global)", str(m_global["mes"]))

st.divider()


# =========================
# Tabs
# =========================
t1, t2, t3, t4 = st.tabs(["🧾 Cargar asistencia", "👥 Personas", "📊 Reportes", "🌍 Global"])

# -------------------------
# TAB 1: Cargar asistencia
# -------------------------
with t1:
    st.subheader("Cargar asistencia (con control de duplicados y permisos)")

    colA, colB, colC = st.columns([1, 1, 2])
    with colA:
        fecha = st.date_input("Fecha", value=date.today())
    with colB:
        modo = st.selectbox("Tipo de día", ["Día habitual", "Evento especial", "Salida", "Centro cerrado"], index=0)
    with colC:
        notas = st.text_input("Notas (opcional)", value="")

    cerr = (modo == "Centro cerrado")
    presentes = st.number_input("Presentes", min_value=0, step=1, value=0, disabled=cerr)

    # Validación permisos (antes de guardar)
    ok_perm, msg_perm = can_user_load(CENTRO, COORDINADOR, ESPACIO)
    if not ok_perm:
        st.error(msg_perm)

    if st.button("✅ Guardar", use_container_width=True, disabled=not ok_perm):
        fecha_str = fecha.isoformat()
        esp = ESPACIO if CENTRO == "Casa Maranatha" else ""

        # Recargar asistencia para evitar race
        df_a_now = parse_asistencia(read_table(ASISTENCIA_TAB))

        if is_duplicate(df_a_now, CENTRO, fecha_str, esp):
            if CENTRO != "Casa Maranatha":
                st.warning(f"Ya se cargó asistencia para **{CENTRO}** en **{fecha_str}**. (1 carga por día)")
            else:
                st.warning(f"Ya se cargó **{CENTRO} / {esp}** en **{fecha_str}**. (1 carga por día por espacio)")
        else:
            row = [
                datetime.now().isoformat(timespec="seconds"),
                fecha_str,
                int(fecha_str[:4]),
                CENTRO,
                esp,
                int(presentes) if not cerr else 0,
                COORDINADOR,
                modo,
                clean_cell(notas),
                st.session_state.get("auth_user", ""),
            ]
            append_row(ASISTENCIA_TAB, row)
            st.success("Asistencia guardada ✅")
            st.rerun()

    st.markdown("### Últimos registros (este centro / este año)")
    df_c = df_asistencia[(df_asistencia["centro"] == CENTRO) & (df_asistencia["anio"] == YEAR)].copy()
    if df_c.empty:
        st.info("Todavía no hay registros.")
    else:
        st.dataframe(df_c.sort_values("fecha", ascending=False).head(30), use_container_width=True)


# -------------------------
# TAB 2: Personas
# -------------------------
with t2:
    st.subheader("Personas (por centro)")

    # Import robusto
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("📥 Importar datapersonas.csv (FORZAR)", use_container_width=True):
            meta = seed_personas_from_csv_if_needed(force=True)
            st.success(f"Importadas: {meta.get('imported',0)} | Total final: {meta.get('final_total','?')}")
            st.write(meta)
            st.rerun()
    with c2:
        p = find_csv_path()
        st.caption(f"CSV detectado: **{p or 'NO'}** (nombre esperado: datapersonas.csv)")

    # Mostrar personas del centro actual
    df_p = df_personas[df_personas["centro"] == CENTRO].copy()
    st.markdown(f"<span class='hc-pill'>Personas visibles: <b>{len(df_p)}</b></span>", unsafe_allow_html=True)

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
            if df_all.empty:
                df_all = pd.DataFrame(columns=["nombre", "frecuencia", "centro"])
            df_all = pd.concat(
                [df_all, pd.DataFrame([{"nombre": clean_cell(nombre_new), "frecuencia": frec_new, "centro": CENTRO}])],
                ignore_index=True,
            )
            df_all = normalize_personas_df(df_all)
            overwrite_df(PERSONAS_TAB, df_all)
            st.success("Persona agregada ✅")
            st.rerun()


# -------------------------
# TAB 3: Reportes (Centro + detalles)
# -------------------------
with t3:
    st.subheader("Reportes del centro (día / semana / mes + detalle)")

    df_c = df_asistencia[(df_asistencia["centro"] == CENTRO) & (df_asistencia["anio"] == YEAR)].copy()
    if df_c.empty:
        st.info("No hay datos para este centro en este año.")
    else:
        # Diario
        st.markdown("### Asistencia por día (suma)")
        g = df_c.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
        st.line_chart(g.set_index("fecha")["presentes"])

        # Coordinador
        st.markdown("### Por coordinador (suma)")
        gc = df_c.groupby("coordinador", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
        st.bar_chart(gc.set_index("coordinador")["presentes"])

        # Maranatha por espacio
        if CENTRO == "Casa Maranatha":
            st.markdown("### Por espacio (Maranatha)")
            ge = df_c.groupby("espacio", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            st.bar_chart(ge.set_index("espacio")["presentes"])

        st.markdown("### Base de datos (registros)")
        st.dataframe(df_c.sort_values("fecha", ascending=False), use_container_width=True)

        st.download_button(
            "⬇️ Descargar CSV (este centro / este año)",
            data=df_c.to_csv(index=False).encode("utf-8"),
            file_name=f"asistencia_{CENTRO.replace(' ','_')}_{YEAR}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# -------------------------
# TAB 4: Global (todos los centros)
# -------------------------
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
            gd = gd.tail(90)
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

