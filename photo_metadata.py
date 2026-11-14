"""Извлечение и проверка метаданных фотографий."""

from datetime import datetime, timezone
from io import BytesIO

from PIL import Image
from PIL.ExifTags import TAGS


def extract_datetime(content: bytes) -> datetime | None:
    """Извлекает дату и время съёмки из EXIF-данных фото.
    
    Возвращает datetime с UTC timezone или None, если метаданные отсутствуют.
    """
    try:
        image = Image.open(BytesIO(content))
        exif_data = image._getexif()
        
        if exif_data is None:
            return None
        
        # Поиск даты съёмки в EXIF
        # Ключи: 36867 (DateTimeOriginal), 36868 (DateTimeDigitized), 306 (DateTime)
        for tag_id in (36867, 36868, 306):
            if tag_id in exif_data:
                date_str = exif_data[tag_id]
                try:
                    # EXIF формат: "YYYY:MM:DD HH:MM:SS"
                    dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    # Предполагаем, что время в EXIF — локальное, конвертируем в UTC
                    return dt.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue
        
        return None
    except Exception:
        return None


def check_photo_freshness(content: bytes, max_age_minutes: int = 30) -> tuple[bool, str]:
    """Проверяет, что фото сделано не раньше max_age_minutes назад.
    
    Возвращает:
        (True, "") если фото свежее
        (False, сообщение) если фото слишком старое или метаданные отсутствуют
    """
    photo_datetime = extract_datetime(content)
    
    # Если не удалось извлечь дату — запрещаем загрузку
    if photo_datetime is None:
        return False, "Фото не содержит метаданных о дате съёмки. Используйте камеру с включёнными геоданными"
    
    now = datetime.now(timezone.utc)
    age_seconds = (now - photo_datetime).total_seconds()
    max_age_seconds = max_age_minutes * 60
    
    if age_seconds < 0:
        # Фото "из будущего" — возможно неправильные часы на устройстве
        return False, "Некорректная дата съёмки в метаданных фото (дата из будущего)"
    
    if age_seconds > max_age_seconds:
        age_minutes = int(age_seconds / 60)
        return False, f"Фото устарело (снято {age_minutes} мин. назад, допустимо до {max_age_minutes} мин.)"
    
    return True, ""
