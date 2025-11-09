from rest_framework import viewsets
from api.models import Category
from api.serializers.category import CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = (
        Category.objects
        .select_related("company", "parent_category")
        .order_by("name", "id")
    )
    serializer_class = CategorySerializer
