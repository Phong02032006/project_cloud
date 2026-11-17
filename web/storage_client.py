import os
import uuid
from pathlib import Path

from flask import current_app, has_app_context

ALLOWED_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
LOCAL_UPLOAD_DIR = Path(__file__).resolve().parent / "static" / "uploads"


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        return (current_app.config.get(key) or default).strip()
    return (os.environ.get(key) or default).strip()


def upload_question_image(file_storage) -> str:
    """Validate and store a question illustration image on Azure Blob Storage (or locally when unconfigured)."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        raise ValueError("No image file provided.")

    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS.keys())
        raise ValueError(f"Invalid image format '{ext}'. Allowed formats: {allowed}.")

    data = file_storage.read()
    if not data:
        raise ValueError("Uploaded image file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image size exceeds the 5 MB limit.")

    filename = f"{uuid.uuid4().hex}{ext}"
    content_type = ALLOWED_EXTENSIONS[ext]

    conn_str = _cfg("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        container_name = _cfg("AZURE_STORAGE_CONTAINER", "question-images") or "question-images"
        service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = service_client.get_container_client(container_name)
        try:
            if not container_client.exists():
                container_client.create_container(public_access="blob")
        except Exception:
            # Ignore race conditions if container was just created
            pass

        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_client.url

    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = LOCAL_UPLOAD_DIR / filename
    dest.write_bytes(data)
    return f"/static/uploads/{filename}"
