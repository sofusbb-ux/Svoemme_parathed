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
ATHLETE_NAME = "Sofus"
LOGO_FILE = "agf_logo.png"

# Faste træningstider (0 = Mandag ... 6 = Søndag)
TRAINING_SCHEDULE = {
    0: {"dag": "Mandag", "pas": ["Aften: 15:45 – 17:45"]},
    1: {"dag": "Tirsdag", "pas": ["Morgen: 05:50 – 07:30", "Aften: 15:30 – 17:30"]},
    2: {"dag": "Onsdag", "pas": ["Aften: 15:30 – 17:30"]},
    3: {"dag": "Torsdag", "pas": ["Morgen: 05:50 – 07:30", "Aften: 16:00 – 18:00"]},
    4: {"dag": "Fredag", "pas": ["Ingen fast planlagt træning"]},
    5: {"dag": "Lørdag", "pas": ["Ingen fast planlagt træning"]},
    6: {"dag": "Søndag", "pas": ["Ingen fast planlagt træning"]},
}


# --- INDLÆS LOGO TIL BAGGRUND & SIDEBAR ---
def get_base64_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


logo_b64 = get_base64_image(LOGO_FILE)

# --- KITMAN LABS / AGF PERFORMANCE TEMA (CSS) ---
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}

    .stApp {{
        background: radial-gradient(circle at top right, #111c33 0%, #070b14 60%);
        color: #f8fafc;
    }}

    {watermark_css}

    /* Typografi i Kitman Labs-stil */
    h1 {{
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        color: #ffffff !important;
        font-size: 2.1rem !important;
        margin-bottom: 0.25rem !important;
    }}

    h2, h3 {{
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #e2e8f0 !important;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: #0b1120;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .sidebar-logo {{
        width: 125px;
        filter: grayscale(1) invert(1) contrast(2);
        mix-blend-mode: screen;
        margin-bottom: 8px;
    }}

    /* Micro-labels (uppercase) */
    .kl-label {{
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: #94a3b8;
        margin-bottom: 6px;
    }}

    /* Performance-kort */
    .kl-card {{
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 18px 20px;
        backdrop-filter: blur(8px);
        margin-bottom: 16px;
    }}

    .kl-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 14px;
        margin-bottom: 16px;
    }}

    .kl-kpi {{
        background: rgba(15, 23, 42, 0.78);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 14px 16px;
    }}

    .kl-kpi-value {{
        font-size: 1.65rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #ffffff;
        line-height: 1.2;
    }}

    .kl-kpi-unit {{
        font-size: 0.9rem;
        font-weight: 500;
        color: #64748b;
    }}

    /* Træningsplan-banner */
    .kl-schedule {{
        background: rgba(30, 58, 138, 0.22);
        border: 1px solid rgba(59, 130, 246, 0.35);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 20px;
        font-size: 0.92rem;
        color: #e2e8f0;
    }}

    /* Knapper */
    .stButton>button {{
        background-color: #ffffff !important;
        color: #070b14 !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        padding: 0.45rem 1rem !important;
    }}

    .stButton>button:hover {{
        background-color: #e2e8f0 !important;
    }}

    /* FIFA 13 Restitutionsbar */
    .cylinder-bar-bg {{
        background: #131c2e;
        border: 1.5px solid #26354d;
        border-radius: 12px;
        height: 26px;
        width: 100%;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.65);
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


# --- DATAHENTNING FRA GOOGLE SHEETS ---
def clean_danish_timestamp(val: str) -> str:
    s = str(val).strip()
    s = re.sub(r"(\d{1,2})\.(\d{2})\.(\d{2})", r"\1:\2:\3", s)
    return s


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

    df = df.sort_values("timestamp").drop_duplicates(subset=["dato"], keep="last")
    return df.reset_index(drop=True)


def calc_readiness(soevn: float, mental: float, fysisk: float):
    soevn_score = min(10.0, max(1.0, (soevn / 8.0) * 10.0))
    score = round((soevn_score + mental + fysisk) / 3.0, 1)

    if score >= 7.5:
        return score, "Klar til fuld belastning", "glow-green"
    elif score >= 5.5:
        return score, "Moderat parathed – overvej justering", "glow-yellow"
    else:
        return score, "Lav parathed – tag en snak / sænk volumen", "glow-red"


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
    st.markdown('<div class="kl-label">AGF SVØMNING · PERFORMANCE</div>', unsafe_allow_html=True)
    st.title("Træner Login")
    st.write("Indtast pinkode for at tilgå atletdata.")
    with st.form("login_form"):
        pin_input = st.text_input("Pinkode", type="password", max_chars=10)
        submitted = st.form_submit_button("Log ind")
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
    st.markdown('<div class="kl-label">AGF SVØMNING · PERFORMANCE</div>', unsafe_allow_html=True)
    st.selectbox("Vælg atlet", [ATHLETE_NAME])

    if st.button("Opdatér data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Synkroniserer automatisk med Google Sheets hvert minut.")


# --- TRÆNER-DASHBOARD ---
st.markdown('<div class="kl-label">ATLET-OVERBLIK · DAGLIG PARATHED</div>', unsafe_allow_html=True)
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
    <div class="kl-schedule">
        <span style="color:#93c5fd; font-weight:700; text-transform:uppercase; font-size:0.78rem; letter-spacing:0.06em;">
            {ugedag_info['dag']} {valgt_dato.strftime('%d/%m/%Y')}
        </span><br>
        <strong>Planlagte pas:</strong> {pas_tekst}
    </div>
    """,
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1, 1.35], gap="large")

with col_left:
    st.markdown('<div class="kl-label">DAGENS STATUS</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("Ingen svar fundet i Google Sheetet endnu.")
    else:
        dagens_raekke = df[df["dato"] == valgt_dato_str]

        if dagens_raekke.empty:
            st.warning(f"Ingen melding modtaget fra {ATHLETE_NAME} for denne dato endnu (deadline kl. 12:00).")
        else:
            row = dagens_raekke.iloc[-1]
            score, status_tekst, fill_class = calc_readiness(
                float(row["soevn_timer"]),
                float(row["mental_friskhed"]),
                float(row["fysisk_friskhed"]),
            )
            percentage = int(score * 10)
            deadline_txt = check_deadline_status(str(row["tidspunkt_sendt"]))

            # Paratheds-kort med FIFA 13 restitutionsbar
            st.markdown(
                f"""
                <div class="kl-card">
                    <div class="kl-label">SAMLET PARATHEDSSCORE</div>
                    <div style="display:flex; align-items:baseline; justify-content:space-between;">
                        <span style="font-size: 2.1rem; font-weight: 800; letter-spacing: -0.03em; color: #ffffff;">
                            {score} <span style="font-size: 1rem; font-weight: 500; color: #64748b;">/ 10</span>
                        </span>
                        <span style="font-size: 0.9rem; font-weight: 600; color: #cbd5e1;">{status_tekst}</span>
                    </div>
                    <div class="cylinder-bar-bg">
                        <div class="cylinder-bar-fill {fill_class}" style="width: {percentage}%;"></div>
                    </div>
                    <div style="font-size: 0.78rem; color: #64748b; margin-top: 10px;">{deadline_txt}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 3 KPI-kort i Kitman Labs-stil
            st.markdown(
                f"""
                <div class="kl-kpi-grid">
                    <div class="kl-kpi">
                        <div class="kl-label">SØVN</div>
                        <div class="kl-kpi-value">{row['soevn_timer']} <span class="kl-kpi-unit">t</span></div>
                    </div>
                    <div class="kl-kpi">
                        <div class="kl-label">MENTAL</div>
                        <div class="kl-kpi-value">{int(row['mental_friskhed'])} <span class="kl-kpi-unit">/ 10</span></div>
                    </div>
                    <div class="kl-kpi">
                        <div class="kl-label">FYSISK</div>
                        <div class="kl-kpi-value">{int(row['fysisk_friskhed'])} <span class="kl-kpi-unit">/ 10</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Kommentar-kort
            kommentar = str(row["kommentar"]).strip()
            kommentar_indhold = f'"{kommentar}"' if kommentar else "Ingen kommentar tilføjet."
            kommentar_farve = "#e2e8f0" if kommentar else "#64748b"
            st.markdown(
                f"""
                <div class="kl-card">
                    <div class="kl-label">ATLET-KOMMENTAR</div>
                    <div style="font-size: 0.95rem; color: {kommentar_farve}; font-style: italic;">
                        {kommentar_indhold}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("Polar-sensor data (v2)", expanded=False):
        st.caption(
            "Her kobles puls, kcal og minutter i pulszone 1–5 på, når "
            "sensor-compliance er på plads."
        )

with col_right:
    st.markdown('<div class="kl-label">TENDENS · SIDSTE 7 MÅLINGER</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Ingen historik endnu.")
    else:
        df_hist = df[df["dato"] <= valgt_dato_str].tail(7).copy()

        if df_hist.empty:
            st.info("Ingen målinger på eller før den valgte dato.")
        else:
            df_hist["dato_label"] = pd.to_datetime(df_hist["dato"]).dt.strftime("%d/%m")

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["fysisk_friskhed"],
                    mode="lines+markers",
                    name="Fysisk (1-10)",
                    line=dict(color="#22c55e", width=3),
                    marker=dict(size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["mental_friskhed"],
                    mode="lines+markers",
                    name="Mental (1-10)",
                    line=dict(color="#3b82f6", width=3),
                    marker=dict(size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["soevn_timer"],
                    mode="lines+markers",
                    name="Søvn (timer)",
                    line=dict(color="#e2e8f0", width=2, dash="dot"),
                    marker=dict(size=7),
                )
            )

            fig.add_hline(
                y=5,
                line_dash="dash",
                line_color="rgba(239, 68, 68, 0.5)",
                annotation_text="OBS-grænse (5)",
                annotation_position="bottom right",
                annotation_font=dict(color="#f87171", size=11),
            )

            fig.update_layout(
                font=dict(family="Inter, sans-serif", color="#94a3b8"),
                paper_bgcolor="rgba(15, 23, 42, 0.72)",
                plot_bgcolor="rgba(0, 0, 0, 0)",
                yaxis=dict(
                    range=[0, 10.5],
                    title="Score / Timer",
                    gridcolor="rgba(255, 255, 255, 0.06)",
                    zerolinecolor="rgba(255, 255, 255, 0.08)",
                    tickfont=dict(color="#94a3b8"),
                ),
                xaxis=dict(
                    title="Dato",
                    gridcolor="rgba(255, 255, 255, 0.06)",
                    tickfont=dict(color="#94a3b8"),
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.03,
                    xanchor="left",
                    x=0,
                    font=dict(color="#e2e8f0", size=12),
                ),
                margin=dict(l=16, r=16, t=44, b=16),
                height=390,
                hovermode="x unified",
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Se rå tal for de sidste 7 målinger"):
                vis_df = df_hist[
                    ["dato", "soevn_timer", "mental_friskhed", "fysisk_friskhed", "kommentar"]
                ].rename(
                    columns={
                        "dato": "Dato",
                        "soevn_timer": "Søvn (t)",
                        "mental_friskhed": "Mental",
                        "fysisk_friskhed": "Fysisk",
                        "kommentar": "Kommentar",
                    }
                )
                st.dataframe(vis_df, use_container_width=True, hide_index=True)
