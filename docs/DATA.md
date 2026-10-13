# Data

`js/data.js` — drivers, tower, tyres, stints, radios, strategy, alerts, circuits, cars, engineers, sponsors, guests.
`js/data-extra.js` — lap table + telemetry samples + debrief notes for density.

## Consistency rules

- Each lap time equals the sum of its three sectors (tower and `laps`).
- A stint's `best` is never slower than its `avg`.
- Race best is **1:22.721 by KAI (#18, lap 4, SOFT, ST-013)**. Tower P1 is VEX #11 at 1:24.697. The session is on lap 38/58.
- Qualifying session bests and circuit records may be faster than the race best, which is expected.

## Single source of truth: the lap tape

`AX_EXTRA.laps` holds every car's laps 1..`driver.laps` (373 laps), each with sectors, compound, stint number and pit flag (`in`/`out`). `python3 tools/derive.py` generates the tape from the strategy plans and then **derives** everything else from it: the stint book (count = `driver.stint`, stint laps sum = laps completed, compounds in plan order, avg/best from that stint's laps), mounted tyre age = active stint laps, race best lap and holder, purple sectors, report row counts, and every baked page copy (lap tables, stint tables, stint cards, ticker, count cards). `qa/audit.py` recomputes all of these from the tape and fails on any mismatch.

Run `python3 tools/derive.py` after editing plans or driver records, `python3 tools/sync_baked.py` after editing tyres or stints (it re-renders every baked copy: tables, ticker, pills, stint cards), then `python3 qa/audit.py`.

Number-book rules enforced by the audit: one Mounted set per car, matching that driver's current tyre; at most one Active stint per driver, on the current tyre; each plan's compound sequence has stops + 1 stints and its current stint matches the driver's tyre; session, plan, tyre, stint and driver rows on every page match `AX_DATA`; global stat cards (temps, wind, alerts, counts) match `kpis`.

Pit and count rules (also derived and audited): a car may only show `PIT` while its strategy plan still has a stop left (stops made = stints − 1, tape in-laps = stops), and car, rail, table and field-card statuses follow `drivers[].status`. Tyre-set detail cards (age, fitted lap, status, heat, press, car) come from `AX_DATA.tyres` and the lap tape. A count card must equal the rows of the table it describes, unless that table is labelled as a sample ("first 36 of 500 notes", "all 36 alerts").

Physical models in `tools/derive.py` (audited by `qa/audit.py`):
- **Running order and gaps:** every gap is cumulative race time at the timing line: a car with L laps completed is compared with the leader after L laps (cum_car(L) − cum_leader(L)). `derive.py` spreads each car's difference evenly over its free laps (not pit in/out, not the tower last lap, not the race-best lap), so positions sort by (laps desc, cumulative time asc) and every displayed gap equals the derived value within 0.001 s. The leader has just completed lap 38; cars inside the snapshot offset are on 38, the rest on 37, and nobody is a lap down.
- **Fuel:** 100 % at the start, burn per lap = 53/38 % (VEX) × that car's mixture factor, so the field sits at 41–60 % (KAI 48 %).
- **ERS:** battery state of charge per car (20–95 %), equal to the tape's last lap.
- **Wear:** active-stint wear ≈ stint laps × compound rate (SOFT 5.5, MEDIUM 3.5, HARD 2.4, INTER 4.5 %/lap).
- **Tyre thermals:** Mounted sets run hot (≥ 85C, ≥ 22 psi, labelled Hot), Blanket 70–80C, Scrubbed sets cool to 48–70C, Cage and Retired sit at ambient. Pressure state labels follow heat: Hot ≥ 90C, Warm ≥ 60C, Cold below.
