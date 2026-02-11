import base64
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import streamlit as st

from mikroabenteuer.config import APP_TITLE
from mikroabenteuer.data_loader import load_adventures
from mikroabenteuer.openai_settings import configure_openai_api_key
from mikroabenteuer.scheduler import start_scheduler
from mikroabenteuer.ui.details import render_adventure_details
from mikroabenteuer.ui.table import render_adventure_table

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌿",
    layout="wide",
)


@dataclass(frozen=True)
class LandingAdventureCard:
    title: str
    teaser: str
    age_group: str
    duration: str
    season: str
    mood: str


def inject_custom_styles(background_path: Path) -> None:
    """Inject a light, readable theme with a custom background image."""
    background_b64 = base64.b64encode(background_path.read_bytes()).decode("utf-8")

    st.markdown(
        f"""
        <style>
            .stApp {{
                background: linear-gradient(
                    rgba(255, 255, 255, 0.87),
                    rgba(255, 255, 255, 0.87)
                ), url("data:image/png;base64,{background_b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                color: #1f2937;
            }}

            h1, h2, h3, .stCaption, p, label, span {{
                color: #1f2937 !important;
            }}

            [data-testid="stMetric"],
            [data-testid="stExpander"],
            [data-testid="stDataFrame"],
            [data-testid="stMarkdownContainer"] > div,
            .stTextInput > div > div,
            .stSelectbox > div > div {{
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 0.8rem;
            }}

            .stButton > button {{
                background-color: #374151;
                color: #ffffff !important;
                border: none;
            }}

            .stButton > button p,
            .stButton > button span {{
                color: #ffffff !important;
            }}

            .stButton > button:hover {{
                background-color: #1f2937;
            }}

            .landing-card {{
                background-color: rgba(255, 255, 255, 0.85);
                border-radius: 0.8rem;
                padding: 1rem;
                border: 1px solid rgba(37, 99, 235, 0.2);
                min-height: 190px;
            }}

            .landing-proof {{
                font-weight: 600;
                color: #065f46;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_landing_page(cards: list[LandingAdventureCard]) -> None:
    """Render conversion-focused bilingual funnel sections."""
    st.markdown(
        """
        # Mikroabenteuer für Familien – Rausgehen war noch nie so einfach
        ### Kleine Abenteuer. Keine Vorbereitung. Direkt vor eurer Haustür.
        #### Family micro-adventures made easy: short, spontaneous, and close to home.
        """
    )

    proof_col1, proof_col2, proof_col3 = st.columns(3)
    proof_col1.markdown(
        "<p class='landing-proof'>✓ ab 3 Jahren geeignet / suitable from age 3+</p>",
        unsafe_allow_html=True,
    )
    proof_col2.markdown(
        "<p class='landing-proof'>✓ ohne Planung möglich / no planning required</p>",
        unsafe_allow_html=True,
    )
    proof_col3.markdown(
        "<p class='landing-proof'>✓ ganzjährig umsetzbar / works all year round</p>",
        unsafe_allow_html=True,
    )

    cta_col1, cta_col2 = st.columns([1, 1])
    with cta_col1:
        if st.button(
            "Jetzt Mikroabenteuer entdecken / Discover micro-adventures now",
            use_container_width=True,
        ):
            st.info(
                "Weiter unten findest du die Abenteuerkarten und Filter. / Scroll down for cards and filters."
            )
    with cta_col2:
        if st.button(
            "Nach Jahreszeit filtern / Filter by season", use_container_width=True
        ):
            st.info("Wähle unten die passende Jahreszeit aus. / Select a season below.")

    st.divider()
    st.header(
        '„Uns ist langweilig.“ – Kennst du das? / "We are bored." – Know that feeling?'
    )
    st.markdown(
        """
        Wochenende. Regen. Keine Lust auf großen Ausflug. Kinder mit Energie.

        **Mikroabenteuer lösen genau dieses Problem.** Sie sind kurz, spontan und machen Natur wieder aufregend.

        Weekend. Rain. No motivation for a big trip. Kids full of energy.

        **Micro-adventures solve exactly this pain point.** They are short, spontaneous, and make nature exciting again.
        """
    )

    st.divider()
    st.header("Was ist ein Mikroabenteuer? / What is a micro-adventure?")
    st.markdown(
        """
        Ein Mikroabenteuer ist ein kleines Naturerlebnis, das ohne Vorbereitung möglich ist – direkt vor eurer Haustür.
        Es braucht keine Ausrüstung, keinen Urlaub und keinen perfekten Plan.

        A micro-adventure is a small outdoor experience you can start without preparation, right outside your front door.
        No special gear, no holiday, no perfect plan needed.
        """
    )

    principle_col1, principle_col2, principle_col3 = st.columns(3)
    principle_col1.markdown(
        "### 1. Einfach / Simple\nKeine Planung, kein Aufwand.\n\nNo planning, no overhead."
    )
    principle_col2.markdown(
        "### 2. Draußen / Outside\nNatur bewusst erleben.\n\nExperience nature mindfully."
    )
    principle_col3.markdown(
        "### 3. Gemeinsam / Together\nZeit statt Zeug.\n\nTime over stuff."
    )

    st.divider()
    st.header("Finde euer nächstes Mikroabenteuer / Find your next micro-adventure")

    season_options = ["Alle / All"] + sorted({card.season for card in cards})
    duration_options = ["Alle / All"] + sorted({card.duration for card in cards})
    age_options = ["Alle / All"] + sorted({card.age_group for card in cards})
    mood_options = ["Alle / All"] + sorted({card.mood for card in cards})

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        selected_season = st.selectbox("Jahreszeit / Season", options=season_options)
    with filter_col2:
        selected_duration = st.selectbox("Dauer / Duration", options=duration_options)
    with filter_col3:
        selected_age = st.selectbox("Alter / Age", options=age_options)
    with filter_col4:
        selected_mood = st.selectbox("Stimmung / Mood", options=mood_options)

    filtered_cards = [
        card
        for card in cards
        if (selected_season == "Alle / All" or card.season == selected_season)
        and (selected_duration == "Alle / All" or card.duration == selected_duration)
        and (selected_age == "Alle / All" or card.age_group == selected_age)
        and (selected_mood == "Alle / All" or card.mood == selected_mood)
    ]

    if not filtered_cards:
        st.warning(
            "Keine Abenteuer für diese Kombination gefunden. / No adventures found for this filter combination.",
        )

    for row_start in range(0, len(filtered_cards), 3):
        row_cards = filtered_cards[row_start : row_start + 3]
        row_columns = st.columns(3)
        for index, card in enumerate(row_cards):
            with row_columns[index]:
                st.markdown(
                    (
                        "<div class='landing-card'>"
                        f"<h4>{card.title}</h4>"
                        f"<p>{card.teaser}</p>"
                        f"<p><strong>Alter | Age:</strong> {card.age_group}<br>"
                        f"<strong>Dauer | Duration:</strong> {card.duration}</p>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                st.button(
                    f"Details ansehen / View details · {card.title}",
                    key=f"details-{card.title}",
                    use_container_width=True,
                )

    st.divider()
    st.header(
        "Warum kleine Abenteuer große Wirkung haben / Why tiny adventures have big impact"
    )
    benefit_col1, benefit_col2, benefit_col3 = st.columns(3)
    benefit_col1.markdown(
        "### Bewegung / Movement\nMotorik, Gleichgewicht, Körpergefühl.\n\nMotor skills, balance, body awareness."
    )
    benefit_col2.markdown(
        "### Wahrnehmung / Perception\nAchtsamkeit, Fokus, Sinneserfahrung.\n\nMindfulness, focus, sensory learning."
    )
    benefit_col3.markdown(
        "### Verbindung / Connection\nGemeinsame Erinnerungen.\n\nShared family memories."
    )

    st.divider()
    st.header(
        "So startet ihr euer erstes Mikroabenteuer / Start your first micro-adventure in 3 steps"
    )
    st.markdown(
        """
        1. Abenteuer auswählen / Pick an adventure  
        2. Rausgehen / Head outside  
        3. Erleben / Experience together
        """
    )
    st.button(
        "Jetzt erstes Abenteuer starten / Start your first adventure now",
        use_container_width=True,
    )

    st.divider()
    st.header("10 Mikroabenteuer als kostenlose Liste / 10 free micro-adventure ideas")
    st.markdown(
        """
        Hol dir eine kompakte Übersicht mit sofort umsetzbaren Ideen.

        Get a compact list of ideas you can start right away.
        """
    )
    st.button("Kostenlos herunterladen / Download for free", use_container_width=True)

    st.divider()
    st.header("Abenteuer beginnen vor der Haustür / Adventure starts at your doorstep")
    st.markdown(
        """
        Es braucht keinen Urlaub, kein Event und keinen perfekten Moment.
        Nur den ersten Schritt nach draußen.

        You do not need a holiday, event, or perfect timing.
        You only need your first step outside.
        """
    )
    st.button("Jetzt loslegen / Get started now", use_container_width=True)


inject_custom_styles(Path("Hintergrund.png"))

top_col_left, top_col_center, top_col_right = st.columns([1, 1.6, 1])
with top_col_center:
    st.markdown(
        """
        <h2 style="text-align: center; margin-bottom: 0.3rem;">
            Kleine Abenteuer. Große Erinnerungen 🎂
        </h2>
        <p style="text-align: center; margin-top: 0; margin-bottom: 0.8rem; color: #4b5563;">
            Small adventures. Big memories.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.image(
        image="20251219_155329.jpg",
        width=240,
    )

configure_openai_api_key()

if os.getenv("ENABLE_DAILY_SCHEDULER", "0") == "1":
    try:
        start_scheduler()
    except Exception:
        st.warning(
            "Scheduler konnte nicht gestartet werden / Scheduler could not be started.",
        )

adventures = load_adventures()

landing_cards = [
    LandingAdventureCard(
        title="🌧 Matschwandern / Mud puddle hiking",
        teaser="Regen? Perfekt. Rein in die Pfützen. / Rain? Perfect. Jump into puddles.",
        age_group="3+",
        duration="30–45 min",
        season="Herbst / Autumn",
        mood="Bewegung / Movement",
    ),
    LandingAdventureCard(
        title="🔦 Taschenlampen-Spaziergang / Flashlight walk",
        teaser="Die Nacht neu entdecken. / Discover the night in a new way.",
        age_group="4+",
        duration="20–40 min",
        season="Winter",
        mood="Achtsam / Mindful",
    ),
    LandingAdventureCard(
        title="🐾 Tiere beobachten / Observe animals",
        teaser="Geduld wird zum Abenteuer. / Patience turns into adventure.",
        age_group="5+",
        duration="30–60 min",
        season="Frühling / Spring",
        mood="Ruhig / Calm",
    ),
    LandingAdventureCard(
        title="🌼 Frühlingspflanzen begrüßen / Welcome spring plants",
        teaser="Die ersten Farbtupfer finden. / Find the first colorful blooms.",
        age_group="3+",
        duration="20–35 min",
        season="Frühling / Spring",
        mood="Kreativ / Creative",
    ),
    LandingAdventureCard(
        title="🎯 Waldbingo / Forest bingo",
        teaser="Natur als Suchspiel. / Turn nature into a treasure hunt.",
        age_group="4+",
        duration="30–50 min",
        season="Sommer / Summer",
        mood="Kreativ / Creative",
    ),
    LandingAdventureCard(
        title="🌲 Blind durch den Wald / Blindfold forest walk",
        teaser="Mit allen Sinnen erleben. / Explore with all senses.",
        age_group="6+",
        duration="15–30 min",
        season="Sommer / Summer",
        mood="Achtsam / Mindful",
    ),
]

render_landing_page(landing_cards)

today = date.today().isoformat()
todays_adventure = adventures[hash(today) % len(adventures)]

st.divider()
st.header("📅 Abenteuer des Tages / Adventure of the day")
render_adventure_details(todays_adventure, expanded=True, key_prefix="today")

st.divider()
st.header("🗺 Alternative Mikroabenteuer / Alternative micro-adventures")
render_adventure_table(adventures)
