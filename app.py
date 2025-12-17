import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError
import time
import pytz
import io
import unicodedata

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
def normalize_private_key(pk: str) -> str:
    if not isinstance(pk, str): return pk
    if "\\n" in pk: pk = pk.replace("\\n", "\n")
    return pk

def clean_string(s):
    if not isinstance(s, str): return ""
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.strip().upper()

# =========================
# Google Sheets connection
# =========================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    sa = {
        "type": "service_account",
        "project_id": "hogar-de-cristo-asistencia",
        "private_key_id": "cb7af14255a324107d2d2119a4f95d4348ed5b90",
        "private_key": """-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDA6M0EIfQYCvZ/\n2cF1j9knWNLM1nGE0nohznJz8C9XsIJYZyPNXruD/y0cjdiQWyNopjzx3o15hoy2\ncRQOHDBgQA2alX9r7xd7rWvazwOTsgkNpRQVk0+wlOFUZdg79vQe9cn42JB71I0b\n0qsSLaeW35n3c8RFAzcv0XVmUdkRm76lU8pNhBKWOv3/DJJ2wB8VMW4l9Iq7MKyL\ng5t6d7qMPVckc3kGBsq/N+mPiisRjsPLgyvP3IHRzddIvcKiW9JpzNZoSqvOwpha\n2o+eMHuPHcJKev1JcJcU72CO1djfwwGM4L4ioRVVuE4w2EfCNdshSQC8Ht14alL3\ngQ6DMugNAgMBAAECggEAF1x562yzMzAsrsnvkC2V5hpvGMhFYgjdKnfmS10EVrG0\n70C6SLYWrkL6MxGIbt7imFs9WSsS5esh4jwqahUG1LkdDKHbFvaS2PLk81ALhljS\nmNjraDt5NJCrAv38ZDKhWJh6V4zeXmicmAh4mBB4UaCNdDaMR7E+fyd1+KijyWpl\noRqGUdpyEHoKCaXbPKQoGC9lGNs7xB7MGjPGi2pMz6O78oDTE1Obocqxk6sZYjrQ\nCH0jKwqTSosxlAb40hOFlGUUpDW7DF03trH0D9w2vNJTN/PqVJNOp5X7VKf2GTcg\n44ivcaEH2ZZF8hHIn9uDjWglVUFNJEwBGfEBmfVcQQKBgQDkkZzYG9czVslP+OHY\nANFQHAJ1tyEQ69O4YF8RZVLU6+QTIv8GplObaapVa1cAXPp0kMrU/bzUUKs38gZG\n8PQXYYpkCv/iceHqyLSm8KsvtKRSwXBwlzI5sn9XjSE1qAQsfg68LKikK3DswGjB\nc6qnsrm4fhnj1vU/ffsa7Xo5LQKBgQDYD5z3YATFvF5LHv3Ihj3gZZBoJMFss+EA\nt1TVt4KHaI94F224Bp52NDS3sScumQa+01WAaMBmGhPkw0G0hszQ428i5G7TCVuz\nM89Xb1aaQCSyopFKP8dVJYSJXXbwj+Cyno0DQc4jkcjSsfj2GgbG1BAjJqlnUGzr\nKAqBm/r2YQKBgDZZ6dH5zNKIcJZzuECE8UD7aBpV0acUbOQLBpA8Z9X5weJLEBmk\ns3zhQ3/MZoPPmD7fr1u2epCCHjTPeG6mHWTx7NadRvux2ObbkxmfYRWW/vwuw24C\nhg7yQxWumZcIvPVXhGl6tR9UtSWXG1HlD0+RUFhuo/lpxCe07WEZ11aBAoGBANFp\nUJnzVqzQhhQJVbClbBOyXOSTu2XAcrRe/Lqnwru7fFLJYm6a+7tVnkLsUS244/DQ\npG5xGQnc/KsdFPIENT/BMFaBUWj6CQcHkE8OesHGqcr6BhgQ+QJt+qepDz7aNM7r\nHYGqpkGTazHLjaH6V9cecwWe01JvgSHrDUPSCswBAoGAZgc8T9KvJ5r5sZQC/SkN\nSLzLT47WGr57f+WAT2CiaHhBRV2kwInNcsljsHCi1viFyQO/YDCWVEvozTjh6BoF\nrt4XiT6vnkKojyyG5uKBu+WHmXyaSH0aHj8ZCZl/C0Ab8MMAUVJg5zZHWyrztQAJ\nRx/AQ42L3AHtN6gVhU0zvVU=\n-----END PRIVATE KEY-----\n""",
        "client_email": "hogar-asistencia-bot@hogar-de-cristo-asistencia.iam.gserviceaccount.com",
        "client_id": "101282710856404935805",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/hogar-asistencia-bot%40hogar-de-cristo-asistencia.iam.gserviceaccount.com"
    }
    sa["private_key"] = normalize_private_key(sa.get("private_key", ""))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    sid = "1nCK2Q2ddxUO-erDwa5jgfGsUYsjZD7e4doHXoQ4N9zg"
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
        centro_clean = clean_string(centro)
        df_temp = df_personas.copy()
        df_temp['centro_norm'] = df_temp['centro'].apply(clean_string)
        return df_temp[df_temp['centro_norm'] == centro_clean].copy()
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
        cn1, cn2 = st.columns(2)
        nueva = cn1.text_input("Nombre completo")
        dni_new = cn2.text_input("DNI (Opcional)")
        cn3, cn4 = st.columns(2)
        tel_new = cn3.text_input("Tel (Opcional)")
        # ✅ AQUÍ AGREGUÉ EL CAMPO DE NACIMIENTO
        nac_new = cn4.text_input("Fecha Nac. (DD/MM/AAAA) (Opcional)")
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
            # ✅ PASAMOS TAMBIÉN LA FECHA DE NACIMIENTO
            df_personas = upsert_persona(df_personas, nueva, centro, usuario, frecuencia="Nueva", dni=dni_new, telefono=tel_new, fecha_nacimiento=nac_new)
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
    st.subheader("👥 Legajo Digital y Listado")
    
    df_centro = personas_for_centro(df_personas, centro)
    df_centro = df_centro.sort_values("timestamp", ascending=True).groupby("nombre").tail(1)
    
    nombres = sorted(df_centro["nombre"].unique())

    col_sel, col_act = st.columns([3, 1])
    seleccion = col_sel.selectbox("Seleccionar Persona (Dejar vacío para ver listado completo)", [""] + nombres)
    
    if not seleccion:
        st.markdown(f"### Listado Histórico de personas que pasaron por {centro}")
        
        col_filtro1, col_filtro2 = st.columns(2)
        filtro_txt = col_filtro1.text_input("🔍 Buscar por nombre")
        solo_activos = col_filtro2.checkbox("Solo activos", value=False)
        
        df_show = df_centro.copy()
        
        if filtro_txt:
            df_show = df_show[df_show["nombre"].str.contains(filtro_txt, case=False, na=False)]
        if solo_activos:
            df_show = df_show[df_show["activo"].str.upper() == "SI"]
            
        df_show = df_show.sort_values("nombre", ascending=True)

        m1, m2 = st.columns(2)
        m1.metric("Total Personas Históricas", len(df_centro))
        m2.metric("Personas Listadas Ahora", len(df_show))

        cols_to_show = ["nombre", "frecuencia", "telefono", "dni", "fecha_nacimiento", "activo"]
        for c in cols_to_show:
            if c not in df_show.columns: df_show[c] = ""
            
        st.dataframe(
            df_show[cols_to_show], 
            use_container_width=True,
            hide_index=True,
            column_config={
                "nombre": "Nombre y Apellido",
                "frecuencia": st.column_config.TextColumn("Frecuencia", help="Diaria, Semanal, etc."),
                "fecha_nacimiento": "Fecha Nac.",
                "activo": st.column_config.TextColumn("Estado", width="small")
            }
        )
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    st.markdown(f"## 👤 {seleccion}")
    c_info, c_bitacora = st.columns([1, 2])
    
    with c_info:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("#### Datos Personales")
        with st.form("edit_persona"):
            dni = st.text_input("DNI", value=datos_persona.get("dni", ""))
            tel = st.text_input("Teléfono", value=datos_persona.get("telefono", ""))
            # ✅ CAMPO DE FECHA DE NACIMIENTO EN EL PERFIL
            nac = st.text_input("Fecha Nac. (DD/MM/AAAA)", value=datos_persona.get("fecha_nacimiento", ""))
            dom = st.text_input("Domicilio", value=datos_persona.get("domicilio", ""))
            notas_fija = st.text_area("Notas Fijas", value=datos_persona.get("notas", ""))
            activo_chk = st.checkbox("¿Está Activo?", value=(str(datos_persona.get("activo")).upper() != "NO"))
            
            if st.form_submit_button("💾 Actualizar Datos"):
                nuevo_estado = "SI" if activo_chk else "NO"
                upsert_persona(df_personas, seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija, activo=nuevo_estado)
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
    
    centro_clean = clean_string(centro)
    match_centro = next((c for c in CENTROS if clean_string(c) == centro_clean), None)
    
    if not match_centro:
        st.error(f"Error de Configuración: El centro '{centro}' no coincide con la lista válida. Revisá mayúsculas y acentos en el Excel.")
        if st.button("Salir"):
            st.session_state.clear()
            st.rerun()
        st.stop()
    else:
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
