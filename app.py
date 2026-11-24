import os
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- KONFIGURATION ---
st.set_page_config(
    page_title="Svømmetræner Dashboard – Parathed",
    page_icon="🏊",
    layout="wide",
)

DATA_FILE = "readiness_data.csv"
DEFAULT_ATHLETE = "Svømmer 1"

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

COLUMNS = [
    "dato",
    "tidspunkt_sendt",
    "atlet",
    "soevn_timer",
    "mental_friskhed",
    "fysisk_friskhed",
    "kommentar",
    # Forberedt til senere Polar-integration
    "polar_gns_puls",
    "polar_kcal",
    "polar_z1_min",
    "polar_z2_min",
    "polar_z3_min",
    "polar_z4_min",
    "polar_z5_min",
]


# --- HJÆLPEFUNKTIONER ---
def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, dtype={"kommentar": str})
        df["kommentar"] = df["kommentar"].fillna("")
        return df
    return pd.DataFrame(columns=COLUMNS)


def save_entry(entry: dict):
    df = load_data()
    # Overskriv hvis atleten allerede har svaret for samme dato
    mask = (df["dato"] == entry["dato"]) & (df["atlet"] == entry["atlet"])
    df = df[~mask]
    new_row = pd.DataFrame([entry], columns=COLUMNS)
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("dato")
    df.to_csv(DATA_FILE, index=False)


def seed_demo_data():
    """Indlæser 7 dages realistiske testdata med let stigende træthed."""
    today = date.today()
    demo_rows = [
        (-6, "08:12", 8.5, 9, 8, "God energi efter weekenden"),
        (-5, "08:25", 7.5, 8, 7, "Lidt tung i skuldrene efter morgentræning"),
        (-4, "09:05", 7.0, 7, 7, "Fint overskud, travlt i skolen"),
        (-3, "08:40", 6.5, 6, 6, "Lidt øm i benene"),
        (-2, "10:15", 6.0, 5, 5, "Dårlig søvn, eksamenspres"),
        (-1, "09:50", 7.0, 6, 6, "Bedre i dag, men stadig lidt træt"),
        (0, "08:30", 8.0, 8, 7, "Klar til aftenpas!"),
    ]
    rows = []
    for offset, tid, soevn, mental, fysisk, komm in demo_rows:
        d = (today + timedelta(days=offset)).isoformat()
        rows.append(
            {
                "dato": d,
                "tidspunkt_sendt": tid,
                "atlet": DEFAULT_ATHLETE,
                "soevn_timer": soevn,
                "mental_friskhed": mental,
                "fysisk_friskhed": fysisk,
                "kommentar": komm,
                "polar_gns_puls": None,
                "polar_kcal": None,
                "polar_z1_min": None,
                "polar_z2_min": None,
                "polar_z3_min": None,
                "polar_z4_min": None,
                "polar_z5_min": None,
            }
        )
    pd.DataFrame(rows, columns=COLUMNS).to_csv(DATA_FILE, index=False)


def calc_readiness(soevn: float, mental: int, fysisk: int):
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


# --- SIDEBAR (NAVIGATION) ---
st.sidebar.title("🏊 Svømme-Parathed")
visning = st.sidebar.radio(
    "Vælg visning",
    ["Træner-dashboard (kl. 12)", "Atlet-indtastning (08–12)"],
)

st.sidebar.divider()
st.sidebar.caption("Aktiv atlet (v1)")
aktiv_atlet = st.sidebar.selectbox("Atlet", [DEFAULT_ATHLETE])

st.sidebar.divider()
if st.sidebar.button("Indlæs 7 dages testdata"):
    seed_demo_data()
    st.sidebar.success("Testdata indlæst!")
    st.rerun()


# ==========================================
# VISNING 1: TRÆNER-DASHBOARD
# ==========================================
if visning == "Træner-dashboard (kl. 12)":
    df = load_data()
    df_atlet = df[df["atlet"] == aktiv_atlet].sort_values("dato")

    st.title(f"Træner-dashboard – {aktiv_atlet}")

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
        dagens_raekke = df_atlet[df_atlet["dato"] == valgt_dato_str]

        if dagens_raekke.empty:
            st.warning("Ingen melding modtaget for denne dato endnu (deadline kl. 12:00).")
        else:
            row = dagens_raekke.iloc[-1]
            score, status_tekst, status_type = calc_readiness(
                float(row["soevn_timer"]),
                int(row["mental_friskhed"]),
                int(row["fysisk_friskhed"]),
            )

            # Trafiklys-boks
            if status_type == "success":
                st.success(f"**{status_tekst}** — Samlet score: **{score} / 10**")
            elif status_type == "warning":
                st.warning(f"**{status_tekst}** — Samlet score: **{score} / 10**")
            else:
                st.error(f"**{status_tekst}** — Samlet score: **{score} / 10**")

            st.caption(check_deadline_status(str(row["tidspunkt_sendt"])))

            # Nøgletal
            m1, m2, m3 = st.columns(3)
            m1.metric("Søvn", f"{row['soevn_timer']} t")
            m2.metric("Mental friskhed", f"{int(row['mental_friskhed'])} / 10")
            m3.metric("Fysisk friskhed", f"{int(row['fysisk_friskhed'])} / 10")

            # Kommentar
            st.markdown("**Kommentar fra atleten:**")
            kommentar = str(row["kommentar"]).strip()
            if kommentar:
                st.markdown(f"> {kommentar}")
            else:
                st.caption("Ingen kommentar tilføjet.")

        # Placeholder til senere Polar-integration
        st.divider()
        with st.expander("Polar-sensor data (kommer i v2)", expanded=False):
            st.caption(
                "Her kobles puls, kcal og minutter i pulszone 1–5 på, når "
                "sensor-compliance er på plads."
            )

    with col_right:
        st.subheader("Tendens – sidste 7 målinger")

        # Tag de seneste 7 målinger op til og med den valgte dato
        df_hist = df_atlet[df_atlet["dato"] <= valgt_dato_str].tail(7).copy()

        if df_hist.empty:
            st.info("Ingen historik endnu. Brug 'Indlæs 7 dages testdata' i sidebaren eller indtast et svar.")
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

            # Advarselslinje ved 5 for hurtigt at spotte træthed
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

            # Kompakt oversigtstabel under grafen
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


# ==========================================
# VISNING 2: ATLET-INDTASTNING
# ==========================================
else:
    st.title(f"Morgen-tjek ind – {aktiv_atlet}")
    st.write("Besvar mellem **kl. 08:00 og 12:00**, så træneren kan planlægge dagens træning.")

    with st.form("atlet_form", clear_on_submit=False):
        dato_input = st.date_input("Dato", value=date.today())

        soevn_input = st.slider(
            "Hvor mange timer har du sovet i nat?",
            min_value=0.0,
            max_value=12.0,
            value=8.0,
            step=0.5,
        )

        mental_input = st.slider(
            "Mental friskhed (1 = meget høj stress / presset, 10 = helt rolig / stort overskud)",
            min_value=1,
            max_value=10,
            value=7,
        )

        fysisk_input = st.slider(
            "Fysisk friskhed (1 = helt udkørt / meget øm, 10 = helt frisk og klar)",
            min_value=1,
            max_value=10,
            value=7,
        )

        kommentar_input = st.text_input(
            "Evt. kort kommentar til træneren (maks 50 tegn)",
            max_chars=50,
            placeholder="F.eks. Lidt øm i højre skulder",
        )

        sendt = st.form_submit_button("Send melding til træneren", type="primary")

        if sendt:
            entry = {
                "dato": dato_input.isoformat(),
                "tidspunkt_sendt": datetime.now().strftime("%H:%M"),
                "atlet": aktiv_atlet,
                "soevn_timer": soevn_input,
                "mental_friskhed": mental_input,
                "fysisk_friskhed": fysisk_input,
                "kommentar": kommentar_input.strip(),
                "polar_gns_puls": None,
                "polar_kcal": None,
                "polar_z1_min": None,
                "polar_z2_min": None,
                "polar_z3_min": None,
                "polar_z4_min": None,
                "polar_z5_min": None,
            }
            save_entry(entry)
            st.success("Tak! Din melding er gemt og klar på trænerens dashboard.")