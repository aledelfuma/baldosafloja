PRIMARY_COLOR = "#004E7B"   # Azul Hogar
ACCENT_COLOR = "#63296C"    # Violeta Hogar
BG_COLOR = "#EAF2F6"        # Fondo azul muy claro
CARD_BG = "#F5EFF7"         # Fondo violeta muy claro
TEXT_DARK = "#1A1A1A"

CUSTOM_CSS = f"""
<style>
/* ----- Fondo general ----- */
body {{
    background-color: {BG_COLOR};
    color: {TEXT_DARK};
}}

section.main > div {{
    padding-top: 0.5rem;
}}

/* ----- Títulos ----- */
h1, h2, h3, h4 {{
    color: {PRIMARY_COLOR};
    font-family: "Helvetica", "Arial", sans-serif;
}}

/* ----- Métricas (tarjetitas) ----- */
.stMetric {{
    background-color: {CARD_BG} !important;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    border-left: 6px solid {ACCENT_COLOR};
}}

/* ----- Tabs ----- */
.stTabs [role="tab"] {{
    border-radius: 999px;
    padding: 0.5rem 1.1rem;
    margin-right: 0.3rem;
    background-color: white;
    border: 1px solid rgba(0,0,0,0.1);
    font-weight: 500;
    color: {PRIMARY_COLOR};
}}
.stTabs [aria-selected="true"] {{
    background-color: {PRIMARY_COLOR};
    color: white !important;
    border-color: {PRIMARY_COLOR};
}}

/* ----- Botones ----- */
.stButton>button {{
    border-radius: 999px;
    border: none;
    padding: 0.45rem 1.2rem;
    font-weight: 600;
    background-color: {PRIMARY_COLOR};
    color: white;
}}
.stButton>button:hover {{
    background-color: {ACCENT_COLOR};
    color: white;
}}

/* ----- Sidebar ----- */
[data-testid="stSidebar"] {{
    background-color: white;
    border-right: 3px solid {PRIMARY_COLOR};
}}

/* ----- Inputs ----- */
input, select, textarea {{
    border-radius: 6px !important;
}}

/* ----- Tablas ----- */
[data-testid="stDataFrame"] {{
    background-color: white;
    border-radius: 8px;
    padding: 0.6rem;
}}

</style>
"""
