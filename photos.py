import os
import re
import uuid


MAX_PHOTO_BYTES = 5 * 1024 * 1024
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# расширение -> сигнатура начала файла (magic bytes)
ALLOWED = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}

MIME_BY_EXT = {"png": "image/png", "jpg": "image/jpeg"}
SAFE_NAME = re.compile(r"^[0-9a-f]{32}\.(png|jpg)$")


def get_upload_dir() -> str:
    return os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))


def is_safe_name(filename: str) -> bool:
    """Имена генерируем сами, поэтому любой другой вид имени отвергаем."""
    return bool(filename) and bool(SAFE_NAME.match(filename))


def photo_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def photo_path(filename: str) -> str:
    if not is_safe_name(filename):
        raise ValueError("Некорректное имя файла")
    return os.path.join(get_upload_dir(), filename)


def read_photo(filename: str) -> bytes:
    with open(photo_path(filename), "rb") as fh:
        return fh.read(MAX_PHOTO_BYTES + 1)


def save_photo(file_storage) -> dict:
    """Проверяет фото, сохраняет на диск и возвращает имя, MIME и размер."""
    name = file_storage.filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED:
        raise ValueError("Допустимы только файлы PNG и JPG")

    content = file_storage.read(MAX_PHOTO_BYTES + 1)
    if not content:
        raise ValueError("Файл пустой")
    if len(content) > MAX_PHOTO_BYTES:
        raise ValueError("Фото должно быть не больше 5 МБ")
    if not content.startswith(ALLOWED[ext]):
        raise ValueError("Содержимое файла не похоже на PNG или JPG")

    out_ext = "jpg" if ext == "jpeg" else ext
    filename = f"{uuid.uuid4().hex}.{out_ext}"
    upload_dir = get_upload_dir()
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, filename), "wb") as fh:
        fh.write(content)

    return {
        "filename": filename,
        "mime": MIME_BY_EXT[out_ext],
        "size": len(content),
    }
