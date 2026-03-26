from pathlib import Path
import base64
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Deep Naval Search", page_icon="🚢", layout="wide")

ROOT = Path(__file__).parent
COMP = ROOT / "components"
ASSETS = ROOT / "assets" / "ships"


def img_to_data_uri(path: Path) -> str:
    mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_html() -> str:
    html = (COMP / "battleship_template.html").read_text(encoding="utf-8")
    css = (COMP / "style.css").read_text(encoding="utf-8")
    js = (COMP / "app.js").read_text(encoding="utf-8")

    replacements = {
        "/static/ships/portaaviones.png": img_to_data_uri(ASSETS / "portaaviones.png"),
        "/static/ships/acorazado.png": img_to_data_uri(ASSETS / "acorazado.png"),
        "/static/ships/crucero.png": img_to_data_uri(ASSETS / "crucero.png"),
        "/static/ships/submarino.png": img_to_data_uri(ASSETS / "submarino.png"),
        "/static/ships/destructor.png": img_to_data_uri(ASSETS / "destructor.png"),
        "/static/ships/barcos.png": img_to_data_uri(ASSETS / "barcos.png"),
    }
    for old, new in replacements.items():
        js = js.replace(old, new)

    html = html.replace("{{STYLE_CSS}}", css)
    html = html.replace("{{APP_JS}}", js)
    return html


st.title("🚢 Deep Naval Search")
st.caption("Versión para Streamlit con tablero HTML/CSS/JS incrustado. Lista para subir a GitHub y desplegar en Streamlit Community Cloud.")

with st.sidebar:
    st.header("Cómo usarlo")
    st.markdown(
        """
- Coloca la flota en el tablero izquierdo.
- Usa **Rotar barco** para cambiar orientación.
- Pulsa **Comenzar partida** cuando estén los 5 barcos.
- Juega contra la IA y revisa pestañas de heatmap y registro.
        """
    )
    st.info("Toda la interacción del tablero ocurre dentro del componente HTML, por eso aquí no dependes de botones por casilla de Streamlit.")

components.html(build_html(), height=1750, scrolling=True)
