from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomTokenObtainPairSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserReadSerializer,
    ValidationErrorSerializer,
)


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Регистрация по email",
        description=(
            "Обычный пользователь может не передавать `phone_number`. Если номер указан, "
            "он должен иметь формат +996 и ровно 9 цифр после кода страны. "
            "Поле `birthdate` принимается в формате YYYY-MM-DD и нужно для создания продуктов."
        ),
        request=RegisterSerializer,
        responses={
            201: UserReadSerializer,
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Ошибки email, пароля или номера телефона.",
            ),
        },
        examples=[
            OpenApiExample(
                "Регистрация без телефона",
                value={
                    "email": "aliya@example.com",
                    "birthdate": "1997-01-15",
                    "password": "<your password>",
                    "password_confirm": "<your password>",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Регистрация с телефоном",
                value={
                    "email": "aliya@example.com",
                    "phone_number": "+996555123456",
                    "password": "<your password>",
                    "password_confirm": "<your password>",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Созданный пользователь",
                value={
                    "id": 1,
                    "email": "aliya@example.com",
                    "phone_number": "",
                    "birthdate": "1997-01-15",
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Неверный номер телефона",
                value={
                    "phone_number": [
                        "Введите номер в формате +996XXXXXXXXX: после +996 должно быть ровно 9 цифр."
                    ]
                },
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Пароли не совпадают",
                value={"password_confirm": ["Пароли не совпадают."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
        tags=["Аутентификация"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserReadSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Вход по email и паролю",
        description="Проверяет учетные данные и возвращает пару JWT access/refresh.",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Неверный email или пароль.",
            ),
        },
        examples=[
            OpenApiExample(
                "Учетные данные",
                value={"email": "aliya@example.com", "password": "<your password>"},
                request_only=True,
            ),
            OpenApiExample(
                "Успешный вход",
                value={
                    "refresh": "<refresh token>",
                    "access": "<access token>",
                    "user": {
                        "id": 1,
                        "email": "aliya@example.com",
                        "phone_number": "",
                        "birthdate": None,
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Ошибка входа",
                value={"detail": "Неверный email или пароль."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
        tags=["Аутентификация"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserReadSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Получение JWT по email и паролю",
        description="Стандартная пара Simple JWT; поле `email` является полем входа.",
        examples=[
            OpenApiExample(
                "Вход для получения токена",
                value={"email": "aliya@example.com", "password": "<your password>"},
                request_only=True,
            ),
            OpenApiExample(
                "JWT-токены",
                value={"refresh": "<refresh token>", "access": "<access token>"},
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["JWT"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class EmailTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Обновление access JWT",
        description="Принимает действующий refresh-токен и возвращает новый access-токен.",
        examples=[
            OpenApiExample(
                "Refresh запрос",
                value={"refresh": "<refresh token>"},
                request_only=True,
            ),
            OpenApiExample(
                "Обновленный access",
                value={"access": "<access token>"},
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["JWT"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    """Return the authenticated user's public account details."""

    @extend_schema(
        summary="Данные текущего пользователя",
        description="Доступно только с заголовком Authorization: Bearer <access token>.",
        responses={
            200: UserReadSerializer,
            401: OpenApiResponse(description="Не передан действующий access JWT."),
        },
        tags=["Аутентификация"],
    )
    def get(self, request):
        return Response(UserReadSerializer(request.user).data)
