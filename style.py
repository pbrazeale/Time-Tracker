from __future__ import annotations

import streamlit as st

from constants import (
    ACCENT_BLUE,
    APP_TITLE,
    LIGHT_TEXT,
    LOGO_PATH,
    PRIMARY_RED,
    ROYAL_PURPLE,
)


THEME_STYLE = """
<style>
:root {{
    --primary-red: {primary_red};
    --accent-blue: {accent_blue};
    --royal-purple: {royal_purple};
    --text-light: {light_text};
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba(30, 63, 128, 0.96), rgba(123, 31, 162, 0.88));
}}

[data-testid="stSidebar"] * {{
    color: var(--text-light) !important;
}}

.sidebar-app-title {{
    text-align: center;
    font-weight: 700;
    font-size: 1.4rem;
    margin: 0.5rem 0 0.75rem;
    letter-spacing: 0.03em;
}}

.sidebar-divider {{
    height: 1px;
    margin: 0.75rem 0 1.25rem;
    background: linear-gradient(90deg, transparent, var(--accent-blue), transparent);
}}
</style>
""".format(
    primary_red=PRIMARY_RED,
    accent_blue=ACCENT_BLUE,
    royal_purple=ROYAL_PURPLE,
    light_text=LIGHT_TEXT,
)


def apply_theme() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        page_icon=LOGO_PATH,
    )
    st.sidebar.image(LOGO_PATH, use_container_width=True)
    st.sidebar.markdown(
        f"<div class='sidebar-app-title'>{APP_TITLE}</div>"
        "<div class='sidebar-divider'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(THEME_STYLE, unsafe_allow_html=True)
