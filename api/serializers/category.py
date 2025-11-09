from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from api.models import Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "company", "name", "parent_category", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=Category.objects.all(),
                fields=["company", "name"],
                message="同一の会社内で同名のカテゴリは作成できません。",
            )
        ]

    def validate(self, attrs):
        # name: 前後空白を削り、空白のみは禁止
        name = attrs.get("name", None)
        if name is not None:
            name = name.strip() if isinstance(name, str) else name
            if not name:
                raise serializers.ValidationError({"name": ["空白のみは不可です。"]})
            attrs["name"] = name

        # 自己参照禁止（更新時に自分自身を親にしない）
        instance = getattr(self, "instance", None)
        parent = attrs.get("parent_category")
        if instance is not None and parent is not None and parent == instance:
            raise serializers.ValidationError({"parent_category": ["自分自身は親にできません。"]})

        return attrs