import os
import re
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from google.auth.exceptions import RefreshError


# =========================
# Config / Estilo
# =========================
PRIMARY = "#004E7B"
ACCENT = "#63296C"

st.set_page_config(page_title="Asistencia – Hogar de Cristo", layout="wide")

st.markdown(
    f"""
    <style>
      :root {{
        --hc-primary: {PRIMARY};
        --hc-accent: {ACCENT};
      }}
      h1,h2,h3 {{ color: var(--hc-primary); }}
      .hc-pill {{
        display:inline-block; padding:6px 12px; border-radius:999px;
        background: rgba(0,78,123,.16);
        border:1px solid rgba(0,78,123,.35);
        color:white; font-weight:700;
      }}
      .hc-card {{
        border: 1px solid rgba(99,41,108,.35);
        background: rgba(255,255,255,.03);
        border-radius: 16px;
        padding: 14px 16px;
      }}
      .hc-badge {{
        display:inline-block; padding:4px 10px; border-radius:999px;
        background: rgba(99,41,108,.18);
        border:1px solid rgba(99,41,108,.35);
        color:white; font-weight:700;
        font-size: 0.85rem;
      }}
      .stButton>button {{
        background: var(--hc-primary) !important;
        color: white !important;
        border-radius: 999px !important;
        font-weight: 800 !important;
        border: 1px solid rgba(255,255,255,.10) !important;
      }}
      .stButton>button:hover {{
        background: var(--hc-accent) !important;
      }}
      .stTabs [data-baseweb="tab"] {{
        font-weight: 800 !important;
      }}
      .stTabs [aria-selected="true"] {{
        border-bottom: 3px solid var(--hc-accent) !important;
      }}
      .small-note {{
        opacity: .85;
        font-size: 0.92rem;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

CENTROS = ["Calle Belén", "Casa Maranatha", "Nudo a Nudo"]

ESPACIOS_MARANATHA = [
    "Taller de costura",
    "Apoyo escolar primaria",
    "Apoyo escolar secundaria",
    "FINES",
    "Espacio Joven",
    "La Ronda",
    "Otro",
]

FRECUENCIAS = ["Diaria", "Semanal", "Mensual", "No asiste"]

TAB_PERSONAS = "personas"
TAB_ASISTENCIA = "asistencia"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CSV_FALLBACK = "data/personas.csv"


# =========================
# Helpers: limpieza / normalización
# =========================
def clean_cell(x) -> str:
    if x is None:
        return ""
    s = str(x)
    s = s.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_frecuencia(x) -> str:
    s = clean_cell(x).lower()
    if "diar" in s:
        return "Diaria"
    if "seman" in s:
        return "Semanal"
    if "mens" in s:
        return "Mensual"
    if "no" in s and "asist" in s:
        return "No asiste"
    return "Semanal" if s else "Semanal"

def normalize_centro(x) -> str:
    s = clean_cell(x).lower()
    if "bel" in s:
        return "Calle Belén"
    if "mara" in s:
        return "Casa Maranatha"
    if "nudo" in s:
        return "Nudo a Nudo"
    return clean_cell(x)


# =========================
# Google Sheets (REST)
# =========================
def _require_secrets():
    if "gcp_service_account" not in st.secrets:
        st.error("Falta [gcp_service_account] en Secrets.")
        st.stop()
    if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
        st.error("Falta [sheets] spreadsheet_id en Secrets.")
        st.stop()

@st.cache_resource(show_spinner=False)
def get_session():
    _require_secrets()
    sa = dict(st.secrets["gcp_service_account"])

    # IMPORTANTÍSIMO: private_key debe venir con \n reales
    pk = str(sa.get("private_key", ""))
    pk = pk.replace("\\n", "\n").strip()
    if not pk.endswith("\n"):
        pk += "\n"
    sa["private_key"] = pk

    try:
        creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
        creds.refresh(Request())
        return AuthorizedSession(creds)
    except RefreshError as e:
        st.error("Google rechazó la autenticación (RefreshError).")
        st.code(str(e))
        st.stop()

def _base(spreadsheet_id: str) -> str:
    return f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"

def sheets_get_meta(session: AuthorizedSession, sid: str) -> dict:
    r = session.get(_base(sid))
    r.raise_for_status()
    return r.json()

def ensure_sheet(session: AuthorizedSession, sid: str, title: str):
    meta = sheets_get_meta(session, sid)
    titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if title in titles:
        return
    url = _base(sid) + ":batchUpdate"
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    r = session.post(url, json=body)
    r.raise_for_status()

def get_values(session: AuthorizedSession, sid: str, a1: str) -> list:
    url = _base(sid) + f"/values/{a1}"
    r = session.get(url)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get("values", [])

def put_values(session: AuthorizedSession, sid: str, a1: str, values: list):
    url = _base(sid) + f"/values/{a1}?valueInputOption=USER_ENTERED"
    body = {"range": a1, "majorDimension": "ROWS", "values": values}
    r = session.put(url, json=body)
    r.raise_for_status()

def append_values(session: AuthorizedSession, sid: str, a1: str, values: list):
    url = _base(sid) + f"/values/{a1}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    body = {"range": a1, "majorDimension": "ROWS", "values": values}
    r = session.post(url, json=body)
    r.raise_for_status()

def clear_range(session: AuthorizedSession, sid: str, a1: str):
    url = _base(sid) + f"/values/{a1}:clear"
    r = session.post(url, json={})
    r.raise_for_status()

def _df_from_sheet(values: list, cols: list) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=cols)
    header = values[0]
    rows = values[1:] if len(values) > 1 else []
    if [c.strip().lower() for c in header] != [c.strip().lower() for c in cols]:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)

def ensure_headers(session, sid):
    ensure_sheet(session, sid, TAB_PERSONAS)
    ensure_sheet(session, sid, TAB_ASISTENCIA)

    if not get_values(session, sid, f"{TAB_PERSONAS}!A1:C1"):
        put_values(session, sid, f"{TAB_PERSONAS}!A1:C1", [["nombre", "frecuencia", "centro"]])

    if not get_values(session, sid, f"{TAB_ASISTENCIA}!A1:I1"):
        put_values(session, sid, f"{TAB_ASISTENCIA}!A1:I1", [[
            "fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"
        ]])

def load_personas(session, sid) -> pd.DataFrame:
    vals = get_values(session, sid, f"{TAB_PERSONAS}!A1:Z")
    df = _df_from_sheet(vals, ["nombre","frecuencia","centro"])
    if df.empty:
        return df
    df["nombre"] = df["nombre"].map(clean_cell)
    df["frecuencia"] = df["frecuencia"].map(normalize_frecuencia)
    df["centro"] = df["centro"].map(normalize_centro)
    df = df[df["nombre"] != ""]
    df = df.drop_duplicates(subset=["nombre","centro"], keep="first")
    return df

def load_asistencia(session, sid) -> pd.DataFrame:
    vals = get_values(session, sid, f"{TAB_ASISTENCIA}!A1:Z")
    df = _df_from_sheet(vals, ["fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"])
    if df.empty:
        return df
    df["presentes"] = pd.to_numeric(df["presentes"], errors="coerce").fillna(0).astype(int)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(df["fecha"].dt.year).astype(int)
    df["centro"] = df["centro"].map(normalize_centro)
    df["espacio"] = df["espacio"].map(clean_cell)
    df["coordinador"] = df["coordinador"].map(clean_cell)
    df["modo"] = df["modo"].map(clean_cell)
    df["notas"] = df["notas"].map(clean_cell)
    return df


# =========================
# CSV Fallback (repo)
# =========================
def load_personas_csv_fallback() -> pd.DataFrame:
    if not os.path.exists(CSV_FALLBACK):
        return pd.DataFrame(columns=["nombre","frecuencia","centro"])
    try:
        df = pd.read_csv(CSV_FALLBACK)
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_FALLBACK, encoding="latin1")

    df.columns = [c.strip().lower() for c in df.columns]
    if "personas" in df.columns and "nombre" not in df.columns:
        df = df.rename(columns={"personas": "nombre"})

    for k in ["nombre","frecuencia","centro"]:
        if k not in df.columns:
            df[k] = ""

    df = df[["nombre","frecuencia","centro"]].copy()
    df["nombre"] = df["nombre"].map(clean_cell)
    df["frecuencia"] = df["frecuencia"].map(normalize_frecuencia)
    df["centro"] = df["centro"].map(normalize_centro)
    df = df[df["nombre"] != ""]
    df = df.drop_duplicates(subset=["nombre","centro"], keep="first")
    return df

def seed_personas_if_empty(session, sid) -> bool:
    df_sheet = load_personas(session, sid)
    if not df_sheet.empty and df_sheet["nombre"].astype(str).str.strip().any():
        return False

    df_csv = load_personas_csv_fallback()
    if df_csv.empty:
        return False

    rows = df_csv[["nombre","frecuencia","centro"]].values.tolist()
    append_values(session, sid, f"{TAB_PERSONAS}!A1", rows)
    return True


# =========================
# LOGIN (usuarios en secrets)
# =========================
def require_users():
    if "users" not in st.secrets:
        st.error("Falta [users] en Secrets.")
        st.stop()

def do_login():
    require_users()
    users = dict(st.secrets["users"])

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if st.session_state.auth_ok:
        return

    st.title("Acceso — Sistema de Asistencia")
    st.write("Ingresá con tu usuario y contraseña.")

    user_keys = list(users.keys())
    u = st.selectbox("Usuario", user_keys)
    pw = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        info = dict(users[u])
        if pw == info.get("password", ""):
            st.session_state.auth_ok = True
            st.session_state.user_key = u
            st.session_state.user_nombre = info.get("nombre", u)
            st.session_state.user_centro = info.get("centro", "")
            st.success("✅ Acceso correcto")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

    st.stop()

def logout_button():
    if st.sidebar.button("Salir"):
        st.session_state.auth_ok = False
        for k in ["user_key","user_nombre","user_centro"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()


# =========================
# App
# =========================
do_login()

st.title("Sistema de Asistencia — Hogar de Cristo Bahía Blanca")

sid = st.secrets["sheets"]["spreadsheet_id"]
session = get_session()

ensure_headers(session, sid)
seeded = seed_personas_if_empty(session, sid)

df_personas = load_personas(session, sid)
df_asistencia = load_asistencia(session, sid)

# Sidebar (centro + coordinador BLOQUEADOS)
st.sidebar.header("Acceso")
st.sidebar.success(f"Conectado como: {st.session_state.user_key}")
logout_button()
st.sidebar.markdown("---")

centro = st.session_state.user_centro
coordinador = st.session_state.user_nombre

st.sidebar.write(f"Centro asignado: **{centro}**")
st.sidebar.write(f"¿Quién carga?: **{coordinador}**")
st.sidebar.caption("App interna — Hogar de Cristo Bahía Blanca")

if seeded:
    st.success("✅ Importé automáticamente `data/personas.csv` a Google Sheets (solo esta vez).")

today = date.today()
anio_actual = today.year

# Datos filtrados
dfA = df_asistencia.copy()
dfCentro = dfA[dfA["centro"] == centro].copy() if not dfA.empty else dfA
dfCentroYear = dfCentro[dfCentro["anio"] == anio_actual].copy() if not dfCentro.empty else dfCentro

st.markdown(f"""<div class="hc-pill">Estás trabajando sobre: {centro} — 👤 {coordinador}</div>""", unsafe_allow_html=True)

# KPIs + alerta semana
ing_hoy = int(dfCentroYear[dfCentroYear["fecha"].dt.date == today]["presentes"].sum()) if not dfCentroYear.empty else 0
ing_7 = int(dfCentroYear[dfCentroYear["fecha"].dt.date >= (today - timedelta(days=6))]["presentes"].sum()) if not dfCentroYear.empty else 0

start_week = today - timedelta(days=today.weekday())
dias_cargados = set(dfCentroYear[dfCentroYear["fecha"].dt.date >= start_week]["fecha"].dt.date.unique()) if not dfCentroYear.empty else set()
dias_semana = [start_week + timedelta(days=i) for i in range(7)]
dias_sin = sum(1 for d in dias_semana if d not in dias_cargados and d <= today)

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f'<div class="hc-card"><b>Ingresos HOY</b><br><span style="font-size:42px;font-weight:900;">{ing_hoy}</span></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="hc-card"><b>Ingresos últimos 7 días</b><br><span style="font-size:42px;font-weight:900;">{ing_7}</span></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="hc-card"><b>Días sin cargar esta semana</b><br><span style="font-size:42px;font-weight:900;">{dias_sin}</span></div>', unsafe_allow_html=True)

if dias_sin >= 2:
    st.warning(f"⚠️ Ojo: hay **{dias_sin} días** sin cargar esta semana en {centro}.", icon="⚠️")

tabs = st.tabs(["📌 Registrar asistencia", "👥 Personas", "📊 Reportes / Base de datos", "🌍 Global"])


# =========================
# TAB 1: Registrar asistencia (con evitar duplicados + modo lista)
# =========================
with tabs[0]:
    st.subheader("Registrar asistencia")

    c1, c2 = st.columns([2,1])
    with c1:
        fecha = st.date_input("Fecha", value=today)
    with c2:
        anio = st.number_input("Año", min_value=2020, max_value=2100, value=fecha.year, step=1)

    if centro == "Casa Maranatha":
        espacio = st.selectbox("Espacio (solo Maranatha)", ESPACIOS_MARANATHA)
    else:
        espacio = "General"
        st.info("Este centro registra asistencia general (sin espacios).")

    st.markdown("---")
    st.markdown("### Modo de carga")

    dfP = df_personas.copy()
    dfP_c = dfP[dfP["centro"] == centro].copy() if not dfP.empty else pd.DataFrame(columns=["nombre","frecuencia","centro"])
    dfP_c = dfP_c.sort_values("nombre") if not dfP_c.empty else dfP_c

    modo = st.radio("¿Cómo querés cargar?", ["Número total", "Lista (tildar presentes)"], horizontal=True)

    presentes = 0
    lista_presentes = []

    if modo == "Número total":
        presentes = st.number_input("Total presentes", min_value=0, step=1)
    else:
        st.caption("Tildá quiénes estuvieron hoy. El total se calcula solo.")
        if dfP_c.empty:
            st.warning("No hay personas cargadas para este centro todavía.")
        else:
            opciones = dfP_c["nombre"].tolist()
            lista_presentes = st.multiselect("Presentes", opciones, default=[])
            presentes = len(lista_presentes)
            st.info(f"Total calculado: **{presentes}**")

    notas = st.text_area("Notas (opcional)")

    # evitar duplicado por clave
    clave_existente = False
    if not dfCentro.empty:
        df_check = dfCentro.copy()
        df_check["fecha_d"] = df_check["fecha"].dt.date
        clave_existente = ((df_check["fecha_d"] == fecha) &
                           (df_check["centro"] == centro) &
                           (df_check["espacio"] == espacio) &
                           (df_check["coordinador"] == coordinador)).any()

    if clave_existente:
        st.warning("⚠️ Ya existe un registro con **misma fecha + centro + espacio + coordinador**. Podés sobrescribirlo.")

    sobrescribir = False
    if clave_existente:
        sobrescribir = st.checkbox("Sobrescribir ese registro existente")

    if st.button("Guardar asistencia"):
        if clave_existente and not sobrescribir:
            st.error("Ya existe registro. Marcá 'Sobrescribir' si querés reemplazarlo.")
        else:
            # Si sobrescribe, limpiamos y reescribimos todo el tab (simple y robusto)
            if clave_existente and sobrescribir:
                # recargar tab completo
                df_all = df_asistencia.copy()
                df_all["fecha_d"] = df_all["fecha"].dt.date
                mask = ~(
                    (df_all["fecha_d"] == fecha) &
                    (df_all["centro"] == centro) &
                    (df_all["espacio"] == espacio) &
                    (df_all["coordinador"] == coordinador)
                )
                df_all = df_all[mask].drop(columns=["fecha_d"])

                # limpiar hoja y reescribir
                clear_range(session, sid, f"{TAB_ASISTENCIA}!A:Z")
                put_values(session, sid, f"{TAB_ASISTENCIA}!A1:I1", [[
                    "fecha","anio","centro","espacio","presentes","coordinador","modo","notas","timestamp"
                ]])
                if not df_all.empty:
                    rows_old = []
                    for _, r in df_all.sort_values("fecha").iterrows():
                        rows_old.append([
                            r["fecha"].date().isoformat() if pd.notna(r["fecha"]) else "",
                            str(int(r["anio"])) if str(r.get("anio","")).strip() else "",
                            clean_cell(r["centro"]),
                            clean_cell(r["espacio"]),
                            str(int(r["presentes"])),
                            clean_cell(r["coordinador"]),
                            clean_cell(r.get("modo","")),
                            clean_cell(r.get("notas","")),
                            clean_cell(r.get("timestamp","")),
                        ])
                    append_values(session, sid, f"{TAB_ASISTENCIA}!A1", rows_old)

            modo_txt = "lista" if modo != "Número total" else "total"
            notas_final = notas
            if modo_txt == "lista" and lista_presentes:
                # guardamos la lista en notas (resumen)
                notas_final = (notas_final + " | " if notas_final else "") + "Presentes: " + ", ".join(lista_presentes)

            row = [[
                fecha.isoformat(),
                str(anio),
                clean_cell(centro),
                clean_cell(espacio),
                str(int(presentes)),
                clean_cell(coordinador),
                modo_txt,
                clean_cell(notas_final),
                datetime.now().isoformat(timespec="seconds"),
            ]]
            append_values(session, sid, f"{TAB_ASISTENCIA}!A1", row)
            st.success("✅ Asistencia guardada.")
            st.rerun()

    st.markdown("---")
    st.caption("Últimos registros (este centro / este año)")
    show = dfCentroYear.sort_values("fecha", ascending=False).head(20) if not dfCentroYear.empty else dfCentroYear
    st.dataframe(show, use_container_width=True)


# =========================
# TAB 2: Personas (buscador + filtros)
# =========================
with tabs[1]:
    st.subheader("Personas registradas (este centro)")

    dfP = df_personas.copy()
    dfP_c = dfP[dfP["centro"] == centro].copy() if not dfP.empty else pd.DataFrame(columns=["nombre","frecuencia","centro"])
    dfP_c = dfP_c.sort_values("nombre") if not dfP_c.empty else dfP_c

    f1, f2, f3 = st.columns([2,1,1])
    with f1:
        q = st.text_input("Buscar por nombre", placeholder="Ej: Reynaldo, Coca, Acebedo…")
    with f2:
        freq = st.selectbox("Frecuencia", ["Todas"] + FRECUENCIAS, index=0)
    with f3:
        solo_activos = st.checkbox("Ocultar 'No asiste'", value=False)

    view = dfP_c.copy()
    if q.strip():
        qq = q.strip().lower()
        view = view[view["nombre"].str.lower().str.contains(qq, na=False)]
    if freq != "Todas":
        view = view[view["frecuencia"] == freq]
    if solo_activos:
        view = view[view["frecuencia"] != "No asiste"]

    st.markdown(f"<div class='hc-badge'>Personas visibles: {len(view)}</div>", unsafe_allow_html=True)
    st.dataframe(view, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar persona (manual)")
    nombre = st.text_input("Nombre completo")
    frecuencia = st.selectbox("Frecuencia", FRECUENCIAS)

    if st.button("Agregar"):
        n = clean_cell(nombre)
        if not n:
            st.error("Poné un nombre.")
        else:
            row = [[n, frecuencia, centro]]
            append_values(session, sid, f"{TAB_PERSONAS}!A1", row)
            st.success("✅ Persona agregada.")
            st.rerun()

    st.markdown("---")
    st.subheader("Export rápido (Personas)")
    st.download_button(
        "⬇️ Descargar personas del centro (CSV)",
        dfP_c.to_csv(index=False).encode("utf-8"),
        file_name=f"personas_{centro}.csv",
        mime="text/csv"
    )


# =========================
# TAB 3: Reportes / Base de datos (export semana/mes)
# =========================
with tabs[2]:
    st.subheader("Reportes (este centro)")

    if dfCentro.empty:
        st.info("Todavía no hay registros de asistencia para este centro.")
    else:
        anios = sorted(dfCentro["anio"].dropna().unique().tolist())
        if anio_actual not in anios:
            anios = [anio_actual] + anios

        anio_sel = st.selectbox("Año", anios, index=(anios.index(anio_actual) if anio_actual in anios else 0))
        data = dfCentro[dfCentro["anio"] == anio_sel].copy()

        if data.empty:
            st.info("No hay registros para ese año.")
        else:
            serie = data.groupby(data["fecha"].dt.date)["presentes"].sum().sort_index()
            st.caption("Asistencia por día")
            st.line_chart(serie)

            by_coord = data.groupby("coordinador")["presentes"].sum().sort_values(ascending=False)
            st.caption("Acumulado por coordinador/a")
            st.bar_chart(by_coord)

            if centro == "Casa Maranatha":
                by_esp = data.groupby("espacio")["presentes"].sum().sort_values(ascending=False)
                st.caption("Por espacio (Maranatha)")
                st.bar_chart(by_esp)

            st.markdown("---")
            st.subheader("Base de datos (descargas rápidas)")

            hoy = date.today()
            semana_desde = hoy - timedelta(days=6)
            mes_desde = hoy - timedelta(days=29)

            data2 = data.copy()
            data2["fecha_d"] = data2["fecha"].dt.date

            semana = data2[data2["fecha_d"] >= semana_desde].drop(columns=["fecha_d"])
            mes = data2[data2["fecha_d"] >= mes_desde].drop(columns=["fecha_d"])

            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button(
                    "⬇️ Descargar semana (CSV)",
                    semana.to_csv(index=False).encode("utf-8"),
                    file_name=f"asistencia_{centro}_semana.csv",
                    mime="text/csv"
                )
            with c2:
                st.download_button(
                    "⬇️ Descargar mes (CSV)",
                    mes.to_csv(index=False).encode("utf-8"),
                    file_name=f"asistencia_{centro}_mes.csv",
                    mime="text/csv"
                )
            with c3:
                st.download_button(
                    "⬇️ Descargar todo el año (CSV)",
                    data.drop(columns=["fecha"], errors="ignore").to_csv(index=False).encode("utf-8"),
                    file_name=f"asistencia_{centro}_{anio_sel}.csv",
                    mime="text/csv"
                )

            st.markdown("---")
            st.caption("Tabla completa (filtrada por año)")
            st.dataframe(data.sort_values("fecha", ascending=False), use_container_width=True)


# =========================
# TAB 4: Global
# =========================
with tabs[3]:
    st.subheader("Tablero global (todos los centros)")

    if dfA.empty:
        st.info("Todavía no hay registros globales.")
    else:
        anios_g = sorted(dfA["anio"].dropna().unique().tolist())
        anio_g = st.selectbox("Año (global)", anios_g, index=(anios_g.index(anio_actual) if anio_actual in anios_g else 0))

        dg = dfA[dfA["anio"] == anio_g].copy()
        if dg.empty:
            st.info("Sin datos para ese año.")
        else:
            st.caption("Asistencia total por centro")
            by_c = dg.groupby("centro")["presentes"].sum().sort_values(ascending=False)
            st.bar_chart(by_c)

            st.caption("Evolución diaria total (todos los centros)")
            serie_g = dg.groupby(dg["fecha"].dt.date)["presentes"].sum().sort_index()
            st.line_chart(serie_g)

            st.markdown("---")
            st.caption("Tabla completa (filtrada por año)")
            st.dataframe(dg.sort_values("fecha", ascending=False), use_container_width=True)
