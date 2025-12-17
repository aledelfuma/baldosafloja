import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError
import time
import pytz
import io

# =========================
# Config UI / Branding
# =========================
PRIMARY = "#004E7B"
SECONDARY = "#63296C"

st.set_page_config(
    page_title="Asistencia — Hogar de Cristo Bahía Blanca",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
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
.profile-card {{
    background-color: rgba(255, 255, 255, 0.05);
    padding: 20px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;
}}
.stTextArea textarea {{
    background-color: rgba(0,0,0,0.2);
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
SEGUIMIENTO_TAB = "seguimiento"

ASISTENCIA_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"]
PERSONAS_COLS = ["nombre", "frecuencia", "centro", "edad", "domicilio", "notas", "activo", "timestamp", "usuario", "dni", "fecha_nacimiento", "telefono"]
ASISTENCIA_PERSONAS_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario", "notas"]
USUARIOS_COLS = ["usuario", "password", "centro", "nombre"]
SEGUIMIENTO_COLS = ["timestamp", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"]

# =========================
# Centros / espacios
# =========================
CENTROS = ["Calle Belén", "Nudo a Nudo", "Casa Maranatha"]
ESPACIOS_MARANATHA = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
DEFAULT_ESPACIO = "General"
CATEGORIAS_SEGUIMIENTO = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# =========================
# Helpers
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
# Google Sheets connection (MODO SEGURO - Lee de Secrets)
# =========================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    # Intenta leer de secrets
    sa = dict(get_secret("gcp_service_account", {}))
    
    if not sa:
        # Fallback de emergencia si falla secrets (pero idealmente usá secrets)
        raise KeyError("Falta configuración [gcp_service_account] en secrets.toml")

    sa["private_key"] = normalize_private_key(sa.get("private_key", ""))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    sid = get_secret("sheets.spreadsheet_id")
    if not sid:
        raise KeyError("Falta [sheets] spreadsheet_id en secrets.toml")
    gc = get_gspread_client()
    return gc.open_by_key(sid)

def _open_ws_strict(sh, title: str):
    return sh.worksheet(title)

def get_or_create_ws(title: str, cols: list):
    sh = get_spreadsheet()
    try: return _open_ws_strict(sh, title)
    except Exception: pass
    try:
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(20, len(cols)))
        ws.update("A1", [cols])
        return ws
    except Exception as e:
        st.error(f"Error pestaña '{title}': {e}")
        st.stop()

def safe_get_all_values(ws, tries=4):
    for i in range(tries):
        try: return ws.get_all_values()
        except APIError: time.sleep(0.5)
        except Exception: time.sleep(0.5)
    st.error("Error leyendo Google Sheets.")
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
# CACHING
# =========================
@st.cache_data(ttl=600, show_spinner=False)
def get_users_db():
    return read_ws_df(USUARIOS_TAB, USUARIOS_COLS)

@st.cache_data(ttl=300, show_spinner="Cargando datos...")
def load_all_data():
    df_a = read_ws_df(ASISTENCIA_TAB, ASISTENCIA_COLS)
    df_p = read_ws_df(PERSONAS_TAB, PERSONAS_COLS)
    df_ap = read_ws_df(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS)
    df_seg = read_ws_df(SEGUIMIENTO_TAB, SEGUIMIENTO_COLS)
    return df_a, df_p, df_ap, df_seg

# =========================
# LOGIC
# =========================
def year_of(fecha_iso: str) -> str:
    try: return str(pd.to_datetime(fecha_iso).year)
    except: return str(get_today_ar().year)

def clean_int(x, default=0):
    try: return int(float(str(x).strip()))
    except: return default

def norm_text(x):
    return str(x).strip() if x else ""

def latest_asistencia(df):
    if df.empty: return df
    df2 = df.copy()
    df2["timestamp_dt"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    df2["k"] = (df2["anio"].astype(str)+"|"+df2["fecha"].astype(str)+"|"+df2["centro"].astype(str)+"|"+df2["espacio"].astype(str))
    return df2.sort_values("timestamp_dt").groupby("k", as_index=False).tail(1)

def last_load_info(df_latest, centro):
    if df_latest.empty: return None, None
    d = df_latest[df_latest["centro"] == centro].copy()
    if d.empty: return None, None
    last = pd.to_datetime(d["fecha"], errors="coerce").max()
    if pd.isna(last): return None, None
    days = (pd.Timestamp(get_today_ar()).date() - last.date()).days
    return last.date().isoformat(), int(days)

# =========================
# WRITES
# =========================
def personas_for_centro(df_personas, centro):
    if df_personas.empty: return df_personas
    if "centro" in df_personas.columns:
        return df_personas[df_personas["centro"] == centro].copy()
    return df_personas.copy()

def upsert_persona(df_personas, nombre, centro, usuario, **kwargs):
    nombre = norm_text(nombre)
    if not nombre: return df_personas
    now = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    row = {c: "" for c in PERSONAS_COLS}
    row.update({"nombre": nombre, "centro": centro, "activo": "SI", "timestamp": now, "usuario": usuario})
    for k, v in kwargs.items():
        if k in PERSONAS_COLS: row[k] = str(v)
    append_ws_rows(PERSONAS_TAB, PERSONAS_COLS, [[row[c] for c in PERSONAS_COLS]])
    return pd.concat([df_personas, pd.DataFrame([row])], ignore_index=True)

def append_asistencia(fecha, centro, espacio, presentes, coordinador, modo, notas, usuario, accion="append"):
    ts = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha), "centro": centro, 
        "espacio": espacio, "presentes": str(presentes), "coordinador": coordinador, 
        "modo": modo, "notas": notas, "usuario": usuario, "accion": accion
    }
    append_ws_rows(ASISTENCIA_TAB, ASISTENCIA_COLS, [[row.get(c, "") for c in ASISTENCIA_COLS]])

def append_asistencia_personas(fecha, centro, espacio, nombre, estado, es_nuevo, coordinador, usuario, notas=""):
    ts = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha), "centro": centro, 
        "espacio": espacio, "nombre": nombre, "estado": estado, "es_nuevo": es_nuevo, 
        "coordinador": coordinador, "usuario": usuario, "notas": notas
    }
    append_ws_rows(ASISTENCIA_PERSONAS_TAB, ASISTENCIA_PERSONAS_COLS, [[row.get(c, "") for c in ASISTENCIA_PERSONAS_COLS]])

def append_seguimiento(fecha, centro, nombre, categoria, observacion, usuario):
    ts = get_now_ar().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "timestamp": ts, "fecha": fecha, "anio": year_of(fecha), "centro": centro,
        "nombre": nombre, "categoria": categoria, "observacion": observacion, "usuario": usuario
    }
    append_ws_rows(SEGUIMIENTO_TAB, SEGUIMIENTO_COLS, [[row.get(c, "") for c in SEGUIMIENTO_COLS]])

# =========================
# UI COMPONENTS
# =========================
def show_login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_hogar.png", width=200)
        except: st.title("Hogar de Cristo")
        st.markdown("### Sistema de Asistencia y Acompañamiento")
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                df_users = get_users_db()
                row = df_users[(df_users["usuario"].astype(str).str.strip()==u.strip()) & (df_users["password"].astype(str).str.strip()==p.strip())]
                if not row.empty:
                    r = row.iloc[0]
                    st.session_state.update({"logged_in": True, "usuario": r["usuario"], "centro_asignado": r["centro"].strip(), "nombre_visible": r["nombre"]})
                    st.rerun()
                else:
                    st.error("Error de credenciales.")
    st.stop()

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

def sidebar_birthdays(df_personas, centro):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎂 Cumpleaños")
    if df_personas.empty: return
    df_c = personas_for_centro(df_personas, centro)
    df_c["timestamp_dt"] = pd.to_datetime(df_c["timestamp"], errors="coerce")
    df_c = df_c.sort_values("timestamp_dt").groupby("nombre").tail(1)
    today = get_today_ar()
    cumples = []
    for _, row in df_c.iterrows():
        fn_str = str(row.get("fecha_nacimiento", "")).strip()
        if not fn_str: continue
        try:
            fn = pd.to_datetime(fn_str, dayfirst=True, errors="coerce")
            if not pd.isna(fn):
                if fn.month == today.month and fn.day == today.day:
                    cumples.append(row["nombre"])
        except: pass
    if cumples:
        st.sidebar.success(f"🎉 ¡Hoy cumple años! \n\n" + "\n".join([f"- {c}" for c in cumples]))
    else:
        st.sidebar.caption("Nadie cumple años hoy.")

def sidebar_alerts(df_ap, centro):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚠️ Alerta: Ausencia")
    if df_ap.empty: return
    d = df_ap[(df_ap["centro"]==centro) & (df_ap["estado"]=="Presente")].copy()
    if d.empty: return
    d["fecha_dt"] = pd.to_datetime(d["fecha"], errors="coerce")
    last = d.groupby("nombre")["fecha_dt"].max().reset_index()
    hoy = pd.Timestamp(get_today_ar())
    last["dias"] = (hoy - last["fecha_dt"]).dt.days
    alertas = last[(last["dias"]>7) & (last["dias"]<60)].sort_values("dias", ascending=False)
    if alertas.empty: st.sidebar.success("Asistencia regular.")
    else:
        st.sidebar.caption("Ausentes > 7 días:")
        for _, r in alertas.iterrows():
            st.sidebar.markdown(f"🔴 **{r['nombre']}**: {r['dias']} días")

# =========================
# PAGES
# =========================
def page_registrar_asistencia(df_personas, df_asistencia, centro, nombre_visible, usuario):
    st.subheader(f"Registrar: {centro}")
    fecha = st.date_input("Fecha", value=get_today_ar()).isoformat()
    espacio = st.selectbox("Espacio", ESPACIOS_MARANATHA) if centro == "Casa Maranatha" else DEFAULT_ESPACIO
    modo = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    notas = st.text_area("Notas generales del día")
    st.markdown("---")

    df_centro = personas_for_centro(df_personas, centro)
    nombres = sorted(list(set([n for n in df_centro["nombre"].astype(str).tolist() if n.strip()])))
    
    c1, c2 = st.columns([3, 1])
    presentes = c1.multiselect("Asistentes", options=nombres)
    total_presentes = c2.number_input("Total", min_value=0, value=len(presentes))
    
    with st.expander("👤 ¿Vino alguien nuevo?"):
        cn1, cn2, cn3 = st.columns([2, 1, 1])
        nueva = cn1.text_input("Nombre completo")
        dni_new = cn2.text_input("DNI (Opcional)")
        tel_new = cn3.text_input("Tel (Opcional)")
        agregar_nueva = st.checkbox("Agregar a la base")

    df_latest = latest_asistencia(df_asistencia)
    ya = df_latest[(df_latest.get("fecha","")==fecha) & (df_latest.get("centro","")==centro) & (df_latest.get("espacio","")==espacio)]
    overwrite = True
    if not ya.empty:
        st.warning("⚠️ Ya existe carga para hoy. Se sobreescribirá.")
        overwrite = st.checkbox("Confirmar", value=False)
    
    if st.button("💾 Guardar Asistencia", type="primary", use_container_width=True):
        if not overwrite: st.error("Confirmá sobreescritura"); st.stop()
        
        if agregar_nueva and nueva.strip():
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, frecuencia="Nueva", dni=dni_new, telefono=tel_new)
            if nueva not in presentes: presentes.append(nueva)
        
        if len(presentes)>0: total_presentes = len(presentes)
        accion = "overwrite" if not ya.empty else "append"
        
        with st.spinner("Guardando..."):
            append_asistencia(fecha, centro, espacio, total_presentes, nombre_visible, modo, notas, usuario, accion)
            for n in presentes:
                append_asistencia_personas(fecha, centro, espacio, n, "Presente", "SI" if (agregar_nueva and n==nueva) else "NO", nombre_visible, usuario)
            ausentes = [n for n in nombres if n not in presentes]
            for n in ausentes:
                append_asistencia_personas(fecha, centro, espacio, n, "Ausente", "NO", nombre_visible, usuario)

        st.toast("✅ Guardado"); time.sleep(1.5); st.cache_data.clear(); st.rerun()

def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.subheader("👥 Legajo Digital")
    df_centro = personas_for_centro(df_personas, centro)
    nombres = sorted(list(set(df_centro["nombre"].dropna().unique())))
    
    col_sel, col_act = st.columns([3, 1])
    seleccion = col_sel.selectbox("Seleccionar Persona", [""] + nombres)
    
    if not seleccion:
        st.info("Seleccioná una persona para ver su ficha completa.")
        st.markdown("### Padrón General")
        st.dataframe(df_centro.sort_values("timestamp", ascending=False).groupby("nombre").head(1)[["nombre","telefono","dni","frecuencia"]], use_container_width=True)
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].sort_values("timestamp", ascending=True).tail(1).iloc[0]
    
    st.markdown(f"## 👤 {seleccion}")
    c_info, c_bitacora = st.columns([1, 2])
    
    with c_info:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("#### Datos Personales")
        with st.form("edit_persona"):
            dni = st.text_input("DNI", value=datos_persona.get("dni", ""))
            tel = st.text_input("Teléfono", value=datos_persona.get("telefono", ""))
            nac = st.text_input("Fecha Nac. (DD/MM/AAAA)", value=datos_persona.get("fecha_nacimiento", ""))
            dom = st.text_input("Domicilio", value=datos_persona.get("domicilio", ""))
            notas_fija = st.text_area("Notas Fijas", value=datos_persona.get("notas", ""))
            if st.form_submit_button("💾 Actualizar Datos"):
                upsert_persona(df_personas, seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija)
                st.toast("Datos actualizados"); st.cache_data.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if not df_ap.empty:
            hist = df_ap[(df_ap["nombre"]==seleccion) & (df_ap["centro"]==centro)]
            presencias = len(hist[hist["estado"]=="Presente"])
            st.metric("Asistencias Totales", presencias)

    with c_bitacora:
        st.markdown("#### 📖 Bitácora de Seguimiento")
        with st.expander("➕ Agregar Nota / Intervención", expanded=False):
            with st.form("new_seg"):
                fecha_seg = st.date_input("Fecha", value=get_today_ar())
                cat = st.selectbox("Tipo", CATEGORIAS_SEGUIMIENTO)
                obs = st.text_area("Detalle de la intervención...")
                if st.form_submit_button("Guardar en Bitácora"):
                    append_seguimiento(str(fecha_seg), centro, seleccion, cat, obs, usuario)
                    st.toast("Nota guardada"); st.cache_data.clear(); st.rerun()
        
        if not df_seg.empty:
            mis_notas = df_seg[(df_seg["nombre"]==seleccion) & (df_seg["centro"]==centro)].copy()
            if not mis_notas.empty:
                mis_notas["fecha_dt"] = pd.to_datetime(mis_notas["fecha"], errors="coerce")
                mis_notas = mis_notas.sort_values("fecha_dt", ascending=False)
                for _, note in mis_notas.iterrows():
                    icon = "🩺" if "Salud" in note["categoria"] else "📝"
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:5px; margin-bottom:10px; border-left: 3px solid {SECONDARY}">
                        <small>{note['fecha']} | <b>{note['categoria']}</b> ({note['usuario']})</small><br>
                        {icon} {note['observacion']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No hay notas registradas aún.")

def page_reportes(df_asistencia, centro):
    st.subheader("Reportes")
    df_latest = latest_asistencia(df_asistencia)
    df_c = df_latest[df_latest["centro"] == centro].copy()
    if df_c.empty: st.info("Sin datos."); return
    
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"])
    df_c["presentes_i"] = df_c["presentes"].apply(lambda x: clean_int(x, 0))
    df_c = df_c.sort_values("fecha_dt")
    
    c1, c2 = st.columns([3,1])
    c1.line_chart(df_c.set_index("fecha")["presentes_i"])
    with c2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_c.to_excel(writer, sheet_name='Asistencia', index=False)
        st.download_button("📥 Descargar Excel", buffer, f"asistencia_{centro}.xlsx", "application/vnd.ms-excel")
    st.dataframe(df_c[["fecha", "espacio", "presentes", "coordinador", "notas"]].sort_values("fecha", ascending=False), use_container_width=True)

def page_global(df_asistencia, df_ap):
    st.subheader("Panorama Global")
    df = latest_asistencia(df_asistencia).copy()
    if df.empty: return
    df["presentes_i"] = df["presentes"].apply(lambda x: clean_int(x, 0))
    anio = str(get_today_ar().year)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Asistencias {anio}**")
        st.bar_chart(df[df["anio"].astype(str)==anio].groupby("centro")["presentes_i"].sum())
    with c2:
        st.markdown("**Nuevos Ingresos**")
        if not df_ap.empty:
            nuevos = df_ap[(df_ap["es_nuevo"]=="SI") & (df_ap["anio"].astype(str)==anio)]
            if not nuevos.empty: st.bar_chart(nuevos.groupby("centro").size(), color="#63296C")
            else: st.info("Sin nuevos ingresos.")

# =========================
# MAIN
# =========================
def main():
    if not st.session_state.get("logged_in"): show_login_screen()
    
    u = st.session_state["usuario"]
    centro = st.session_state["centro_asignado"]
    nombre = st.session_state["nombre_visible"]
    
    match_centro = next((c for c in CENTROS if c.lower() == centro.lower()), None)
    if not match_centro: st.error(f"Centro '{centro}' no válido."); st.stop()
    centro = match_centro

    st.sidebar.image("logo_hogar.png", width=120)
    st.sidebar.markdown(f"Hola, **{nombre}**")
    st.sidebar.caption(f"📍 {centro}")
    if st.sidebar.button("Salir"): st.session_state.clear(); st.cache_data.clear(); st.rerun()
    if st.sidebar.button("🔄 Refrescar"): st.cache_data.clear(); st.rerun()

    df_asistencia, df_personas, df_ap, df_seg = load_all_data()

    kpi_row(latest_asistencia(df_asistencia), centro)
    sidebar_pending(latest_asistencia(df_asistencia), centro)
    sidebar_birthdays(df_personas, centro)
    sidebar_alerts(df_ap, centro)

    t1, t2, t3, t4 = st.tabs(["📝 Asistencia", "👥 Legajo Digital", "📈 Reportes", "🌍 Global"])
    with t1: page_registrar_asistencia(df_personas, df_asistencia, centro, nombre, u)
    with t2: page_personas_full(df_personas, df_ap, df_seg, centro, u)
    with t3: page_reportes(df_asistencia, centro)
    with t4: page_global(df_asistencia, df_ap)

if __name__ == "__main__":
    main()
