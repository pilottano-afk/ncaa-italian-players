# NCAA Italian Players

Dashboard di analisi NCAA maschile, con directory dei giocatori italiani e Top 30 assoluta NBA Draft 2027.

## Pubblicazione gratuita: Neon + Streamlit Community Cloud

Architettura: Neon per PostgreSQL, Streamlit Community Cloud per la dashboard e GitHub Actions per importare i dati. La dashboard si collega direttamente a PostgreSQL, quindi non serve pubblicare un server API separato per visualizzare copertura e record grezzi.

### 1. Crea il database Neon
1. Apri https://neon.tech/ e crea un account gratuito.
2. Crea un progetto PostgreSQL, scegliendo una regione europea se disponibile.
3. Apri **Connect** e copia la stringa PostgreSQL (preferibilmente la variante pooled). Non condividerla pubblicamente.

### 2. Collega Neon a GitHub Actions
Nel repository apri **Settings → Secrets and variables → Actions → New repository secret**.
- Nome: **NCAA_DATABASE_URL**
- Valore: la stringa di connessione copiata da Neon.

Poi apri **Actions → Import NCAA 2026-27 data into PostgreSQL → Run workflow**. Il workflow importa esclusivamente la stagione 2026-27 e conserva i record originali con provenienza. Il workflow non crea il database.

### 3. Pubblica la dashboard
1. Apri https://share.streamlit.io/ e accedi con GitHub.
2. Seleziona **Create app**.
3. Repository: **pilottano-afk/ncaa-italian-players**.
4. Branch: **main**.
5. Main file path: **apps/dashboard/app.py**.
6. Crea l'app.
7. Nelle impostazioni dell'app apri **Secrets** e inserisci:

   DATABASE_URL = "INCOLLA_QUI_LA_STRINGA_DI_NEON"

   Il valore va inserito nel pannello Secrets, mai nel codice o nel repository. Salva e riavvia l'app se richiesto.

### Cosa offre la dashboard
- Stato e conteggi reali del database.
- Esplorazione paginata dei record originali con provenienza.
- Top 30 Draft NBA 2027 separato dalla directory dei giocatori italiani.
- Nessuna statistica simulata.

### Limiti del piano gratuito
I limiti di spazio e utilizzo possono cambiare. Play-by-play, possessi e tiri possono occupare molto spazio: controlla il consumo Neon dopo l'importazione e non passare a un piano a pagamento senza aver verificato i costi.

## API dati grezzi
Il backend API resta nel repository per sviluppi futuri:
- GET /api/v1/database/summary
- GET /api/v1/database/datasets
- GET /api/v1/raw/{dataset}?limit=25&offset=0

## Ambito e qualità
- Solo NCAA 2026-27 (season key 2027), nessuno storico.
- Dati reali e verificabili; nessun dato simulato.
- Nazionalità italiana verificata tramite fonti ufficiali, mai dedotta dal nome.
- Provenienza e timestamp conservati.
- Metriche avanzate calcolate solo quando i dati necessari sono disponibili.

## Stato
La dashboard è predisposta per PostgreSQL diretto. Database cloud, importazione e pubblicazione richiedono la configurazione degli account e dei Secrets sopra descritta.
