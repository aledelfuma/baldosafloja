import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError
import time

# =========================
# Config UI / Branding
# =========================
PRIMARY = "#004E7B"
SECONDARY = "#63296C"

st.set_page_config(
    page_title="Asistencia — Hogar de Cristo Bahía Blanca",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = f"""
<style>
:root {{
  --primary: {PRIMARY};
  --secondary: {SECONDARY};
}}
section[data-testid="stSidebar"] {{
  border-right: 1px solid rgba(255,255,255,.08);
}}
.badge {{
  display:inline-block;
  padding:.25rem .6rem;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.14);
  background: rgba(0,0,0,.25);
  font-size:.85rem;
}}
.kpi {{
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(0,0,0,.25);
}}
.kpi h3 {{
  margin: 0;
  font-size: .9rem;
  opacity: .9;
}}
.kpi .v {{
  font-size: 2rem;
  font-weight: 700;
  margin-top: .2rem;
}}
hr {{
  border: none;
  border-top: 1px solid rgba(255,255,255,.10);
}}
.small {{
  opacity: .85;
  font-size: .9rem;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================
# Sheets schema
# =========================
ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
ASISTENCIA_PERSONAS_TAB = "asistencia_personas"

ASISTENCIA_COLS = [
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
    "accion",
]

PERSONAS_COLS = [
    "nombre",
    "frecuencia",
    "centro",
    "edad",
    "domicilio",
    "notas",
    "activo",
    "timestamp",
    "usuario",
]

ASISTENCIA_PERSONAS_COLS = [
    "timestamp",
    "fecha",
    "anio",
    "centro",
    "espacio",
    "nombre",
    "estado",        # "Presente" | "Ausente"
    "es_nuevo",      # "SI" | "NO"
    "coordinador",
    "usuario",
    "notas",
]

# =========================
# Centros / espacios
# =========================
CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar (Primaria)",
    "Apoyo escolar (Secundaria)",
    "Fines",
    "Espacio Joven",
    "La Ronda",
    "General",
]

DEFAULT_ESPACIO = "General"

# =========================
# Helpers: secrets / auth
# =========================
def get_secret(path, default=None):
    try:
        node = st.secrets
        for p in path.split("."):
            node = node[p]
        return node
    except Exception:
        return default

def normalize_private_key(pk: str) -> str:
    if not isinstance(pk, str):
        return pk
    if "\\n" in pk:
        pk = pk.replace("\\n", "\n")
    return pk

def login_box():
    st.sidebar.markdown("## Acceso")
    if st.session_state.get("logged_in"):
        usuario = st.session_state.get("usuario")
        st.sidebar.success(f"Conectado como: {usuario}")
        if st.sidebar.button("Salir"):
            for k in ["logged_in", "usuario", "centro_asignado", "nombre_visible"]:
                st.session_state.pop(k, None)
            st.rerun()
        return True

    u = st.sidebar.text_input("Usuario", key="login_user")
    p = st.sidebar.text_input("Contraseña", type="password", key="login_pass")
    if st.sidebar.button("Ingresar"):
        users = get_secret("users", {})
        if u in users and str(users[u]) == str(p):
            st.session_state["logged_in"] = True
            st.session_state["usuario"] = u
            prof = get_secret(f"user_profile.{u}", {})
            st.session_state["centro_asignado"] = prof.get("centro", "")
            st.session_state["nombre_visible"] = prof.get("nombre", u)
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos.")
    return False

# =========================
# Google Sheets connection
# =========================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    sa = dict(get_secret("gcp_service_account", {}))
    if not sa:
        raise KeyError("Falta [gcp_service_account] en secrets.toml")

    sa["private_key"] = normalize_private_key(sa.get("private_key", ""))

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    sid = get_secret("sheets.spreadsheet_id", "")
    if not sid:
        raise KeyError("Falta [sheets].spreadsheet_id en secrets.toml")
    gc = get_gspread_client()
    return gc.open_by_key(sid)

def _open_ws_strict(sh, title: str):
    return sh.worksheet(title)

def get_or_create_ws(title: str, cols: list, rows: int = 2000):
    """
    FIX: si al crear dice "already exists", re-intenta abrir y listo.
    """
    sh = get_spreadsheet()

    try:
        return _open_ws_strict(sh, title)
    except Exception:
        pass

    try:
        ws = sh.add_worksheet(title=title, rows=rows, cols=max(20, len(cols)))
        ws.update("A1", [cols])
        return ws
    except Exception as e:
        msg = str(e).lower()

        if "already exists" in msg or "alreadyexists" in msg:
            try:
                return _open_ws_strict(sh, title)
            except Exception:
                st.error(
                    f"No pude abrir la pestaña '{title}' aunque Google dice que existe.\n\n"
                    f"Revisá si tiene espacios raros en el nombre (ej: 'asistencia_personas '), "
                    f"o si está en otra planilla.\n\nDetalle: {e}"
                )
                st.stop()

        st.error(
            f"No pude crear la pestaña '{title}'.\n\n"
            f"Solución: creala manualmente en el Google Sheet con ese nombre y recargá.\n\n"
            f"Detalle: {e}"
        )
        st.stop()

# =========================
# ✅ FIX: Retry/backoff para APIError de Google
# =========================
def _apierror_info(e: APIError) -> str:
    # gspread guarda info HTTP en e.response
    try:
        status = getattr(e.response, "status_code", None)
        text = getattr(e.response, "text", "")
        if text and len(text) > 800:
            text = text[:800] + "…"
        return f"HTTP {status} — {text}"
    except Exception:
        return str(e)

def safe_get_all_values(ws, tries=6):
    """
    Evita que la app se caiga por 429/503/temporales.
    Backoff: 1s, 2s, 4s, 8s...
    """
    last_err = None
    for i in range(tries):
        try:
            return ws.get_all_values()
        except APIError as e:
            last_err = e
            info = _apierror_info(e).lower()
            # Reintenta en errores típicos temporales / cuota
            if "429" in info or "rate" in info or "quota" in info or "503" in info or "timeout" in info:
                time.sleep(2 ** i * 0.5)
                continue
            # Si no parece temporal, cortar con diagnóstico
            st.error("Google Sheets devolvió un error al leer datos.")
            st.code(_apierror_info(e))
            st.stop()
        except Exception as e:
            last_err = e
            time.sleep(2 ** i * 0.5)

    st.error("No pude leer la planilla luego de varios intentos (posible cuota o error temporal).")
    if isinstance(last_err, APIError):
        st.code(_apierror_info(last_err))
    else:
        st.code(str(last_err))
    st.stop()

def read_ws_df(title: str, cols: list) -> pd.DataFrame:
    ws = get_or_create_ws(title, cols)

    # ✅ usa lectura con retry
    values = safe_get_all_values(ws)

    if not values:
        ws.update("A1", [cols])
        return pd.DataFrame(columns=cols)

    header = values[0]
    body = values[1:] if len(values) > 1 else []

    if header[: len(cols)] == cols:
        df = pd.DataFrame(body, columns=header)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df = df[cols]
        return df

    df = pd.DataFrame(values)
    for i in range(df.shape[1], len(cols)):
        df[i] = ""
    df = df.iloc[:, : len(cols)]
    df.columns = cols
    return df

def append_ws_rows(title: str, cols: list, rows: list[list]):
    ws = get_or_create_ws(title, cols)
    first = safe_get_all_values(ws)[:1]
    if not first or first[0][: len(cols)] != cols:
        ws.update("A1", [cols])
    ws.append_rows(rows, value_input_option="USER_ENTERED")

def repair_headers(title: str, cols: list):
    ws = get_or_create_ws(title, cols)
    values = safe_get_all_values(ws)
    if not values:
        ws.update("A1", [cols])
        return
    df = pd.DataFrame(values)
    for i in range(df.shape[1], len(cols)):
        df[i] = ""
    df = df.iloc[:, : len(cols)]
    data = df.values.tolist()
    ws.clear()
    ws.update("A1", [cols])
    ws.update("A2", data)

# =========================
# Data normalization
# =========================
def year_of(fecha_iso: str) -> str:
    try:
        return str(pd.to_datetime(fecha_iso).year)
    except Exception:
        return str(date.today().year)

def clean_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(str(x).strip()))
    except Exception:
        return default

def norm_text(x):
    if x is None:
        return ""
    return str(x).strip()

# =========================
# Asistencia aggregation
# =========================
def latest_asistencia(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df2 = df.copy()
    for c in ["timestamp","fecha","anio","centro","espacio","presentes"]:
        if c not in df2.columns:
            df2[c] = ""
    df2["timestamp_dt"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    df2["k"] = (
        df2["anio"].astype(str) + "|" +
        df2["fecha"].astype(str) + "|" +
        df2["centro"].astype(str) + "|" +
        df2["espacio"].astype(str)
    )
    df2 = df2.sort_values("timestamp_dt", ascending=True)
    df2 = df2.groupby("k", as_index=False).tail(1)
    df2 = df2.drop(columns=["k"], errors="ignore")
    return df2

def last_load_info(df_latest: pd.DataFrame, centro: str):
    if df_latest.empty:
        return None, None
    d = df_latest[df_latest["centro"] == centro].copy()
    if d.empty:
        return None, None
    d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    last = d["fecha_dt"].max()
    if pd.isna(last):
        return None, None
    days = (pd.Timestamp(date.today()) - last).days
    return last.date().isoformat(), int(days)

# =========================
# Personas logic
# =========================
def personas_for_centro(df_personas: pd.DataFrame, centro: str) -> pd.DataFrame:
    if df_personas.empty:
        return df_personas
    if "centro" in df_personas.columns:
        return df_personas[df_personas["centro"] == centro].copy()
    return df_personas.copy()

def upsert_persona(df_personas: pd.DataFrame, nombre: str, centro: str, usuario: str, frecuencia="Nueva"):
    nombre = norm_text(nombre)
    if not nombre:
        return df_personas

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not df_personas.empty:
        mask = (df_personas.get("nombre", "") == nombre) & (df_personas.get("centro", "") == centro)
        if mask.any():
            return df_personas

    row = {
        "nombre": nombre,
        "frecuencia": frecuencia,
        "centro": centro,
        "edad": "",
        "domicilio": "",
        "notas": "",
        "activo": "SI",
        "timestamp": now,
        "usuario": usuario,
    }
    append_ws_rows(PERSONAS_TAB, PERSONAS_COLS, [[row.get(c, "") for c in PERSONAS_COLS]])
    df2 = pd.concat([df_personas, pd.DataFrame([row])], ignore_index=True)
    return df2

# =========================
# Writes
# =========================
def append_asistencia(fecha, centro, espacio, presentes, coordinador, modo, notas, usuario, accion="append"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    anio = year_of(fecha)
    row = {
        "timestamp": ts,
        "fecha": fecha,
        "anio": anio,
        "centro": centro,
        "espacio": espacio,
        "presentes": str(presentes),
        "coordinador": coordinador,
        "modo": modo,
        "notas": notas,
        "usuario": usuario,
        "accion": accion,
    }
    append_ws_rows(ASISTENCIA_TAB, ASISTENCIA_COLS, [[row.get(c, "") for c in ASISTENCIA_COLS]])

def append_asistencia_personas(fecha, centro, espacio, nombre, estado, es_nuevo, coordinador, usuario, notas=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    anio = year_of(fecha)
    row = {
        "timestamp": ts,
        "fecha": fecha,
        "anio": anio,
        "centro": centro,
        "espacio": espacio,
        "nombre": nombre,
        "estado": estado,
        "es_nuevo": es_nuevo,
        "coordinador": coordinador,
        "usuario": usuario,
        "notas": notas,
    }
    append_ws_rows(
        ASISTENCIA_PERSONAS_TAB,
        ASISTENCIA_PERSONAS_COLS,
        [[row.get(c, "") for c in ASISTENCIA_PERSONAS_COLS]]
    )

# =========================
# UI blocks
# =========================
def kpi_row(df_latest, centro):
    hoy = date.today().isoformat()
    now = date.today()
    week_ago = (now - timedelta(days=6)).isoformat()
    month_start = now.replace(day=1).isoformat()

    d = df_latest.copy()
    if d.empty:
        c1 = c2 = c3 = 0
    else:
        d["presentes_i"] = d.get("presentes", "").apply(lambda x: clean_int(x, 0))
        c1 = int(d[(d["centro"] == centro) & (d["fecha"] == hoy)]["presentes_i"].sum())
        c2 = int(d[(d["centro"] == centro) & (d["fecha"] >= week_ago) & (d["fecha"] <= hoy)]["presentes_i"].sum())
        c3 = int(d[(d["centro"] == centro) & (d["fecha"] >= month_start) & (d["fecha"] <= hoy)]["presentes_i"].sum())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='kpi'><h3>Este mes</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)

def sidebar_pending(df_latest, centro):
    last_date, days = last_load_info(df_latest, centro)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Pendientes")
    if last_date is None:
        st.sidebar.warning("⚠️ Todavía no hay cargas para este centro.")
        return

    if days == 0:
        st.sidebar.success("✅ Ya se cargó hoy.")
    else:
        st.sidebar.warning(f"⏰ Última carga: {last_date} (hace {days} días)")

    today = date.today()
    start = today - timedelta(days=today.weekday())
    days_list = [start + timedelta(days=i) for i in range(7)]
    df_c = df_latest[df_latest["centro"] == centro].copy()
    loaded = set(pd.to_datetime(df_c["fecha"], errors="coerce").dt.date.dropna().tolist())
    missing = [d for d in days_list if d <= today and d not in loaded]
    if missing:
        st.sidebar.info("📌 Días sin carga esta semana:\n- " + "\n- ".join([m.isoformat() for m in missing]))
    else:
        st.sidebar.success("🎉 Semana al día (hasta hoy).")

def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.subheader("Registrar asistencia")

    anio = str(date.today().year)
    fecha = st.date_input("Fecha", value=date.today()).isoformat()

    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio (solo Maranatha)", ESPACIOS_MARANATHA, index=ESPACIOS_MARANATHA.index("General"))
    else:
        espacio = DEFAULT_ESPACIO
        st.info("Este centro no usa espacios internos. (Solo Maranatha)")

    modo = st.selectbox("Tipo de día", ["Día habitual", "Actividad especial", "Centro cerrado / no abrió"], index=0)
    notas = st.text_area("Notas (opcional)", placeholder="Ej: visita, salida, situación particular...")

    st.markdown("### Asistencia persona por persona")

    df_centro = personas_for_centro(df_personas, centro)
    for c in PERSONAS_COLS:
        if c not in df_centro.columns:
            df_centro[c] = ""

    nombres = sorted([n for n in df_centro["nombre"].astype(str).tolist() if n.strip()])

    colA, colB = st.columns([2, 1])
    with colA:
        presentes = st.multiselect("¿Quiénes vinieron hoy?", options=nombres, default=[])
    with colB:
        total_presentes = st.number_input(
            "Total presentes (si no marcás uno por uno)",
            min_value=0,
            value=len(presentes),
            step=1
        )

    st.markdown("### Persona nueva (si vino alguien que no está)")
    nueva = st.text_input("Nombre y apellido (opcional)", placeholder="Ej: Pérez, Juan")
    agregar_nueva = st.checkbox("Hoy vino y es persona nueva")

    df_latest = latest_asistencia(df_asistencia)
    ya = df_latest[
        (df_latest.get("fecha","") == fecha) &
        (df_latest.get("centro","") == centro) &
        (df_latest.get("espacio","") == espacio) &
        (df_latest.get("anio","") == anio)
    ]
    existe = not ya.empty
    if existe:
        st.warning("⚠️ Ya hay una carga para este centro / fecha / espacio. Si guardás de nuevo, quedará como última versión (overwrite).")
        overwrite = st.checkbox("Confirmo sobreescritura", value=False)
    else:
        overwrite = True

    guardar_ausentes = st.checkbox("Guardar también AUSENTES (marca Ausente para todos los que no vinieron)", value=False)

    st.divider()

    if st.button("✅ Guardar asistencia", type="primary", use_container_width=True):
        if not overwrite:
            st.error("Te falta confirmar la sobreescritura.")
            st.stop()

        if agregar_nueva and nueva.strip():
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, frecuencia="Nueva")
            if nueva not in presentes:
                presentes = presentes + [nueva]

        if len(presentes) > 0:
            total_presentes = len(presentes)

        accion = "overwrite" if existe else "append"

        with st.spinner("Guardando en Google Sheets..."):
            append_asistencia(
                fecha=fecha,
                centro=centro,
                espacio=espacio,
                presentes=total_presentes,
                coordinador=nombre_visible,
                modo=modo,
                notas=notas,
                usuario=usuario,
                accion=accion,
            )

            for n in presentes:
                append_asistencia_personas(
                    fecha=fecha,
                    centro=centro,
                    espacio=espacio,
                    nombre=n,
                    estado="Presente",
                    es_nuevo="SI" if (agregar_nueva and n == nueva.strip()) else "NO",
                    coordinador=nombre_visible,
                    usuario=usuario,
                    notas="",
                )

            if guardar_ausentes:
                ausentes = [n for n in nombres if n not in presentes]
                for n in ausentes:
                    append_asistencia_personas(
                        fecha=fecha,
                        centro=centro,
                        espacio=espacio,
                        nombre=n,
                        estado="Ausente",
                        es_nuevo="NO",
                        coordinador=nombre_visible,
                        usuario=usuario,
                        notas="",
                    )

        st.toast("✅ Asistencia guardada en Google Sheets", icon="✅")
        st.success("Listo. Se guardó correctamente.")
        st.rerun()

def page_personas(df_personas, centro, usuario):
    st.subheader("Personas (base del centro)")
    df_centro = personas_for_centro(df_personas, centro).copy()

    for c in PERSONAS_COLS:
        if c not in df_centro.columns:
            df_centro[c] = ""

    c1, c2 = st.columns([2, 1])
    with c1:
        q = st.text_input("Buscar", placeholder="Filtrar por nombre...")
    with c2:
        solo_activos = st.checkbox("Solo activos", value=True)

    if q.strip():
        df_centro = df_centro[df_centro["nombre"].astype(str).str.contains(q.strip(), case=False, na=False)]
    if solo_activos:
        df_centro = df_centro[df_centro["activo"].astype(str).str.upper().fillna("") != "NO"]

    st.markdown(f"<span class='badge'>Personas visibles: {len(df_centro)}</span>", unsafe_allow_html=True)
    st.dataframe(df_centro[["nombre","frecuencia","edad","domicilio","notas","activo"]], use_container_width=True)

def page_reportes(df_asistencia, centro):
    st.subheader("Reportes (este centro)")
    df_latest = latest_asistencia(df_asistencia)
    if df_latest.empty:
        st.info("Todavía no hay registros.")
        return

    anios = sorted(df_latest["anio"].astype(str).unique())
    anio = st.selectbox("Año", anios, index=len(anios)-1)

    df_c = df_latest[(df_latest["centro"] == centro) & (df_latest["anio"].astype(str) == str(anio))].copy()
    if df_c.empty:
        st.info("Todavía no hay registros para este centro / año.")
        return

    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"], errors="coerce")
    df_c = df_c.sort_values("fecha_dt", ascending=True)

    st.markdown("### Últimos registros (este centro / este año)")
    st.dataframe(df_c[["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"]].tail(30), use_container_width=True)

    st.markdown("### Evolución (por fecha)")
    serie = df_c.groupby("fecha", as_index=False)["presentes_i"].sum().sort_values("fecha")
    st.line_chart(serie.set_index("fecha")["presentes_i"])

def page_global(df_asistencia):
    st.subheader("Global (todos los centros)")
    df_latest = latest_asistencia(df_asistencia)
    if df_latest.empty:
        st.info("Todavía no hay registros globales.")
        return

    anios = sorted(df_latest["anio"].astype(str).unique())
    anio = st.selectbox("Año (global)", anios, index=len(anios)-1)

    d = df_latest[df_latest["anio"].astype(str) == str(anio)].copy()
    d["presentes_i"] = d["presentes"].apply(lambda x: clean_int(x, 0))

    st.markdown("### Por centro (acumulado)")
    por = d.groupby("centro", as_index=False)["presentes_i"].sum().sort_values("presentes_i", ascending=False)
    st.bar_chart(por.set_index("centro")["presentes_i"])

def main():
    st.title("Sistema de Asistencia — Hogar de Cristo Bahía Blanca")

    ok = login_box()
    if not ok:
        st.stop()

    usuario = st.session_state.get("usuario", "")
    centro_asignado = st.session_state.get("centro_asignado", "")
    nombre_visible = st.session_state.get("nombre_visible", usuario)

    if centro_asignado not in CENTROS:
        st.error("Tu usuario no tiene centro asignado. Revisá [user_profile] en secrets.toml.")
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Centro / Coordinador")
    st.sidebar.markdown(f"**Centro asignado:** {centro_asignado}")
    st.sidebar.markdown(f"**Quién carga:** {nombre_visible}")

    with st.spinner("Cargando datos desde Google Sheets..."):
        df_asistencia = read_ws_df(ASISTENCIA_TAB, ASISTENCIA_COLS)
        df_personas = read_ws_df(PERSONAS_TAB, PERSONAS_COLS)
        _ = read_ws_df(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS)

    df_latest = latest_asistencia(df_asistencia)

    st.caption(f"Estás trabajando sobre: **{centro_asignado}** — 👤 **{nombre_visible}**")
    kpi_row(df_latest, centro_asignado)
    sidebar_pending(df_latest, centro_asignado)

    tabs = st.tabs(["🧾 Registrar asistencia", "👥 Personas", "📊 Reportes", "🌍 Global"])
    with tabs[0]:
        page_registrar_asistencia(df_personas, df_asistencia, centro_asignado, nombre_visible, usuario)
    with tabs[1]:
        page_personas(df_personas, centro_asignado, usuario)
    with tabs[2]:
        page_reportes(df_asistencia, centro_asignado)
    with tabs[3]:
        page_global(df_asistencia)

if __name__ == "__main__":
    main()
