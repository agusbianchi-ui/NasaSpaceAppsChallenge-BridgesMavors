from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from typing import Any

from app.core.config import get_settings
from app.schemas.common import ErrorResponse, ErrorDetail

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/assistant")
def ai_assistant(body: dict[str, Any] = Body(...)) -> Any:
    message = body.get("message", "")
    """Asistente científico Mars Ops.

    Responde utilizando información disponible del sistema:
    - Estado de la misión
    - Datasets y fuentes de datos
    - Capabilidades de análisis
    - Meta información del proyecto

    No inventa datos científicos ni presenta modelos entrenados.
    """
    try:
        settings = get_settings()

        # Construir respuesta basada en datos disponibles del sistema
        response_parts = []

        # Información de la misión
        response_parts.append(
            f"**Estado de la Misión Mars OPS:** Entorno simulado de demostración."
        )

        # Fuentes de datos disponibles
        response_parts.append(
            "- **Datos NASA:** 6 fuentes catalogadas (Perseverance, MRO, Odyssey, MGS, PDS, Mars Trek)"
        )

        # Datasets disponibles
        response_parts.append(
            "- **Datasets Aeolian:** 5 manifestos verificados (Hargraves, Coprates, repeat CTX, HiRISE, Jezero)"
        )

        # Capabilidades de análisis
        response_parts.append(
            "- **Análisis disponibles:** Migración de dunas, segmentación, detección de desplazamiento"
        )

        # Métodos de registro
        response_parts.append(
            "- **Métodos de registro:** Correlación de fases, ORB+RANSAC, registro de crestas"
        )

        # Limitaciones científicas
        response_parts.append(
            "- **Restricciones:** Sin modelos entrenados comprometidos, pixels no comprometidos, "
            "fechas y scales requeridos explícitamente"
        )

        # Si el mensaje contiene palabras clave específicas, agregar información más detallada
        message_lower = message.lower()

        if "dune" in message_lower or "migration" in message_lower:
            response_parts.append(
                "- **Migración de dunas:** Análisis observados disponibles mediante secuencia fechas con scale métrico"
            )

        if "dataset" in message_lower or "dataset" in message_lower:
            response_parts.append(
                "- **Conjunto de datos:** Manifestos verificados con metadatos de fuente, resolución, CRS y limitaciones"
            )

        if "registration" in message_lower or "register" in message_lower:
            response_parts.append(
                "- **Registro de imágenes:** Correlación de fases, ORB+RANSAC, detección de crestas"
            )

        if "report" in message_lower or "resumen" in message_lower:
            response_parts.append(
                "- **Informes:** Estructura disponible con nombre del análisis, dataset, métodos, limitaciones y procedencia"
            )

        if "status" in message_lower or "estado" in message_lower:
            response_parts.append(
                "- **Estado del sistema:** El catálogo y los análisis deben verificarse en cada ejecución; no se certifica disponibilidad ni entrenamiento desde este asistente"
            )

        response = "\n\n".join(response_parts)

        return {"response": response}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(code="internal_error", message=str(e))
            ).model_dump(),
        )