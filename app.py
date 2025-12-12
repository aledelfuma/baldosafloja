import streamlit as st
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from google.auth.exceptions import RefreshError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

st.title("Diagnóstico Google Sheets")

# ---------- Chequeo de secrets ----------
if "gcp_service_account" not in st.secrets:
    st.error("❌ Falta [gcp_service_account] en Secrets.")
    st.stop()

if "sheets" not in st.secrets or "spreadsheet_id" not in st.secrets["sheets"]:
    st.error("❌ Falta [sheets] → spreadsheet_id en Secrets.")
    st.stop()

sa = dict(st.secrets["gcp_service_account"])
sid = st.secrets["sheets"]["spreadsheet_id"]

# ---------- Mostrar datos seguros ----------
st.subheader("Datos detectados (seguros)")
st.write("client_email:", sa.get("client_email"))
st.write("project_id:", sa.get("project_id"))
st.write("token_uri:", sa.get("token_uri"))

pk = str(sa.get("private_key", ""))
st.write("private_key tiene BEGIN / END:",
         ("BEGIN PRIVATE KEY" in pk and "END PRIVATE KEY" in pk))
st.write("private_key largo:", len(pk))

# ---------- Normalizar private_key ----------
pk = pk.replace("\\n", "\n").strip()
if not pk.endswith("\n"):
    pk += "\n"
sa["private_key"] = pk

# ---------- Intentar autenticación ----------
try:
    creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
    creds.refresh(Request())
    st.success("✅ AUTH OK — Google aceptó el Service Account")

    session = AuthorizedSession(creds)
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"

    r = session.get(base)

    st.subheader("Resultado acceso a la planilla")
    st.write("Status HTTP:", r.status_code)
    st.code(r.text[:1200])

    if r.status_code == 200:
        st.success("✅ SHEETS OK — Puedo leer la planilla")
    else:
        st.error("❌ No pude acceder a la planilla")

except RefreshError as e:
    st.error("❌ RefreshError — Google rechazó la autenticación")
    st.code(str(e))
