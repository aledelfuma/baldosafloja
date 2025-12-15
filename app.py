import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread

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
    """
    Asegura formato correcto:
    - Si viene con \\n, lo convierte a saltos reales
    - Si viene ya con saltos reales, lo deja
    """
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

def get_or_create_ws(title: str, cols: list, rows: int = 2000):
    sh = get_spreadsheet()
    try:
        ws = sh.worksheet(title)
        return ws
    except Exception:
        # Intentar crear
        try:
            ws = sh.add_worksheet(title=title, rows=rows, cols=max(20, len(cols)))
            # set headers
            ws.update("A1", [cols])
            return ws
        except Exception as e:
            # Si no puede crear (límite/permisos), mostrar instrucción clara
            st.error(
                f"No pude crear la pestaña '{title}'.\n\n"
                f"Solución: creala manualmente en el Google Sheet con ese nombre "
                f"y volvé a recargar.\n\nDetalle: {e}"
            )
            st.stop()

def read_ws_df(title: str, cols: list) -> pd.DataFrame:
    ws = get_or_create_ws(title, cols)
    values = ws.get_all_values()

    if not values:
        # sheet vacía: poner headers
        ws.update("A1", [cols])
        return pd.DataFrame(columns=cols)

    # Si la primera fila no coincide con headers, intentamos "reparar" leyendo por posición
    header = values[0]
    body = values[1:] if len(values) > 1 else []

    # Caso 1: headers OK
    if header[: len(cols)] == cols:
        df = pd.DataFrame(body, columns=header)
        # asegurar columnas requeridas
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df = df[cols]
        return df

    # Caso 2: headers rotos / no existen -> interpretar por posición
    df = pd.DataFrame(values)
    # Si hay menos columnas que las esperadas, completar
    for i in range(df.shape[1], len(cols)):
        df[i] = ""
    df = df.iloc[:, : len(cols)]
    df.columns = cols
    # Primera fila probablemente era data: NO la descartamos
    return df

def append_ws_rows(title: str, cols: list, rows: list[list]):
    ws = get_or_create_ws(title, cols)
    # garantizar headers
    first = ws.get_all_values()[:1]
    if not first or first[0][: len(cols)] != cols:
        ws.update("A1", [cols])
    ws.append_rows(rows, value_input_option="USER_ENTERED")

def repair_headers(title: str, cols: list):
    ws = get_or_create_ws(title, cols)
    values = ws.get_all_values()
    if not values:
        ws.update("A1", [cols])
        return
    # Reescribimos: headers + data por posición (sin perder filas)
    df = pd.DataFrame(values)
    for i in range(df.shape[1], len(cols)):
        df[i] = ""
    df = df.iloc[:, : len(cols)]
    data = df.values.tolist()
    ws.clear()
    ws.update("A1", [cols])
    # Guardar todo lo que había como data debajo (incluyendo la vieja fila 1)
    ws.update("A2", data)

# =========================
# Data normalization
# =========================
def today_str():
    return date.today().isoformat()

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

    # Si existe (mismo nombre + centro), no duplicar
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
    df2 = pd.concat([df_personas, pd.DataFrame([row])], ignore_index=True)
    append_ws_rows(PERSONAS_TAB, PERSONAS_COLS, [[row.get(c, "") for c in PERSONAS_COLS]])
    return df2

# =========================
# Asistencia logic (audit-friendly: append con accion)
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
    append_ws_rows(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS, [[row.get(c, "") for c in ASISTENCIA_PERSONAS_COLS]])

def latest_asistencia(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo el último registro por (anio,fecha,centro,espacio) usando timestamp."""
    if df.empty:
        return df
    # normalizar
    df2 = df.copy()
    for c in ["timestamp","fecha","anio","centro","espacio"]:
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

# =========================
# UI pages
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

def page_registrar_asistencia(df_personas, df_asistencia, df_asist_personas, centro, nombre_visible, usuario):
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
    nombres = sorted([n for n in df_centro.get("nombre", pd.Series(dtype=str)).astype(str).tolist() if n.strip()])

    colA, colB = st.columns([2, 1])
    with colA:
        presentes = st.multiselect(
            "¿Quiénes vinieron hoy? (seleccioná personas)",
            options=nombres,
            default=[],
        )
    with colB:
        total_presentes = st.number_input(
            "Total presentes (si no querés marcar uno por uno)",
            min_value=0,
            value=len(presentes),
            step=1
        )

    st.caption("Tip: si marcás personas en la lista, el total se autocompleta; si no, podés cargar solo el total.")

    st.markdown("### Persona nueva (si vino alguien que no está en la lista)")
    nueva = st.text_input("Nombre y apellido (opcional)", placeholder="Ej: Pérez, Juan")
    agregar_nueva = st.checkbox("Hoy vino y es persona nueva")

    # Dedupe: ya existe carga para ese día/centro/espacio?
    df_latest = latest_asistencia(df_asistencia)
    ya = df_latest[
        (df_latest.get("fecha","") == fecha) &
        (df_latest.get("centro","") == centro) &
        (df_latest.get("espacio","") == espacio) &
        (df_latest.get("anio","") == anio)
    ]
    existe = not ya.empty

    if existe:
        st.warning("⚠️ Ya existe una carga para este centro / fecha / espacio. Si guardás de nuevo, quedará como *última versión* (no borra, agrega con 'overwrite').")
        overwrite = st.checkbox("Confirmo que quiero sobreescribir (última versión)", value=False)
    else:
        overwrite = True

    if st.button("Guardar asistencia", type="primary", use_container_width=True):
        if not overwrite:
            st.error("Marcá la confirmación de sobreescritura para guardar.")
            st.stop()

        # Si agrego persona nueva:
        if agregar_nueva and nueva.strip():
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, frecuencia="Nueva")
            if nueva not in presentes:
                presentes = presentes + [nueva]

        # Calcular totales
        if len(presentes) > 0:
            total_presentes = len(presentes)

        # Guardar resumen (asistencia)
        accion = "overwrite" if existe else "append"
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

        # Guardar asistencia_personas
        # - Presente: los seleccionados
        # - Ausente: el resto (solo si el usuario quiere; para no inflar, lo hacemos opcional)
        guardar_ausentes = st.session_state.get("guardar_ausentes", False)

        # presentes
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

        # ausentes (opcional)
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

        st.success("✅ Guardado en Google Sheets.")
        st.rerun()

    st.checkbox(
        "Guardar también AUSENTES (marca 'Ausente' para todos los que no vinieron)",
        key="guardar_ausentes",
        value=False
    )

def page_personas(df_personas, centro, usuario):
    st.subheader("Personas (base del centro)")
    df_centro = personas_for_centro(df_personas, centro).copy()

    # Normalizar columnas si faltan
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

    if solo_activos and "activo" in df_centro.columns:
        df_centro = df_centro[df_centro["activo"].astype(str).str.upper().fillna("") != "NO"]

    st.markdown(f"<span class='badge'>Personas visibles: {len(df_centro)}</span>", unsafe_allow_html=True)
    st.dataframe(df_centro[["nombre","frecuencia","edad","domicilio","notas","activo"]], use_container_width=True)

    st.markdown("### Agregar persona manualmente")
    with st.form("add_person"):
        nombre = st.text_input("Nombre y apellido", placeholder="Ej: Gómez, Ana")
        frecuencia = st.selectbox("Frecuencia", ["Diaria","Semanal","Mensual","No asiste","Nueva"], index=4)
        edad = st.text_input("Edad (opcional)")
        domicilio = st.text_input("Domicilio (opcional)")
        notas = st.text_area("Notas (opcional)")
        activo = st.selectbox("Activo", ["SI","NO"], index=0)
        ok = st.form_submit_button("Guardar persona")

    if ok:
        nombre = nombre.strip()
        if not nombre:
            st.error("Falta el nombre.")
            st.stop()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "nombre": nombre,
            "frecuencia": frecuencia,
            "centro": centro,
            "edad": edad.strip(),
            "domicilio": domicilio.strip(),
            "notas": notas.strip(),
            "activo": activo,
            "timestamp": now,
            "usuario": usuario,
        }
        append_ws_rows(PERSONAS_TAB, PERSONAS_COLS, [[row.get(c, "") for c in PERSONAS_COLS]])
        st.success("✅ Persona guardada.")
        st.rerun()

def page_reportes(df_asistencia, centro):
    st.subheader("Reportes (este centro)")
    df_latest = latest_asistencia(df_asistencia)
    if df_latest.empty:
        st.info("Todavía no hay registros.")
        return

    anio = st.selectbox("Año", sorted(df_latest["anio"].astype(str).unique()), index=len(sorted(df_latest["anio"].astype(str).unique()))-1)
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
    serie = serie.set_index("fecha")["presentes_i"]
    st.line_chart(serie)

    st.markdown("### Por espacio (Maranatha) / General")
    esp = df_c.groupby("espacio", as_index=False)["presentes_i"].sum().sort_values("presentes_i", ascending=False)
    st.bar_chart(esp.set_index("espacio")["presentes_i"])

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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='kpi'><h3>Total año (global)</h3><div class='v'>{int(d['presentes_i'].sum())}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='kpi'><h3>Centros con registros</h3><div class='v'>{d['centro'].nunique()}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='kpi'><h3>Días registrados</h3><div class='v'>{d['fecha'].nunique()}</div></div>", unsafe_allow_html=True)

    st.markdown("### Por centro (acumulado)")
    por = d.groupby("centro", as_index=False)["presentes_i"].sum().sort_values("presentes_i", ascending=False)
    st.bar_chart(por.set_index("centro")["presentes_i"])

    st.markdown("### Evolución global (por día)")
    dia = d.groupby("fecha", as_index=False)["presentes_i"].sum().sort_values("fecha")
    st.line_chart(dia.set_index("fecha")["presentes_i"])

    st.markdown("### Base (últimos 50 registros)")
    st.dataframe(d.sort_values("timestamp", ascending=False)[["fecha","centro","espacio","presentes","coordinador","modo","timestamp"]].head(50), use_container_width=True)

def page_admin_tools():
    st.subheader("Herramientas (reparación)")
    st.warning("Usá esto solo si tu sheet quedó con columnas corridas o sin encabezados.")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("Reparar encabezados: asistencia"):
            repair_headers(ASISTENCIA_TAB, ASISTENCIA_COLS)
            st.success("Listo.")
    with colB:
        if st.button("Reparar encabezados: personas"):
            repair_headers(PERSONAS_TAB, PERSONAS_COLS)
            st.success("Listo.")
    with colC:
        if st.button("Reparar encabezados: asistencia_personas"):
            repair_headers(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS)
            st.success("Listo.")

# =========================
# Main
# =========================
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

    # Cargar data desde Sheets
    with st.spinner("Cargando datos desde Google Sheets..."):
        df_asistencia = read_ws_df(ASISTENCIA_TAB, ASISTENCIA_COLS)
        df_personas = read_ws_df(PERSONAS_TAB, PERSONAS_COLS)
        df_asist_personas = read_ws_df(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS)

    # KPIs
    st.caption(f"Estás trabajando sobre: **{centro_asignado}** — 👤 **{nombre_visible}**")
    kpi_row(latest_asistencia(df_asistencia), centro_asignado)

    tabs = st.tabs(["🧾 Registrar asistencia", "👥 Personas", "📊 Reportes / Base", "🌍 Global", "🛠️ Herramientas"])

    with tabs[0]:
        page_registrar_asistencia(df_personas, df_asistencia, df_asist_personas, centro_asignado, nombre_visible, usuario)

    with tabs[1]:
        page_personas(df_personas, centro_asignado, usuario)

    with tabs[2]:
        page_reportes(df_asistencia, centro_asignado)

    with tabs[3]:
        page_global(df_asistencia)

    with tabs[4]:
        page_admin_tools()

if __name__ == "__main__":
    main()
