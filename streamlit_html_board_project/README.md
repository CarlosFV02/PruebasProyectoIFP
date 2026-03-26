# Deep Naval Search - Streamlit + tablero HTML

Este proyecto adapta la versión web del tablero a **Streamlit** sin depender de un tablero hecho con botones por casilla.

## Estructura

```text
streamlit_html_board_project/
├─ streamlit_app.py
├─ components/
│  ├─ battleship_template.html
│  ├─ style.css
│  └─ app.js
├─ backend/
│  └─ game_logic.py
├─ assets/
│  └─ ships/
├─ .streamlit/
│  └─ config.toml
└─ requirements.txt
```

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Subir a GitHub y desplegar

1. Sube esta carpeta a un repositorio.
2. En Streamlit Community Cloud, conecta GitHub.
3. Selecciona el repo, la rama y el archivo principal `streamlit_app.py`.
4. Despliega la app.

## Nota

La interacción del juego ocurre dentro de un componente HTML incrustado, así que se evita el problema típico de Streamlit con rejillas de botones y reruns continuos.
