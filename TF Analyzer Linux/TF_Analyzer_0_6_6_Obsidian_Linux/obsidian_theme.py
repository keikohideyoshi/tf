
import streamlit as st

BG = "#0B101A"
PANEL = "#151E2B"
BRONZE = "#B79A69"
TURQUOISE = "#44C9C2"
EMERALD = "#5BC49A"
TEXT = "#E8EDF4"
MUTED = "#9AAFC1"

def apply_obsidian():
    st.markdown("""
    <style>
    :root { color-scheme: dark; }
    .stApp, [data-testid="stAppViewContainer"] {
        background: radial-gradient(ellipse at 82% 0%, #122332 0%, #0b101a 43%, #090d15 100%);
        color: #E8EDF4;
    }
    [data-testid="stHeader"] { background: rgba(11,16,26,.92); }
    [data-testid="stSidebar"] { background: #101927; border-right: 1px solid #293849; }
    [data-testid="stSidebar"] * { color: #E8EDF4; }
    h1, h2, h3 { color: #E8EDF4 !important; letter-spacing: .012em; }
    h2, h3 { border-bottom: 1px solid rgba(183,154,105,.22); padding-bottom: .3rem; }
    p, label { line-height: 1.5; }
    [data-testid="stMetric"] {
        background: #151E2B;
        border: 1px solid #293849;
        border-top: 2px solid #B79A69;
        border-radius: 10px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #9AAFC1; }
    [data-testid="stMetricValue"] { color: #44C9C2; }
    button[data-baseweb="tab"] { color: #AFC0D1; font-weight: 550; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #44C9C2 !important; }
    [data-baseweb="tab-highlight"] { background-color: #44C9C2 !important; }
    [data-testid="stDataFrame"], [data-testid="stFileUploader"],
    [data-testid="stAlert"] { border-radius: 10px; }
    [data-testid="stFileUploader"] { border: 1px solid #293849; }
    .stButton > button[kind="primary"] {
        background: #176d70;
        border: 1px solid #44C9C2;
        color: white;
    }
    .stButton > button[kind="primary"]:hover { background: #208489; }
    [data-testid="stDownloadButton"] button {
        border-color: #B79A69;
        color: #E8EDF4;
    }
    [data-testid="stHorizontalBlock"] { row-gap: .6rem; }
    .obsidian-subtitle {
        color: #9AAFC1;
        font-size: .86rem;
        margin: .35rem 0 1.1rem;
        letter-spacing: .02em;
    }
    .obsidian-divider {
        height: 1px;
        background: linear-gradient(90deg, #B79A69 0%, #2a3b4b 60%, transparent 100%);
        margin: 0 0 1.1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def show_banner():
    st.markdown(
        '<div style="font-size:2.25rem;font-weight:750;letter-spacing:.025em;'
        'color:#B79A69;margin:.25rem 0 .1rem">TF Analyzer</div>'
        '<div class="obsidian-subtitle">TÚLÉLŐK FÖLDJE · FORDULÓELEMZŐ</div>'
        '<div class="obsidian-divider"></div>',
        unsafe_allow_html=True,
    )

def themed_chart(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="sans-serif", size=13),
        title=dict(font=dict(color=TEXT, size=17)),
        margin=dict(l=30, r=24, t=58, b=36),
        colorway=[TURQUOISE, EMERALD, BRONZE],
        xaxis=dict(gridcolor="#293849", zerolinecolor="#293849"),
        yaxis=dict(gridcolor="#293849", zerolinecolor="#293849"),
        hoverlabel=dict(bgcolor="#223246", font_color=TEXT),
    )
    fig.update_traces(marker_color=TURQUOISE, selector=dict(type="bar"))
    return fig
