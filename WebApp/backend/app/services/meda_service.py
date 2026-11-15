from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

_SETTINGS = get_settings()
_MEDA_PDS_URL = "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html"


class MedaError(RuntimeError):
    pass


class MedaDataNotAvailable(MedaError):
    pass


class MedaValidationError(MedaError):
    pass


def _fetch_medasol( sol: int, timeout: float | None = None) -> Optional[Dict[str, Any]]:
    """Fetch MEDA observations for a given sol number.
    
    NOTE: This is a placeholder implementation. In a production system,
    this would query the PDS/MEDA data archive for the specified sol.
    The actual PDS endpoint structure is documented at:
    https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html
    
    For MARS OPS, we treat this as metadata-only access: we return any
    available cached data or a "no observations" signal.
    """
    timeout_val = timeout or _SETTINGS.nasa_request_timeout_seconds
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_val)) as client:
            # The MEDA PDS page provides metadata manifests; actual product
            # access requires separate PDS ingest. We fetch the metadata page
            # to check availability without downloading full datasets.
            response = client.get(_MEDA_PDS_URL)
            if response.status_code != 200:
                return None
            # In a full implementation, we would parse the HTML or use
            # the PDS API to find sol-specific observation records.
            # For now, we return structured availability info.
            return {
                "source": "pds-atmospheres.nmsu.edu",
                "url": _MEDA_PDS_URL,
                "note": "MEDA metadata page retrieved; sol-specific data requires",
                "per_sol": {},
            }
    except httpx.HTTPError as exc:
        raise MedaError(
            f"Unable to retrieve MEDA data from PDS: {exc}"
        ) from exc


def _meda_value_to_celsius(raw: float, var: str) -> float | None:
    """Convert MEDA raw values to Celsius based on variable type.
    
    MEDA temperature sensor range: typically -100°C to +20°C
    stored as integer values in 0.1°C units with offsets.
    """
    if raw is None:
        return None
    if var == "temperature":
        # MEDA TIR temperature in 0.1°C, offset of -273.15 for Kelvin->Celsius
        # Raw values from MEDA are already in Celsius with 0.1 resolution
        return round(raw, 1)
    return None


def _format_meda_result(raw_data: Dict[str, Any], variable: str) -> Dict[str, Any]:
    """Format a MEDA observation result with value, unit, and provenance."""
    value = None
    unit = ""
    status = "unknown"
    source = "unknown"
    sol = None
    observation_datetime = None

    if variable == "temperature":
        value = _meda_value_to_celsius(raw_data.get("temperature"), variable)
        if value is not None:
            unit = "°C"
            status = "measured"
        else:
            status = "not_available"
    elif variable == "pressure":
        value = raw_data.get("pressure")
        if value is not None:
            unit = "Pa"
            status = "measured"
        else:
            status = "not_available"
    elif variable == "wind_speed":
        value = raw_data.get("wind_speed")
        if value is not None:
            unit = "m/s"
            status = "measured"
        else:
            status = "not_available"
    elif variable == "wind_direction":
        value = raw_data.get("wind_direction")
        if value is not None:
            unit = "degrees"
            status = "measured"
        else:
            status = "not_available"
    elif variable == "relative_humidity":
        value = raw_data.get("relative_humidity")
        if value is not None:
            unit = "%"
            status = "measured"
        else:
            status = "not_available"

    if value is not None:
        source = "MEDA / Perseverance"
        observation_datetime = datetime.now(timezone.utc).isoformat()

    return {
        "value": value,
        "unit": unit,
        "status": status,
        "source": source,
        "sol": sol,
        "observation_datetime_utc": observation_datetime,
    }


def get_meda_observation(
    sol: int,
    variable: str,
    cached: dict | None = None,
) -> Optional[Dict[str, Any]]:
    """Get a MEDA observation for a given sol and variable.
    
    Args:
        sol: Mars sol number (Sol 0 = 2021-02-18 landing)
        variable: One of "temperature", "pressure", "wind_speed", 
                  "wind_direction", "relative_humidity"
        cached: Optional dict with previously cached results keyed by sol
    
    Returns:
        Dict with observation value, unit, status, source, and datetime,
        or None if no data available for this sol/variable combination.
    """
    # Check cache first
    if cached and sol in cached:
        result = _format_meda_result(cached[sol], variable)
        if result["status"] != "not_available":
            return result

    # Fetch fresh data
    try:
        fresh = _fetch_medasol(sol)
        if fresh is None or not fresh.get("per_sol"):
            return None

        # Try to find data for the requested sol and variable
        per_sol = fresh.get("per_sol", {})
        sol_data = per_sol.get(str(sol))
        if sol_data is None:
            return None

        # Extract the requested variable
        raw_value = sol_data.get(variable)
        if raw_value is None:
            return None

        result = _format_meda_result(
            {"temperature": raw_value} if variable == "temperature" else raw_data,
            variable,
        )
        return result

    except MedaError:
        return None