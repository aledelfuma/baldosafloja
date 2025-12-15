# app.py
import re
import csv
import io
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st

# =========================
# Config / Estilo
# =========================
APP_TITLE = "Sistema de Asistencia — Hogar de Cristo Bahía Blanca"

COLOR_A = "#004E7B"  # azul
COLOR_B = "#63296C"  # violeta

CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]
MARANATHA_ESPACIOS = [
    "Taller de costura",
    "Apoyo escolar (Primaria)",
    "Apoyo escolar (Secundaria)",
    "FinEs",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]
MODO_DIA = ["Día habitual", "Día especial", "Feriado", "Cerrado / no abrió"]

ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"

DEFAULT_HEADERS_ASIST = [
    "timestamp", "fecha", "anio", "centro", "espacio", "presentes",
    "coordinador", "modo", "notas", "usuario", "cargado_por", "accion"
]
DEFAULT_HEADERS_PERSONAS = ["nombre", "frecuencia", "centro"]


# =========================
# Helpers UI
# =========================
def inject_css():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: radial-gradient(circle at 20% 0%, rgba(99,41,108,0.25), transparent 40%),
                        radial-gradient(circle at 90% 20%, rgba(0,78,123,0.25), transparent 40%),
                        #0b0f16 !important;
            color: #e9eef6;
        }}
        h1, h2, h3, h4 {{ color: #ffffff; }}
        .hc-badge {{
            display:inline-block; padding:6px 10px; border-radius:999px;
            background: rgba(99,41,108,0.25); border: 1px solid rgba(99,41,108,0.45);
            color: #fff; font-weight: 600; font-size: 12px;
        }}
        .hc-card {{
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.04);
            padding: 14px 16px;
        }}
        .hc-kpi {{
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.04);
            padding: 16px;
        }}
        .hc-kpi-title {{ font-size: 13px; opacity: 0.85; }}
        .hc-kpi-value {{ font-size: 34px; font-weight: 800; margin-top: 4px; }}
        .stButton>button {{
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.12);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_date_safe(x):
    """Devuelve date o None."""
    if x is None:
        return None
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    s = str(x).strip()
    if not s:
        return None
    # acepta YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    # a veces viene "2025-12-12 19:40:00"
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def parse_int_safe(x):
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == "":
            return None
        return int(float(s))
    except Exception:
        return None


def normalize_colname(c: str) -> str:
    c = str(c or "").strip().lower()
    c = c.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    c = c.replace("ñ", "n")
    c = re.sub(r"\s+", "_", c)
    return c


# =========================
# Google Sheets (gspread)
# =========================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    if "gcp_service_account" not in st.secrets:
        st.error("Falta [gcp_service_account] en secrets.")
        st.stop()

    sa = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)


def get_spreadsheet_id():
    if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
        st.error("Falta [sheets].spreadsheet_id en secrets.")
        st.stop()
    return st.secrets["sheets"]["spreadsheet_id"]


@st.cache_resource(show_spinner=False)
def open_spreadsheet():
    gc = get_gspread_client()
    sid = get_spreadsheet_id()
    return gc.open_by_key(sid)


def ensure_worksheet(title: str, headers: list[str]):
    sh = open_spreadsheet()
    try:
        ws = sh.worksheet(title)
    except Exception:
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(12, len(headers)))
        ws.append_row(headers)
        return ws

    # Si está vacía, agrega headers
    values = ws.get_all_values()
    if not values:
        ws.append_row(headers)
        return ws

    # Si la primera fila no tiene headers razonables, fuerza headers arriba
    first = [normalize_colname(x) for x in values[0]]
    want = [normalize_colname(x) for x in headers]
    if len(set(first).intersection(set(want))) < max(2, len(want)//3):
        ws.insert_row(headers, index=1)
    return ws


def ws_asistencia():
    return ensure_worksheet(ASISTENCIA_TAB, DEFAULT_HEADERS_ASIST)


def ws_personas():
    return ensure_worksheet(PERSONAS_TAB, DEFAULT_HEADERS_PERSONAS)


# =========================
# Lectura/Normalización de tablas
# =========================
def sheet_to_df(ws) -> pd.DataFrame:
    raw = ws.get_all_values()
    if not raw or len(raw) < 2:
        return pd.DataFrame()

    headers = [normalize_colname(h) for h in raw[0]]
    rows = raw[1:]

    # limpia filas totalmente vacías
    rows = [r for r in rows if any(str(x).strip() for x in r)]

    # normaliza largo
    maxlen = max(len(headers), max((len(r) for r in rows), default=0))
    headers = (headers + [f"col_{i}" for i in range(len(headers), maxlen)])[:maxlen]
    rows = [(r + [""] * (maxlen - len(r)))[:maxlen] for r in rows]

    df = pd.DataFrame(rows, columns=headers)
    return df


def normalize_asistencia_df(df: pd.DataFrame):
    """
    Repara:
    - columnas mal nombradas
    - filas corridas (como tu captura)
    - tipos (fecha/anio/presentes)
    Devuelve df_normalizado, repaired_count
    """
    if df.empty:
        return df, 0

    # Mapeo de posibles nombres a estándar
    rename_map = {
        "ano": "anio",
        "año": "anio",
        "centro_barrial": "centro",
        "coordinador_a": "coordinador",
        "coordinadora": "coordinador",
        "presentes_total": "presentes",
        "cantidad": "presentes",
        "observaciones": "notas",
        "usuario": "usuario",
    }
    cols = {c: rename_map.get(c, c) for c in df.columns}
    df = df.rename(columns=cols)

    # asegura columnas
    for c in DEFAULT_HEADERS_ASIST:
        if c not in df.columns:
            df[c] = ""

    repaired = 0

    # Detectar filas corridas:
    # Heurística: si "anio" no es número y "fecha" es número (2025) y "centro" no está en CENTROS pero "anio" sí,
    # corrige desplazando.
    def fix_row(row):
        nonlocal repaired
        ts = str(row.get("timestamp", "")).strip()
        fecha = str(row.get("fecha", "")).strip()
        anio = str(row.get("anio", "")).strip()
        centro = str(row.get("centro", "")).strip()
        espacio = str(row.get("espacio", "")).strip()
        presentes = str(row.get("presentes", "")).strip()
        coord = str(row.get("coordinador", "")).strip()
        modo = str(row.get("modo", "")).strip()
        notas = str(row.get("notas", "")).strip()

        # Caso típico tuyo: fecha=2025, anio=Calle Belén, centro=General, espacio=35, presentes=Natasha...
        anio_num = parse_int_safe(anio)
        fecha_date = parse_date_safe(fecha)
        centro_ok = centro in CENTROS
        anio_is_centro = anio in CENTROS
        presentes_num = parse_int_safe(presentes)

        looks_shifted = (
            (anio_num is None) and (parse_int_safe(fecha) is not None) and (not centro_ok) and anio_is_centro
        ) or (
            (presentes_num is None) and (coord == "" and presentes != "") and (presentes in ["Natasha Carrari", "Martín Pérez Santellán"])
        )

        if looks_shifted:
            # intentamos reconstruir:
            # si timestamp parece fecha real, lo usamos como fecha
            ts_date = parse_date_safe(ts)
            if ts_date:
                row["fecha"] = ts_date.strftime("%Y-%m-%d")
            # anio pasa a ser el año numérico
            year = parse_int_safe(fecha)  # tu "fecha" venía 2025
            if year:
                row["anio"] = str(year)
            # centro pasa a ser lo que estaba en "anio"
            row["centro"] = anio
            # espacio pasa a ser lo que estaba en "centro" (General / taller)
            row["espacio"] = centro
            # presentes pasa a ser lo que estaba en "espacio"
            row["presentes"] = parse_int_safe(espacio) or espacio
            # coordinador pasa a ser lo que estaba en "presentes"
            row["coordinador"] = presentes
            # modo pasa a ser lo que estaba en "coordinador"
            row["modo"] = coord
            # notas pasa a ser lo que estaba en "modo" (a veces timestamp)
            row["notas"] = modo if modo else notas

            repaired += 1

        # Normaliza tipos finales
        f = parse_date_safe(row.get("fecha", ""))
        if f:
            row["fecha"] = f.strftime("%Y-%m-%d")
        y = parse_int_safe(row.get("anio", ""))
        if y:
            row["anio"] = str(y)

        p = parse_int_safe(row.get("presentes", ""))
        if p is not None:
            row["presentes"] = p
        else:
            row["presentes"] = 0

        # defaults
        if not str(row.get("espacio", "")).strip():
            row["espacio"] = "General"

        return row

    df = df.apply(lambda r: pd.Series(fix_row(r.to_dict())), axis=1)

    # deja solo columnas estándar y ordenadas
    df = df[DEFAULT_HEADERS_ASIST].copy()

    # limpia espacios
    df["centro"] = df["centro"].astype(str).str.strip()
    df["espacio"] = df["espacio"].astype(str).str.strip()
    df["coordinador"] = df["coordinador"].astype(str).str.strip()
    df["modo"] = df["modo"].astype(str).str.strip()
    df["notas"] = df["notas"].astype(str).str.strip()
    df["usuario"] = df["usuario"].astype(str).str.strip()

    return df, repaired


def normalize_personas_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # intenta mapear columnas por nombre (por si vienen raras)
    cols = {normalize_colname(c): c for c in df.columns}
    # buscamos algo parecido a nombre/frecuencia/centro
    def find_col(keys):
        for k in keys:
            if k in cols:
                return cols[k]
        return None

    c_nombre = find_col(["nombre", "personas", "persona", "name"])
    c_freq = find_col(["frecuencia", "freq"])
    c_centro = find_col(["centro", "centro_barrial"])

    if c_nombre and c_freq and c_centro:
        out = df[[c_nombre, c_freq, c_centro]].copy()
        out.columns = ["nombre", "frecuencia", "centro"]
    else:
        # si vino sin encabezados, lo intentamos igual
        out = df.copy()
        out = out.iloc[:, :3]
        out.columns = ["nombre", "frecuencia", "centro"]

    out["nombre"] = out["nombre"].astype(str).str.strip()
    out["frecuencia"] = out["frecuencia"].astype(str).str.strip()
    out["centro"] = out["centro"].astype(str).str.strip()

    # normaliza centros (tildes, etc)
    out["centro"] = out["centro"].replace({"Calle Bélen": "Calle Belén", "Calle Belen": "Calle Belén"})
    return out


# =========================
# Import CSV Personas (robusto con comas en el nombre)
# =========================
def load_people_csv_from_repo() -> pd.DataFrame:
    """
    Busca datapersonas.csv / personas.csv / data/personas.csv.
    Carga aunque el nombre tenga comas.
    """
    candidates = ["datapersonas.csv", "personas.csv", "data/personas.csv"]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            df = parse_people_csv_text(text)
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame(columns=["nombre", "frecuencia", "centro"])


def parse_people_csv_text(text: str) -> pd.DataFrame:
    """
    Intenta varios separadores. Si el nombre tiene comas y el CSV está “mal”,
    recompone: nombre = join(cols[0:-2]) y deja las últimas 2 como frecuencia/centro.
    """
    if not text or not text.strip():
        return pd.DataFrame(columns=["nombre", "frecuencia", "centro"])

    # intentos “normales”
    for sep in [",", ";", "\t", "|"]:
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, engine="python", on_bad_lines="skip")
            df = df.dropna(how="all")
            if df.shape[1] >= 3:
                # si tiene headers buenos
                df2 = normalize_personas_df(df)
                if df2.shape[0] > 0:
                    return df2
        except Exception:
            continue

    # fallback: parse manual por líneas
    rows = []
    reader = csv.reader(io.StringIO(text))
    for r in reader:
        r = [x.strip() for x in r if str(x).strip() != ""]
        if len(r) < 3:
            continue
        # si tiene más de 3: el nombre estaba partido por comas
        if len(r) > 3:
            nombre = ", ".join(r[:-2]).strip()
            frecuencia = r[-2].strip()
            centro = r[-1].strip()
        else:
            nombre, frecuencia, centro = r[0], r[1], r[2]
        rows.append([nombre, frecuencia, centro])

    df = pd.DataFrame(rows, columns=["nombre", "frecuencia", "centro"])
    df = normalize_personas_df(df)
    return df


def push_people_to_sheet_if_empty(df_people: pd.DataFrame):
    """
    Si la pestaña 'personas' está vacía, la carga desde el CSV del repo.
    """
    ws = ws_personas()
    df_ws = sheet_to_df(ws)
    df_ws = normalize_personas_df(df_ws) if not df_ws.empty else pd.DataFrame()

    if df_ws.empty and df_people is not None and not df_people.empty:
        # escribir headers + filas
        ws.clear()
        ws.append_row(DEFAULT_HEADERS_PERSONAS)
        ws.append_rows(df_people[["nombre", "frecuencia", "centro"]].fillna("").values.tolist())


# =========================
# Auth simple (usuarios en secrets)
# =========================
def auth_block():
    st.sidebar.markdown("### Acceso")
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    users = st.secrets.get("users", None)

    if st.session_state.auth_user:
        st.sidebar.success(f"Conectado como: {st.session_state.auth_user}")
        if st.sidebar.button("Salir"):
            st.session_state.auth_user = None
            st.rerun()
        return True

    if not users:
        st.sidebar.warning("No hay [users] en secrets. (Modo prueba sin login)")
        st.session_state.auth_user = "demo"
        return True

    u = st.sidebar.text_input("Usuario", value="")
    p = st.sidebar.text_input("Contraseña", type="password", value="")
    if st.sidebar.button("Entrar"):
        if u in users and str(users[u]) == str(p):
            st.session_state.auth_user = u
            st.rerun()
        else:
            st.sidebar.error("Usuario/contraseña incorrectos.")
    return False


# =========================
# Reglas coordinadores por centro
# =========================
COORDS = {
    "Calle Belén": ["Natasha Carrari", "Estefanía Eberle", "Martín Pérez Santellán"],
    "Nudo a Nudo": ["Camila Prada", "Julieta"],
    "Casa Maranatha": ["Florencia", "Guillermina Cazenave"],
}

# (Opcional) asignar centro fijo por usuario (si querés bloquearlo)
USER_CENTRO = {
    # "natasha": "Calle Belén",
    # "camila": "Nudo a Nudo",
    # "florencia": "Casa Maranatha",
}


# =========================
# Escritura asistencia con regla “1 por día”
# =========================
def append_asistencia_row(row: dict):
    ws = ws_asistencia()
    df = sheet_to_df(ws)
    df_norm, _ = normalize_asistencia_df(df) if not df.empty else (pd.DataFrame(columns=DEFAULT_HEADERS_ASIST), 0)

    # Regla: una carga por (fecha, centro, espacio) por coordinador/usuario
    # (si querés más duro: una por centro/espacio sin importar persona, se puede)
    key_fecha = row["fecha"]
    key_centro = row["centro"]
    key_espacio = row["espacio"]

    existing = df_norm[
        (df_norm["fecha"].astype(str) == str(key_fecha)) &
        (df_norm["centro"].astype(str) == str(key_centro)) &
        (df_norm["espacio"].astype(str) == str(key_espacio)) &
        (df_norm["usuario"].astype(str) == str(row.get("usuario", "")))
    ]

    if not existing.empty:
        st.error("Ya existe una carga para ese día/centro/espacio con este usuario. (Para evitar duplicados)")
        return False

    values = [row.get(h, "") for h in DEFAULT_HEADERS_ASIST]
    ws.append_row(values)
    return True


# =========================
# KPIs / Reportes
# =========================
def kpi_box(title, value):
    st.markdown(
        f"""
        <div class="hc-kpi">
            <div class="hc-kpi-title">{title}</div>
            <div class="hc-kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Main
# =========================
def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    inject_css()

    ok = auth_block()
    if not ok:
        st.stop()

    user = st.session_state.auth_user or "demo"

    st.title(APP_TITLE)

    # Centro asignado (bloqueo opcional)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Centro / Coordinador")

    if user in USER_CENTRO:
        centro_sel = USER_CENTRO[user]
        st.sidebar.info(f"Centro asignado: {centro_sel}")
    else:
        centro_sel = st.sidebar.selectbox("Centro asignado", CENTROS, index=0)

    # Coordinador: solo los del centro
    coord_sel = st.sidebar.selectbox("¿Quién carga?", COORDS.get(centro_sel, ["(sin definir)"]))

    # Año
    anio_sel = st.sidebar.selectbox("Año", [date.today().year, date.today().year - 1, date.today().year + 1], index=0)

    st.caption(f"Estás trabajando sobre: **{centro_sel}** — 👤 **{coord_sel}** — 📅 **{anio_sel}**")

    # --- Cargar personas CSV del repo a Sheets si falta ---
    people_repo = load_people_csv_from_repo()
    if people_repo.empty:
        st.sidebar.warning("No encontré datapersonas.csv / personas.csv. (Si existe, revisá que esté en el repo)")
    else:
        push_people_to_sheet_if_empty(people_repo)

    # --- Traer asistencia desde Sheets (y normalizar) ---
    df_raw = sheet_to_df(ws_asistencia())
    df_asist, repaired_count = normalize_asistencia_df(df_raw) if not df_raw.empty else (pd.DataFrame(columns=DEFAULT_HEADERS_ASIST), 0)

    # Filtros centro/año
    df_asist["anio"] = df_asist["anio"].astype(str).replace("", str(anio_sel))
    df_c = df_asist[(df_asist["centro"] == centro_sel) & (df_asist["anio"].astype(str) == str(anio_sel))].copy()
    df_all_year = df_asist[df_asist["anio"].astype(str) == str(anio_sel)].copy()

    # KPIs (centro)
    hoy = date.today().strftime("%Y-%m-%d")
    hoy_total = int(df_c.loc[df_c["fecha"].astype(str) == hoy, "presentes"].sum()) if not df_c.empty else 0
    ult7 = (date.today() - timedelta(days=6)).strftime("%Y-%m-%d")
    ult7_total = int(df_c.loc[df_c["fecha"].astype(str) >= ult7, "presentes"].sum()) if not df_c.empty else 0

    # Días sin cargar esta semana (lun-dom)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_days = [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    loaded_days = set(df_c["fecha"].astype(str).tolist()) if not df_c.empty else set()
    missing_week = sum(1 for d in week_days if d not in loaded_days and d <= today.strftime("%Y-%m-%d"))

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        kpi_box("Ingresos HOY", hoy_total)
    with c2:
        kpi_box("Ingresos últimos 7 días", ult7_total)
    with c3:
        kpi_box("Días sin cargar (esta semana)", missing_week)
    with c4:
        kpi_box("Filas reparadas (Sheets)", repaired_count)

    st.markdown("---")

    tabs = st.tabs(["📌 Registrar asistencia", "👥 Personas", "📊 Reportes / Base de datos", "🌍 Global", "🧰 Debug"])

    # =========================
    # TAB 1: Registrar
    # =========================
    with tabs[0]:
        st.subheader("Registrar asistencia para este centro")

        fecha = st.date_input("Fecha", value=date.today())
        fecha_str = fecha.strftime("%Y-%m-%d")

        if centro_sel == "Casa Maranatha":
            espacio = st.selectbox("Espacio (solo Maranatha)", ["General"] + MARANATHA_ESPACIOS, index=0)
        else:
            espacio = "General"
            st.info("Este centro no usa espacios internos.")

        colA, colB = st.columns([1, 2])
        with colA:
            presentes = st.number_input("Total presentes", min_value=0, step=1, value=0)
            cerrado = st.checkbox("Hoy el centro estuvo cerrado / no abrió")
        with colB:
            modo = st.selectbox("Tipo de día", MODO_DIA, index=0)
            notas = st.text_area("Notas (opcional)", height=90)

        if cerrado:
            presentes = 0
            modo = "Cerrado / no abrió"

        if st.button("✅ Guardar registro"):
            row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fecha": fecha_str,
                "anio": str(anio_sel),
                "centro": centro_sel,
                "espacio": espacio,
                "presentes": int(presentes),
                "coordinador": coord_sel,
                "modo": modo,
                "notas": notas,
                "usuario": user,
                "cargado_por": coord_sel,
                "accion": "append",
            }
            ok = append_asistencia_row(row)
            if ok:
                st.success("Registro guardado en Google Sheets ✅")
                st.rerun()

    # =========================
    # TAB 2: Personas
    # =========================
    with tabs[1]:
        st.subheader("Personas de este centro")

        dfp_raw = sheet_to_df(ws_personas())
        dfp = normalize_personas_df(dfp_raw) if not dfp_raw.empty else pd.DataFrame(columns=["nombre","frecuencia","centro"])
        dfp_c = dfp[dfp["centro"].replace({"Calle Bélen": "Calle Belén"}) == centro_sel].copy()

        st.markdown(f"<span class='hc-badge'>Personas visibles: {len(dfp_c)}</span>", unsafe_allow_html=True)

        # Si sigue vacío, permitir “importar ahora”
        colx, coly = st.columns([1, 2])
        with colx:
            if st.button("📥 Importar CSV ahora (si está vacío)"):
                if people_repo.empty:
                    st.error("No encontré datapersonas.csv / personas.csv en el repo.")
                else:
                    push_people_to_sheet_if_empty(people_repo)
                    st.success("Listo: cargué personas desde el CSV a Sheets.")
                    st.rerun()
        with coly:
            st.caption("Busca datapersonas.csv, personas.csv o data/personas.csv en el repo.")

        if dfp_c.empty:
            st.warning("No hay personas visibles para este centro. Si el CSV existe, revisá separadores/encabezados.")
        else:
            q = st.text_input("Buscar por nombre", value="")
            view = dfp_c
            if q.strip():
                view = view[view["nombre"].str.contains(q, case=False, na=False)]
            st.dataframe(view, use_container_width=True, hide_index=True)

    # =========================
    # TAB 3: Reportes / Base
    # =========================
    with tabs[2]:
        st.subheader("Reportes (este centro)")
        if df_c.empty:
            st.info("Todavía no hay registros de asistencia para este centro (o están mal formateados en Sheets).")
        else:
            st.caption("Últimos registros (este centro / este año)")
            show = df_c.sort_values("fecha", ascending=False).head(50)
            st.dataframe(show, use_container_width=True, hide_index=True)

            # Resumen por día
            st.markdown("### Resumen por día")
            daily = df_c.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
            st.line_chart(daily.set_index("fecha"))

            # Resumen por espacio (solo Maranatha)
            if centro_sel == "Casa Maranatha":
                st.markdown("### Resumen por espacio")
                by_space = df_c.groupby("espacio", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
                st.bar_chart(by_space.set_index("espacio"))

    # =========================
    # TAB 4: Global
    # =========================
    with tabs[3]:
        st.subheader("Global (todos los centros)")

        if df_all_year.empty:
            st.info("No hay registros globales para este año (o no están normalizados).")
        else:
            # Totales por centro
            by_center = df_all_year.groupby("centro", as_index=False)["presentes"].sum().sort_values("presentes", ascending=False)
            st.markdown("### Totales por centro (año)")
            st.bar_chart(by_center.set_index("centro"))

            # Totales por día (todos los centros)
            st.markdown("### Totales por día (todos los centros)")
            daily_all = df_all_year.groupby("fecha", as_index=False)["presentes"].sum().sort_values("fecha")
            st.line_chart(daily_all.set_index("fecha"))

            st.markdown("### Base de datos (filtrable)")
            f_centro = st.multiselect("Filtrar centros", CENTROS, default=CENTROS)
            view = df_all_year[df_all_year["centro"].isin(f_centro)].sort_values(["fecha","centro"], ascending=[False, True])
            st.dataframe(view, use_container_width=True, hide_index=True)

    # =========================
    # TAB 5: Debug
    # =========================
    with tabs[4]:
        st.subheader("Debug Google Sheets")
        st.write("**Spreadsheet ID:**", get_spreadsheet_id())
        st.write("**Pestaña asistencia:**", ASISTENCIA_TAB)
        st.write("**Pestaña personas:**", PERSONAS_TAB)
        st.write("**Registros asistencia (raw):**", 0 if df_raw.empty else len(df_raw))
        st.write("**Registros asistencia (normalizados):**", 0 if df_asist.empty else len(df_asist))
        st.write("**Reparaciones detectadas:**", repaired_count)

        if not df_raw.empty:
            st.markdown("#### Primeras 10 filas (raw)")
            st.dataframe(df_raw.head(10), use_container_width=True)

        if not df_asist.empty:
            st.markdown("#### Primeras 10 filas (normalizadas)")
            st.dataframe(df_asist.head(10), use_container_width=True)


if __name__ == "__main__":
    main()
