from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from analytics import player_season_stats, team_season_stats

st.set_page_config(page_title="NCAA Italian Players", page_icon="🏀", layout="wide")
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.local", override=False)
DRAFT_FILE = ROOT / "docs" / "nba-draft-2027-top-30.md"
SEASON = 2027
DATASETS = ["schedule", "team_rosters", "rosters", "pbp", "player_box", "team_box",
            "lineups", "matchup_stints", "possessions", "shots", "team_ids"]

st.markdown("""<style>
.block-container{padding-top:1.4rem;max-width:1500px}
.hero{padding:1.5rem 1.8rem;border-radius:18px;background:linear-gradient(115deg,#101c35,#193d63);color:white;margin-bottom:1.2rem}
.hero h1{font-size:2.15rem;margin:0 0 .35rem;color:white}.hero p{font-size:1rem;opacity:.88;margin:0}
div[data-testid="stMetric"]{background:rgba(120,140,170,.09);padding:12px;border-radius:12px}
</style>""", unsafe_allow_html=True)

st.sidebar.title("🏀 NCAA Italian Players")
page = st.sidebar.radio("Navigazione", [
    "Dashboard", "Analisi giocatori", "Scheda giocatore", "Analisi squadre",
    "Partite", "Roster NCAA", "Giocatori italiani", "Quintetti e tiri",
    "Draft NBA 2027", "Fonti e dati"
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


def show_load_error(err):
    if err:
        st.warning(err)
        return True
    return False


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
        st.markdown("### Analisi disponibili")
        st.write("• Leaderboard giocatori: medie, totali, percentuali di tiro e percentili con soglia minima.")
        st.write("• Scheda giocatore: riepilogo stagione e box score partita per partita.")
        st.write("• Squadre: ratings e indicatori realmente presenti nei dati.")
        st.write("• Quintetti, matchup e tiri: esplorazione dei dataset originali.")
    with right:
        st.markdown("### Draft NBA 2027")
        prospects = draft_data()
        if not prospects.empty:
            st.dataframe(prospects.head(8), hide_index=True, use_container_width=True)
            st.caption("Snapshot datato 13 novembre 2026; non è un ordine ufficiale del Draft.")

elif page == "Analisi giocatori":
    st.subheader("Leaderboard giocatori · NCAA 2026-27")
    frame, err = load_dataset("player_box")
    if show_load_error(err):
        pass
    elif frame.empty:
        st.info("Nessun box score giocatore importato.")
    else:
        min_games = st.slider("Partite minime per entrare nei percentili", 1, 20, 5)
        result, meta = player_season_stats(frame, min_games=min_games)
        if result.empty:
            st.warning("I campi del dataset non consentono ancora di calcolare una classifica.")
            st.caption("Campi sorgente: " + ", ".join(frame.columns[:60]))
        else:
            st.caption(f"{meta['players']:,} identità aggregate · {meta['qualified_players']:,} nel campione percentile · {meta['identity_unresolved']:,} identità senza ID NCAA")
            st.info("I percentili confrontano i giocatori presenti nei box score importati, con la soglia minima scelta. Non rappresentano ancora una classifica completa di tutta la Division I.")
            c1, c2 = st.columns(2)
            with c1:
                metric = st.selectbox("Ordina per", [c for c in result.columns if c not in ["ID NCAA", "Giocatore", "Squadra ID", "Identità verificata", "Campione percentile valido"]])
            with c2:
                search = st.text_input("Cerca giocatore")
            view = result.copy()
            if search:
                view = view[view["Giocatore"].str.contains(search, case=False, na=False)]
            view = view.sort_values(metric, ascending=False, na_position="last")
            display = view.copy()
            percent_cols = [col for col in ["FG%", "eFG%", "3P%", "FT%", "TS%"] if col in display.columns]
            for col in percent_cols:
                display[col] = pd.to_numeric(display[col], errors="coerce") * 100
            column_config = {
                col: st.column_config.NumberColumn(col, format="%.1f%%")
                for col in percent_cols
            }
            st.dataframe(display, column_config=column_config, hide_index=True,
                         use_container_width=True, height=650)
            if metric in view and view[metric].notna().sum() >= 2:
                st.markdown("#### Primi 20 · " + metric)
                chart = view[["Giocatore", metric]].head(20).copy()
                if metric in percent_cols:
                    chart[metric] = chart[metric] * 100
                st.bar_chart(chart.set_index("Giocatore"))
            st.caption("TS% = PTS / [2 × (FGA + 0,44 × FTA)]. eFG% = (FGM + 0,5 × 3PM) / FGA. Le percentuali sono ricalcolate dai totali stagionali.")

elif page == "Scheda giocatore":
    st.subheader("Scheda giocatore · stagione 2026-27")
    frame, err = load_dataset("player_box")
    if show_load_error(err):
        pass
    elif frame.empty:
        st.info("Nessun box score importato.")
    else:
        result, meta = player_season_stats(frame, min_games=1)
        if result.empty:
            st.warning("Non è ancora possibile costruire le schede dai campi disponibili.")
        else:
            names = sorted(result["Giocatore"].dropna().unique().tolist())
            selected = st.selectbox("Seleziona giocatore", names)
            row = result[result["Giocatore"] == selected].iloc[0]
            stats = ["Partite", "Minuti per partita", "Punti per partita", "Assist per partita",
                     "Rimbalzi offensivi per partita", "Rimbalzi difensivi per partita",
                     "TS%", "eFG%", "3P%", "FT%"]
            available = [s for s in stats if s in result.columns]
            cols = st.columns(min(5, len(available)))
            for i, stat in enumerate(available):
                value = row[stat]
                label = stat
                if stat.endswith("%") and pd.notna(value):
                    value = f"{float(value) * 100:.1f}%"
                elif pd.notna(value):
                    value = f"{float(value):.1f}" if stat != "Partite" else str(int(value))
                else:
                    value = "n/d"
                cols[i % len(cols)].metric(label, value)
            st.caption("ID NCAA: " + (str(row["ID NCAA"]) if pd.notna(row["ID NCAA"]) else "non risolto") +
                       " · Identità verificata: " + ("sì" if row["Identità verificata"] else "no"))
            id_col = first_column(frame, ["player_id", "ncaa_player_id"])
            name_col = first_column(frame, ["clean_name", "player", "name", "athlete_display_name"])
            if id_col and pd.notna(row["ID NCAA"]):
                game_log = frame[frame[id_col].astype("string") == str(row["ID NCAA"])].copy()
            else:
                team_col = first_column(frame, ["team_ncaa_team_id", "team_id", "team"])
                game_log = frame[frame[name_col].astype(str) == selected].copy()
                if team_col and pd.notna(row["Squadra ID"]):
                    game_log = game_log[game_log[team_col].astype(str) == str(row["Squadra ID"])]
            st.markdown("#### Box score partita per partita")
            st.dataframe(game_log, hide_index=True, use_container_width=True, height=500)

elif page == "Analisi squadre":
    st.subheader("Analisi squadre · NCAA 2026-27")
    frame, err = load_dataset("team_box")
    if show_load_error(err):
        pass
    elif frame.empty:
        st.info("Nessun box score squadra importato.")
    else:
        table, meta = team_season_stats(frame)
        if table.empty:
            st.warning("Non è stato trovato un identificativo squadra riconosciuto.")
            st.caption("Campi disponibili: " + ", ".join(frame.columns[:60]))
        else:
            st.caption(f"{meta['teams']} squadre aggregate da {meta['source_rows']:,} record partita.")
            cols = [c for c in table.columns if c != "Squadra ID"]
            metric = st.selectbox("Ordina per indicatore", cols)
            table = table.sort_values(metric, ascending=False, na_position="last")
            display = table.copy()
            percent_cols = [col for col in display.columns if col.endswith("%")]
            for col in percent_cols:
                display[col] = pd.to_numeric(display[col], errors="coerce") * 100
            column_config = {
                col: st.column_config.NumberColumn(col, format="%.1f%%")
                for col in percent_cols
            }
            st.dataframe(display, column_config=column_config, hide_index=True,
                         use_container_width=True, height=650)

elif page == "Partite":
    st.subheader("Calendario e risultati · NCAA 2026-27")
    frame, err = load_dataset("schedule")
    if show_load_error(err):
        pass
    elif frame.empty:
        st.info("Nessun calendario importato.")
    else:
        search = st.text_input("Cerca squadra")
        if search:
            mask = frame.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            frame = frame[mask]
        date_col = first_column(frame, ["game_date", "date"])
        if date_col:
            frame = frame.sort_values(date_col, ascending=False, na_position="last")
        st.caption(f"{len(frame):,} record calendario presenti nella sorgente importata; non è una dichiarazione di copertura completa.")
        st.dataframe(frame, hide_index=True, use_container_width=True, height=650)

elif page == "Roster NCAA":
    st.subheader("Roster NCAA · stagione 2026-27")
    frame, err = load_dataset("team_rosters")
    if show_load_error(err):
        pass
    elif frame.empty:
        st.info("Nessun roster importato.")
    else:
        c1, c2 = st.columns(2)
        team_col = first_column(frame, ["team", "team_name"])
        name_col = first_column(frame, ["clean_name", "player", "name"])
        if team_col:
            teams = ["Tutte"] + sorted(frame[team_col].dropna().astype(str).unique().tolist())
            team = c1.selectbox("Squadra", teams)
            if team != "Tutte":
                frame = frame[frame[team_col].astype(str) == team]
        if name_col:
            search = c2.text_input("Cerca giocatore")
            if search:
                frame = frame[frame[name_col].astype(str).str.contains(search, case=False, na=False)]
        st.caption("Roster originali del provider. La presenza nel roster non dimostra la nazionalità italiana.")
        st.dataframe(frame, hide_index=True, use_container_width=True, height=650)

elif page == "Giocatori italiani":
    st.subheader("Directory giocatori italiani")
    st.info("La directory ufficiale viene popolata solo dopo la verifica della nazionalità tramite biografie universitarie, federazioni o fonti primarie.")
    st.write("Stato attuale: i dati roster NCAA sono consultabili nella sezione Roster NCAA, ma non vengono etichettati automaticamente come italiani.")
    st.caption("Questa separazione evita falsi positivi basati su cognome, luogo di nascita o nome della squadra.")

elif page == "Quintetti e tiri":
    st.subheader("Quintetti, matchup e shot chart · NCAA 2026-27")
    tab1, tab2, tab3 = st.tabs(["Quintetti", "Matchup", "Tiri"])
    with tab1:
        frame, err = load_dataset("lineups")
        if show_load_error(err):
            pass
        elif frame.empty:
            st.info("Nessun dato quintetti importato.")
        else:
            st.caption(f"{len(frame):,} stint di lineup caricati. I campi originali sono mantenuti.")
            st.dataframe(frame, hide_index=True, use_container_width=True, height=550)
    with tab2:
        frame, err = load_dataset("matchup_stints")
        if show_load_error(err):
            pass
        elif frame.empty:
            st.info("Nessun matchup stint importato.")
        else:
            st.caption(f"{len(frame):,} matchup stint caricati.")
            st.dataframe(frame, hide_index=True, use_container_width=True, height=550)
    with tab3:
        frame, err = load_dataset("shots")
        if show_load_error(err):
            pass
        elif frame.empty:
            st.info("Nessun tiro importato.")
        else:
            x_col = first_column(frame, ["shot_x", "x"])
            y_col = first_column(frame, ["shot_y", "y"])
            if x_col and y_col:
                frame[x_col] = pd.to_numeric(frame[x_col], errors="coerce")
                frame[y_col] = pd.to_numeric(frame[y_col], errors="coerce")
                plot = frame.dropna(subset=[x_col, y_col])
                st.caption(f"{len(plot):,} tiri con entrambe le coordinate disponibili su {len(frame):,} record.")
                st.scatter_chart(plot, x=x_col, y=y_col)
            else:
                st.warning("Le coordinate non sono presenti nei campi riconosciuti: nessuno shot chart viene simulato.")
            st.dataframe(frame.head(500), hide_index=True, use_container_width=True, height=450)

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
        st.caption("Snapshot 13 novembre 2026 · consensus Ultimate Big Board.")
        st.link_button("Apri fonte del ranking", "https://ultimatebigboard.com/nba/2027/")

elif page == "Fonti e dati":
    st.subheader("Fonti, copertura e qualità")
    data, err = summary()
    if show_load_error(err):
        pass
    elif data:
        st.metric("Record grezzi stagione 2026-27", f"{data['rows_total']:,}")
        if data["datasets"]:
            st.dataframe(pd.DataFrame(data["datasets"]), hide_index=True, use_container_width=True)
        else:
            st.info("Nessun dataset importato.")
    st.markdown("#### Esplora i record originali")
    dataset = st.selectbox("Dataset", DATASETS)
    frame, load_error = load_dataset(dataset)
    if show_load_error(load_error):
        pass
    elif frame.empty:
        st.info("Nessun record disponibile per questo dataset.")
    else:
        st.caption(f"{len(frame):,} record caricati · limite di consultazione 100.000")
        st.dataframe(frame, hide_index=True, use_container_width=True, height=600)
    st.markdown("#### Regole di qualità")
    st.write("• Solo stagione 2026-27 · • Nessuno storico · • Dato mancante distinto da zero")
    st.write("• Provenienza originale conservata · • Nazionalità italiana documentata")
    st.write("• Percentili su campione esplicito · • Metriche non disponibili non vengono inventate")

st.divider()
st.caption("NCAA Italian Players · stagione 2026-27 · dati reali da PostgreSQL · nessuna statistica simulata.")
