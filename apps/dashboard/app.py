from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

st.set_page_config(page_title="NCAA Italian Players", page_icon="🏀", layout="wide")
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.local", override=False)
DRAFT_FILE = ROOT / "docs" / "nba-draft-2027-top-30.md"
SEASON = 2027
DATASETS = ["schedule", "team_rosters", "rosters", "pbp", "player_box", "team_box",
            "lineups", "matchup_stints", "possessions", "shots", "team_ids"]

st.markdown("""<style>
.block-container{padding-top:1.5rem;max-width:1500px}
.hero{padding:1.5rem 1.8rem;border-radius:18px;background:linear-gradient(115deg,#101c35,#193d63);color:white;margin-bottom:1.2rem}
.hero h1{font-size:2.15rem;margin:0 0 .35rem;color:white}.hero p{font-size:1rem;opacity:.88;margin:0}
div[data-testid="stMetric"]{background:rgba(120,140,170,.09);padding:12px;border-radius:12px}
</style>""", unsafe_allow_html=True)

st.sidebar.title("🏀 NCAA Italian Players")
page = st.sidebar.radio("Navigazione", [
    "Dashboard", "Analisi giocatori", "Analisi squadre", "Partite",
    "Giocatori italiani", "Draft NBA 2027", "Fonti e dati"
])
st.sidebar.caption("Stagione attiva: 2026-27 · season=2027")
st.sidebar.caption("Dati storici esclusi")

def db_url():
    value = os.getenv("DATABASE_URL") or os.getenv("NCAA_DATABASE_URL")
    if not value:
        try:
            value = st.secrets.get("DATABASE_URL") or st.secrets.get("NCAA_DATABASE_URL")
        except Exception:
            value = None
    if not value:
        return None
    value = str(value).strip()
    if value.startswith("postgres://"):
        value = "postgresql+psycopg://" + value[len("postgres://"):]
    elif value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    return value

@st.cache_resource(show_spinner=False)
def engine(url):
    return create_engine(url, pool_pre_ping=True, pool_size=1, max_overflow=0,
                         connect_args={"connect_timeout": 8})

def query(sql, params=None):
    url = db_url()
    if not url:
        return None, "Database non configurato: aggiungi DATABASE_URL nei Secrets di Streamlit."
    try:
        with engine(url).connect() as conn:
            return conn.execute(text(sql), params or {}).mappings().all(), None
    except Exception as exc:
        return None, f"Database non raggiungibile ({exc.__class__.__name__}). Verifica Neon e l'importazione."

@st.cache_data(ttl=300, show_spinner=False)
def summary():
    rows, err = query("""SELECT dataset, COUNT(*) AS rows, MAX(imported_at) AS last_imported
                         FROM ncaa_raw_rows WHERE season=:season GROUP BY dataset ORDER BY dataset""",
                      {"season": SEASON})
    if err:
        return None, err
    data = [{"dataset": r["dataset"], "rows": int(r["rows"]),
             "last_imported": r["last_imported"].isoformat() if r["last_imported"] else None}
            for r in rows]
    return {"rows_total": sum(x["rows"] for x in data), "datasets": data}, None

@st.cache_data(ttl=300, show_spinner=False)
def load_dataset(dataset):
    if dataset not in DATASETS:
        return pd.DataFrame(), "Dataset non consentito."
    rows, err = query("""SELECT payload FROM ncaa_raw_rows
                         WHERE season=:season AND dataset=:dataset
                         ORDER BY source_row_number LIMIT 100000""",
                      {"season": SEASON, "dataset": dataset})
    if err:
        return pd.DataFrame(), err
    if not rows:
        return pd.DataFrame(), None
    return pd.json_normalize([dict(r["payload"]) for r in rows]), None

def draft_data():
    if not DRAFT_FILE.exists():
        return pd.DataFrame(columns=["Rank", "Prospect", "Team / club"])
    rows = []
    for line in DRAFT_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", line)
        if match:
            rows.append({"Rank": int(match.group(1)), "Prospect": match.group(2),
                         "Team / club": match.group(3)})
    return pd.DataFrame(rows)

def first_column(frame, candidates):
    return next((name for name in candidates if name in frame.columns), None)

def numeric(frame, candidates):
    name = first_column(frame, candidates)
    if not name:
        return None
    return pd.to_numeric(frame[name], errors="coerce")

def player_leaderboard(frame):
    name_col = first_column(frame, ["clean_name", "player", "name", "athlete_display_name"])
    id_col = first_column(frame, ["player_id", "ncaa_player_id"])
    if not name_col:
        return pd.DataFrame(), "Il dataset non contiene un campo nome giocatore riconosciuto."
    frame = frame.copy()
    frame["_player"] = frame[name_col].fillna("Giocatore non identificato").astype(str)
    if id_col:
        frame["_id"] = frame[id_col].astype(str)
        keys = ["_id", "_player"]
    else:
        keys = ["_player"]
    metrics = {
        "Partite": ["contest_id"],
        "Minuti": ["mins", "minutes"],
        "Punti": ["pts", "points"],
        "Rimbalzi offensivi": ["orb", "oreb"],
        "Rimbalzi difensivi": ["drb", "dreb"],
        "Assist": ["ast", "assists"],
        "Palle rubate": ["stl", "steals"],
        "Stoppate": ["blk", "blocks"],
        "Palle perse": ["tov", "turnovers"],
        "TS%": ["ts_pct"], "eFG%": ["efg_pct"],
        "FG%": ["fg_pct"], "3P%": ["tp_pct"], "FT%": ["ft_pct"],
        "Possessi offensivi": ["o_poss"],
    }
    usable = {}
    for label, aliases in metrics.items():
        col = first_column(frame, aliases)
        if col:
            usable[label] = col
    if not usable:
        return pd.DataFrame(), "Nessuna colonna statistica riconosciuta nel player_box."
    for label, col in usable.items():
        frame[label] = pd.to_numeric(frame[col], errors="coerce")
    aggregations = {label: "mean" for label in usable}
    if "Partite" in usable:
        aggregations["Partite"] = "nunique"
    result = frame.groupby(keys, dropna=False).agg(aggregations).reset_index()
    result = result.rename(columns={"_player": "Giocatore", "_id": "ID NCAA"})
    if "Minuti" in result:
        result = result[result["Minuti"].fillna(0) > 0]
    for label in ["Punti", "Minuti", "TS%", "eFG%", "FG%", "3P%", "FT%"]:
        if label in result:
            result[label] = result[label].round(1)
    return result, None

st.markdown('<div class="hero"><h1>NCAA Italian Players</h1><p>Basketball intelligence · NCAA Men 2026-27 · Italian player tracker & NBA Draft 2027</p></div>', unsafe_allow_html=True)

if page == "Dashboard":
    st.subheader("Panoramica della stagione")
    data, err = summary()
    a, b, c, d = st.columns(4)
    a.metric("Stagione", "2026-27")
    b.metric("Storico", "Disattivato")
    c.metric("Dataset", len(DATASETS))
    d.metric("Record importati", f"{data['rows_total']:,}" if data else "—")
    if err:
        st.warning("Database non ancora collegato.")
        st.caption(err)
    elif not data["rows_total"]:
        st.info("Database collegato, ma non risultano ancora record importati per il 2026-27.")
    else:
        st.success("Connessione PostgreSQL attiva · conteggi letti dal database.")
        st.dataframe(pd.DataFrame(data["datasets"]), hide_index=True, use_container_width=True)
    st.divider()
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("### Sezioni analitiche")
        st.write("• Leaderboard giocatori con medie per partita e percentuali di tiro")
        st.write("• Statistiche squadra, risultati e calendario quando presenti nei dati")
        st.write("• Possessi, quintetti, matchup e tiri: consultabili solo se importati")
        st.write("• Percentili da pubblicare dopo il controllo della popolazione di confronto")
    with right:
        st.markdown("### Draft NBA 2027")
        prospects = draft_data()
        if not prospects.empty:
            st.dataframe(prospects.head(8), hide_index=True, use_container_width=True)

elif page == "Analisi giocatori":
    st.subheader("Leaderboard giocatori · NCAA 2026-27")
    frame, err = load_dataset("player_box")
    if err:
        st.warning(err)
    elif frame.empty:
        st.info("Nessun box score giocatore importato. La classifica si popolerà dai dati reali.")
    else:
        result, problem = player_leaderboard(frame)
        if problem:
            st.warning(problem)
            st.caption("Campi sorgente rilevati: " + ", ".join(frame.columns[:50]))
        else:
            c1, c2 = st.columns([1, 1])
            with c1:
                metric = st.selectbox("Ordina per", [c for c in result.columns if c not in ["Giocatore", "ID NCAA"]])
            with c2:
                search = st.text_input("Cerca giocatore")
            if search:
                result = result[result["Giocatore"].str.contains(search, case=False, na=False)]
            result = result.sort_values(metric, ascending=False, na_position="last")
            st.caption(f"{len(result):,} giocatori aggregati · medie per partita ove applicabile · stagione 2026-27")
            st.dataframe(result, hide_index=True, use_container_width=True, height=650)
            if metric in result and result[metric].notna().sum() >= 2:
                st.markdown("#### Distribuzione della metrica selezionata")
                st.bar_chart(result.set_index("Giocatore")[[metric]].head(20))

elif page == "Analisi squadre":
    st.subheader("Analisi squadre · NCAA 2026-27")
    frame, err = load_dataset("team_box")
    if err:
        st.warning(err)
    elif frame.empty:
        st.info("Nessun box score squadra importato.")
    else:
        team_col = first_column(frame, ["team", "team_name", "team_display_name", "school"])
        id_col = first_column(frame, ["team_ncaa_team_id", "team_id"])
        if not team_col and not id_col:
            st.warning("Il box score non espone un identificativo squadra riconosciuto.")
            st.caption("Campi disponibili: " + ", ".join(frame.columns[:60]))
        else:
            key = team_col or id_col
            frame = frame.copy()
            frame["_team"] = frame[key].fillna("Squadra non identificata").astype(str)
            preferred = ["possessions", "ORtg", "DRtg", "NetRtg", "efg_pct", "ts_pct",
                         "orb_pct", "drb_pct", "tov_pct", "pts"]
            cols = [c for c in preferred if c in frame.columns]
            for col in cols:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
            if cols:
                table = frame.groupby("_team")[cols].mean(numeric_only=True).round(2).reset_index()
                st.dataframe(table.rename(columns={"_team": "Squadra"}), hide_index=True,
                             use_container_width=True, height=650)
            else:
                st.warning("Colonne avanzate non ancora riconosciute.")
                st.dataframe(frame.head(100), hide_index=True, use_container_width=True)

elif page == "Partite":
    st.subheader("Calendario e risultati · NCAA 2026-27")
    frame, err = load_dataset("schedule")
    if err:
        st.warning(err)
    elif frame.empty:
        st.info("Nessun calendario importato.")
    else:
        search = st.text_input("Cerca squadra")
        if search:
            mask = frame.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            frame = frame[mask]
        st.caption(f"{len(frame):,} partite/record calendario disponibili nella sorgente importata.")
        st.dataframe(frame, hide_index=True, use_container_width=True, height=650)

elif page == "Giocatori italiani":
    st.subheader("Directory giocatori italiani")
    st.info("La directory verrà mostrata quando saranno caricati i record di verifica della nazionalità. I nomi non vengono classificati come italiani in base al cognome o alla sola presenza in un roster.")
    st.caption("Fonti ammesse: biografie ufficiali universitarie, federazioni e registri nazionali. Divisione e roster 2026-27 devono essere verificati separatamente.")

elif page == "Draft NBA 2027":
    st.subheader("NBA Draft 2027 · Top 30 assoluta")
    st.caption("Prospetti di qualsiasi nazionalità. Classifica separata dalla directory italiana.")
    frame = draft_data()
    if frame.empty:
        st.warning("Ranking non trovato.")
    else:
        search = st.text_input("Cerca prospetto o squadra")
        if search:
            frame = frame[frame.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
        st.dataframe(frame, hide_index=True, use_container_width=True, height=650)
        st.caption("Snapshot 13 novembre 2026 · consensus Ultimate Big Board")
        st.link_button("Apri fonte del ranking", "https://ultimatebigboard.com/nba/2027/")

elif page == "Fonti e dati":
    st.subheader("Fonti, copertura e qualità")
    data, err = summary()
    if err:
        st.warning(err)
    elif data:
        st.metric("Record grezzi stagione 2026-27", f"{data['rows_total']:,}")
        if data["datasets"]:
            st.dataframe(pd.DataFrame(data["datasets"]), hide_index=True, use_container_width=True)
        else:
            st.info("Nessun dataset importato.")
    st.markdown("#### Esplora i record originali")
    dataset = st.selectbox("Dataset", DATASETS)
    frame, load_error = load_dataset(dataset)
    if load_error:
        st.warning(load_error)
    elif frame.empty:
        st.info("Nessun record disponibile per questo dataset.")
    else:
        st.caption(f"{len(frame):,} record caricati · limite di consultazione 100.000")
        st.dataframe(frame, hide_index=True, use_container_width=True, height=600)
    st.markdown("#### Regole di qualità")
    st.write("• Solo stagione 2026-27 · • Nessuno storico · • Dato mancante distinto da zero")
    st.write("• Provenienza originale conservata · • Nazionalità italiana documentata")
    st.write("• Metriche e percentili pubblicati solo quando campi e campione sono adeguati")

st.divider()
st.caption("NCAA Italian Players · stagione 2026-27 · dati reali da PostgreSQL · nessuna statistica simulata.")
