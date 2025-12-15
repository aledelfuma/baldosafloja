import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIG GENERAL
# =====================================================
st.set_page_config(page_title="Asistencia Hogar de Cristo", layout="wide")

CENTROS = ["Calle Belén", "Casa Maranatha", "Nudo a Nudo"]

ASISTENCIA_TAB = "asistencia"
PERSONAS_TAB = "personas"
ASISTENCIA_PERSONAS_TAB = "asistencia_personas"

# =====================================================
# GOOGLE SHEETS
# =====================================================
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
        return sh.add_worksheet(title=title, rows=1000, cols=20)

def read_ws(title):
    ws = get_ws(title)
    try:
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def append_row(title, row):
    ws = get_ws(title)
    ws.append_row(row, value_input_option="USER_ENTERED")

# =====================================================
# INIT PERSONAS DESDE CSV (NO ROMPE SI YA EXISTE)
# =====================================================
def init_personas():
    df = read_ws(PERSONAS_TAB)
    if not df.empty:
        return

    try:
        df_csv = pd.read_csv("datapersonas.csv")
        ws = get_ws(PERSONAS_TAB)
        ws.clear()
        ws.append_row(list(df_csv.columns))
        for _, r in df_csv.iterrows():
            ws.append_row(r.tolist())
    except:
        st.warning("No se pudo inicializar personas desde datapersonas.csv")

# =====================================================
# NUEVO: ASISTENCIA POR PERSONA (NO TOCA LO VIEJO)
# =====================================================
def guardar_asistencia_personas(fecha, centro, espacio, personas, usuario):
    ws = get_ws(ASISTENCIA_PERSONAS_TAB)
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

# =====================================================
# APP
# =====================================================
def main():
    st.title("📋 Asistencia – Hogar de Cristo")

    # usuario simple (NO tocamos auth vieja)
    usuario_actual = st.text_input("Usuario", value="")

    init_personas()

    centro = st.selectbox("Centro barrial", CENTROS)
    hoy = date.today().isoformat()
    anio = date.today().year

    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Asistencia general",
        "👥 Personas",
        "📊 Reportes",
        "🧾 Asistencia por persona"
    ])

    # =================================================
    # TAB 1 – ASISTENCIA GENERAL (ORIGINAL)
    # =================================================
    with tab1:
        st.subheader("Registrar asistencia del día")

        presentes = st.number_input("Cantidad total de presentes", min_value=0)
        coordinador = st.text_input("Quién carga la asistencia")
        modo = st.selectbox("Modo", ["Día habitual", "Actividad especial"])
        notas = st.text_area("Notas")

        if st.button("Guardar asistencia general"):
            ts = datetime.now().isoformat(timespec="seconds")
            append_row(ASISTENCIA_TAB, [
                ts,
                hoy,
                anio,
                centro,
                "General",
                presentes,
                coordinador,
                modo,
                notas,
                usuario_actual
            ])
            st.success("Asistencia general guardada")

    # =================================================
    # TAB 2 – PERSONAS (ORIGINAL)
    # =================================================
    with tab2:
        st.subheader("Personas registradas")

       if "centro" in df_personas.columns:
    df_centro = df_personas[df_personas["centro"] == centro]
else:
    df_centro = df_personas.copy()


        st.metric("Total personas", len(df_centro))
        st.dataframe(df_centro, use_container_width=True)

    # =================================================
    # TAB 3 – REPORTES (ORIGINAL)
    # =================================================
    with tab3:
        st.subheader("Reportes")

        df = read_ws(ASISTENCIA_TAB)
        if df.empty:
            st.info("No hay datos todavía")
        else:
            df_c = df[(df["centro"] == centro) & (df["anio"] == anio)]
            st.metric(
                "Total presentes registrados",
                int(df_c["presentes"].sum()) if not df_c.empty else 0
            )
            st.dataframe(df_c.sort_values("fecha", ascending=False),
                         use_container_width=True)

    # =================================================
    # TAB 4 – NUEVO: ASISTENCIA POR PERSONA
    # =================================================
    with tab4:
        st.subheader("Asistencia nominal (por persona)")

        df_personas = read_ws(PERSONAS_TAB)
        df_centro = df_personas[df_personas.get("centro", "") == centro]

        personas_hoy = st.multiselect(
            "Personas que asistieron hoy",
            options=df_centro["nombre"].tolist() if not df_centro.empty else []
        )

        if st.button("Guardar asistencia por persona"):
            guardar_asistencia_personas(
                fecha=hoy,
                centro=centro,
                espacio="General",
                personas=personas_hoy,
                usuario=usuario_actual
            )
            st.success("Asistencia por persona guardada")

# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    main()

