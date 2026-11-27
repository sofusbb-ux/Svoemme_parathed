import base64
import os
import re
from datetime import date, datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- KONFIGURATION ---
st.set_page_config(
    page_title="AGF Svømning – Performance Dashboard",
    page_icon="⚪",
    layout="wide",
)

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4z1vstw_vNusCuZdgYesIYbmvI52mD3sYKlTykpk370wyGAnfpbdru0VCj7c7CX9JBWzeBi_d1Evf/pub?gid=941831444&single=true&output=csv"
ATHLETE_NAME = "Sofus Balladone"
LOGO_FILE = "agf_logo.png"

# Faste træningstider (0 = Mandag ... 6 = Søndag)
TRAINING_SCHEDULE = {
    0: {"dag": "Mandag", "pas": ["Morgen: 05:50 – 07:30", "Aften: 15:45 – 17:45"]},
    1: {"dag": "Tirsdag", "pas": ["Morgen: 05:50 – 07:30", "Aften: 15:30 – 17:30"]},
    2: {"dag": "Onsdag", "pas": ["Aften: 15:30 – 17:30"]},
    3: {"dag": "Torsdag", "pas": ["Morgen: 05:50 – 07:30", "Aften: 16:00 – 18:00"]},
    4: {"dag": "Fredag", "pas": ["Morgen: 05:50 – 07:30"]},
    5: {"dag": "Lørdag", "pas": ["Morgen: 06:00 – 08:00"]},
    6: {"dag": "Søndag", "pas": ["Ingen fast planlagt træning"]},
}


# --- INDLÆS LOGO TIL BAGGRUND & SIDEBAR ---
def get_base64_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


logo_b64 = get_base64_image(LOGO_FILE)

# --- AGF.DK FARVETEMA & FIFA 13 RESTITUTIONSBAR (CSS) ---
watermark_css = (
    f"""
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url("data:image/png;base64,{logo_b64}");
        background-repeat: no-repeat;
        background-position: 56% center;
        background-size: 460px;
        opacity: 0.08;
        filter: grayscale(1) invert(1) contrast(2);
        mix-blend-mode: screen;
        pointer-events: none;
        z-index: 0;
    }}
    """
    if logo_b64
    else ""
)

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@600;700;800&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}

    /* AGF.dk dyb midnatsblå baggrund */
    .stApp {{
        background-color: #131727;
        color: #ffffff;
    }}

    {watermark_css}

    /* AGF.dk overskrifter i Montserrat */
    h1 {{
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 0.02em !important;
        color: #ffffff !important;
        font-size: 2.05rem !important;
        margin-bottom: 0.25rem !important;
    }}

    h2, h3 {{
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em !important;
        color: #ffffff !important;
    }}

    /* Sidebar i mørkere AGF-marine */
    [data-testid="stSidebar"] {{
        background-color: #0e111e;
        border-right: 1px solid rgba(255, 255, 255, 0.14);
    }}

    .sidebar-logo {{
        width: 125px;
        filter: grayscale(1) invert(1) contrast(2);
        mix-blend-mode: screen;
        margin-bottom: 8px;
    }}

    /* Micro-labels (uppercase i AGF-stil) */
    .agf-label {{
        font-family: 'Montserrat', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #b8c0d4;
        margin-bottom: 6px;
    }}

    /* AGF.dk kort med skarp kant */
    .agf-card {{
        background-color: rgba(27, 32, 54, 0.88);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 6px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }}

    .agf-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 14px;
        margin-bottom: 16px;
    }}

    .agf-kpi {{
        background-color: rgba(27, 32, 54, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 6px;
        padding: 14px 16px;
    }}

    .agf-kpi-value {{
        font-family: 'Montserrat', sans-serif;
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        line-height: 1.2;
    }}

    .agf-kpi-unit {{
        font-family: 'Inter', sans-serif;
        font-size: 0.88rem;
        font-weight: 500;
        color: #9ba5be;
    }}

    /* Træningsplan-banner i AGF-stil */
    .agf-schedule {{
        background-color: rgba(27, 32, 54, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-left: 4px solid #ffffff;
        border-radius: 6px;
        padding: 13px 18px;
        margin-bottom: 22px;
        font-size: 0.92rem;
        color: #ffffff;
    }}

    /* AGF.dk pille-formede hvide knapper */
    .stButton>button, [data-testid="stFormSubmitButton"]>button {{
        background-color: #ffffff !important;
        color: #131727 !important;
        border: none !important;
        border-radius: 999px !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.76rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        padding: 0.55rem 1.35rem !important;
        transition: all 0.2s ease !important;
    }}

    .stButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {{
        background-color: #e2e6f0 !important;
        transform: translateY(-1px);
    }}

    /* FIFA 13 Restitutionsbar */
    .cylinder-bar-bg {{
        background: #0e111e;
        border: 1.5px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        height: 26px;
        width: 100%;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.7);
        margin-top: 10px;
    }}

    .cylinder-bar-fill {{
        height: 100%;
        border-radius: 10px 0 0 10px;
        box-shadow: inset 0 6px 10px rgba(255,255,255,0.35), inset 0 -6px 10px rgba(0,0,0,0.4);
        transition: width 0.5s ease-in-out;
    }}

    .glow-green {{
        background: linear-gradient(180deg, #5eff33 0%, #32b305 50%, #1e6d02 100%);
    }}
    .glow-yellow {{
        background: linear-gradient(180deg, #ffee33 0%, #b39b05 50%, #6d5d02 100%);
    }}
    .glow-red {{
        background: linear-gradient(180deg, #ff3333 0%, #b30505 50%, #6d0202 100%);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --- BEREGNING & DATAHENTNING ---
def clean_danish_timestamp(val: str) -> str:
    s = str(val).strip()
    s = re.sub(r"(\d{1,2})\.(\d{2})\.(\d{2})", r"\1:\2:\3", s)
    return s


def calc_readiness_score(soevn: float, mental: float, fysisk: float) -> float:
    soevn_score = min(10.0, max(1.0, (soevn / 8.0) * 10.0))
    return round((soevn_score + mental + fysisk) / 3.0, 1)


def get_readiness_status(score: float):
    if score >= 7.5:
        return "Klar til fuld belastning", "glow-green"
    elif score >= 5.5:
        return "Moderat parathed – overvej justering", "glow-yellow"
    else:
        return "Lav parathed – tag en snak / sænk volumen", "glow-red"


@st.cache_data(ttl=60)
def load_sheet_data(url: str) -> pd.DataFrame:
    if not url or "INDSÆT_DIT_CSV_LINK_HER" in url:
        return pd.DataFrame()

    raw = pd.read_csv(url)
    if raw.empty or raw.shape[1] < 4:
        return pd.DataFrame()

    df = pd.DataFrame()
    ts_clean = raw.iloc[:, 0].apply(clean_danish_timestamp)
    df["timestamp"] = pd.to_datetime(ts_clean, dayfirst=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    df["dato"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["tidspunkt_sendt"] = df["timestamp"].dt.strftime("%H:%M")

    df["soevn_timer"] = pd.to_numeric(
        raw.loc[df.index, raw.columns[1]].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    df["mental_friskhed"] = pd.to_numeric(raw.loc[df.index, raw.columns[2]], errors="coerce")
    df["fysisk_friskhed"] = pd.to_numeric(raw.loc[df.index, raw.columns[3]], errors="coerce")

    if raw.shape[1] >= 5:
        df["kommentar"] = raw.loc[df.index, raw.columns[4]].fillna("").astype(str).str.slice(0, 50)
    else:
        df["kommentar"] = ""

    df = df.sort_values("timestamp").drop_duplicates(subset=["dato"], keep="last").reset_index(drop=True)

    df["samlet_score"] = df.apply(
        lambda r: calc_readiness_score(
            float(r["soevn_timer"]),
            float(r["mental_friskhed"]),
            float(r["fysisk_friskhed"]),
        ),
        axis=1,
    )
    return df


def check_deadline_status(tid_str: str) -> str:
    try:
        t = datetime.strptime(tid_str, "%H:%M").time()
        if t <= datetime.strptime("12:00", "%H:%M").time():
            return f"Modtaget kl. {tid_str} · Inden deadline (12:00)"
        return f"Modtaget sent kl. {tid_str} · Efter deadline (12:00)"
    except Exception:
        return f"Modtaget kl. {tid_str}"


# --- PINKODE-BESKYTTELSE ---
def get_coach_pin() -> str:
    try:
        return str(st.secrets["COACH_PIN"])
    except Exception:
        return "5711"


if "coach_logged_in" not in st.session_state:
    st.session_state["coach_logged_in"] = False

if not st.session_state["coach_logged_in"]:
    st.markdown('<div class="agf-label">AGF SVØMNING · PERFORMANCE</div>', unsafe_allow_html=True)
    st.title("Træner Login")
    st.write("Indtast pinkode for at tilgå atletdata.")
    with st.form("login_form"):
        pin_input = st.text_input("Pinkode", type="password", max_chars=10)
        submitted = st.form_submit_button("Log ind →")
        if submitted:
            if pin_input == get_coach_pin():
                st.session_state["coach_logged_in"] = True
                st.rerun()
            else:
                st.error("Forkert pinkode. Prøv igen.")
    st.stop()


# --- SIDEBAR ---
with st.sidebar:
    if logo_b64:
        st.markdown(
            f'<img src="data:image/png;base64,{logo_b64}" class="sidebar-logo" alt="AGF Svømning">',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="agf-label">AGF SVØMNING · PERFORMANCE</div>', unsafe_allow_html=True)
    st.selectbox("Vælg atlet", [ATHLETE_NAME])

    if st.button("Opdatér data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Synkroniserer automatisk med Google Sheets hvert minut.")


# --- TRÆNER-DASHBOARD ---
st.markdown('<div class="agf-label">ATLET-OVERBLIK · DAGLIG PARATHED</div>', unsafe_allow_html=True)
st.title(f"{ATHLETE_NAME}")

if "INDSÆT_DIT_CSV_LINK_HER" in SHEET_CSV_URL:
    st.error("Husk at indsætte dit Google Sheets `.csv`-link i `SHEET_CSV_URL` i `app.py`.")
    st.stop()

try:
    df = load_sheet_data(SHEET_CSV_URL)
except Exception as e:
    st.error(f"Kunne ikke hente data fra Google Sheets. Fejl: {e}")
    st.stop()

valgt_dato = st.date_input("Træningsdato", value=date.today())
valgt_dato_str = valgt_dato.isoformat()
ugedag_info = TRAINING_SCHEDULE[valgt_dato.weekday()]
pas_tekst = "  ·  ".join(ugedag_info["pas"])

st.markdown(
    f"""
    <div class="agf-schedule">
        <span style="color:#b8c0d4; font-family:'Montserrat',sans-serif; font-weight:700; text-transform:uppercase; font-size:0.75rem; letter-spacing:0.08em;">
            {ugedag_info['dag']} {valgt_dato.strftime('%d/%m/%Y')}
        </span><br>
        <strong>Planlagte pas:</strong> {pas_tekst}
    </div>
    """,
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1, 1.35], gap="large")

with col_left:
    st.markdown('<div class="agf-label">DAGENS STATUS</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("Ingen svar fundet i Google Sheetet endnu.")
    else:
        dagens_raekke = df[df["dato"] == valgt_dato_str]

        if dagens_raekke.empty:
            st.warning(f"Ingen melding modtaget fra {ATHLETE_NAME} for denne dato endnu (deadline kl. 12:00).")
        else:
            row = dagens_raekke.iloc[-1]
            score = float(row["samlet_score"])
            status_tekst, fill_class = get_readiness_status(score)
            percentage = int(score * 10)
            deadline_txt = check_deadline_status(str(row["tidspunkt_sendt"]))

            # Paratheds-kort med FIFA 13 restitutionsbar
            st.markdown(
                f"""
                <div class="agf-card">
                    <div class="agf-label">SAMLET PARATHEDSSCORE</div>
                    <div style="display:flex; align-items:baseline; justify-content:space-between;">
                        <span style="font-family:'Montserrat',sans-serif; font-size: 2.15rem; font-weight: 800; letter-spacing: -0.02em; color: #ffffff;">
                            {score} <span style="font-family:'Inter',sans-serif; font-size: 1rem; font-weight: 500; color: #9ba5be;">/ 10</span>
                        </span>
                        <span style="font-size: 0.9rem; font-weight: 600; color: #ffffff;">{status_tekst}</span>
                    </div>
                    <div class="cylinder-bar-bg">
                        <div class="cylinder-bar-fill {fill_class}" style="width: {percentage}%;"></div>
                    </div>
                    <div style="font-size: 0.78rem; color: #9ba5be; margin-top: 10px;">{deadline_txt}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 3 KPI-kort
            st.markdown(
                f"""
                <div class="agf-kpi-grid">
                    <div class="agf-kpi">
                        <div class="agf-label">SØVN</div>
                        <div class="agf-kpi-value">{row['soevn_timer']} <span class="agf-kpi-unit">t</span></div>
                    </div>
                    <div class="agf-kpi">
                        <div class="agf-label">MENTAL</div>
                        <div class="agf-kpi-value">{int(row['mental_friskhed'])} <span class="agf-kpi-unit">/ 10</span></div>
                    </div>
                    <div class="agf-kpi">
                        <div class="agf-label">FYSISK</div>
                        <div class="agf-kpi-value">{int(row['fysisk_friskhed'])} <span class="agf-kpi-unit">/ 10</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Kommentar-kort
            kommentar = str(row["kommentar"]).strip()
            kommentar_indhold = f'"{kommentar}"' if kommentar else "Ingen kommentar tilføjet."
            kommentar_farve = "#ffffff" if kommentar else "#9ba5be"
            st.markdown(
                f"""
                <div class="agf-card">
                    <div class="agf-label">ATLET-KOMMENTAR</div>
                    <div style="font-size: 0.95rem; color: {kommentar_farve}; font-style: italic;">
                        {kommentar_indhold}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("Polar Verity Sense · Træningsdata", expanded=False):
        st.caption("Klargøres til automatisk synkronisering via Polar AccessLink API.")

with col_right:
    st.markdown('<div class="agf-label">TENDENS · SIDSTE 7 MÅLINGER</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Ingen historik endnu.")
    else:
        df_hist = df[df["dato"] <= valgt_dato_str].tail(7).copy()

        if df_hist.empty:
            st.info("Ingen målinger på eller før den valgte dato.")
        else:
            df_hist["dato_label"] = pd.to_datetime(df_hist["dato"]).dt.strftime("%d/%m")

            fig = go.Figure()

            # 1. De tre baggrundslinjer (nedtonede)
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["fysisk_friskhed"],
                    mode="lines+markers",
                    name="Fysisk (1-10)",
                    line=dict(color="rgba(74, 222, 128, 0.42)", width=1.8),
                    marker=dict(size=5, color="rgba(74, 222, 128, 0.55)"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["mental_friskhed"],
                    mode="lines+markers",
                    name="Mental (1-10)",
                    line=dict(color="rgba(96, 165, 250, 0.42)", width=1.8),
                    marker=dict(size=5, color="rgba(96, 165, 250, 0.55)"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["soevn_timer"],
                    mode="lines+markers",
                    name="Søvn (timer)",
                    line=dict(color="rgba(184, 192, 212, 0.42)", width=1.6, dash="dot"),
                    marker=dict(size=5, color="rgba(184, 192, 212, 0.55)"),
                )
            )

            # 2. Samlet parathedsscore (tydelig hvid hovedlinje øverst)
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["samlet_score"],
                    mode="lines+markers",
                    name="Samlet parathed",
                    line=dict(color="#ffffff", width=4),
                    marker=dict(
                        size=10,
                        color="#ffffff",
                        line=dict(width=2, color="#131727"),
                    ),
                )
            )

            fig.add_hline(
                y=5,
                line_dash="dash",
                line_color="rgba(239, 68, 68, 0.45)",
                annotation_text="OBS-grænse (5)",
                annotation_position="bottom right",
                annotation_font=dict(color="#f87171", size=11),
            )

            fig.update_layout(
                font=dict(family="Inter, sans-serif", color="#b8c0d4"),
                paper_bgcolor="rgba(27, 32, 54, 0.88)",
                plot_bgcolor="rgba(0, 0, 0, 0)",
                yaxis=dict(
                    range=[0, 10.5],
                    title="Score / Timer",
                    gridcolor="rgba(255, 255, 255, 0.08)",
                    zerolinecolor="rgba(255, 255, 255, 0.12)",
                    tickfont=dict(color="#b8c0d4"),
                ),
                xaxis=dict(
                    title="Dato",
                    gridcolor="rgba(255, 255, 255, 0.08)",
                    tickfont=dict(color="#b8c0d4"),
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.03,
                    xanchor="left",
                    x=0,
                    font=dict(color="#ffffff", size=12),
                ),
                margin=dict(l=16, r=16, t=48, b=16),
                height=395,
                hovermode="x unified",
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Se rå tal for de sidste 7 målinger"):
                vis_df = df_hist[
                    ["dato", "samlet_score", "soevn_timer", "mental_friskhed", "fysisk_friskhed", "kommentar"]
                ].rename(
                    columns={
                        "dato": "Dato",
                        "samlet_score": "Parathed",
                        "soevn_timer": "Søvn (t)",
                        "mental_friskhed": "Mental",
                        "fysisk_friskhed": "Fysisk",
                        "kommentar": "Kommentar",
                    }
                )
                st.dataframe(vis_df, use_container_width=True, hide_index=True)
