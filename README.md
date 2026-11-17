# NCAA Italian Players

Dashboard in italiano per l'analisi del basket NCAA maschile, con dati della sola stagione **2026-27** (`season=2027`). Include la Top 30 assoluta del Draft NBA 2027, indipendentemente dalla nazionalità, separata dalla directory dei giocatori italiani verificati.

## Architettura

- **Streamlit**: dashboard e grafici.
- **Neon PostgreSQL**: archivio dei record originali in JSONB.
- **GitHub Actions**: acquisizione, controllo qualità e importazione giornaliera.
- **SportsDataverse NCAA MBB**: fonte primaria corrente; CollegeBasketballData è prevista come fonte secondaria di verifica.

## Funzionalità della dashboard

- Panoramica della stagione e stato dei dataset importati.
- Leaderboard giocatori: totali e medie per partita, FG%, eFG%, 3P%, FT% e TS%.
- Percentili con soglia minima di partite configurabile e popolazione di confronto dichiarata.
- Scheda giocatore con riepilogo stagione e box score gara per gara.
- Analisi squadre e calendario/risultati.
- Roster NCAA, quintetti, matchup stints e coordinate dei tiri, se presenti nella sorgente.
- Top 30 Draft NBA 2027 con snapshot e fonte separati dalla directory italiana.
- Esplorazione dei record originali per dataset.

### Formule

- **TS%** = PTS / [2 × (FGA + 0,44 × FTA)]
- **eFG%** = (FGM + 0,5 × 3PM) / FGA
- FG%, 3P% e FT% sono ricalcolate dai totali stagionali, non dalla media semplice delle percentuali partita per partita.
- I percentili sono calcolati solo sul campione della stagione 2026-27 che supera la soglia minima selezionata. Non sono presentati come ranking nazionale completo finché la copertura non è stata verificata.

## Regole di qualità

- Il solo valore stagione accettato è `2027` (2026-27). Lo storico è escluso.
- I record originali restano tracciabili tramite file sorgente, hash dell'artefatto e numero di riga.
- ID mancanti restano non risolti; non vengono uniti sulla base del solo nome.
- I dati mancanti non vengono convertiti in zero.
- La nazionalità italiana richiede prove da fonti primarie; non viene dedotta da cognome, hometown o roster.
- Shot chart, lineup metrics e altre metriche sono mostrate solo quando i relativi campi esistono.
- I conteggi dei record non costituiscono prova di copertura completa della stagione.

## Configurazione Neon

1. Crea un progetto PostgreSQL su [Neon](https://neon.tech/).
2. Copia la connection string dal pannello **Connect**.
3. Nel repository GitHub apri **Settings → Secrets and variables → Actions → New repository secret**:
   - Nome: `NCAA_DATABASE_URL`
   - Valore: connection string PostgreSQL Neon. Non inserirla nel codice o in file pubblici.
4. Il workflow **Import NCAA 2026-27 data into PostgreSQL** scarica, valida, controlla e importa i dati.

Il progetto non crea il database Neon e non può generare credenziali senza l'autenticazione del proprietario.

## Aggiornamento automatico

Dopo l'attivazione del workflow sul branch `main`, l'importazione è programmata ogni giorno alle **07:00 UTC**: 08:00 in Italia durante l'ora solare (CET) e 09:00 durante l'ora legale (CEST). GitHub Actions usa UTC e non applica automaticamente il cambio dell'ora italiana. È disponibile anche l'avvio manuale da **Actions → Run workflow**.

## Pubblicazione Streamlit

1. Apri [Streamlit Community Cloud](https://share.streamlit.io/) e accedi con GitHub.
2. Crea un'app collegata a `pilottano-afk/ncaa-italian-players`.
3. Imposta branch `main` e file `apps/dashboard/app.py`.
4. In **App settings → Secrets** inserisci `DATABASE_URL` con la stessa connection string Neon.
5. Salva e riavvia l'app.

Il secret GitHub e quello Streamlit sono due configurazioni separate. Non condividere le stringhe di connessione in chat o nei commit.

## API dati grezzi

- `GET /health`
- `GET /api/v1/database/summary`
- `GET /api/v1/database/datasets`
- `GET /api/v1/raw/{dataset}?limit=25&offset=0`
- `GET /api/v1/coverage`

## Stato del progetto

La dashboard e i test sono in sviluppo nel pull request dedicato. Database, importazione effettiva e pubblicazione online diventano operativi dopo la configurazione Neon e Streamlit descritta sopra.
