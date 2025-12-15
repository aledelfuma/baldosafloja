import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Asistencia Hogar de Cristo", layout="wide")

CENTROS = ["Calle Belén", "Casa Maranatha", "Nudo a Nudo"]
ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
ASISTENCIA_PERSONAS_TAB = "asistencia_personas"

# =========================
# GOOGLE SHEETS
# =========================
@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    gc = get_gspread_client()
    return gc.open_by_key(st.secrets["sheets"]["spreadsheet_id"])

def get_ws(title):
    sh = get_spreadsheet()
    try:
        return sh.worksheet(title)
    except:
        ws = sh.add_worksheet(title=title, rows=1000, cols=20)
        return ws

def read_ws(title):
    ws = get_ws(title)
    data = ws.get_all_records()
    return pd.DataFrame(data)

def append_row(title, row):
    ws = get_ws(title)
    ws.append_row(row, value_input_option="USER_ENTERED")

# =========================
# INIT PERSONAS DESDE CSV
# =========================
def init_personas():
    df_sheet = read_ws(PERSONAS_TAB)
    if not df_sheet.empty:
        return

    try:
        df_csv = pd.read_csv("datapersonas.csv")
        ws = get_ws(PERSONAS_TAB)
        ws.append_row(list(df_csv.columns))
        for _, r in df_csv.iterrows():
            ws.append_row(r.tolist())
    except Exception as e:
        st.warning("No se pudo cargar datapersonas.csv")

# =========================
# UI
# =========================
def main():
    st.title("📋 Asistencia – Hogar de Cristo")

    init_personas()

    centro = st.selectbox("Centro", CENTROS)
    hoy = date.today().isoformat()
    anio = date.today().year

    tab1, tab2, tab3 = st.tabs([
        "📝 Registrar asistencia",
        "👥 Personas",
        "📊 Reportes"
    ])

    # =====================
    # REGISTRAR ASISTENCIA
    # =====================
    with tab1:
        st.subheader("Registrar asistencia del día")

        presentes = st.number_input("Cantidad total de presentes", min_value=0)
        coordinador = st.text_input("Quién carga")
        modo = st.selectbox("Modo", ["Día habitual", "Actividad especial"])
        notas = st.text_area("Notas")

        df_personas = read_ws(PERSONAS_TAB)
        df_centro = df_personas[df_personas["centro"] == centro]

        st.markdown("### ¿Quiénes asistieron hoy?")
        seleccionadas = st.multiselect(
            "Personas del centro",
            options=df_centro["nombre"].tolist()
        )

        nueva_persona = st.text_input("Agregar persona nueva (si no está)")

        if st.button("Guardar asistencia"):
            ts = datetime.now().isoformat(timespec="seconds")

            append_row(ASISTENCIA_TAB, [
                ts, hoy, anio, centro, "General",
                presentes, coordinador, modo, notas, coordinador
            ])

            for nombre in seleccionadas:
                append_row(ASISTENCIA_PERSONAS_TAB, [
                    hoy, centro, "General", nombre, "no", coordinador, ts
                ])

            if nueva_persona.strip():
                append_row(PERSONAS_TAB, [
                    nueva_persona.strip(), "Sin definir", centro
                ])
                append_row(ASISTENCIA_PERSONAS_TAB, [
                    hoy, centro, "General", nueva_persona.strip(), "si", coordinador, ts
                ])

            st.success("Asistencia guardada correctamente")

    # =========================
# NUEVO – ASISTENCIA POR PERSONA
# =========================
def guardar_asistencia_personas(fecha, centro, espacio, personas, usuario):
    ws = get_ws("asistencia_personas")
    ts = datetime.now().isoformat(timespec="seconds")

    for nombre in personas:
        ws.append_row([
            fecha,
            centro,
            espacio,
            nombre,
            "si",
            usuario,
            ts
        ])


    # =====================
    # PERSONAS
    # =====================
    with tab2:
        st.subheader("Personas del centro")
        df_personas = read_ws(PERSONAS_TAB)
        df_centro = df_personas[df_personas["centro"] == centro]

        st.metric("Personas visibles", len(df_centro))
        st.dataframe(df_centro, use_container_width=True)

    # =====================
    # REPORTES
    # =====================
    with tab3:
        df = read_ws(ASISTENCIA_TAB)
        if df.empty:
            st.info("Todavía no hay registros.")
            return

        df_c = df[(df["centro"] == centro) & (df["anio"] == anio)]

        st.metric(
            "Total asistentes registrados",
            int(df_c["presentes"].sum()) if not df_c.empty else 0
        )

        st.dataframe(df_c.sort_values("fecha", ascending=False),
                     use_container_width=True)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()

