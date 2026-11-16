# NCAA Italian Players

Piattaforma di analisi del basket NCAA maschile, focalizzata sui giocatori italiani e sui migliori 30 prospetti assoluti del Draft NBA 2027.

## App dashboard

La prima interfaccia Streamlit è disponibile in `apps/dashboard/app.py`. Include:
- Dashboard di stato API e copertura fonti.
- Navigazione Giocatori italiani, Squadre e Partite.
- Top 30 NBA Draft 2027 con ricerca.
- Stato delle fonti e regole di qualità.

Le sezioni statistiche non mostrano numeri fittizi: restano esplicitamente in attesa del database e delle API analitiche. La dashboard legge il ranking Draft dal documento versionato nel repository.

### Avvio dashboard

```bash
pip install -r apps/dashboard/requirements.txt
NCAA_API_URL=http://localhost:8000 streamlit run apps/dashboard/app.py
```

Oppure avviare il container dashboard:

```bash
docker build -f apps/dashboard/Dockerfile -t ncaa-dashboard .
docker run --rm -p 8501:8501 -e NCAA_API_URL=http://host.docker.internal:8000 ncaa-dashboard
```

## Importazione nel database cloud

È presente il workflow GitHub Actions `Import NCAA 2026-27 data into PostgreSQL`:
1. Crea un database PostgreSQL gestito da un provider cloud.
2. Nel repository apri **Settings → Secrets and variables → Actions** e aggiungi il secret `NCAA_DATABASE_URL` con la stringa di connessione PostgreSQL (preferibilmente SSL).
3. Apri **Actions → Import NCAA 2026-27 data into PostgreSQL → Run workflow**.
4. Il workflow scarica i dataset della sola stagione 2026-27, controlla manifest e qualità, quindi importa le righe originali in JSONB. L'importazione è idempotente: rieseguire lo stesso artefatto non duplica le righe.
5. Quando l'API è collegata allo stesso database, la dashboard mostra il conteggio effettivo e consente di esplorare i record originali nella sezione **Fonti e dati**.

Il workflow non crea automaticamente un database né pubblica l'app: il database cloud e il relativo secret devono essere configurati una volta. Non inserire mai la stringa di connessione nel codice o nei file del repository.

## API dati grezzi

- `GET /api/v1/database/summary` — copertura effettivamente importata.
- `GET /api/v1/database/datasets` — dataset disponibili e dataset importati.
- `GET /api/v1/raw/{dataset}?limit=25&offset=0` — anteprima paginata dei record originali della stagione 2026-27.

## Ambito dati

- **Stagione inclusa:** NCAA 2026-27 (season key `2027`).
- **Storico:** escluso. Il progetto non deve importare o mostrare stagioni precedenti.
- **Dati:** solo dati reali provenienti da fonti verificabili. Nessun dato simulato.
- **Copertura:** giocatori italiani NCAA; prospetti Draft NBA 2027 di qualsiasi nazionalità in una sezione distinta.

## Principi di qualità

1. Conservare la provenienza e l'ora di acquisizione di ogni dato.
2. Distinguere valori mancanti, dati non verificati e valori pari a zero.
3. Non dedurre la nazionalità dal solo nome: mantenere una verifica esplicita della fonte.
4. Non confondere i 30 prospetti Draft con la lista dei giocatori italiani.
5. Calcolare metriche avanzate solo quando i dati grezzi necessari sono disponibili.

## Fonti candidate

- SportsDataverse `ncaa-mbb-hoops-data` / hoopR.
- CollegeBasketballData.com (API key necessaria).
- Siti ufficiali NCAA e roster ufficiali delle università per la verifica dei giocatori.

Le fonti sono candidate: la disponibilità effettiva della stagione 2026-27 e dei singoli campi va verificata prima di considerarli utilizzabili.

## Stato

La prima dashboard navigabile è stata aggiunta. Il backend API e la pipeline di staging/audit sono presenti; il database non è ancora popolato e le API analitiche non sono ancora disponibili. La dashboard rende visibile questo stato senza simulare statistiche.

## Stack

- Backend: Python / FastAPI.
- Dashboard iniziale: Streamlit.
- Database: PostgreSQL.
- Aggiornamento: processo schedulato giornaliero, con controllo di freschezza e report degli errori.
