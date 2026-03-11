import streamlit as st, pandas as pd, time, pytz, io, unicodedata, re
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
import gspread

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Baldosa Floja", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

CSS = """<style>
:root {--primary:#60A5FA;--secondary:#A78BFA;--background:#121212;--surface:#1E1E1E;--text-primary:#FFFFFF;--text-secondary:#AAAAAA;--radius-sm:12px;--radius-lg:18px;}
header[data-testid="stHeader"],#MainMenu,footer,.viewerBadge_container,[data-testid="stToolbar"],[data-testid="stAppDeployButton"],.stDeployButton {display: none !important;}
.stApp {background-color: var(--background) !important; font-family: 'Inter', -apple-system, sans-serif !important; color: var(--text-primary) !important;}
.block-container {padding: 1rem 0.8rem 120px 0.8rem !important; max-width: 650px !important; margin: 0 auto; overflow-x: hidden;}
.stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {color: var(--text-primary) !important;}
.top-bar {background-color: var(--surface); padding: 15px 20px; border-radius: var(--radius-lg); margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;}
div.user-info {font-size: 1.2rem; font-weight: 700; line-height: 1.2;} div.center-info {font-size: 0.85rem; font-weight: 600; color: var(--text-secondary) !important; margin-top: 2px;}
.stButton>button {background-color: var(--primary); color: #000000 !important; border-radius: var(--radius-sm); border: none; font-weight: 800; padding: 0.7rem 1rem; transition: 0.2s; width: 100%;}
.stButton>button:active {transform: scale(0.98);}
.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stMultiSelect>div>div>div {border-radius: var(--radius-sm) !important; border: 1px solid rgba(255,255,255,0.1) !important; background-color: #1A1A1A !important; color: var(--text-primary) !important; padding: 0.6rem;}
.streamlit-expanderHeader {color: var(--text-primary) !important; background-color: var(--surface); border-radius: var(--radius-sm);}
.kpi {border-radius: var(--radius-lg); padding: 15px; background: var(--surface); border: 1px solid rgba(255,255,255,0.05); text-align: center; height: 100%;}
.kpi h3 {margin: 0; font-size: 0.65rem; color: var(--text-secondary) !important; text-transform: uppercase; letter-spacing: 0.5px;} .kpi .v {font-size: 2rem; font-weight: 800; color: var(--primary) !important; line-height: 1; margin-top: 5px;}
.alert-box {padding: 12px 15px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 0.9rem; font-weight: 600;} .alert-danger {background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.3);} .alert-success {background-color: rgba(34, 197, 94, 0.15); color: #86EFAC !important; border: 1px solid rgba(34, 197, 94, 0.3);} .alert-gray {background-color: var(--surface); color: var(--text-secondary) !important; border: 1px solid rgba(255,255,255,0.05);}
.id-card {background: linear-gradient(135deg, #004E7B 0%, #63296C 100%); border-radius: 20px; padding: 25px; color: white !important; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; position: relative; overflow: hidden;}
.id-card * {color: white !important;} .id-title {font-size: 0.70rem; letter-spacing: 1px; text-transform: uppercase; opacity: 0.8; margin-bottom: 5px;} .id-name {font-size: 1.6rem; font-weight: 800; margin-bottom: 15px; line-height: 1.1;} .id-data-row {display: flex; gap: 20px; margin-bottom: 15px;} .id-data-col {display: flex; flex-direction: column;} .id-label {font-size: 0.6rem; opacity: 0.7; text-transform: uppercase;} .id-value {font-size: 0.95rem; font-weight: 600;} .tag-container {display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px;} .tag-badge {background-color: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 15px; font-size: 0.75rem; font-weight: 600;}
.btn-wa {display: inline-flex; align-items: center; justify-content: center; background-color: #25D366; color: white !important; padding: 10px 15px; border-radius: var(--radius-sm); text-decoration: none; font-weight: bold; font-size: 0.9rem; margin-top: 10px; transition: 0.3s; width: 100%;}
.stTabs [data-baseweb="tab-list"] {position: fixed; bottom: 0; left: 0; right: 0; background-color: rgba(18, 18, 18, 0.95); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-around; padding: 10px 5px env(safe-area-inset-bottom, 20px) 5px; z-index: 999999 !important;}
.stTabs [data-baseweb="tab"] {flex-grow: 1; text-align: center; justify-content: center; font-size: 0.70rem !important; font-weight: 700; color: var(--text-secondary) !important; padding: 10px 0; border: none !important; background: transparent !important;}
.stTabs [aria-selected="true"] {color: var(--primary) !important; background-color: rgba(96, 165, 250, 0.1) !important; border-radius: 12px;} .stTabs [aria-selected="true"]::after {display: none;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

# --- HELPERS Y SCHEMAS ---
TZ_AR = pytz.timezone('America/Argentina/Buenos_Aires')
def get_now_ar_str(): return datetime.now(TZ_AR).strftime("%Y-%m-%d %H:%M:%S")
def get_today_ar(): return datetime.now(TZ_AR).date()
def calculate_age(b):
    try: b = pd.to_datetime(b, dayfirst=True).date(); t = get_today_ar(); return t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    except: return 0
def format_wa_number(p): return re.sub(r'\D', '', str(p))
def clean_str(s): return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn').strip().upper() if isinstance(s, str) else ""
def clean_int(x, d=0):
    try: return int(float(str(x).strip()))
    except: return d

A_TAB, P_TAB, AP_TAB, U_TAB, S_TAB = "asistencia", "personas", "asistencia_personas", "config_usuarios", "seguimiento"
A_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "presentes", "coordinador", "modo", "notas", "usuario", "accion"]
P_COLS = ["nombre", "frecuencia", "centro", "edad", "domicilio", "notas", "activo", "timestamp", "usuario", "dni", "fecha_nacimiento", "telefono", "contacto_emergencia", "etiquetas"]
AP_COLS = ["timestamp", "fecha", "anio", "centro", "espacio", "nombre", "estado", "es_nuevo", "coordinador", "usuario", "notas"]
U_COLS = ["usuario", "password", "centro", "nombre"]
S_COLS = ["timestamp", "fecha", "anio", "centro", "nombre", "categoria", "observacion", "usuario"]

C_BELEN, C_NUDO, C_MARANATHA = "Calle Belén", "Nudo a Nudo", "Casa Maranatha"
CENTROS = [C_BELEN, C_NUDO, C_MARANATHA]
ESPACIOS = ["Taller de costura", "Apoyo escolar (Primaria)", "Apoyo escolar (Secundaria)", "Fines", "Espacio Joven", "La Ronda", "General"]
CATS = ["Escucha / Acompañamiento", "Salud", "Trámite (DNI/Social)", "Educación", "Familiar", "Crisis / Conflicto", "Otro"]

# --- SHEETS ---
@st.cache_resource(show_spinner=False)
def get_gc():
    pk = """-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDA6M0EIfQYCvZ/\n2cF1j9knWNLM1nGE0nohznJz8C9XsIJYZyPNXruD/y0cjdiQWyNopjzx3o15hoy2\ncRQOHDBgQA2alX9r7xd7rWvazwOTsgkNpRQVk0+wlOFUZdg79vQe9cn42JB71I0b\n0qsSLaeW35n3c8RFAzcv0XVmUdkRm76lU8pNhBKWOv3/DJJ2wB8VMW4l9Iq7MKyL\ng5t6d7qMPVckc3kGBsq/N+mPiisRjsPLgyvP3IHRzddIvcKiW9JpzNZoSqvOwpha\n2o+eMHuPHcJKev1JcJcU72CO1djfwwGM4L4ioRVVuE4w2EfCNdshSQC8Ht14alL3\ngQ6DMugNAgMBAAECggEAF1x562yzMzAsrsnvkC2V5hpvGMhFYgjdKnfmS10EVrG0\n70C6SLYWrkL6MxGIbt7imFs9WSsS5esh4jwqahUG1LkdDKHbFvaS2PLk81ALhljS\nmNjraDt5NJCrAv38ZDKhWJh6V4zeXmicmAh4mBB4UaCNdDaMR7E+fyd1+KijyWpl\noRqGUdpyEHoKCaXbPKQoGC9lGNs7xB7MGjPGi2pMz6O78oDTE1Obocqxk6sZYjrQ\nCH0jKwqTSosxlAb40hOFlGUUpDW7DF03trH0D9w2vNJTN/PqVJNOp5X7VKf2GTcg\n44ivcaEH2ZZF8hHIn9uDjWglVUFNJEwBGfEBmfVcQQKBgQDkkZzYG9czVslP+OHY\nANFQHAJ1tyEQ69O4YF8RZVLU6+QTIv8GplObaapVa1cAXPp0kMrU/bzUUKs38gZG\n8PQXYYpkCv/iceHqyLSm8KsvtKRSwXBwlzI5sn9XjSE1qAQsfg68LKikK3DswGjB\nc6qnsrm4fhnj1vU/ffsa7Xo5LQKBgQDYD5z3YATFvF5LHv3Ihj3gZZBoJMFss+EA\nt1TVt4KHaI94F224Bp52NDS3sScumQa+01WAaMBmGhPkw0G0hszQ428i5G7TCVuz\nM89Xb1aaQCSyopFKP8dVJYSJXXbwj+Cyno0DQc4jkcjSsfj2GgbG1BAjJqlnUGzr\nKAqBm/r2YQKBgDZZ6dH5zNKIcJZzuECE8UD7aBpV0acUbOQLBpA8Z9X5weJLEBmk\ns3zhQ3/MZoPPmD7fr1u2epCCHjTPeG6mHWTx7NadRvux2ObbkxmfYRWW/vwuw24C\nhg7yQxWumZcIvPVXhGl6tR9UtSWXG1HlD0+RUFhuo/lpxCe07WEZ11aBAoGBANFp\nUJnzVqzQhhQJVbClbBOyXOSTu2XAcrRe/Lqnwru7fFLJYm6a+7tVnkLsUS244/DQ\npG5xGQnc/KsdFPIENT/BMFaBUWj6CQcHkE8OesHGqcr6BhgQ+QJt+qepDz7aNM7r\nHYGqpkGTazHLjaH6V9cecwWe01JvgSHrDUPSCswBAoGAZgc8T9KvJ5r5sZQC/SkN\nSLzLT47WGr57f+WAT2CiaHhBRV2kwInNcsljsHCi1viFyQO/YDCWVEvozTjh6BoF\nrt4XiT6vnkKojyyG5uKBu+WHmXyaSH0aHj8ZCZl/C0Ab8MMAUVJg5zZHWyrztQAJ\nRx/AQ42L3AHtN6gVhU0zvVU=\n-----END PRIVATE KEY-----\n"""
    sa = {"type": "service_account", "project_id": "hogar-de-cristo-asistencia", "private_key_id": "cb7af14255a324107d2d2119a4f95d4348ed5b90", "private_key": pk.replace("\\n", "\n"), "client_email": "hogar-asistencia-bot@hogar-de-cristo-asistencia.iam.gserviceaccount.com", "client_id": "101282710856404935805", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/hogar-asistencia-bot%40hogar-de-cristo-asistencia.iam.gserviceaccount.com"}
    return gspread.authorize(Credentials.from_service_account_info(sa, scopes=["https://www.googleapis.com/auth/spreadsheets"]))

def get_sh(): return get_gc().open_by_key("1nCK2Q2ddxUO-erDwa5jgfGsUYsjZD7e4doHXoQ4N9zg")
def get_ws(t, cols):
    try: return get_sh().worksheet(t)
    except:
        try: w = get_sh().add_worksheet(title=t, rows=2000, cols=max(20, len(cols))); w.update("A1", [cols]); return w
        except: return get_sh().worksheet(t)

def get_df(t, cols):
    v = get_ws(t, cols).get_all_values()
    if not v: get_ws(t, cols).update("A1", [cols]); return pd.DataFrame(columns=cols)
    d = pd.DataFrame(v[1:] if len(v)>1 else [], columns=v)
    for c in cols:
        if c not in d.columns: d[c] = ""
    return d[cols]

@st.cache_data(ttl=600, show_spinner=False)
def get_users_db(): return get_df(U_TAB, U_COLS)
@st.cache_data(ttl=300, show_spinner="Sincronizando...")
def load_all_data(): return get_df(A_TAB, A_COLS), get_df(P_TAB, P_COLS), get_df(AP_TAB, AP_COLS), get_df(S_TAB, S_COLS)

def year_of(f):
    try: return str(pd.to_datetime(f).year)
    except: return str(get_today_ar().year)

def append_row(t, cols, data_dict):
    r = [str(data_dict.get(c, "")) for c in cols]
    get_ws(t, cols).append_rows([r], value_input_option="USER_ENTERED")

def upsert_persona(df, nom, cen, usr, **kw):
    if not nom.strip(): return df
    d = {c: "" for c in P_COLS}; d.update({"nombre": nom.strip(), "centro": cen, "activo": "SI", "timestamp": get_now_ar_str(), "usuario": usr})
    for k, v in kw.items():
        if k in P_COLS: d[k] = str(v).strip()
    append_row(P_TAB, P_COLS, d)
    return pd.concat([df, pd.DataFrame([d])], ignore_index=True)

# --- UI COMPONENTES ---
def show_login():
    _, c2, _ = st.columns()
    with c2:
        st.write("<br>", unsafe_allow_html=True)
        st.title("🏠 Baldosa Floja")
        with st.form("login_form"):
            u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                db = get_users_db()
                r = db[(db["usuario"].str.strip() == u.strip()) & (db["password"].str.strip() == p.strip())]
                if not r.empty:
                    st.session_state.update({"logged_in": True, "usuario": r.iloc["usuario"].strip(), "centro_asignado": r.iloc["centro"].strip(), "nombre_visible": r.iloc["nombre"].strip()})
                    st.rerun()
                else: st.error("Error de credenciales.")
        st.markdown("<div style='text-align:center; font-size:0.85rem; color:#888; margin-top:20px;'>Problemas? <br><a href='mailto:alejandrodelfuma@gmail.com' style='color:#60A5FA;'>alejandrodelfuma@gmail.com</a></div>", unsafe_allow_html=True)
    st.stop()

def top_alerts(df_a, df_p, df_ap, c):
    d = df_a[df_a["centro"] == c].copy() if not df_a.empty else pd.DataFrame()
    last_d = pd.to_datetime(d["fecha"], errors="coerce").max() if not d.empty else None
    hoy = get_today_ar()
    dias = (hoy - last_d.date()).days if pd.notna(last_d) else None

    df_act = df_p[(df_p["centro"].apply(clean_str) == clean_str(c)) & (df_p["activo"].str.upper() == "SI")] if not df_p.empty else pd.DataFrame()
    df_act = df_act.sort_values("timestamp").groupby("nombre").tail(1) if not df_act.empty else df_act
    cumples = [r["nombre"] for _, r in df_act.iterrows() if pd.notna(f:=pd.to_datetime(r.get("fecha_nacimiento"), dayfirst=True, errors="coerce")) and f.month == hoy.month and f.day == hoy.day]

    aus = []
    if not df_ap.empty:
        dp = df_ap[(df_ap["centro"]==c) & (df_ap["estado"]=="Presente")]
        if not dp.empty:
            dp["fecha_dt"] = pd.to_datetime(dp["fecha"], errors="coerce")
            last_p = dp.groupby("nombre")["fecha_dt"].max().reset_index()
            last_p["dias"] = (pd.Timestamp(hoy) - last_p["fecha_dt"]).dt.days
            aus = [f"{r['nombre']} ({r['dias']}d)" for _, r in last_p[(last_p["dias"]>7) & (last_p["dias"]<90)].sort_values("dias", ascending=False).iterrows()]

    st.markdown("<h4 style='font-size:1rem; margin-bottom:10px;'>📊 Novedades</h4>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c_a = df_a[(df_a["fecha"] == hoy.isoformat()) & (df_a["centro"] == c)] if not df_a.empty else pd.DataFrame()
    with c1: st.markdown(f"<div class='alert-box alert-{'success' if not c_a.empty else 'danger'}'>{'✅ Al día' if not c_a.empty else '⚠️ Faltan Asistencias'}</div>", unsafe_allow_html=True)
    with c2: 
        if cumples: 
            with st.expander(f"🎉 Cumples ({len(cumples)})", expanded=True): [st.write(f"- {x}") for x in cumples]
        else: st.markdown("<div class='alert-box alert-gray'>🎂 Sin cumples</div>", unsafe_allow_html=True)
    with c3:
        if aus:
            with st.expander(f"⚠️ Ausentes ({len(aus)})"): [st.write(f"🔴 {x}") for x in aus]
        else: st.markdown("<div class='alert-box alert-gray'>✔️ Sin Inasistencias</div>", unsafe_allow_html=True)

# --- PÁGINAS ---
def page_asist(df_p, df_a, c, nm, u):
    st.markdown("<h3 style='margin-bottom:15px;'>📝 Carga Diaria</h3>", unsafe_allow_html=True)
    hoy = get_today_ar(); f = st.date_input("Fecha", value=hoy)
    if f > hoy: st.error("⛔ Fecha futura inválida."); return
    fs = f.isoformat()
    c_e, c_m = st.columns(2)
    with c_e: esp = st.selectbox("Espacio", ESPACIOS) if c == C_MARANATHA else "General"
    with c_m: mod = st.selectbox("Modo", ["Día habitual", "Actividad especial", "Cerrado"])
    not_v = st.text_area("Notas del día", height=70)

    df_act = df_p[(df_p["centro"].apply(clean_str) == clean_str(c)) & (df_p["activo"].str.upper() == "SI")]
    df_act = df_act.sort_values("timestamp").groupby("nombre").tail(1) if not df_act.empty else df_act
    noms = sorted(list(set([n for n in df_act["nombre"].astype(str).tolist() if n.strip()])))

    st.markdown("#### 👥 Marcar Asistencia")
    pres = st.multiselect("Buscador de personas", options=noms)
    tot = st.number_input("Total numérico", min_value=0, value=len(pres))
    if pres: tot = len(pres)

    with st.expander("➕ ¿Vino alguien nuevo?"):
        n_nom = st.text_input("Nombre"); n_dni = st.text_input("DNI"); n_tel = st.text_input("Teléfono"); n_nac = st.text_input("F. Nacimiento (DD/MM/AAAA)")
        chk_n = st.checkbox("Agregar al Padrón")
        if chk_n and n_dni.strip() and not df_p[df_p['dni'].astype(str).str.strip() == n_dni.strip()].empty:
            st.error("⚠️ DNI duplicado.")

    df_lt = df_a.sort_values("timestamp").groupby(["fecha","centro","espacio"]).tail(1) if not df_a.empty else pd.DataFrame()
    ya = df_lt[(df_lt["fecha"]==fs) & (df_lt["centro"]==c) & (df_lt["espacio"]==esp)] if not df_lt.empty else pd.DataFrame()
    ow = st.checkbox("Confirmar sobreescritura", value=False) if not ya.empty else True
    if not ya.empty: st.warning("⚠️ Ya existe carga hoy.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 GUARDAR ASISTENCIA"):
        if not ow: st.error("Falta confirmar."); st.stop()
        if tot <= 0 and mod != "Cerrado": st.error("Faltan presentes."); st.stop()
        if chk_n and n_nom.strip():
            df_p = upsert_persona(df_p, n_nom, c, u, frecuencia="Nueva", dni=n_dni, telefono=n_tel, fecha_nacimiento=n_nac)
            if n_nom not in pres: pres.append(n_nom)
        if pres: tot = len(pres)
        
        with st.spinner("Guardando..."):
            append_row(A_TAB, A_COLS, {"timestamp":get_now_ar_str(),"fecha":fs,"anio":year_of(fs),"centro":c,"espacio":esp,"presentes":tot,"coordinador":nm,"modo":mod,"notas":not_v,"usuario":u,"accion":"append" if ya.empty else "overwrite"})
            for p in pres: append_row(AP_TAB, AP_COLS, {"timestamp":get_now_ar_str(),"fecha":fs,"anio":year_of(fs),"centro":c,"espacio":esp,"nombre":p,"estado":"Presente","es_nuevo":"SI" if (chk_n and p==n_nom) else "NO","coordinador":nm,"usuario":u})
            for a in [x for x in noms if x not in pres]: append_row(AP_TAB, AP_COLS, {"timestamp":get_now_ar_str(),"fecha":fs,"anio":year_of(fs),"centro":c,"espacio":esp,"nombre":a,"estado":"Ausente","es_nuevo":"NO","coordinador":nm,"usuario":u})
        st.toast("✅ Éxito"); time.sleep(1.5); st.cache_data.clear(); st.rerun()

def page_leg(df_p, df_ap, df_s, c, u):
    st.markdown("### 👥 Legajos", unsafe_allow_html=True)
    with st.expander("➕ Alta Directa Padrón Histórico"):
        with st.form("alta"):
            c1, c2 = st.columns(2)
            nn = c1.text_input("Nombre *"); nd = c1.text_input("DNI"); nf = c1.text_input("F. Nacimiento")
            nt = c2.text_input("Teléfono"); ne = c2.text_input("Emergencia"); ndo = c2.text_input("Dirección")
            nq = st.text_input("Etiquetas"); nno = st.text_area("Notas")
            if st.form_submit_button("Guardar"):
                if not nn: st.error("Nombre requerido.")
                elif not df_p[df_p['nombre'].str.upper() == nn.strip().upper()].empty: st.warning("⚠️ Ya existe.")
                else: upsert_persona(df_p, nn, c, u, dni=nd, telefono=nt, fecha_nacimiento=nf, domicilio=ndo, contacto_emergencia=ne, etiquetas=nq, notas=nno); st.success("✅ Guardado"); time.sleep(1); st.cache_data.clear(); st.rerun()

    df_c = df_p[(df_p["centro"].apply(clean_str) == clean_str(c))] if not df_p.empty else pd.DataFrame()
    df_c = df_c.sort_values("timestamp").groupby("nombre").tail(1) if not df_c.empty else df_c
    noms = sorted(df_c["nombre"].unique()) if not df_c.empty else []

    sel = st.selectbox("Buscador:", [""] + noms)
    if not sel:
        st.markdown("<hr>#### 📋 Padrón Completo", unsafe_allow_html=True)
        with st.expander("Ver Tabla Excel"):
            if not df_c.empty:
                b = io.BytesIO(); df_c.to_excel(b, index=False)
                st.download_button("📥 Descargar", b, f"padron_{c}.xlsx")
                df_s = df_c[df_c["activo"].str.upper() == "SI"] if st.checkbox("Solo activos", True) else df_c
                st.dataframe(df_s[["nombre", "dni", "fecha_nacimiento", "telefono", "activo"]].sort_values("nombre"), hide_index=True)
        return

    dp = df_c[df_c["nombre"] == sel].iloc
    tgs = "".join([f"<span class='tag-badge'>{t.strip()}</span>" for t in str(dp.get("etiquetas","")).split(",") if t.strip() and t.strip().lower()!="nan"])
    wa = f"<a href='https://wa.me/{format_wa_number(dp.get('telefono',''))}' class='btn-wa'>💬 WhatsApp</a>" if format_wa_number(dp.get("telefono","")) else ""
    dniv = dp.get('dni','') if str(dp.get('dni','')).lower()!='nan' else 'S/D'
    nacv = dp.get('fecha_nacimiento','') if str(dp.get('fecha_nacimiento','')).lower()!='nan' else 'S/D'
    nm = f"{nacv} ({calculate_age(nacv)}a)" if nacv!='S/D' else 'S/D'

    st.markdown(f"""<div class="id-card"><div style="display:flex; justify-content:space-between; margin-bottom:5px;"><div class="id-title">HOGAR DE CRISTO</div><span style="font-weight:800; background:rgba(255,255,255,0.2); padding:5px 12px; border-radius:12px; font-size:0.7rem;">{'🟢 ACTIVO' if str(dp.get('activo')).upper()!='NO' else '🔴 INACTIVO'}</span></div><div style="display:flex; gap:15px; align-items:center; margin-bottom:20px;"><img src="https://api.dicebear.com/7.x/initials/svg?seed={io.BytesIO(sel.encode()).getvalue().hex()}&backgroundColor=004e7b&textColor=ffffff" style="width:60px; border-radius:50%; border:2px solid #fff;"/><div class="id-name" style="margin-bottom:0;">{sel}</div></div><div class="id-data-row"><div class="id-data-col"><span class="id-label">DNI</span><span class="id-value">{dniv}</span></div><div class="id-data-col"><span class="id-label">Nacimiento</span><span class="id-value">{nm}</span></div></div><div class="tag-container">{tgs}</div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="background:var(--surface); padding:15px; border-radius:var(--radius-sm); margin-bottom:15px;"><div><div style="font-size:0.75rem; color:#aaa;">TELÉFONO</div><div style="font-size:1.1rem;">{dp.get('telefono','') if str(dp.get('telefono','')).lower()!='nan' else 'S/D'}</div>{wa}</div><div style="margin-top:10px;"><div style="font-size:0.75rem; color:#aaa;">DIRECCIÓN</div><div style="font-size:1.1rem;">{dp.get('domicilio','') if str(dp.get('domicilio','')).lower()!='nan' else 'S/D'}</div></div></div>""", unsafe_allow_html=True)
    
    if str(dp.get('contacto_emergencia','')).lower()!='nan' and dp.get('contacto_emergencia',''): st.markdown(f"""<div style="background:rgba(239,68,68,0.1); padding:15px; border-radius:var(--radius-sm); border-left:4px solid #EF4444; margin-bottom:15px;"><div style="font-size:0.75rem; color:#EF4444; font-weight:800;">EMERGENCIA</div><div style="font-weight:700; font-size:1.1rem; color:#FCA5A5;">{dp.get('contacto_emergencia')}</div></div>""", unsafe_allow_html=True)
    if str(dp.get('notas','')).lower()!='nan' and dp.get('notas',''): st.info(f"📌 {dp.get('notas')}")

    with st.expander("✏️ Editar Ficha"):
        with st.form("edit"):
            edni=st.text_input("DNI",dp.get('dni','')); etel=st.text_input("Teléfono",dp.get('telefono','')); eem=st.text_input("Emergencia",dp.get('contacto_emergencia',''))
            enac=st.text_input("F.Nac",dp.get('fecha_nacimiento','')); edom=st.text_input("Dirección",dp.get('domicilio','')); eetq=st.text_input("Etiquetas",dp.get('etiquetas',''))
            enot=st.text_area("Notas",dp.get('notas','')); eact=st.checkbox("Activo",str(dp.get('activo')).upper()!='NO')
            if st.form_submit_button("Guardar"): upsert_persona(df_p, sel, c, u, dni=edni, telefono=etel, contacto_emergencia=eem, fecha_nacimiento=enac, domicilio=edom, etiquetas=eetq, notas=enot, activo="SI" if eact else "NO"); st.toast("OK"); time.sleep(1); st.cache_data.clear(); st.rerun()

    st.markdown("### 📖 Bitácora")
    with st.expander("➕ Cargar Nota"):
        with st.form("ns"):
            fs=st.date_input("Fecha",get_today_ar()); ct=st.selectbox("Área",CATS); ob=st.text_area("Detalle")
            if st.form_submit_button("Guardar"):
                if len(ob)>5: append_row(S_TAB,S_COLS,{"timestamp":get_now_ar_str(),"fecha":fs,"anio":year_of(fs),"centro":c,"nombre":sel,"categoria":ct,"observacion":ob,"usuario":u}); st.toast("OK"); time.sleep(1); st.cache_data.clear(); st.rerun()

    if not df_s.empty:
        ms = df_s[(df_s["nombre"]==sel) & (df_s["centro"]==c)].copy()
        if not ms.empty:
            ms["fecha_dt"] = pd.to_datetime(ms["fecha"], errors="coerce")
            for _, n in ms.sort_values("fecha_dt", ascending=False).iterrows():
                ic = "🩺" if "salud" in n['categoria'].lower() else "🚨" if "crisis" in n['categoria'].lower() else "📌"
                cl = "#EF4444" if "crisis" in n['categoria'].lower() else "var(--secondary)"
                st.markdown(f"""<div style="background:var(--surface); padding:15px; border-radius:12px; margin-bottom:10px; border-left:4px solid {cl};"><div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px; margin-bottom:5px;"><strong style="color:var(--primary);">{ic} {n['categoria']}</strong><small style="color:#aaa;">{n['fecha']} ({n.get('usuario','')})</small></div><div>{n['observacion']}</div></div>""", unsafe_allow_html=True)

def page_rep(df_a, c):
    st.markdown("### 📊 Reportes", unsafe_allow_html=True)
    df_l = df_a.sort_values("timestamp").groupby(["fecha","centro","espacio"]).tail(1) if not df_a.empty else pd.DataFrame()
    if df_l.empty: st.info("Sin datos."); return
    df_c = df_l[df_l["centro"] == c].copy()
    
    with st.expander("📥 Backup Total Excel"):
        b = io.BytesIO(); df_l.to_excel(b, index=False)
        st.download_button("Descargar", b, f"BACKUP_HC_{date.today()}.xlsx", use_container_width=True)

    if df_c.empty: return
    df_c["fecha_dt"] = pd.to_datetime(df_c["fecha"])
    df_c["p_i"] = df_c["presentes"].apply(clean_int)
    st.line_chart(df_c.sort_values("fecha_dt").set_index("fecha")["p_i"], color="#60A5FA")
    st.markdown(f"**Promedio:** {df_c['p_i'].mean():.1f} chicos/día.")
    st.dataframe(df_c.sort_values("fecha", ascending=False)[["fecha","espacio","presentes","coordinador"]], use_container_width=True)
    st.markdown("<div style='text-align:center; color:#888; font-size:0.8rem; margin-top:20px;'>Soporte: alejandrodelfuma@gmail.com</div>", unsafe_allow_html=True)

def page_glo(df_a, df_p, df_ap):
    st.markdown("### 🌍 Consola Central", unsafe_allow_html=True)
    df_la = df_a.sort_values("timestamp").groupby(["fecha","centro","espacio"]).tail(1) if not df_a.empty else pd.DataFrame()
    an = str(get_today_ar().year)
    t_p = len(df_p.sort_values("timestamp").groupby("nombre").tail(1)) if not df_p.empty else 0
    t_a = df_la[df_la["anio"].astype(str)==an]["presentes"].apply(clean_int).sum() if not df_la.empty and "anio" in df_la.columns else 0
    t_n = len(df_ap[(df_ap["es_nuevo"]=="SI") & (df_ap["anio"].astype(str)==an)]) if not df_ap.empty and "es_nuevo" in df_ap.columns else 0
    d_u = df_la[df_la["anio"].astype(str)==an]["fecha"].nunique() if not df_la.empty and "anio" in df_la.columns else 0
    pr = t_a/d_u if d_u>0 else 0

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='kpi'><h3>Total</h3><div class='v'>{t_p}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'><h3>Prom/Día</h3><div class='v'>{pr:.1f}</div></div>", unsafe_allow_html=True)
    st.write("<br>", unsafe_allow_html=True); c3, c4 = st.columns(2)
    c3.markdown(f"<div class='kpi'><h3>Asist {an}</h3><div class='v'>{t_a}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi'><h3>Nuevos {an}</h3><div class='v'>{t_n}</div></div>", unsafe_allow_html=True)

    st.markdown(f"#### 🏢 Ingresos por Centro ({an})")
    if not df_la.empty and "anio" in df_la.columns:
        df_an = df_la[df_la["anio"].astype(str)==an].copy()
        df_an["p"] = df_an["presentes"].apply(clean_int)
        st.bar_chart(df_an.groupby("centro")["p"].sum(), color="#60A5FA")

    st.markdown("#### 👥 Edades")
    if not df_p.empty:
        dp_u = df_p.sort_values("timestamp").groupby("nombre").tail(1).copy()
        dp_u["e"] = dp_u["fecha_nacimiento"].apply(calculate_age)
        de = dp_u[dp_u["e"]>0].copy()
        if not de.empty:
            de['Rango'] = pd.cut(de['e'], bins=, labels=['Niños','Adolescentes','Jóvenes','Adultos','Mayores'], right=False)
            st.bar_chart(de['Rango'].value_counts().sort_index(), color="#A78BFA")

# --- MAIN ---
def main():
    if not st.session_state.get("logged_in"): show_login()
    u, c, nm = st.session_state["usuario"], st.session_state["centro_asignado"], st.session_state["nombre_visible"]
    
    mc = next((x for x in CENTROS if clean_str(x)==clean_str(c)), None)
    if not mc: st.error("Error Centro."); st.stop()
    if mc == C_BELEN and u.upper() != "NATASHA":
        st.error("🔒 ACCESO DENEGADO: Calle Belén es exclusivo para Natasha.")
        if st.button("Salir"): st.session_state.clear(); st.rerun()
        st.stop()

    show_top_header(nm, mc)
    da, dp, dap, ds = load_all_data()

    lt = ["🏠 Inicio", "👥 Legajos", "📊 Reportes"]
    if u.upper() == "NATASHA": lt.append("🌍 Global")
    t = st.tabs(lt)

    with t: top_alerts(da, dp, dap, mc); page_asist(dp, da, mc, nm, u)
    with t: page_leg(dp, dap, ds, mc, u)
    with t: page_rep(da, mc)
    if len(t)>3: 
        with t: page_glo(da, dp, dap)

if __name__ == "__main__":
    main()
