from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.exceptions import AppHttpException
from app.utils.file_upload import save_upload, save_uploads
from app.utils.pagination import PaginationDep
from app.utils.response import ApiResponse, empty, paginated, success

router = APIRouter(tags=["test"], prefix="/test")

# ---------------------------------------------------------------------------
# Ejemplos de uso del envelope estándar de respuesta
# ---------------------------------------------------------------------------


@router.get("/ping", response_model=ApiResponse[dict])
async def ping():
    """Respuesta simple con data."""
    return success(data={"message": "pong!"})


@router.get("/paginated", response_model=ApiResponse[list[dict]])
async def paginated_example(pagination: PaginationDep):
    """Respuesta paginada — data y pagination al mismo nivel."""
    _mock_items = [{"id": i, "name": f"Item {i}"} for i in range(1, 51)]
    page_items = _mock_items[pagination.offset : pagination.offset + pagination.size]
    return paginated(page_items, total=len(_mock_items), pagination=pagination)


@router.delete("/resource/{resource_id}", response_model=ApiResponse[None])
async def delete_example(resource_id: int):
    """Respuesta sin data — solo message (ej: DELETE)."""
    return empty(f"Recurso {resource_id} eliminado exitosamente")


# ---------------------------------------------------------------------------
# Ejemplos de manejo de errores (el formato detail es independiente al envelope)
# ---------------------------------------------------------------------------


@router.put("/custom-error")
async def custom_error():
    """Demuestra que AppHttpException retorna detail, independiente del envelope."""
    raise AppHttpException("Custom error")


@router.post("/syntax-error")
async def syntax_error():
    if None > 0:
        return success(data={"message": "Syntax error!"})
    return success(data={"message": "No syntax error!"})


# ---------------------------------------------------------------------------
# Ejemplos de upload de archivos
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=ApiResponse[dict])
async def upload_single(file: UploadFile = File(...)):
    """
    Ejemplo de upload de un solo archivo.

    Flujo completo:
      1. save_upload() valida y guarda el archivo en uploads/
      2. El controller lee el archivo desde disco para procesarlo
      3. El archivo temporal se elimina en el bloque finally

    En un proyecto real, el paso 2 sería subir a S3/GCS/Azure o
    procesar la imagen, parsear el CSV, etc.
    """
    # — Paso 1: guardar en uploads/ con validaciones
    file_info = await save_upload(
        file,
        allowed_types=["image/jpeg", "image/png", "image/webp", "text/plain"],
        max_size_mb=5,
    )

    file_path = Path(file_info["path"])

    try:
        # — Paso 2: leer y procesar desde disco
        #   read_bytes() → contenido binario (imágenes, PDFs, binarios)
        #   read_text()  → contenido como string (CSV, JSON, TXT)
        raw_content = file_path.read_bytes()

        # Aquí iría la lógica real: subir a bucket, procesar imagen, etc.
        # Ejemplo: client_s3.upload(raw_content, key=file_info["filename"])

        result = {
            "original_filename": file_info["original_filename"],
            "saved_as": file_info["filename"],
            "content_type": file_info["content_type"],
            "size_mb": file_info["size_mb"],
            "size_bytes": file_info["size_bytes"],
            "bytes_read": len(raw_content),
        }

    finally:
        # — Paso 3: eliminar el archivo temporal siempre, incluso si hay error
        if file_path.exists():
            file_path.unlink()

    return success(data=result, message="Archivo procesado y eliminado exitosamente")


@router.post("/upload/multiple", response_model=ApiResponse[list[dict]])
async def upload_multiple(files: list[UploadFile] = File(...)):
    """
    Ejemplo de upload de múltiples archivos simultáneos.

    Cada archivo se guarda, procesa y elimina individualmente.
    Si un archivo falla la validación, los anteriores ya guardados
    quedan en disco — el developer decide cómo manejar el rollback.
    """
    saved_files = await save_uploads(
        files,
        allowed_types=["image/jpeg", "image/png", "image/webp"],
        max_size_mb=5,
    )

    results = []
    for file_info in saved_files:
        file_path = Path(file_info["path"])
        try:
            raw_content = file_path.read_bytes()

            # Lógica de procesamiento por archivo...

            results.append(
                {
                    "original_filename": file_info["original_filename"],
                    "content_type": file_info["content_type"],
                    "size_mb": file_info["size_mb"],
                    "bytes_read": len(raw_content),
                }
            )
        finally:
            if file_path.exists():
                file_path.unlink()

    return success(data=results, message=f"{len(results)} archivo(s) procesado(s)")
