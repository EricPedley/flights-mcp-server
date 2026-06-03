# Google Flights search

Search Google Flights from the command line or an MCP client. Find cheapest, "best", or time-filtered flights for any route — one-way or round-trip.

## What it does

Scrapes live Google Flights and returns compact, one-line-per-flight results:

```
BOS 5:40 PM Jul 6 -> ARN 9:15 AM Jul 7 | Scandinavian Airlines | 1stop | 9h35m | $867 *
```
(`*` = flagged "best" by Google.)

Four searches: `general` (all flights), `cheapest` (price-sorted), `best` (Google's picks), `time-filtered` (by departure time). Each takes origin/destination (IATA codes), a date, and optional trip-type, seat class, and passenger counts.

**Round-trip:** pass `--trip-type round-trip --return-date`. Returns outbound legs carrying the full bundle price (cheaper than two one-ways). Run a separate search on the return date for return-leg times.

## How it works

- `flights.py` — the CLI and all search/format helpers.
- `flights_mcp.py` — a thin MCP server (stdio) wrapping the same helpers.
- Backed by [`fast_flights`](https://pypi.org/project/fast-flights/), which parses Google Flights HTML. Prices are live and shift between calls.

## Quick start

Install [`uv`](https://docs.astral.sh/uv/), then:

```bash
# CLI
uv run python flights.py cheapest BOS ARN 2026-07-06
uv run python flights.py -h          # full help + examples

# MCP server (stdio)
uv run python flights_mcp.py
```

### Point your agent at it

- **Coding agents (Claude Code, Cursor, etc.):** the agent should read **[AGENTS.md](AGENTS.md)** — it documents every command, option, and the round-trip gotcha. Then just drive `flights.py` directly.
- **MCP clients (Claude Desktop, Cursor):** add the server to your `mcpServers` config:

  ```json
  {
    "mcpServers": {
      "flights": {
        "command": "/ABSOLUTE/PATH/TO/uv",
        "args": ["--directory", "/ABSOLUTE/PATH/TO/THIS/REPO", "run", "flights_mcp.py"]
      }
    }
  }
  ```
  Use absolute paths (`which uv` for the command). Restart the client after editing. Config locations: Claude Desktop -> `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) / `%AppData%\Claude\claude_desktop_config.json` (Windows); Cursor -> `.cursor/mcp.json` or `~/.cursor/mcp.json`.

> **Note:** the MCP path can't yet do round-trip (`fetch_mode="local"` clashes with the server's event loop). Use the CLI for round-trip until that's fixed. See [AGENTS.md](AGENTS.md).

## Example prompts

- "Cheapest flights Atlanta -> Shanghai on Jan 1 2026"
- "Best round-trip BOS -> ARN, out Jul 6 back Jul 9"
- "LAX departures today after 8:00 PM"

## License

MIT — see [LICENSE](LICENSE).

> Not endorsed by or affiliated with Google. Built as a learning project.
