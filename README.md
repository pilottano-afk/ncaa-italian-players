# NCAA Italian Players

Piattaforma di analisi del basket NCAA maschile, focalizzata sui giocatori italiani e sui migliori 30 prospetti assoluti del Draft NBA 2027.

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
- RealGM come fonte di scoperta, non come unica prova di appartenenza a Division I.

Le fonti sono candidate: la disponibilità effettiva della stagione 2026-27 e dei singoli campi va verificata prima di considerarli utilizzabili.

## Stato

Repository inizializzato. In questa prima fase si definiscono architettura, modello dati e controlli di qualità prima di collegare le fonti live.

## Stack previsto

- Backend: Python.
- Database: PostgreSQL.
- Frontend: TypeScript / Next.js.
- Aggiornamento: processo schedulato giornaliero, con controllo di freschezza e report degli errori.

## Avvio

Le istruzioni di sviluppo saranno aggiunte insieme ai primi componenti eseguibili. Non configurare API key o credenziali nel repository: usare variabili d'ambiente e `.env` locale escluso da Git.
