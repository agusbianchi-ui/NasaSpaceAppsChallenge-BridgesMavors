from fastapi import APIRouter, HTTPException, status

from app.schemas.common import APIResponse, ErrorResponse
from app.schemas.mars import (
    MarsDataSource,
    MarsLayer,
    MarsLocation,
    WMTSCapabilities,
)
from app.services.mars_data_service import (
    MarsUpstreamError,
    get_mars_data_service,
)

router = APIRouter(prefix="/mars", tags=["mars"])
_service = get_mars_data_service()


@router.get(
    "/sources",
    response_model=APIResponse[list[MarsDataSource]],
    summary="List NASA data sources",
)
def list_sources() -> APIResponse[list[MarsDataSource]]:
    return APIResponse(data=_service.list_sources())


@router.get(
    "/layers",
    response_model=APIResponse[list[MarsLayer]],
    summary="List available Mars layers",
)
def list_layers() -> APIResponse[list[MarsLayer]]:
    return APIResponse(data=_service.list_layers())


@router.get(
    "/layers/{layer_id}",
    response_model=APIResponse[MarsLayer],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Layer not found",
        }
    },
    summary="Get a Mars layer by id",
)
def get_layer(layer_id: str) -> APIResponse[MarsLayer]:
    layer = _service.get_layer(layer_id)
    if layer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer '{layer_id}' not found.",
        )
    return APIResponse(data=layer)


@router.get(
    "/layers/{layer_id}/capabilities",
    response_model=APIResponse[WMTSCapabilities],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Layer or WMTS service not found",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "NASA Mars Trek is unavailable or returned invalid data",
        },
    },
    summary="Get verified or live WMTS metadata for a layer",
)
async def get_layer_capabilities(
    layer_id: str, live: bool = False
) -> APIResponse[WMTSCapabilities]:
    layer = _service.get_layer(layer_id)
    if layer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer '{layer_id}' not found.",
        )
    if layer.wmts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No WMTS service is registered for layer '{layer_id}'."
            ),
        )

    if not live:
        return APIResponse(data=layer.wmts)

    try:
        capabilities = await _service.fetch_live_capabilities(layer_id)
    except MarsUpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if capabilities is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No WMTS service is registered for layer '{layer_id}'."
            ),
        )
    return APIResponse(data=capabilities)


@router.get(
    "/locations/jezero",
    response_model=APIResponse[MarsLocation],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Location not found",
        }
    },
    summary="Get Jezero Crater reference metadata",
)
def get_jezero() -> APIResponse[MarsLocation]:
    location = _service.get_location("jezero")
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location 'jezero' not found.",
        )
    return APIResponse(data=location)
