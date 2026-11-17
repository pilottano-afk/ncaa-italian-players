from __future__ import annotations

import os
import re
import unicodedata
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
ITALIAN_CANDIDATES_FILE = ROOT / "docs" / "italian-player-candidates-2026-27.csv"
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
    "Giocatori italiani", "Scheda giocatore", "Draft NBA 2027",
    "Analisi squadre", "Partite", "Dashboard", "Fonti e dati"
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


def normalized_name(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def italian_candidates():
    if not ITALIAN_CANDIDATES_FILE.exists():
        return pd.DataFrame()
    frame = pd.read_csv(ITALIAN_CANDIDATES_FILE)
    if "source_name" in frame:
        frame["_match_name"] = frame["source_name"].map(normalized_name)
    return frame


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
    st.subheader("Scheda giocatore · italiani NCAA 2026-27")
    candidates = italian_candidates()
    box, err = load_dataset("player_box")
    if show_load_error(err):
        pass
    elif candidates.empty or box.empty:
        st.info("Elenco italiano o box score non disponibili.")
    else:
        result, _ = player_season_stats(box, min_games=1)
        if result.empty:
            st.info("Non ci sono ancora statistiche individuali utilizzabili.")
        else:
            result["_match_name"] = result["Giocatore"].map(normalized_name)
            options = candidates[["source_name", "team", "_match_name"]].drop_duplicates()
            selected = st.selectbox("Seleziona un giocatore italiano", options["source_name"].tolist())
            candidate = options[options["source_name"] == selected].iloc[0]
            matches = result[result["_match_name"] == candidate["_match_name"]]
            if len(matches) != 1:
                st.info("Statistiche non ancora collegate in modo univoco. La scheda sarà completata quando avremo un'identificazione sicura.")
            else:
                row = matches.iloc[0]
                st.markdown(f"### {selected}")
                st.caption(f"{candidate['team']} · stagione 2026-27")
                metrics = ["Partite", "Minuti per partita", "Punti per partita", "Assist per partita",
                           "Rimbalzi offensivi per partita", "Rimbalzi difensivi per partita",
                           "TS%", "eFG%", "3P%", "FT%"]
                available = [item for item in metrics if item in result.columns]
                cols = st.columns(min(5, len(available)))
                for i, item in enumerate(available):
                    value = row[item]
                    if item.endswith("%") and pd.notna(value):
                        value = f"{float(value) * 100:.1f}%"
                    elif pd.notna(value):
                        value = f"{float(value):.1f}" if item != "Partite" else str(int(value))
                    else:
                        value = "n/d"
                    cols[i % len(cols)].metric(item, value)
                name_col = first_column(box, ["clean_name", "player", "name", "athlete_display_name"])
                if name_col:
                    game_log = box[box[name_col].map(normalized_name) == candidate["_match_name"]].copy()
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
    st.subheader("Giocatori italiani · NCAA Division I · 2026-27")
    candidates = italian_candidates()
    if candidates.empty:
        st.error("Non trovo la lista italiana di riferimento. Controllare il file CSV nella repository.")
    else:
        st.caption("Elenco di riferimento: Bamboden · statistiche partita per partita: archivio NCAA collegato a Neon.")
        box, err = load_dataset("player_box")
        if show_load_error(err):
            box = pd.DataFrame()
        stats = pd.DataFrame()
        if not box.empty:
            stats, _ = player_season_stats(box, min_games=1)
        if not stats.empty:
            stats["_match_name"] = stats["Giocatore"].map(normalized_name)
            counts = stats.groupby("_match_name")["ID NCAA"].nunique(dropna=True)
            unique_names = set(counts[counts <= 1].index)
            stats = stats[stats["_match_name"].isin(unique_names)].drop_duplicates("_match_name")
            wanted = ["Partite", "Minuti per partita", "Punti per partita", "Assist per partita",
                      "Rimbalzi offensivi per partita", "Rimbalzi difensivi per partita",
                      "FG%", "3P%", "FT%", "TS%"]
            keep = ["_match_name"] + [col for col in wanted if col in stats.columns]
            view = candidates.merge(stats[keep], on="_match_name", how="left")
        else:
            view = candidates.copy()
        orb = pd.to_numeric(view.get("Rimbalzi offensivi per partita", pd.Series(index=view.index, dtype=float)), errors="coerce").fillna(0)
        drb = pd.to_numeric(view.get("Rimbalzi difensivi per partita", pd.Series(index=view.index, dtype=float)), errors="coerce").fillna(0)
        view["Rimbalzi per partita"] = orb + drb
        view["Stato statistiche"] = view["Punti per partita"].notna().map({True: "Disponibili", False: "In attesa"})
        a, b = st.columns(2)
        a.metric("Giocatori nell'elenco Bamboden", len(candidates))
        b.metric("Con statistiche collegate", int(view["Punti per partita"].notna().sum()))
        search = st.text_input("Cerca giocatore o università")
        if search:
            mask = view.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            view = view[mask]
        pairs = [("source_name", "Giocatore"), ("team", "Università"), ("Partite", "Partite"),
                 ("Minuti per partita", "Minuti"), ("Punti per partita", "Punti"),
                 ("Assist per partita", "Assist"), ("Rimbalzi per partita", "Rimbalzi"),
                 ("FG%", "FG%"), ("3P%", "3P%"), ("FT%", "FT%"), ("TS%", "TS%"),
                 ("Stato statistiche", "Stato")]
        available_pairs = [(col, label) for col, label in pairs if col in view.columns]
        display = view[[col for col, _ in available_pairs]].copy()
        display.columns = [label for _, label in available_pairs]
        percent_cols = [col for col in ["FG%", "3P%", "FT%", "TS%"] if col in display]
        for col in percent_cols:
            display[col] = pd.to_numeric(display[col], errors="coerce") * 100
        config = {col: st.column_config.NumberColumn(col, format="%.1f%%") for col in percent_cols}
        st.dataframe(display, column_config=config, hide_index=True, use_container_width=True, height=620)
        st.caption("Statistiche collegate solo quando il nome coincide in modo univoco. Nessuna associazione incerta viene inventata.")
        st.link_button("Apri elenco Bamboden", "https://college.bamboden.com/en/italiani")
        st.caption("Fonte elenco: Bamboden. Statistiche: dataset NCAA importati in Neon. Solo stagione corrente.")

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
