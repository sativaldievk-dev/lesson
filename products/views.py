from rest_framework.viewsets import ModelViewSet

from .models import Product
from .permissions import IsModerator
from .serializers import ProductSerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related("created_by").all()
    serializer_class = ProductSerializer
    permission_classes = [IsModerator]
