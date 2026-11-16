from __future__ import annotations
import os, re
from pathlib import Path
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="NCAA Italian Players", page_icon="🏀", layout="wide")
ROOT = Path(__file__).resolve().parents[2]
DRAFT_FILE = ROOT / "docs" / "nba-draft-2027-top-30.md"
SEASON = 2027
DATASETS = ["schedule","team_rosters","rosters","pbp","player_box","team_box","lineups","matchup_stints","possessions","shots","team_ids"]

st.markdown("""<style>
.block-container{padding-top:2rem;max-width:1440px}
.hero{padding:1.6rem 1.8rem;border-radius:18px;background:linear-gradient(115deg,#101c35,#193d63);color:white;margin-bottom:1.2rem}
.hero h1{font-size:2.25rem;margin:0 0 .35rem;color:white}.hero p{font-size:1rem;opacity:.88;margin:0}
div[data-testid="stMetric"]{background:rgba(120,140,170,.09);padding:14px;border-radius:12px}
</style>""", unsafe_allow_html=True)
st.sidebar.title("🏀 NCAA Italian Players")
page=st.sidebar.radio("Navigazione",["Dashboard","Giocatori italiani","Squadre","Partite","Draft NBA 2027","Fonti e dati"])
st.sidebar.caption("Stagione attiva: 2026-27")
st.sidebar.caption("Archivio storico disattivato")

def db_url():
    value=os.getenv("DATABASE_URL") or os.getenv("NCAA_DATABASE_URL")
    if not value:
        try: value=st.secrets.get("DATABASE_URL") or st.secrets.get("NCAA_DATABASE_URL")
        except Exception: value=None
    if not value: return None
    value=str(value).strip()
    if value.startswith("postgres://"): value="postgresql+psycopg://"+value[len("postgres://"):]
    elif value.startswith("postgresql://"): value="postgresql+psycopg://"+value[len("postgresql://"):]
    return value

@st.cache_resource(show_spinner=False)
def engine(url):
    return create_engine(url,pool_pre_ping=True,pool_size=1,max_overflow=0,connect_args={"connect_timeout":8})

def query(sql,params=None):
    url=db_url()
    if not url: return None,"Database non configurato: aggiungi DATABASE_URL nei Secrets di Streamlit."
    try:
        with engine(url).connect() as conn: return conn.execute(text(sql),params or {}).mappings().all(),None
    except Exception as exc:
        return None,f"Database non raggiungibile ({exc.__class__.__name__}). Controlla la stringa DATABASE_URL e l'importazione."

def summary():
    rows,err=query("SELECT dataset,COUNT(*) AS rows,MAX(imported_at) AS last_imported FROM ncaa_raw_rows WHERE season=:season GROUP BY dataset ORDER BY dataset",{"season":SEASON})
    if err:return None,err
    data=[{"dataset":r["dataset"],"rows":int(r["rows"]),"last_imported":r["last_imported"].isoformat() if r["last_imported"] else None} for r in rows]
    return {"rows_total":sum(x["rows"] for x in data),"datasets":data},None

def raw_rows(dataset,limit,offset):
    if dataset not in DATASETS:return None,"Dataset non consentito."
    total,err=query("SELECT COUNT(*) AS total FROM ncaa_raw_rows WHERE season=:season AND dataset=:dataset",{"season":SEASON,"dataset":dataset})
    if err:return None,err
    rows,err=query("SELECT source_file,artifact_sha256,source_row_number,imported_at,payload FROM ncaa_raw_rows WHERE season=:season AND dataset=:dataset ORDER BY source_row_number LIMIT :lim OFFSET :off",{"season":SEASON,"dataset":dataset,"lim":limit,"off":offset})
    if err:return None,err
    return {"total":int(total[0]["total"]),"records":rows},None

def draft_data():
    if not DRAFT_FILE.exists():return pd.DataFrame(columns=["Rank","Prospect","Team / club"])
    rows=[]
    for line in DRAFT_FILE.read_text(encoding="utf-8").splitlines():
        m=re.match(r"\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|",line)
        if m:rows.append({"Rank":int(m.group(1)),"Prospect":m.group(2),"Team / club":m.group(3)})
    return pd.DataFrame(rows)

st.markdown('<div class="hero"><h1>NCAA Italian Players</h1><p>Basketball intelligence · NCAA Men 2026-27 · Italian player tracker & NBA Draft 2027</p></div>',unsafe_allow_html=True)
if page=="Dashboard":
    st.subheader("Panoramica stagione")
    data,err=summary()
    a,b,c,d=st.columns(4);a.metric("Stagione","2026-27");b.metric("Storico","Disattivato");c.metric("Dataset previsti",len(DATASETS));d.metric("Record nel database",f"{data['rows_total']:,}" if data else "—")
    if err:st.warning("Database non ancora collegato.");st.caption(err)
    elif not data["rows_total"]:st.info("Database collegato, ma l'importazione NCAA 2026-27 non è ancora stata eseguita.")
    else:st.success("PostgreSQL collegato · conteggi reali letti direttamente dal database.");st.dataframe(pd.DataFrame(data["datasets"]),hide_index=True,use_container_width=True)
    st.divider();left,right=st.columns([1.35,1])
    with left:
        st.markdown("### Centro analisi");st.info("Le statistiche saranno mostrate quando i dati necessari saranno disponibili e verificati. Nessun numero simulato.")
        st.write("• Directory verificata dei giocatori italiani");st.write("• TS%, eFG%, ORtg, DRtg, NetRtg e usage");st.write("• Lineup, possessi, play-by-play e shot charts");st.write("• Percentili per giocatori e squadre")
    with right:
        st.markdown("### Prospetti Draft");df=draft_data()
        if not df.empty:st.dataframe(df.head(5),hide_index=True,use_container_width=True)
elif page=="Giocatori italiani":
    st.subheader("Giocatori italiani NCAA");st.info("La directory sarà pubblicata solo dopo la verifica della nazionalità tramite roster universitari ufficiali o fonti federali. Nessun nome viene dedotto dal solo cognome.")
elif page=="Squadre":
    st.subheader("Squadre NCAA");st.info("Schede squadra, conference, record, offensive/defensive rating, four factors e andamento partita per partita.")
elif page=="Partite":
    st.subheader("Partite e risultati");st.info("Calendario, risultati, box score, play-by-play e analisi dei possessi. Solo stagione 2026-27.")
elif page=="Draft NBA 2027":
    st.subheader("NBA Draft 2027 · Top 30");st.caption("Classifica generale, qualsiasi nazionalità, separata dalla directory italiana.")
    df=draft_data()
    if df.empty:st.warning("Ranking non trovato.")
    else:
        q=st.text_input("Cerca prospetto o squadra",placeholder="Nome, università o club…")
        if q:df=df[df.astype(str).apply(lambda col:col.str.contains(q,case=False,na=False)).any(axis=1)]
        st.dataframe(df,hide_index=True,use_container_width=True,height=650)
        st.caption("Snapshot 13 novembre 2026 · ranking consensus Ultimate Big Board")
        st.link_button("Apri fonte del ranking","https://ultimatebigboard.com/nba/2027/")
elif page=="Fonti e dati":
    st.subheader("Fonti, copertura e qualità");data,err=summary()
    if err:st.warning(err)
    else:
        st.success(f"PostgreSQL collegato · {data['rows_total']:,} record della stagione 2026-27.")
        if data["datasets"]:st.dataframe(pd.DataFrame(data["datasets"]),hide_index=True,use_container_width=True)
        else:st.info("Nessun dataset importato.")
    st.markdown("#### Esplora i record originali");st.caption("Consultazione diretta del database, con provenienza.")
    ds=st.selectbox("Dataset",DATASETS);size=st.select_slider("Record per pagina",options=[10,25,50,100,200],value=25);pg=st.number_input("Pagina",min_value=1,value=1,step=1)
    if st.button("Carica record",type="primary"):st.session_state["raw_request"]=(ds,size,pg)
    if "raw_request" in st.session_state:
        ds2,n,p=st.session_state["raw_request"];result,err=raw_rows(ds2,n,(p-1)*n)
        if err:st.warning(err)
        elif result:
            st.caption(f"{result['total']:,} record totali · pagina {p} · stagione 2026-27")
            if result["records"]:
                st.dataframe(pd.json_normalize([dict(r["payload"]) for r in result["records"]]),hide_index=True,use_container_width=True,height=420)
                with st.expander("Provenienza dei record"):
                    st.dataframe(pd.DataFrame([{k:(r[k].isoformat() if k=="imported_at" and r[k] else r[k]) for k in ("source_file","artifact_sha256","source_row_number","imported_at")} for r in result["records"]]),hide_index=True,use_container_width=True)
            else:st.info("Nessun record per questo dataset.")
    st.markdown("#### Regole di qualità");st.write("• Solo stagione 2026-27 · • Nessuno storico · • Zero distinto da dato mancante · • Nazionalità documentata · • Provenienza conservata.")
st.divider();st.caption("NCAA Italian Players · dati reali da PostgreSQL · nessuna statistica simulata.")
