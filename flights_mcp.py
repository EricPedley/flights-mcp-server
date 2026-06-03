"""MCP server exposing the flight-search helpers from flights.py over stdio.

Run with:  uv run python flights_mcp.py
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from flights import _general, _cheapest, _best, _time_filtered

mcp = FastMCP("flights")


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
