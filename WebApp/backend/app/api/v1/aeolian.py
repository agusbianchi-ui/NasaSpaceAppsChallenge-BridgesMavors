from fastapi import APIRouter, HTTPException, status

from app.schemas.aeolian import (
    AeolianAnalysisResult,
    AeolianAnalyzeRequest,
    AeolianDataset,
    AeolianPredictRequest,
)
from app.schemas.common import APIResponse, ErrorResponse
from app.services.aeolian_service import (
    AeolianServiceError,
    PredictionUnavailableError,
    get_aeolian_service,
)

router = APIRouter(prefix="/aeolian", tags=["aeolian"])
_service = get_aeolian_service()


def _http_error(exc: AeolianServiceError) -> HTTPException:
    detail = str(exc)
    if isinstance(exc, PredictionUnavailableError):
        detail = (
            f"{detail} Required artifacts: "
            + "; ".join(exc.required_artifacts)
        )
    return HTTPException(status_code=exc.status_code, detail=detail)


@router.get(
    "/datasets",
    response_model=APIResponse[list[AeolianDataset]],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Mars dataset manifest is unavailable or invalid",
        }
    },
    summary="List Mars aeolian dataset metadata",
)
def list_datasets() -> APIResponse[list[AeolianDataset]]:
    try:
        return APIResponse(data=_service.list_datasets())
    except AeolianServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/analyze",
    response_model=APIResponse[AeolianAnalysisResult],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid or incomplete analysis request",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Aeolian data root or manifest is unavailable",
        },
    },
    summary="Analyze observed dune migration between dated local observations",
)
def analyze(
    payload: AeolianAnalyzeRequest,
) -> APIResponse[AeolianAnalysisResult]:
    try:
        return APIResponse(data=_service.analyze(payload))
    except AeolianServiceError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/results/{analysis_id}",
    response_model=APIResponse[AeolianAnalysisResult],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Analysis not found",
        }
    },
    summary="Get a completed aeolian analysis by id",
)
def get_result(analysis_id: str) -> APIResponse[AeolianAnalysisResult]:
    try:
        return APIResponse(data=_service.get_result(analysis_id))
    except AeolianServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/predict",
    response_model=ErrorResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Referenced analysis or dataset not found",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid prediction request",
        },
        status.HTTP_501_NOT_IMPLEMENTED: {
            "model": ErrorResponse,
            "description": "No validated prediction model is available",
        },
    },
    summary="Request a model prediction (currently unavailable)",
)
def predict(_payload: AeolianPredictRequest) -> ErrorResponse:
    try:
        _service.predict(_payload)
    except AeolianServiceError as exc:
        raise _http_error(exc) from exc
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="No prediction was produced.",
    )
