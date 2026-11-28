from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Product
from .permissions import IsModerator, ProductCreateAgePermission
from .serializers import ProductSerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related("created_by").all()
    serializer_class = ProductSerializer
    permission_classes = [IsModerator]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), ProductCreateAgePermission()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
