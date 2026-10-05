import streamlit as st


def apply_theme(theme):
    dark = theme == "Dark"
    colors = {
        "bg": "#0f172a" if dark else "#f7f9fc",
        "panel": "#172033" if dark else "#ffffff",
        "panel_soft": "#111827" if dark else "#eef6ff",
        "text": "#e5e7eb" if dark else "#172033",
        "muted": "#9ca3af" if dark else "#5b6472",
        "border": "#263244" if dark else "#dbe5f0",
        "accent": "#2dd4bf" if dark else "#0f766e",
        "accent_2": "#f59e0b" if dark else "#ea580c",
        "button_text": "#06231f" if dark else "#ffffff",
        "input": "#111827" if dark else "#ffffff",
        "shadow": "rgba(0, 0, 0, 0.35)" if dark else "rgba(15, 23, 42, 0.08)",
    }

    st.markdown(
        f"""
        <style>
        :root {{
            --app-bg: {colors["bg"]};
            --app-panel: {colors["panel"]};
            --app-panel-soft: {colors["panel_soft"]};
            --app-text: {colors["text"]};
            --app-muted: {colors["muted"]};
            --app-border: {colors["border"]};
            --app-accent: {colors["accent"]};
            --app-accent-2: {colors["accent_2"]};
            --app-button-text: {colors["button_text"]};
            --app-input: {colors["input"]};
            --app-shadow: {colors["shadow"]};
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, color-mix(in srgb, var(--app-accent) 16%, transparent), transparent 32rem),
                radial-gradient(circle at top right, color-mix(in srgb, var(--app-accent-2) 14%, transparent), transparent 28rem),
                var(--app-bg);
            color: var(--app-text);
        }}

        .block-container {{
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        h1, h2, h3, label, .stMarkdown, .stCaptionContainer, .stTextInput label,
        .stTextArea label, .stCheckbox label, .stFileUploader label {{
            color: var(--app-text) !important;
        }}

        .stRadio label,
        .stRadio label span,
        .stRadio div[role="radiogroup"] label,
        .stRadio div[role="radiogroup"] label span,
        .stCheckbox label,
        .stCheckbox label span,
        div[data-baseweb="radio"] label,
        div[data-baseweb="radio"] label span,
        div[data-baseweb="checkbox"] label,
        div[data-baseweb="checkbox"] label span {{
            color: var(--app-text) !important;
            opacity: 1 !important;
        }}

        .stRadio p,
        .stCheckbox p,
        div[data-testid="stWidgetLabel"] p {{
            color: var(--app-text) !important;
            opacity: 1 !important;
        }}

        h1 {{
            font-size: 2.6rem !important;
            line-height: 1.1 !important;
            margin-bottom: 0.35rem !important;
        }}

        h2, h3 {{
            letter-spacing: 0 !important;
        }}

        .stCaptionContainer, .stMarkdown p {{
            color: var(--app-muted) !important;
        }}

        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stTextInput"]),
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stFileUploader"]),
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stTextArea"]) {{
            background: var(--app-panel);
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 1rem 1rem 0.85rem;
            box-shadow: 0 14px 36px var(--app-shadow);
        }}

        div[data-testid="stTabs"] [role="tablist"] {{
            gap: 0.4rem;
            border-bottom: 1px solid var(--app-border);
        }}

        div[data-testid="stTabs"] button[role="tab"] {{
            background: transparent;
            border-radius: 8px 8px 0 0;
            color: var(--app-muted);
            padding: 0.65rem 0.9rem;
        }}

        div[data-testid="stTabs"] button[aria-selected="true"] {{
            color: var(--app-text);
            border-bottom: 3px solid var(--app-accent);
            background: color-mix(in srgb, var(--app-accent) 12%, transparent);
        }}

        input, textarea, div[data-baseweb="select"] > div {{
            background: var(--app-input) !important;
            color: var(--app-text) !important;
            border-color: var(--app-border) !important;
            border-radius: 8px !important;
        }}

        input:focus, textarea:focus {{
            border-color: var(--app-accent) !important;
            box-shadow: 0 0 0 2px color-mix(in srgb, var(--app-accent) 28%, transparent) !important;
        }}

        .stButton > button, .stDownloadButton > button {{
            border: 0 !important;
            border-radius: 8px !important;
            background: linear-gradient(135deg, var(--app-accent), var(--app-accent-2)) !important;
            color: var(--app-button-text) !important;
            font-weight: 700 !important;
            box-shadow: 0 12px 26px color-mix(in srgb, var(--app-accent) 26%, transparent);
        }}

        .stButton > button:hover, .stDownloadButton > button:hover {{
            filter: brightness(1.05);
            transform: translateY(-1px);
        }}

        div[data-testid="stExpander"] {{
            background: var(--app-panel);
            border: 1px solid var(--app-border);
            border-radius: 8px;
        }}

        div[data-testid="stAlert"] {{
            border-radius: 8px;
        }}

        section[data-testid="stSidebar"] {{
            background: var(--app-panel-soft);
            border-right: 1px solid var(--app-border);
        }}

        .app-hero {{
            background: linear-gradient(135deg, color-mix(in srgb, var(--app-panel) 88%, var(--app-accent)), var(--app-panel));
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 1.25rem 1.35rem;
            box-shadow: 0 18px 42px var(--app-shadow);
            margin-bottom: 1rem;
        }}

        .app-hero p {{
            color: var(--app-muted);
            margin: 0.35rem 0 0;
            max-width: 760px;
        }}

        .metric-row {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 1rem 0 1.25rem;
        }}

        .metric-pill {{
            background: var(--app-panel);
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 0.75rem 0.85rem;
            box-shadow: 0 10px 24px var(--app-shadow);
        }}

        .metric-pill strong {{
            color: var(--app-accent);
            display: block;
            font-size: 0.82rem;
            text-transform: uppercase;
        }}

        .metric-pill span {{
            color: var(--app-text);
            font-weight: 650;
        }}

        @media (max-width: 760px) {{
            .metric-row {{
                grid-template-columns: 1fr;
            }}
            h1 {{
                font-size: 2rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
