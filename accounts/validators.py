from django.core.validators import RegexValidator


kyrgyz_phone_validator = RegexValidator(
    regex=r"^\+996\d{9}$",
    message="Введите номер в формате +996XXXXXXXXX: после +996 должно быть ровно 9 цифр.",
    code="invalid_phone_number",
)
