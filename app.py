from datetime import date, datetime
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- KONFIGURATION ---
st.set_page_config(
    page_title="Svømmetræner Dashboard – Parathed",
    page_icon="🏊",
    layout="wide",
)

# Indsæt dit "Publicer på nettet (.csv)"-link fra Google Sheets herunder:
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4z1vstw_vNusCuZdgYesIYbmvI52mD3sYKlTykpk370wyGAnfpbdru0VCj7c7CX9JBWzeBi_d1Evf/pub?gid=941831444&single=true&output=csv"
ATHLETE_NAME = "Svømmer 1"

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


# --- DATAHENTNING FRA GOOGLE SHEETS ---
def clean_danish_timestamp(val: str) -> str:
    """Gør danske tidsstempler (f.eks. 24.11.2026 08.15.00) læsbare for Python."""
    s = str(val).strip()
    # Erstat punktum i klokkeslæt (08.15.00 -> 08:15:00)
    s = re.sub(r"(\d{1,2})\.(\d{2})\.(\d{2})", r"\1:\2:\3", s)
    return s


@st.cache_data(ttl=60)
def load_sheet_data(url: str) -> pd.DataFrame:
    if not url or "INDSÆT_DIT_CSV_LINK_HER" in url:
        return pd.DataFrame()

    raw = pd.read_csv(url)
    if raw.empty or raw.shape[1] < 4:
        return pd.DataFrame()

    # Google Forms-kolonner i rækkefølge:
    # 0: Tidsstempel, 1: Søvn, 2: Mental, 3: Fysisk, 4: Kommentar (valgfri)
    df = pd.DataFrame()
    ts_clean = raw.iloc[:, 0].apply(clean_danish_timestamp)
    df["timestamp"] = pd.to_datetime(ts_clean, dayfirst=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    df["dato"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["tidspunkt_sendt"] = df["timestamp"].dt.strftime("%H:%M")

    # Håndtér både punktum og komma i søvn-timer
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

    # Hvis svømmeren har svaret flere gange samme dag, behold det seneste svar
    df = df.sort_values("timestamp").drop_duplicates(subset=["dato"], keep="last")
    return df.reset_index(drop=True)


def calc_readiness(soevn: float, mental: float, fysisk: float):
    """Beregner samlet paratheds-score (1-10) og trafiklys-status."""
    soevn_score = min(10.0, max(1.0, (soevn / 8.0) * 10.0))
    score = round((soevn_score + mental + fysisk) / 3.0, 1)

    if score >= 7.5:
        return score, "🟢 Klar til fuld belastning", "success"
    elif score >= 5.5:
        return score, "🟡 Moderat parathed – overvej justering", "warning"
    else:
        return score, "🔴 Lav parathed – tag en snak / sænk volumen", "error"


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
        return "1234"  # Fallback-pinkode (skift den her eller i Streamlit Secrets)


if "coach_logged_in" not in st.session_state:
    st.session_state["coach_logged_in"] = False

if not st.session_state["coach_logged_in"]:
    st.title("🔒 Træner-login")
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
st.sidebar.title("🏊 Svømme-Parathed")
st.sidebar.caption("Aktiv atlet (v1)")
st.sidebar.selectbox("Atlet", [ATHLETE_NAME])

if st.sidebar.button("🔄 Hent nyeste svar"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("Data opdateres automatisk fra Google Sheets hvert minut.")


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

# Dagens træningsplan øverst
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
            st.warning("Ingen melding modtaget for denne dato endnu (deadline kl. 12:00).")
        else:
            row = dagens_raekke.iloc[-1]
            score, status_tekst, status_type = calc_readiness(
                float(row["soevn_timer"]),
                float(row["mental_friskhed"]),
                float(row["fysisk_friskhed"]),
            )

            if status_type == "success":
                st.success(f"**{status_tekst}** — Samlet score: **{score} / 10**")
            elif status_type == "warning":
                st.warning(f"**{status_tekst}** — Samlet score: **{score} / 10**")
            else:
                st.error(f"**{status_tekst}** — Samlet score: **{score} / 10**")

            st.caption(check_deadline_status(str(row["tidspunkt_sendt"])))

            m1, m2, m3 = st.columns(3)
            m1.metric("Søvn", f"{row['soevn_timer']} t")
            m2.metric("Mental friskhed", f"{int(row['mental_friskhed'])} / 10")
            m3.metric("Fysisk friskhed", f"{int(row['fysisk_friskhed'])} / 10")

            st.markdown("**Kommentar fra atleten:**")
            kommentar = str(row["kommentar"]).strip()
            if kommentar:
                st.markdown(f"> {kommentar}")
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
                    line=dict(color="#1f77b4", width=3),
                    marker=dict(size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["mental_friskhed"],
                    mode="lines+markers",
                    name="Mental friskhed (1-10)",
                    line=dict(color="#2ca02c", width=3),
                    marker=dict(size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["dato_label"],
                    y=df_hist["soevn_timer"],
                    mode="lines+markers",
                    name="Søvn (timer)",
                    line=dict(color="#ff7f0e", width=2, dash="dot"),
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
                yaxis=dict(range=[0, 10.5], title="Score / Timer"),
                xaxis=dict(title="Dato"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
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
