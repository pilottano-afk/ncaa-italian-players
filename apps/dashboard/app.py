from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="NCAA Italian Players", page_icon="🏀", layout="wide")

API_URL = os.getenv("NCAA_API_URL", "http://localhost:8000").rstrip("/")
ROOT = Path(__file__).resolve().parents[2]
DRAFT_FILE = ROOT / "docs" / "nba-draft-2027-top-30.md"

st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1440px;}
  .hero {padding: 1.6rem 1.8rem; border-radius: 18px; background: linear-gradient(115deg,#101c35,#193d63); color: white; margin-bottom: 1.2rem;}
  .hero h1 {font-size: 2.25rem; margin: 0 0 .35rem 0; color: white;}
  .hero p {font-size: 1rem; opacity: .88; margin: 0;}
  div[data-testid="stMetric"] {background: rgba(120,140,170,.09); padding: 14px; border-radius: 12px;}
  .muted {color: #8a93a3; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🏀 NCAA Italian Players")
page = st.sidebar.radio(
    "Navigazione",
    ["Dashboard", "Giocatori italiani", "Squadre", "Partite", "Draft NBA 2027", "Fonti e dati"],
)
st.sidebar.caption("Stagione attiva: 2026-27")
st.sidebar.caption("Archivio storico disattivato")


def get_json(path: str):
    try:
        response = requests.get(f"{API_URL}{path}", timeout=4)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return None, str(exc)


def load_draft() -> pd.DataFrame:
    if not DRAFT_FILE.exists():
        return pd.DataFrame(columns=["Rank", "Prospect", "Team / club"])
    rows = []
    for line in DRAFT_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", line)
        if match:
            rows.append({"Rank": int(match.group(1)), "Prospect": match.group(2), "Team / club": match.group(3)})
    return pd.DataFrame(rows)


def hero():
    st.markdown(
        '<div class="hero"><h1>NCAA Italian Players</h1>'
        '<p>Basketball intelligence · NCAA Men 2026-27 · Italian player tracker & NBA Draft 2027</p></div>',
        unsafe_allow_html=True,
    )


def status_panel():
    health, error = get_json("/health")
    if health:
        st.success(f"API online · stagione {health.get('season_label', '2026-27')}")
    else:
        st.warning("API non collegata. La dashboard è online, ma i dati dinamici arriveranno quando il backend sarà pubblicato.")
        with st.expander("Dettagli connessione"):
            st.code(error or "API non raggiungibile")


hero()

if page == "Dashboard":
    st.subheader("Panoramica stagione")
    status_panel()
    coverage, coverage_error = get_json("/api/v1/coverage")
    database = coverage.get("database", {}) if coverage else {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stagione", "2026-27")
    c2.metric("Storico", "Disattivato")
    c3.metric("Fonti catalogate", str(len(coverage.get("sources", []))) if coverage else "—")
    c4.metric("Righe nel database", f"{database.get('rows_total', 0):,}" if database else "—")
    if database:
        if database.get("status") == "connected":
            st.success("Database collegato · dati reali presenti")
        elif database.get("status") == "connected_empty":
            st.info("Database collegato, ma l’importazione dei dataset non è ancora stata eseguita.")
        else:
            st.warning("Database non ancora pronto o non raggiungibile.")
        imported = database.get("datasets", [])
        if imported:
            st.markdown("#### Dataset NCAA 2026-27 effettivamente importati")
            st.dataframe(pd.DataFrame(imported), hide_index=True, use_container_width=True)
        elif database.get("message"):
            st.caption(database["message"])
    st.divider()
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("### Centro analisi")
        st.info("La struttura dell'app è attiva. Le classifiche e le statistiche dei giocatori saranno mostrate qui appena il database NCAA sarà collegato: nessun numero simulato.")
        st.markdown("**Sezioni in costruzione**")
        st.write("• Directory verificata dei giocatori italiani")
        st.write("• Advanced stats: TS%, eFG%, ORtg, DRtg, NetRtg, usage e metriche per possesso")
        st.write("• Lineup, possessi, play-by-play e shot charts")
        st.write("• Percentili per giocatori e squadre")
    with right:
        st.markdown("### Prossimo aggiornamento")
        st.metric("Dataset previsti", "11")
        st.caption("Schedule, roster, player/team box score, play-by-play, possessi, lineup, matchup stints e tiri.")
        st.markdown("### Prospetti Draft")
        draft = load_draft()
        if not draft.empty:
            st.dataframe(draft.head(5), hide_index=True, use_container_width=True)
            st.caption("Top 30 completo nella sezione Draft NBA 2027.")
        else:
            st.warning("Snapshot Draft non trovato nel repository.")

elif page == "Giocatori italiani":
    st.subheader("Giocatori italiani NCAA")
    st.info("La directory sarà popolata esclusivamente dopo la verifica della nazionalità tramite roster universitari ufficiali o fonti federali. Non vengono mostrati nomi dedotti o non verificati.")
    st.markdown("**Campi previsti:** giocatore · università · conference · anno · ruolo · presenze · minuti · statistiche avanzate · fonte di verifica.")
    st.caption("Stato: schema e fonti in preparazione; nessun elenco verificato ancora pubblicato.")

elif page == "Squadre":
    st.subheader("Squadre NCAA")
    st.info("La sezione mostrerà schede squadra, conference, record, offensive/defensive rating, four factors e andamento partita per partita.")
    st.caption("In attesa del collegamento del database 2026-27.")

elif page == "Partite":
    st.subheader("Partite e risultati")
    st.info("Calendario, risultati, box score, play-by-play e analisi dei possessi saranno disponibili qui.")
    st.caption("Solo stagione 2026-27. Le partite senza dati verificati non verranno completate con valori stimati.")

elif page == "Draft NBA 2027":
    st.subheader("NBA Draft 2027 · Top 30")
    st.caption("Classifica generale, qualsiasi nazionalità. Dataset separato dalla directory dei giocatori italiani.")
    draft = load_draft()
    if draft.empty:
        st.warning("File di ranking non disponibile.")
    else:
        query = st.text_input("Cerca prospetto o squadra", placeholder="Nome, università o club…")
        view = draft
        if query:
            view = draft[draft.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)]
        st.dataframe(view, hide_index=True, use_container_width=True, height=650)
        st.caption(f"{len(draft)} prospetti · snapshot 13 novembre 2026 · ranking consensus Ultimate Big Board")
        st.link_button("Apri fonte del ranking", "https://ultimatebigboard.com/nba/2027/")

elif page == "Fonti e dati":
    st.subheader("Fonti, copertura e qualità")
    coverage, error = get_json("/api/v1/coverage")
    if coverage:
        st.write(f"Stato API: **{coverage.get('status', 'non disponibile')}**")
        st.write(coverage.get("note", ""))
        st.markdown("#### Fonti catalogate")
        for source in coverage.get("sources", []):
            with st.expander(source.get("name", source.get("id", "Fonte"))):
                st.write(source)
        st.markdown("#### Stato delle connessioni")
        for source in coverage.get("source_health", []):
            st.write(f"**{source.get('name', source.get('id'))}** — {source.get('status')}")
            st.caption(source.get("message", ""))
    else:
        st.warning("Il backend non è ancora raggiungibile dalla dashboard.")
        st.caption(error or "")
    st.markdown("#### Regole di qualità")
    st.write("• Solo stagione 2026-27 · • Nessuno storico · • Zero distinto da dato mancante · • Nazionalità documentata · • Provenienza e timestamp conservati.")

st.divider()
st.caption("NCAA Italian Players · prototipo applicativo in evoluzione · dati reali solo quando verificati e collegati.")
