from streamlit_ui.app import run_app
from streamlit_ui.helpers import show_error

if __name__ == "__main__":
    try:
        run_app()
    except Exception as exc:
        show_error(exc, operation="app")
