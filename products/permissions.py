from rest_framework.permissions import BasePermission


class IsModerator(BasePermission):
    """Allow staff users to read and manage products, except creating them."""

    allowed_methods = {"GET", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"}

    def _is_moderator_request(self, request):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and request.method in self.allowed_methods
        )

    def has_permission(self, request, view):
        return self._is_moderator_request(request)

    def has_object_permission(self, request, view, obj):
        # Ownership is deliberately irrelevant: moderators can manage any product.
        return self._is_moderator_request(request)
