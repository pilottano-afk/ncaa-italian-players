# Italian NCAA player candidates — reconciliation note

Checked: 2026-11-17  
Season: 2026-27 only  
Status: candidate discovery, not a certified nationality register.

## Sources compared

1. **Bamboden** — https://college.bamboden.com/en/italiani  
   Its current page labels 38 players as Italian Division I players for 2026-27. The 38 names and teams are preserved in `italian-player-candidates-2026-27.csv`. The page states that its data is provided by CollegeBasketballData.com; it is still a secondary aggregation and does not provide primary nationality evidence for every player.

2. **BasketballNCAA** — https://www.basketballncaa.com/guida-preview-italiani-ncaa-26-27/  
   Its September 8, 2026 preview refers to 34 Italian players in Division I and discusses eligibility, roster movement and transfers. This is a useful independent editorial cross-check, but not a machine-verified current roster.

3. **Paolo Spelorzi** — https://paolospelorzi.substack.com/p/italian-players-in-ncaab-div-1-2026  
   Its October 28, 2026 list contains a broader set of names, including several explicitly marked with dual nationalities and a note for players formed in Italy. Its inclusion criteria are not identical to the Bamboden list.

4. **RealGM** — https://basketball.realgm.com/national/countries/6/Italy/ncaa-players  
   Useful as another discovery source, but its country classification and current roster coverage must be reconciled player by player.

## Why the counts differ

The sources use different definitions and update schedules. Some include dual nationals, players formed in Italy, late roster additions, or players whose eligibility/transfer status may have changed. A single headline count is therefore not a safe canonical roster.

## Import policy

- The CSV is a **watchlist** only. Every row has `needs_primary_source_verification`.
- The candidate list must not be presented as 38 confirmed Italian citizens.
- Verify each player's 2026-27 university roster and Division I membership separately.
- Verify Italian nationality or Italian national-team representation from a primary source (official university biography, federation or national-team record).
- Record source URL, title, evidence type and checked date for every accepted claim.
- Keep dual nationality, Italian formation and citizenship as separate fields when evidence supports them.
- Never infer nationality from surname, hometown or team.
- Do not attach statistics from secondary list pages to the NCAA player database; use the season-2027 box-score feed after identity matching.

## Known reconciliation flags

- Bamboden writes **Elise Assui**; other sources write **Elisee Assui**. Treat as a name alias to resolve against official roster identity, not as two people.
- The source lists differ on players such as Maximo Adams, Emmanuel Innocenti, Alessio Calamita, Randy Livingston Jr., Stephane Djiya, Quinn Ellis, Imran Suljanovic and Omer Suljanovic.
- The CSV intentionally preserves Bamboden's 38-player Division I snapshot; it is not the union of all sources and does not imply those differences have been resolved.
