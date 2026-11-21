from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "phone_number")
        read_only_fields = fields


class ValidationErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    email = serializers.ListField(child=serializers.CharField(), required=False)
    phone_number = serializers.ListField(child=serializers.CharField(), required=False)
    password = serializers.ListField(child=serializers.CharField(), required=False)
    password_confirm = serializers.ListField(child=serializers.CharField(), required=False)


class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserReadSerializer()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(help_text="Уникальный email для входа.")
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Необязательный номер Кыргызстана в формате +996XXXXXXXXX.",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Пароль должен пройти настроенные валидаторы Django.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Повторите пароль для проверки.",
    )

    class Meta:
        model = User
        fields = ("email", "phone_number", "password", "password_confirm")

    def validate_email(self, value):
        email = value.strip().casefold()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

    def validate_phone_number(self, value):
        if value:
            from accounts.validators import kyrgyz_phone_validator

            kyrgyz_phone_validator(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        validate_password(attrs["password"], user=User(email=attrs["email"]))
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email, использованный при регистрации.")
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs["email"].strip().casefold()
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError({"detail": "Неверный email или пароль."})
        attrs["user"] = user
        return attrs
