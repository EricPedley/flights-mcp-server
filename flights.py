import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from fast_flights import FlightData, Passengers, Result, get_flights


mcp = FastMCP("flights")


# ---------- Helpers ----------

def format_flight_info(flight_data, origin_airport, destination_airport):
    # Compact one-line format for agent consumption (no prose).
    # e.g. "BOS 5:10 PM Jul 5 -> ARN 11:50 AM Jul 6 | Air France | 1stop | 12h40m | $480 *"
    def short_dt(date_str):
        # "5:10 PM on Sun, Jul 5" -> "5:10 PM Jul 5"
        parts = date_str.split()
        return f"{parts[0]} {parts[1]} {parts[4]} {parts[5]}"

    dp = flight_data['duration'].split()
    dur = f"{dp[0]}h{dp[2]}m" if len(dp) == 4 else flight_data['duration']

    stops = flight_data["stops"]
    stops_text = "nonstop" if stops == 0 else f"{stops}stop"
    star = " *" if flight_data['is_best'] else ""

    return (
        f"{origin_airport} {short_dt(flight_data['departure'])} -> "
        f"{destination_airport} {short_dt(flight_data['arrival'])} | "
        f"{flight_data['name']} | {stops_text} | {dur} | {flight_data['price']}{star}"
    )


def _lines(flights, origin, destination):
    """Format flights to compact lines, dropping exact duplicates."""
    seen, out = set(), []
    for f in flights:
        line = format_flight_info(f, origin, destination)
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def _validate(origin, destination, departure_date, trip_type, seat, return_date=None):
    if len(origin) != 3 or len(destination) != 3:
        return "Origin and destination must be 3 characters."
    if len(departure_date) != 10 or departure_date[4] != '-' or departure_date[7] != '-':
        return "Departure date must be in YYYY-MM-DD format."
    if trip_type not in ("one-way", "round-trip"):
        return "Trip type must be either 'one-way' or 'round-trip'."
    if seat not in ("economy", "premium-economy", "business", "first"):
        return "Seat type must be either 'economy', 'premium-economy', 'business', or 'first'."
    # Round-trip returns outbound legs, each carrying the full round-trip bundle price.
    if trip_type == "round-trip" and not return_date:
        return "round-trip requires return_date (YYYY-MM-DD)."
    return None


def _search(origin, destination, departure_date, trip_type, seat,
            adults, children, infants_in_seat, infants_on_lap,
            return_date=None) -> dict | str:
    err = _validate(origin, destination, departure_date, trip_type, seat, return_date)
    if err:
        return err

    flight_data_input = [FlightData(date=departure_date, from_airport=origin, to_airport=destination)]
    if trip_type == "round-trip":
        flight_data_input.append(FlightData(date=return_date, from_airport=destination, to_airport=origin))

    passengers_input = Passengers(
        adults=adults, children=children,
        infants_in_seat=infants_in_seat, infants_on_lap=infants_on_lap,
    )

    try:
        result: Result = get_flights(
            flight_data=flight_data_input,
            trip=trip_type,
            seat=seat,
            passengers=passengers_input,
            fetch_mode="local",
        )
        return asdict(result)
    except httpx.RequestError:
        return "Unable to connect to the flight search service. Please try again later."
    except ValueError as e:
        return f"Invalid data received: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while searching for flights: {str(e)}"


def _general(origin, destination, departure_date, trip_type, seat,
             adults, children, infants_in_seat, infants_on_lap,
             n_flights, return_date=None) -> list[str]:
    result = _search(origin, destination, departure_date, trip_type, seat,
                     adults, children, infants_in_seat, infants_on_lap, return_date)
    if isinstance(result, str):
        return [result]
    if not result or "flights" not in result:
        return ["No flight data available for the specified route and dates."]

    current_price = result["current_price"]
    all_flights = result["flights"]
    if not all_flights:
        return ["No flights found for the specified route and dates."]

    info = _lines(all_flights[: min(n_flights, len(all_flights))], origin, destination)
    rt = f" RT->{return_date}" if trip_type == "round-trip" else ""
    return [f"general {origin}->{destination} {departure_date}{rt} (overall:{current_price}):"] + info


def _cheapest(origin, destination, departure_date, trip_type, seat,
              adults, children, infants_in_seat, infants_on_lap,
              return_date=None) -> list[str]:
    result = _search(origin, destination, departure_date, trip_type, seat,
                     adults, children, infants_in_seat, infants_on_lap, return_date)
    if isinstance(result, str):
        return [result]
    if not result or "flights" not in result:
        return ["No flight data available for the specified route and dates."]

    all_flights = result["flights"]
    if not all_flights:
        return ["No flights found for the specified route and dates."]

    def price_value(flight):
        s = flight['price'].replace('$', '').replace(',', '')
        try:
            return float(s)
        except ValueError:
            return float('inf')

    sorted_flights = sorted(all_flights, key=price_value)
    info = _lines(sorted_flights[: min(30, len(sorted_flights))], origin, destination)
    rt = f" RT->{return_date}" if trip_type == "round-trip" else ""
    return [f"cheapest {origin}->{destination} {departure_date}{rt}:"] + info


def _best(origin, destination, departure_date, trip_type, seat,
          adults, children, infants_in_seat, infants_on_lap,
          return_date=None) -> list[str]:
    result = _search(origin, destination, departure_date, trip_type, seat,
                     adults, children, infants_in_seat, infants_on_lap, return_date)
    if isinstance(result, str):
        return [result]
    if not result or "flights" not in result:
        return ["No flight data available for the specified route and dates."]

    all_flights = result["flights"]
    if not all_flights:
        return ["No flights found for the specified route and dates."]

    best_flights = [f for f in all_flights if f.get('is_best')]
    if not best_flights:
        return ["No best flights found for the specified route and dates."]

    info = _lines(best_flights[: min(30, len(best_flights))], origin, destination)
    rt = f" RT->{return_date}" if trip_type == "round-trip" else ""
    return [f"best {origin}->{destination} {departure_date}{rt}:"] + info


def _time_filtered(state, target_time_str, origin, destination, departure_date,
                   trip_type, seat, adults, children, infants_in_seat, infants_on_lap,
                   return_date=None) -> list[str]:
    if state not in ("before", "after"):
        return ["State must be either 'before' or 'after'."]
    try:
        target_time = datetime.strptime(target_time_str, '%I:%M %p').time()
    except ValueError:
        return ["Invalid time format. Please use HH:MM AM/PM format (e.g., '7:00 PM')."]

    result = _search(origin, destination, departure_date, trip_type, seat,
                     adults, children, infants_in_seat, infants_on_lap, return_date)
    if isinstance(result, str):
        return [result]
    if not result or "flights" not in result:
        return ["No flight data available for the specified route and dates."]

    all_flights = result["flights"]
    if not all_flights:
        return ["No flights found for the specified route and dates."]

    valid = []
    for flight in all_flights:
        parts = flight['departure'].split(" ")
        time_str = parts[0] + " " + parts[1]
        flight_time = datetime.strptime(time_str, '%I:%M %p').time()
        if state == "before" and flight_time < target_time:
            valid.append(flight)
        elif state == "after" and flight_time >= target_time:
            valid.append(flight)

    if not valid:
        return [f"No flights found {state} {target_time_str} for the specified route and dates."]

    info = _lines(valid[: min(30, len(valid))], origin, destination)
    op = "<" if state == "before" else ">="
    return [f"time-filtered {origin}->{destination} {departure_date} dep{op}{target_time_str}:"] + info


# ---------- MCP tools ----------

@mcp.tool()
async def get_general_flights_info(origin: str, destination: str, departure_date: str,
                                   trip_type: str = "one-way", seat: str = "economy",
                                   adults: int = 1, children: int = 0,
                                   infants_in_seat: int = 0, infants_on_lap: int = 0,
                                   n_flights: int = 40,
                                   return_date: Optional[str] = None) -> list[str]:
    """Get general flight info. For round-trip bundle pricing, set trip_type='round-trip' and pass return_date (YYYY-MM-DD)."""
    return _general(origin, destination, departure_date, trip_type, seat,
                    adults, children, infants_in_seat, infants_on_lap, n_flights, return_date)


@mcp.tool()
async def get_cheapest_flights(origin: str, destination: str, departure_date: str,
                               trip_type: str = "one-way", seat: str = "economy",
                               adults: int = 1, children: int = 0,
                               infants_in_seat: int = 0, infants_on_lap: int = 0,
                               return_date: Optional[str] = None) -> list[str]:
    """Get cheapest flights. For round-trip bundle pricing, set trip_type='round-trip' and pass return_date."""
    return _cheapest(origin, destination, departure_date, trip_type, seat,
                     adults, children, infants_in_seat, infants_on_lap, return_date)


@mcp.tool()
async def get_best_flights(origin: str, destination: str, departure_date: str,
                           trip_type: str = "one-way", seat: str = "economy",
                           adults: int = 1, children: int = 0,
                           infants_in_seat: int = 0, infants_on_lap: int = 0,
                           return_date: Optional[str] = None) -> list[str]:
    """Get best flights. For round-trip bundle pricing, set trip_type='round-trip' and pass return_date."""
    return _best(origin, destination, departure_date, trip_type, seat,
                 adults, children, infants_in_seat, infants_on_lap, return_date)


@mcp.tool()
async def get_time_filtered_flights(state: str, target_time_str: str, origin: str, destination: str,
                                    departure_date: str,
                                    trip_type: str = "one-way", seat: str = "economy",
                                    adults: int = 1, children: int = 0,
                                    infants_in_seat: int = 0, infants_on_lap: int = 0,
                                    return_date: Optional[str] = None) -> list[str]:
    """Filter outbound flights by departure time. For round-trip bundle pricing, pass return_date."""
    return _time_filtered(state, target_time_str, origin, destination, departure_date,
                          trip_type, seat, adults, children, infants_in_seat, infants_on_lap, return_date)


# ---------- CLI ----------

def _add_common(p):
    p.add_argument("origin")
    p.add_argument("destination")
    p.add_argument("departure_date", help="YYYY-MM-DD")
    p.add_argument("--trip-type", default="one-way", choices=["one-way", "round-trip"])
    p.add_argument("--return-date", default=None, help="YYYY-MM-DD (required for round-trip)")
    p.add_argument("--seat", default="economy", choices=["economy", "premium-economy", "business", "first"])
    p.add_argument("--adults", type=int, default=1)
    p.add_argument("--children", type=int, default=0)
    p.add_argument("--infants-in-seat", type=int, default=0)
    p.add_argument("--infants-on-lap", type=int, default=0)


def main():
    parser = argparse.ArgumentParser(description="Flight search CLI / MCP server")
    sub = parser.add_subparsers(dest="cmd")

    p_mcp = sub.add_parser("mcp", help="Run as MCP server over stdio")

    p_g = sub.add_parser("general", help="General flight info")
    _add_common(p_g)
    p_g.add_argument("--n-flights", type=int, default=40)

    p_c = sub.add_parser("cheapest", help="Cheapest flights")
    _add_common(p_c)

    p_b = sub.add_parser("best", help="Best flights")
    _add_common(p_b)

    p_t = sub.add_parser("time-filtered", help="Filter by outbound time")
    p_t.add_argument("state", choices=["before", "after"])
    p_t.add_argument("target_time_str", help="e.g. '7:00 PM'")
    _add_common(p_t)

    args = parser.parse_args()

    if args.cmd is None or args.cmd == "mcp":
        mcp.run(transport='stdio')
        return

    common = dict(
        origin=args.origin, destination=args.destination, departure_date=args.departure_date,
        trip_type=args.trip_type, seat=args.seat,
        adults=args.adults, children=args.children,
        infants_in_seat=args.infants_in_seat, infants_on_lap=args.infants_on_lap,
        return_date=args.return_date,
    )

    if args.cmd == "general":
        out = _general(**common, n_flights=args.n_flights)
    elif args.cmd == "cheapest":
        out = _cheapest(**common)
    elif args.cmd == "best":
        out = _best(**common)
    elif args.cmd == "time-filtered":
        out = _time_filtered(args.state, args.target_time_str, **common)
    else:
        parser.print_help()
        sys.exit(2)

    for line in out:
        print(line)


if __name__ == "__main__":
    main()
