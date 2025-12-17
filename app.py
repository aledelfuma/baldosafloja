import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError
import time
import pytz
import io # Para la descarga de Excel

# =========================
# Config UI / Branding
# =========================
PRIMARY = "#004E7B"
SECONDARY = "#63296C"

st.set_page_config(
    page_title="Asistencia — Hogar de Cristo Bahía Blanca",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed", # Colapsado al inicio para limpiar el login
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
/* Estilo para el Login Centralizado */
.login-container {{
    border: 1px solid rgba(255,255,255,0.1);
    padding: 2rem;
    border-radius: 10px;
    background-color: rgba(255,255,255,0.05);
    text-align: center;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================
# Zona Horaria (Argentina)
# =========================
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')

def get_now_ar():
    return datetime.now(TZ_AR)

def get_today_ar():
    return datetime.now(TZ_AR).date()

# =========================
# Sheets schema
# =========================
ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
ASISTENCIA_PERSONAS_TAB = "asistencia_personas"
USUARIOS_TAB = "config_usuarios"

ASISTENCIA_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"]
PERSONAS_COLS = ["nombre", "frecuencia", "centro", "edad", "domicilio", "notas", "activo", "timestamp", "usuario"]
ASISTENCIA_PERSONAS_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario", "notas"]
USUARIOS_COLS = ["usuario", "password", "centro", "nombre"]

# =========================
# Centros / espacios
# =========================
# IMPORTANTE: Deben coincidir EXACTAMENTE con lo que escribas en el Excel
CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]

ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
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
    if not isinstance(pk, str): return pk
    if "\\n" in pk: pk = pk.replace("\\n", "\n")
    return pk

# =========================
# Google Sheets connection
# =========================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    sa = dict(get_secret("gcp_service_account", {}))
    if not sa:
        raise KeyError("Falta [gcp_service_account] en secrets.toml")
    sa["private_key"] = normalize_private_key(sa.get("private_key", ""))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    sid = get_secret("sheets.spreadsheet_id", "")
    if not sid: raise KeyError("Falta [sheets].spreadsheet_id en secrets.toml")
    gc = get_gspread_client()
    return gc.open_by_key(sid)

def _open_ws_strict(sh, title: str):
    return sh.worksheet(title)

def get_or_create_ws(title: str, cols: list, rows: int = 2000):
    sh = get_spreadsheet()
    try: return _open_ws_strict(sh, title)
    except Exception: pass
    try:
        ws = sh.add_worksheet(title=title, rows=rows, cols=max(20, len(cols)))
        ws.update("A1", [cols])
        return ws
    except Exception as e:
        st.error(f"Error pestaña '{title}': {e}")
        st.stop()

def safe_get_all_values(ws, tries=4):
    for i in range(tries):
        try: return ws.get_all_values()
        except APIError as e: time.sleep(2 ** i * 0.5)
        except Exception: time.sleep(2 ** i * 0.5)
    st.error("Error leyendo Google Sheets (Timeout/Quota).")
    st.stop()

def read_ws_df(title: str, cols: list) -> pd.DataFrame:
    ws = get_or_create_ws(title, cols)
    values = safe_get_all_values(ws)
    if not values:
        ws.update("A1", [cols])
        return pd.DataFrame(columns=cols)
    header = values[0]
    body = values[1:] if len(values) > 1 else []
    df = pd.DataFrame(body)
    if not df.empty:
        df = df.iloc[:, :len(header)]
        df.columns = header
    else:
        df = pd.DataFrame(columns=header)
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df[cols]

def append_ws_rows(title: str, cols: list, rows: list[list]):
    ws = get_or_create_ws(title, cols)
    first = safe_get_all_values(ws)[:1]
    if not first or first[0][: len(cols)] != cols: ws.update("A1", [cols])
    ws.append_rows(rows, value_input_option="USER_ENTERED")

# =========================
# CACHING & LOADERS
# =========================
@st.cache_data(ttl=600, show_spinner="Cargando usuarios...")
def get_users_db():
    return read_ws_df(USUARIOS_TAB, USUARIOS_COLS)

@st.cache_data(ttl=600, show_spinner="Actualizando datos...")
def load_all_data():
    df_a = read_ws_df(ASISTENCIA_TAB, ASISTENCIA_COLS)
    df_p = read_ws_df(PERSONAS_TAB, PERSONAS_COLS)
    df_ap = read_ws_df(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS)
    return df_a, df_p, df_ap

# =========================
# UTILS & HELPERS
# =========================
def year_of(fecha_iso: str) -> str:
    try: return str(pd.to_datetime(fecha_iso).year)
    except: return str(get_today_ar().year)

def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default

def norm_text(x):
    if x is None: return ""
    return str(x).strip()

def latest_asistencia(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    df2["k"] = (df2["anio"].astype(str) + "|" + df2["fecha"].astype(str) + "|" +
                df2["centro"].astype(str) + "|" + df2["espacio"].astype(str))
    df2 = df2.sort_values("timestamp_dt", ascending=True)
    df2 = df2.groupby("k", as_index=False).tail(1)
    return df2

def last_load_info(df_latest: pd.DataFrame, centro: str):
    if df_latest.empty: return None, None
    d = df_latest[df_latest["centro"] == centro].copy()
    if d.empty: return None, None
    d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    last = d["fecha_dt"].max()
    if pd.isna(last): return None, None
    days = (pd.Timestamp(get_today_ar()).date() - last.date()).days
    return last.date().isoformat(), int(days)

# =========================
# WRITE FUNCTIONS
# =========================
def personas_for_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    if "centro" in df_personas.columns:
        return df_personas[df_personas["centro"] == centro].copy()
    return df_personas.copy()

def upsert_persona(df_personas, nombre, centro, usuario, frecuencia="Nueva"):
    nombre = norm_text(nombre)
    if not nombre: return df_personas
    now = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    if not df_personas.empty:
        mask = (df_personas.get("nombre", "") == nombre) & (df_personas.get("centro", "") == centro)
        if mask.any(): return df_personas
    row = {c: "" for c in PERSONAS_COLS}
    row.update({"nombre": nombre, "frecuencia": frecuencia, "centro": centro, 
                "activo": "SI", "timestamp": now, "usuario": usuario})
    append_ws_rows(PERSONAS_TAB, PERSONAS_COLS, [[row[c] for c in PERSONAS_COLS]])
    return pd.concat([df_personas, pd.DataFrame([row])], ignore_index=True)

def append_asistencia(fecha, centro, espacio, presentes, coordinador, modo, notas, usuario, accion="append"):
    ts = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha),
        "centro": centro, "espacio": espacio, "presentes": str(presentes),
        "coordinador": coordinador, "modo": modo, "notas": notas,
        "usuario": usuario, "accion": accion
    }
    append_ws_rows(ASISTENCIA_TAB, ASISTENCIA_COLS, [[row.get(c, "") for c in ASISTENCIA_COLS]])

def append_asistencia_personas(fecha, centro, espacio, nombre, estado, es_nuevo, coordinador, usuario, notas=""):
    ts = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha),
        "centro": centro, "espacio": espacio, "nombre": nombre,
        "estado": estado, "es_nuevo": es_nuevo, "coordinador": coordinador,
        "usuario": usuario, "notas": notas
    }
    append_ws_rows(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS, [[row.get(c, "") for c in ASISTENCIA_PERSONAS_COLS]])

# =========================
# ✅ LOGIN CENTRALIZADO
# =========================
def show_login_screen():
    # Creamos columnas para centrar el contenido
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True) # Espacio arriba
        
        # LOGO DEL HOGAR
        try:
            st.image("logo_hogar.png", width=200) # Ajustar el ancho según el logo
        except Exception:
            st.warning("Falta el archivo 'logo_hogar.png' en la carpeta.")
            st.title("Hogar de Cristo") # Fallback si no está el logo

        st.markdown("### Sistema de Asistencia")
        st.markdown("Ingresá tus credenciales para continuar.")
        
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submitted:
                df_users = get_users_db()
                user_row = df_users[
                    (df_users["usuario"].astype(str).str.strip() == u.strip()) & 
                    (df_users["password"].astype(str).str.strip() == p.strip())
                ]
                
                if not user_row.empty:
                    row = user_row.iloc[0]
                    st.session_state["logged_in"] = True
                    st.session_state["usuario"] = row["usuario"]
                    # Normalizamos el centro para evitar errores de mayúsculas/acentos
                    st.session_state["centro_asignado"] = row["centro"].strip() 
                    st.session_state["nombre_visible"] = row["nombre"]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    
    # Detener la ejecución si no está logueado para que no cargue el resto de la app
    st.stop()

# =========================
# UI BLOCKS & PAGES
# =========================
def sidebar_alerts(df_ap: pd.DataFrame, centro: str):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚠️ Alerta: Sin asistencia")
    if df_ap.empty: return
    
    d = df_ap[(df_ap["centro"] == centro) & (df_ap["estado"] == "Presente")].copy()
    if d.empty: return
    
    d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    last_seen = d.groupby("nombre")["fecha_dt"].max().reset_index()
    hoy = pd.Timestamp(get_today_ar())
    last_seen["dias"] = (hoy - last_seen["fecha_dt"]).dt.days
    
    alertas = last_seen[(last_seen["dias"] > 7) & (last_seen["dias"] < 60)].sort_values("dias", ascending=False)
    
    if alertas.empty:
        st.sidebar.success("👏 Asistencia regular.")
    else:
        st.sidebar.caption(f"Personas ausentes > 7 días:")
        for _, r in alertas.iterrows():
            st.sidebar.markdown(f"🔴 **{r['nombre']}**: hace {r['dias']} días")

def kpi_row(df_latest, centro):
    hoy_date = get_today_ar()
    hoy = hoy_date.isoformat()
    week_ago = (hoy_date - timedelta(days=6)).isoformat()
    month_start = hoy_date.replace(day=1).isoformat()
    d = df_latest.copy()
    if d.empty: c1 = c2 = c3 = 0
    else:
        d["presentes_i"] = d.get("presentes", "").apply(lambda x: clean_int(x, 0))
        c1 = int(d[(d["centro"] == centro) & (d["fecha"] == hoy)]["presentes_i"].sum())
        c2 = int(d[(d["centro"] == centro) & (d["fecha"] >= week_ago) & (d["fecha"] <= hoy)]["presentes_i"].sum())
        c3 = int(d[(d["centro"] == centro) & (d["fecha"] >= month_start) & (d["fecha"] <= hoy)]["presentes_i"].sum())
    
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='kpi'><h3>Ingresos HOY</h3><div class='v'>{c1}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi'><h3>Últimos 7 días</h3><div class='v'>{c2}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi'><h3>Este mes</h3><div class='v'>{c3}</div></div>", unsafe_allow_html=True)

def sidebar_pending(df_latest, centro):
    last_date, days = last_load_info(df_latest, centro)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Estado de Carga")
    if last_date is None:
        st.sidebar.warning("⚠️ Sin cargas previas.")
        return
    if days == 0:
        st.sidebar.success("✅ Ya se cargó hoy.")
    else:
        st.sidebar.warning(f"⏰ Última carga: {last_date} (hace {days} días)")

# --- PÁGINAS ---
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.subheader(f"Registrar: {centro}")
    fecha = st.date_input("Fecha", value=get_today_ar()).isoformat()
    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA, index=ESPACIOS_MARANATHA.index("General"))
    else:
        espacio = DEFAULT_ESPACIO
    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"], index=0)
    notas = st.text_area("Notas del día", placeholder="Ocurrencias, visitas, faltantes...")
    st.markdown("---")
    
    df_centro = personas_for_centro(df_personas, centro)
    nombres = sorted([n for n in df_centro["nombre"].astype(str).tolist() if n.strip()])
    
    c1, c2 = st.columns([3, 1])
    with c1:
        presentes = st.multiselect("Asistentes hoy", options=nombres, default=[])
    with c2:
        total_presentes = st.number_input("Total (manual)", min_value=0, value=len(presentes), step=1)
    
    with st.expander("👤 ¿Vino alguien nuevo?"):
        col_new1, col_new2 = st.columns([3, 1])
        nueva = col_new1.text_input("Nombre completo")
        agregar_nueva = col_new2.checkbox("Es nuevo/a")
    
    df_latest = latest_asistencia(df_asistencia)
    ya = df_latest[(df_latest.get("fecha","")==fecha) & (df_latest.get("centro","")==centro) & (df_latest.get("espacio","")==espacio)]
    existe = not ya.empty
    overwrite = True
    if existe:
        st.warning("⚠️ Ya existe una carga para hoy/espacio. Se sobreescribirá.")
        overwrite = st.checkbox("Confirmar sobreescritura", value=False)
    
    guardar_ausentes = st.checkbox("Guardar Ausentes", value=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("💾 Guardar Asistencia", type="primary", use_container_width=True):
        if not overwrite:
            st.error("Confirmá la sobreescritura.")
            st.stop()
        if agregar_nueva and nueva.strip():
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, "Nueva")
            if nueva not in presentes: presentes.append(nueva)
        if len(presentes) > 0: total_presentes = len(presentes)
        accion = "overwrite" if existe else "append"
        
        with st.spinner("Guardando..."):
            append_asistencia(fecha, centro, espacio, total_presentes, nombre_visible, modo, notas, usuario, accion)
            for n in presentes:
                append_asistencia_personas(fecha, centro, espacio, n, "Presente", "SI" if (agregar_nueva and n==nueva) else "NO", nombre_visible, usuario)
            if guardar_ausentes:
                ausentes = [n for n in nombres if n not in presentes]
                for n in ausentes:
                    append_asistencia_personas(fecha, centro, espacio, n, "Ausente", "NO", nombre_visible, usuario)

        st.toast("✅ Guardado exitoso!")
        time.sleep(1.5)
        st.cache_data.clear()
        st.rerun()

def page_personas(df_personas, centro, usuario):
    st.subheader("Base de Personas")
    df_centro = personas_for_centro(df_personas, centro)
    c1, c2 = st.columns([2, 1])
    q = c1.text_input("🔍 Buscar persona")
    activos = c2.checkbox("Ocultar inactivos", value=True)
    if q: df_centro = df_centro[df_centro["nombre"].str.contains(q, case=False, na=False)]
    if activos: df_centro = df_centro[df_centro["activo"].astype(str).str.upper() != "NO"]
    st.dataframe(df_centro[["nombre", "frecuencia", "edad", "notas", "activo"]], use_container_width=True)

def page_reportes(df_asistencia, centro):
    st.subheader("Reportes")
    df_latest = latest_asistencia(df_asistencia)
    df_c = df_latest[df_latest["centro"] == centro].copy()
    
    if df_c.empty:
        st.info("Sin datos.")
        return
    
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"])
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c = df_c.sort_values("fecha_dt")
    
    # ✅ NUEVO: Botón de descarga de Excel
    col_dl1, col_dl2 = st.columns([3,1])
    with col_dl1:
        st.line_chart(df_c.set_index("fecha")["presentes_i"])
    with col_dl2:
        st.markdown("### Exportar")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_c.to_excel(writer, sheet_name='Asistencia', index=False)
        st.download_button(
            label="📥 Descargar Excel",
            data=buffer,
            file_name=f"asistencia_{centro.replace(' ', '_')}.xlsx",
            mime="application/vnd.ms-excel"
        )
    
    st.dataframe(df_c[["fecha", "espacio", "presentes", "coordinador", "notas"]].sort_values("fecha", ascending=False), use_container_width=True)

def page_global(df_asistencia, df_ap):
    st.subheader("Panorama Global")
    df = latest_asistencia(df_asistencia).copy()
    if df.empty: return
    df["presentes_i"] = df["presentes"].apply(lambda x: clean_int(x, 0))
    anio = str(get_today_ar().year)
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown(f"**Asistencias Totales {anio} (Por Centro)**")
        d = df[df["anio"].astype(str) == anio]
        st.bar_chart(d.groupby("centro")["presentes_i"].sum())

    # ✅ NUEVO: Gráfico de Nuevos vs Recurrentes
    with col_g2:
        st.markdown("**Nuevos Ingresos**")
        if not df_ap.empty:
            nuevos = df_ap[(df_ap["es_nuevo"] == "SI") & (df_ap["anio"].astype(str) == anio)]
            if not nuevos.empty:
                por_centro = nuevos.groupby("centro").size()
                st.bar_chart(por_centro, color="#63296C") # Color secundario
            else:
                st.info("No se registraron nuevos ingresos este año.")

# =========================
# MAIN APP
# =========================
def main():
    # 1. Chequear estado de login. Si no está, mostrar pantalla Login y frenar.
    if not st.session_state.get("logged_in"):
        show_login_screen()

    # 2. Si pasa, cargamos la UI principal
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]

    # Validación de Centro (ahora menos propensa a errores por mayúsculas)
    # Buscamos coincidencias "flexibles"
    match_centro = next((c for c in CENTROS if c.lower() == centro.lower()), None)
    
    if not match_centro:
        st.error(f"Error de Configuración: El centro '{centro}' asignado a tu usuario no coincide con la lista válida del sistema. Revisá mayúsculas y acentos en el Excel.")
        if st.button("Salir"):
            st.session_state.clear()
            st.rerun()
        st.stop()
    else:
        centro = match_centro # Usamos el nombre oficial (bien escrito)

    # SIDEBAR
    st.sidebar.image("logo_hogar.png", width=120) # Logo en sidebar también queda bien
    st.sidebar.markdown(f"Hola, **{nombre}**")
    st.sidebar.caption(f"📍 {centro}")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()
        
    if st.sidebar.button("🔄 Refrescar Datos"):
        st.cache_data.clear()
        st.rerun()

    # CARGA DE DATOS
    df_asistencia, df_personas, df_ap = load_all_data()

    # DASHBOARD
    kpi_row(latest_asistencia(df_asistencia), centro)
    
    sidebar_pending(latest_asistencia(df_asistencia), centro)
    sidebar_alerts(df_ap, centro)

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Asistencia", "👥 Personas", "📈 Reportes", "🌍 Global"])
    
    with tab1:
        page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
    with tab2:
        page_personas(df_personas, centro, u)
    with tab3:
        page_reportes(df_asistencia, centro)
    with tab4:
        page_global(df_asistencia, df_ap)

if __name__ == "__main__":
    main()
