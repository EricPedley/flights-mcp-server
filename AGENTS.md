# AGENTS.md

Google Flights search. Two entrypoints, same helpers in `flights.py`:

- **CLI** — `flights.py`. Use this for agent/script work. Compact output.
- **MCP server** — `flights_mcp.py` (`uv run python flights_mcp.py`, stdio). Thin wrapper over the same helpers.

## CLI usage

```
uv run python flights.py <command> ORIGIN DEST DEPARTURE_DATE [opts]
```

`uv run python flights.py -h` for full help + examples.

### Commands
| Command | Returns |
|---------|---------|
| `general` | All flights, Google default order. `--n-flights N` (default 40). |
| `cheapest` | All flights, price ascending. |
| `best` | Only Google-flagged "best" flights. |
| `time-filtered STATE TIME` | Filter by OUTBOUND departure. `STATE`=`before`\|`after`, `TIME` like `"6:00 PM"`. `before`=dep<TIME, `after`=dep>=TIME. |

### Common opts
`--trip-type one-way|round-trip` (default one-way) · `--return-date YYYY-MM-DD` (required for round-trip) · `--seat economy|premium-economy|business|first` · `--adults N` `--children N` `--infants-in-seat N` `--infants-on-lap N`

### Output
One line per flight:
```
BOS 5:40 PM Jul 6 -> ARN 9:15 AM Jul 7 | Scandinavian Airlines | 1stop | 9h35m | $867 *
```
`*` = Google "best" flag. Exact duplicate rows dropped.

## Round-trip — important
- `--trip-type round-trip --return-date DATE` returns **outbound legs only**, each carrying the **full round-trip bundle price** (much cheaper than summing two one-ways).
- Return leg times are **not** in that output. Run a separate one-way search on the return date to get them.
- Dates are `YYYY-MM-DD`. Airports are 3-letter IATA (BOS, ARN).

### Example: round-trip planning
```
# bundle totals + outbound times
uv run python flights.py best BOS ARN 2026-07-06 --trip-type round-trip --return-date 2026-07-09
# return leg times (separate one-way)
uv run python flights.py best ARN BOS 2026-07-09
```

## Gotchas
- Scraper hits live Google Flights — results/prices shift between calls.
- MCP `fetch_mode="local"` calls `asyncio.run` internally; fails inside MCP's running loop (`asyncio.run() cannot be called from a running event loop`). **CLI is unaffected** (top-level asyncio). Use the CLI for round-trip work until the MCP path is fixed (offload to a thread).
