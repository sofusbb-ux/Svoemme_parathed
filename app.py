from datetime import date, datetime
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- CONFIGURATION & AGF TEMA ---
st.set_page_config(
    page_title="AGF Svømning – Træner Dashboard",
    page_icon="⚪",
    layout="wide",
)

# Indsæt dit Google Sheets .csv-link herunder:
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4z1vstw_vNusCuZdgYesIYbmvI52mD3sYKlTykpk370wyGAnfpbdru0VCj7c7CX9JBWzeBi_d1Evf/pub?gid=941831444&single=true&output=csv"
ATHLETE_NAME = "Sofus"

# AGF Logo og styling (mørkeblå, hvid, grå)
AGF_LOGO_URL = "https://images.squarespace-cdn.com/content/v1/5ea04c7df8b64a2754687d65/1589363388719-75S4E6G4ZOWUEMN1A6NZ/AGF_Svoemning_Logo.png"

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

# Tilpasning af AGF visualisering (CSS)
st.markdown(
    """
    <style>
    /* Generel mørk baggrund og AGF hvid/mørkeblå skrift */
    .stApp {
        background-color: #0c121c;
        color: #ffffff;
    }

    /* AGF vandmærke i baggrunden i midten */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url("https://upload.wikimedia.org/wikipedia/commons/e/e6/AGF_logo.svg");
        background-repeat: no-repeat;
        background-position: 55% center;
        background-size: 450px;
        opacity: 0.06;
        filter: brightness(0) invert(1);
        pointer-events: none;
        z-index: 0;
    }
    /* Sidebaren */
    [data-testid="stSidebar"] {
        background-color: #111a28;
        border-right: 1px solid #1f2e45;
    }
    
    /* Info bokse mørkeblå */
    .stAlert {
        background-color: #162438 !important;
        border: 1px solid #0056b3 !important;
        color: #ffffff !important;
    }
    
    /* Knapper */
    .stButton>button {
        background-color: #ffffff !important;
        color: #0c121c !important;
        border-radius: 4px;
        font-weight: bold;
    }
    
    /* FIFA 13 Restitutionsbar styling */
    .cylinder-bar-bg {
        background: #1d2836;
        border: 2px solid #2e3e53;
        border-radius: 12px;
        height: 28px;
        width: 100%;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.6), 0 1px 0 rgba(255,255,255,0.05);
    }
    
    .cylinder-bar-fill {
        height: 100%;
        border-radius: 10px 0 0 10px;
        box-shadow: inset 0 6px 12px rgba(255,255,255,0.4), inset 0 -6px 12px rgba(0,0,0,0.4);
        transition: width 0.5s ease-in-out;
    }
    
    /* Grøn glød ved god restitution */
    .glow-green {
        background: linear-gradient(180deg, #5eff33 0%, #32b305 50%, #1e6d02 100%);
    }
    /* Gul glød ved moderat restitution */
    .glow-yellow {
        background: linear-gradient(180deg, #ffee33 0%, #b39b05 50%, #6d5d02 100%);
    }
    /* Rød glød ved lav restitution */
    .glow-red {
        background: linear-gradient(180deg, #ff3333 0%, #b30505 50%, #6d0202 100%);
    }
    </style>
    """,
    unsafe_allow_html=True
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
    """Beregner samlet paratheds-score (1-10) og bar farvetype."""
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
            return f"Modtaget kl. {tid_str} (inden deadline kl. 12:00)"
        return f"Modtaget sent kl. {tid_str} (efter kl. 12:00)"
    except Exception:
        return f"Modtaget kl. {tid_str}"


# --- PINKODE-BESKYTTELSE ---
def get_coach_pin() -> str:
    try:
        return str(st.secrets["COACH_PIN"])
    except Exception:
        return "1234"  # Fallback-pinkode


if "coach_logged_in" not in st.session_state:
    st.session_state["coach_logged_in"] = False

if not st.session_state["coach_logged_in"]:
    st.title("🔒 AGF Svømning – Træner Login")
    st.write("Indtast pinkode for at åbne dashboardet.")
    with st.form("login_form"):
        pin_input = st.text_input("Pinkode", type="password", max_chars=10)
        submitted = st.form_submit_button("Log ind", type="primary")
        if submitted:
            if pin_input == get_coach_pin():
                st.session_state["coach_logged_in"] = True
                st.rerun()
            else:
                st.error("Forkert pinkode. Prøv igen.")
    st.stop()


# --- SIDEBAR ---
with st.sidebar:
    # AGF logo i hvid / mørkeblå (eller officiel version, hvis hentet)
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e6/AGF_logo.svg", width=110)
    st.subheader("AGF SVØMNING")
    
    st.caption("Aktiv atlet (v1)")
    st.selectbox("Atlet", [ATHLETE_NAME])

    if st.button("Hent nyeste svar"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Data opdateres automatisk fra Google Sheets hvert minut.")


# --- TRÆNER-DASHBOARD ---
st.title(f"Træner-dashboard – {ATHLETE_NAME}")

if "INDSÆT_DIT_CSV_LINK_HER" in SHEET_CSV_URL:
    st.error("Husk at indsætte dit Google Sheets `.csv`-link i `SHEET_CSV_URL` i `app.py`.")
    st.stop()

try:
    df = load_sheet_data(SHEET_CSV_URL)
except Exception as e:
    st.error(f"Kunne ikke hente data fra Google Sheets. Tjek at linket er publiceret som .csv. Fejl: {e}")
    st.stop()

# Vælg dato (standard: i dag)
valgt_dato = st.date_input("Vælg træningsdag", value=date.today())
valgt_dato_str = valgt_dato.isoformat()
ugedag_info = TRAINING_SCHEDULE[valgt_dato.weekday()]

# Dagens træningsplan øverst (mørkeblå info boks)
pas_tekst = "  |  ".join(ugedag_info["pas"])
st.info(f"**{ugedag_info['dag']} ({valgt_dato.strftime('%d/%m/%Y')}) – Planlagte pas:** {pas_tekst}")

# To kolonner: Venstre = Dagens svar, Højre = 7 målingers tendens
col_left, col_right = st.columns([1, 1.35], gap="large")

with col_left:
    st.subheader("Dagens status")

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

            # Vis paratheds-score og FIFA 13 Restitutionsbar
            percentage = int(score * 10) # F.eks. 8.0 bliver til 80%
            
            st.markdown(
                f"""
                <div style="margin-bottom: 12px;">
                    <span style="font-size: 1.5rem; font-weight: bold; color: #ffffff;">Parathed: <span style="font-size: 1.8rem;">{score}</span> / 10</span><br>
                    <span style="font-size: 1.1rem; color: #a4b3c6; font-weight: bold;">{status_tekst}</span>
                </div>
                <div class="cylinder-bar-bg">
                    <div class="cylinder-bar-fill {fill_class}" style="width: {percentage}%;"></div>
                </div>
                """, 
                unsafe_allow_html=True
            )

            st.caption(check_deadline_status(str(row["tidspunkt_sendt"])))
            st.markdown("<br>", unsafe_allow_html=True)

            # Talværdier
            m1, m2, m3 = st.columns(3)
            m1.metric("Søvn", f"{row['soevn_timer']} t")
            m2.metric("Mental friskhed", f"{int(row['mental_friskhed'])} / 10")
            m3.metric("Fysisk friskhed", f"{int(row['fysisk_friskhed'])} / 10")

            st.markdown("**Kommentar fra atleten:**")
            kommentar = str(row["kommentar"]).strip()
            if kommentar:
                st.markdown(
                    f"""
                    <div style="background-color: #162438; border-left: 4px solid #ffffff; padding: 10px; border-radius: 0 4px 4px 0;">
                        <i>"{kommentar}"</i>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.caption("Ingen kommentar tilføjet.")

    st.divider()
    with st.expander("Polar-sensor data (kommer i v2)", expanded=False):
        st.caption(
            "Her kobles puls, kcal og minutter i pulszone 1–5 på, når "
            "sensor-compliance er på plads."
        )

with col_right:
    st.subheader("Tendens – sidste 7 målinger")

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
                    name="Fysisk friskhed (1-10)",
                    line=dict(color="#2ca02c", width=3),  # Sportsgrøn
                    marker=dict(size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["mental_friskhed"],
                    mode="lines+markers",
                    name="Mental friskhed (1-10)",
                    line=dict(color="#1f77b4", width=3),  # Blå
                    marker=dict(size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["soevn_timer"],
                    mode="lines+markers",
                    name="Søvn (timer)",
                    line=dict(color="#ffffff", width=2, dash="dot"),  # Hvid
                    marker=dict(size=7),
                )
            )

            fig.add_hline(
                y=5,
                line_dash="dash",
                line_color="rgba(220, 53, 69, 0.45)",
                annotation_text="OBS-grænse (5)",
                annotation_position="bottom right",
            )

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(
                    range=[0, 10.5], 
                    title="Score / Timer", 
                    gridcolor="#1f2e45", 
                    zerolinecolor="#1f2e45",
                    tickfont=dict(color="#a4b3c6")
                ),
                xaxis=dict(
                    title="Dato", 
                    gridcolor="#1f2e45",
                    tickfont=dict(color="#a4b3c6")
                ),
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="left", 
                    x=0,
                    font=dict(color="#ffffff")
                ),
                margin=dict(l=10, r=10, t=40, b=10),
                height=380,
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
