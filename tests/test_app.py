from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_boots_without_exceptions():
    app = Path(__file__).resolve().parent.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=30).run()
    assert not at.exception
    assert len(at.selectbox) == 1
    assert len(at.button) >= 2

