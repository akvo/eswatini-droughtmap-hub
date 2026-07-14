import os
from pathlib import Path

from rest_framework.exceptions import ValidationError

from utils import storage

from api.v1.v1_activity.constants import ALLOWED_EXTENSIONS, ALLOWED_MIMES

RASTER_IMAGE_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
}  # SVG has no raster dimensions
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_W, MAX_IMAGE_H = 800, 400


def _ext(name):
    ext_part = name.rsplit(".", 1)[-1].lower() if "." in (name or "") else ""
    return f".{ext_part}" if ext_part else ""


def sanitize_filename(name):
    """Basename only — defeats path traversal (`../`, absolute paths)."""
    base = os.path.basename((name or "").replace("\\", "/"))
    return base or "upload"


def validate_source_file(f, validate_dimensions=True):
    """Extension + mime + size + (for raster images) max-dimension check."""
    ext = _ext(getattr(f, "name", ""))
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}."
        )

    # MIME check
    mime = getattr(f, "content_type", "")
    if mime and mime not in ALLOWED_MIMES:
        raise ValidationError(f"Unsupported MIME type '{mime}'.")

    if f.size > MAX_FILE_SIZE:
        raise ValidationError("File too large (max 10 MB).")
    if validate_dimensions and ext in RASTER_IMAGE_EXT:
        try:
            from PIL import Image

            image = Image.open(f)
            width, height = image.size
        except Exception:
            raise ValidationError("Uploaded image is not a valid image file.")
        finally:
            f.seek(0)
        if width > MAX_IMAGE_W or height > MAX_IMAGE_H:
            raise ValidationError(
                f"Image exceeds max dimensions {MAX_IMAGE_W}x{MAX_IMAGE_H}px."
            )


def save_source_file(uploaded, code):
    """Persist an uploaded file under activity/<code>/ and return the
    relative path."""
    safe = sanitize_filename(uploaded.name)
    tmp_dir = Path("./tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / safe
    with open(tmp_path, "wb") as fh:
        for chunk in uploaded.chunks():
            fh.write(chunk)
    try:
        storage.upload(str(tmp_path), folder=f"activity/{code}", filename=safe)
    finally:
        os.remove(tmp_path)
    return f"activity/{code}/{safe}"
