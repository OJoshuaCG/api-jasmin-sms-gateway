import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.environments import REQUEST_MAX_SIZE_MB
from app.exceptions.AppHttpException import AppHttpException

# Directorio temporal donde se almacenan los archivos subidos.
# El developer decide qué hacer con ellos después (subir a bucket, procesar, etc.)
# y debe eliminarlos manualmente una vez procesados.
UPLOAD_DIR = Path("uploads")


async def save_upload(
    file: UploadFile,
    allowed_types: list[str] | None = None,
    max_size_mb: float | None = None,
    destination: Path | None = None,
) -> dict:
    """
    Guarda un archivo subido en el directorio de uploads y retorna su metadata.

    El archivo queda en disco para que el developer lo procese (ej: subir a S3/GCS).
    Se recomienda eliminarlo después de procesarlo.

    Args:
        file:          Archivo recibido desde el endpoint (UploadFile de FastAPI).
        allowed_types: Lista de MIME types permitidos.
                       Ej: ["image/jpeg", "image/png", "application/pdf"]
                       Si es None, se acepta cualquier tipo.
        max_size_mb:   Tamaño máximo del archivo en MB.
                       Si es None, se usa el límite global REQUEST_MAX_SIZE_MB
                       como fallback de última instancia.
        destination:   Carpeta destino. Si es None, usa UPLOAD_DIR ("uploads/").

    Returns:
        Dict con metadata del archivo guardado:
        {
            "filename":          "uuid-generado.jpg",
            "original_filename": "foto.jpg",
            "content_type":      "image/jpeg",
            "size_bytes":        204800,
            "size_mb":           0.1953,
            "path":              "uploads/uuid-generado.jpg"
        }

    Raises:
        AppHttpException 415: Tipo de archivo no permitido.
        AppHttpException 413: Archivo supera el tamaño máximo.

    Uso en un endpoint:
        from fastapi import UploadFile, File
        from app.utils.file_upload import save_upload

        @router.post("/avatar")
        async def upload_avatar(file: UploadFile = File(...)):
            result = await save_upload(
                file,
                allowed_types=["image/jpeg", "image/png", "image/webp"],
                max_size_mb=5,
            )
            # Aquí puedes subir result["path"] a S3, etc.
            # Recuerda eliminar el archivo temporal después.
            return result
    """
    # Validar tipo de archivo
    if allowed_types and file.content_type not in allowed_types:
        raise AppHttpException(
            message=f"Tipo de archivo no permitido: {file.content_type}",
            status_code=415,
            context={
                "allowed_types": allowed_types,
                "received_type": file.content_type,
            },
        )

    content = await file.read()
    size_bytes = len(content)

    # Validar tamaño — usa el parámetro o cae al límite global del middleware
    effective_max_mb = max_size_mb if max_size_mb is not None else REQUEST_MAX_SIZE_MB
    max_bytes = effective_max_mb * 1024 * 1024

    if size_bytes > max_bytes:
        raise AppHttpException(
            message=f"Archivo demasiado grande. Máximo permitido: {effective_max_mb}MB",
            status_code=413,
            context={
                "max_mb": effective_max_mb,
                "received_mb": round(size_bytes / 1024 / 1024, 4),
            },
        )

    # Guardar en disco
    upload_dir = destination or UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_name = file.filename or "file"
    extension = Path(original_name).suffix
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = upload_dir / unique_filename

    file_path.write_bytes(content)

    return {
        "filename": unique_filename,
        "original_filename": original_name,
        "content_type": file.content_type,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / 1024 / 1024, 4),
        "path": str(file_path),
    }


async def save_uploads(
    files: list[UploadFile],
    allowed_types: list[str] | None = None,
    max_size_mb: float | None = None,
    destination: Path | None = None,
) -> list[dict]:
    """
    Versión de save_upload para múltiples archivos simultáneos.

    Procesa cada archivo individualmente. Si alguno falla la validación,
    lanza la excepción y los archivos ya guardados quedan en disco.

    Args:
        files:         Lista de archivos (UploadFile) recibidos del endpoint.
        allowed_types: Ver save_upload.
        max_size_mb:   Ver save_upload.
        destination:   Ver save_upload.

    Returns:
        Lista de dicts con metadata de cada archivo guardado.

    Uso en un endpoint:
        from fastapi import UploadFile, File
        from app.utils.file_upload import save_uploads

        @router.post("/attachments")
        async def upload_attachments(files: list[UploadFile] = File(...)):
            results = await save_uploads(
                files,
                allowed_types=["application/pdf", "image/jpeg"],
                max_size_mb=10,
            )
            return results
    """
    results = []
    for file in files:
        result = await save_upload(file, allowed_types, max_size_mb, destination)
        results.append(result)
    return results
