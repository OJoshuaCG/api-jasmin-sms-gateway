# File Upload

## Flujo de Trabajo

```
Route recibe UploadFile
  → save_upload() valida y guarda en uploads/
    → Controller lee el archivo desde disco
      → Procesar (subir a S3, parsear CSV, etc.)
        → file_path.unlink() elimina el temporal
```

Los archivos en `uploads/` son **temporales**. Deben eliminarse después de procesarlos.

## Upload de Un Archivo

```python
from fastapi import File, UploadFile
from pathlib import Path
from app.utils.file_upload import save_upload
from app.utils.response import ApiResponse, success

@router.post("/avatar", response_model=ApiResponse[dict])
async def upload_avatar(file: UploadFile = File(...)):
    file_info = await save_upload(
        file,
        allowed_types=["image/jpeg", "image/png", "image/webp"],
        max_size_mb=2,
    )
    file_path = Path(file_info["path"])
    try:
        content = file_path.read_bytes()
        # Aquí va la lógica real: subir a S3, procesar, etc.
        return success(data={"processed": True}, message="Avatar actualizado")
    finally:
        if file_path.exists():
            file_path.unlink()  # Siempre eliminar — incluso si hay error
```

## Upload de Múltiples Archivos

```python
from app.utils.file_upload import save_uploads

@router.post("/attachments", response_model=ApiResponse[list[dict]])
async def upload_attachments(files: list[UploadFile] = File(...)):
    saved = await save_uploads(
        files,
        allowed_types=["application/pdf", "image/jpeg"],
        max_size_mb=10,
    )
    results = []
    for file_info in saved:
        file_path = Path(file_info["path"])
        try:
            content = file_path.read_bytes()
            results.append({"name": file_info["original_filename"]})
        finally:
            if file_path.exists():
                file_path.unlink()
    return success(data=results)
```

## `save_upload()` — Parámetros

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `file` | `UploadFile` | requerido | Archivo recibido de FastAPI |
| `allowed_types` | `list[str] \| None` | `None` | MIME types permitidos. `None` = acepta todo |
| `max_size_mb` | `float \| None` | `None` | MB máximos. `None` = usa `REQUEST_MAX_SIZE_MB` como fallback |
| `destination` | `Path \| None` | `None` | Carpeta destino. `None` = `uploads/` |

## Respuesta de `save_upload()`

```python
{
    "filename":          "3f7a1b2c-uuid.jpg",  # Nombre único generado (UUID + extensión)
    "original_filename": "foto.jpg",             # Nombre original del cliente
    "content_type":      "image/jpeg",
    "size_bytes":        204800,
    "size_mb":           0.1953,
    "path":              "uploads/3f7a1b2c-uuid.jpg"
}
```

## Leer el Archivo

```python
file_path = Path(file_info["path"])

# Contenido binario (imágenes, PDFs, Excel, cualquier binario)
content = file_path.read_bytes()

# Contenido como texto (CSV, JSON, TXT, XML)
text = file_path.read_text(encoding="utf-8")
```

## Errores Que Puede Lanzar

| Error | Status | Cuándo |
|---|---|---|
| `AppHttpException` | 415 | Tipo de archivo no está en `allowed_types` |
| `AppHttpException` | 413 | Tamaño del archivo supera `max_size_mb` |

Estos errores se manejan automáticamente por el handler global y retornan:
```json
{"detail": {"msg": "Tipo de archivo no permitido: application/exe", "type": "AppHttpException"}}
```

## MIME Types Comunes

```python
# Imágenes
allowed_types=["image/jpeg", "image/png", "image/webp", "image/gif"]

# Documentos
allowed_types=["application/pdf", "application/msword",
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

# Hojas de cálculo
allowed_types=["application/vnd.ms-excel",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]

# Texto
allowed_types=["text/plain", "text/csv"]
```

## Integración con Controller

```python
# app/controllers/user_controller.py
from fastapi import UploadFile
from pathlib import Path
from app.utils.file_upload import save_upload

class UserController:
    async def update_avatar(self, user_id: int, file: UploadFile) -> dict:
        file_info = await save_upload(
            file,
            allowed_types=["image/jpeg", "image/png"],
            max_size_mb=2,
        )
        file_path = Path(file_info["path"])
        try:
            content = file_path.read_bytes()
            # url = s3_client.upload(content, key=f"avatars/{user_id}.jpg")
            self.user_model.update(user_id, {"avatar_url": "url_resultante"})
            return {"avatar_url": "url_resultante"}
        finally:
            if file_path.exists():
                file_path.unlink()
```

## Notas Importantes

- `uploads/` está en `.gitignore` (solo se versiona `.gitkeep` para mantener la carpeta)
- El `try/finally` garantiza que el archivo temporal se elimine siempre, incluso si hay una excepción durante el procesamiento
- El nombre del archivo guardado es un UUID para evitar colisiones y ocultar nombres originales
- Si `max_size_mb=None`, usa `REQUEST_MAX_SIZE_MB` del middleware como fallback de última instancia
