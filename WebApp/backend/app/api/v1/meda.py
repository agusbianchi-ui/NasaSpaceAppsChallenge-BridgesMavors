from fastapi import APIRouter, HTTPException, status

from app.schemas.common import APIResponse, ErrorResponse
from app.services.meda_service import (
    MedaError,
    MedaDataNotAvailable,
    get_meda_observation,
)

router = APIRouter(prefix="/meda", tags=["meda"])


@router.get(
    "/observation",
    response_model=APIResponse[dict | None],
    summary="Get MEDA observation for a given Sol and variable",
)
def get_observation(
    sol: int,
    variable: str,
    status_code: int = 200,
) -> APIResponse[dict | None]:
    """Retrieve a MEDA observation for the given Mars sol and variable.
    
    Variables:
    - temperature: Air temperature in °C
    - pressure: Atmospheric pressure in Pa
    - wind_speed: Wind speed in m/s
    - wind_direction: Wind direction in degrees clockwise from north
    - relative_humidity: Relative humidity in %
    
    The Sol number uses the mission convention: Sol 0 = 2021-02-18 (Perseverance landing).
    
    If no observations are available for the requested sol/variable,
    the response data will be null and a "no observations available" note
    will be included in the metadata.
    
    This endpoint does not provide live/real-time data. It returns the most
    recently available archived MEDA data products from the PDS archive.
    """
    try:
        result = get_meda_observation(sol, variable)
        return APIResponse(data=result)
    except MedaError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc