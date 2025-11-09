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
        # 1) name：前後空白を削除し、空白のみは 400
        name = attrs.get("name", None)
        if name is not None:
            name = name.strip() if isinstance(name, str) else name
            if not name:
                raise serializers.ValidationError({"name": ["空白のみは不可です。"]})
            attrs["name"] = name

        instance = getattr(self, "instance", None)

        # 2) 更新では company を変更不可（作成時は受け付ける）
        if instance is not None and "company" in attrs and attrs["company"] != instance.company:
            raise serializers.ValidationError({"company": ["作成後に company は変更できません。"]})

        # 3) この操作後に有効となる company
        target_company = attrs.get("company") if instance is None else instance.company

        # 4) parent：未指定なら現状を評価に使う
        parent = attrs.get("parent_category", None)
        if instance is not None and parent is None:
            parent = instance.parent_category

        # 5) 自己参照禁止（更新時）
        if instance is not None and parent is not None and parent == instance:
            raise serializers.ValidationError({"parent_category": ["自分自身は親にできません。"]})

        # 6) 親は同一 company 必須（作成/更新）
        if parent is not None and target_company is not None:
            if parent.company_id != getattr(target_company, "id", target_company):
                raise serializers.ValidationError({
                    "parent_category": ["親カテゴリは同じ会社のものである必要があります。"]
                })

        # 7) 親チェーンの循環検査（作成でも親側に既存の循環があれば検出）
        if parent is not None:
            seen = set()
            current = parent
            steps = 0
            while current is not None:
                if instance is not None and current.pk == instance.pk:
                    raise serializers.ValidationError({"parent_category": ["循環参照が発生します。"]})
                if current.pk in seen:
                    raise serializers.ValidationError({"parent_category": ["親ツリーに循環が存在します。"]})
                seen.add(current.pk)
                steps += 1
                if steps > 2048:
                    raise serializers.ValidationError({"parent_category": ["親ツリーが深すぎます。循環の可能性があります。"]})
                current = current.parent_category

        return attrs
