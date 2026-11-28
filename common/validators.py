from datetime import date

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied


def validate_birthdate_from_token(token, *, today=None):
    """Reject product creation unless the JWT birthdate shows the user is 18+."""
    birthdate_value = token.get("birthdate") if token is not None else None
    if not birthdate_value:
        raise PermissionDenied("Укажите дату рождения, чтобы создать продукт.")

    try:
        if isinstance(birthdate_value, date):
            birthdate = birthdate_value
        else:
            birthdate = date.fromisoformat(str(birthdate_value))
    except (TypeError, ValueError):
        raise PermissionDenied("Укажите дату рождения, чтобы создать продукт.")

    today = today or timezone.localdate()
    age = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1

    if age < 18:
        raise PermissionDenied("Вам должно быть 18 лет, чтобы создать продукт.")

    return birthdate
