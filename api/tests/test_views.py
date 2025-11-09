from uuid import uuid4
from rest_framework.test import APITestCase
from rest_framework import status
from api.models import Company, Category

class CategoryViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="Demo Co")
        cls.other_company = Company.objects.create(name="Other Co")

    # 成功系：一覧
    def test_list(self):
        Category.objects.create(company=self.company, name="A")
        Category.objects.create(company=self.company, name="B")
        res = self.client.get("/api/categories/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.json()), 2)

    # 成功系：取得
    def test_retrieve(self):
        cat = Category.objects.create(company=self.company, name="Beverages")
        res = self.client.get(f"/api/categories/{cat.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["name"], "Beverages")

    # 成功系：作成（前後空白はtrim）
    def test_create(self):
        payload = {"company": str(self.company.id), "name": "  Snacks  "}
        res = self.client.post("/api/categories/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()["name"], "Snacks")

    # 成功系：更新（通常の名前変更）
    def test_update(self):
        cat = Category.objects.create(company=self.company, name="Food")
        res = self.client.patch(f"/api/categories/{cat.id}/", {"name": "Groceries"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["name"], "Groceries")

    # 成功系：削除
    def test_destroy(self):
        cat = Category.objects.create(company=self.company, name="Temp")
        res = self.client.delete(f"/api/categories/{cat.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    # 失敗系：空白名は400
    def test_create_blank_name_is_rejected(self):
        res = self.client.post(
            "/api/categories/",
            {"company": str(self.company.id), "name": "   "},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", res.json())

    # 失敗系：同一company内の重複名は400（他社は許容）
    def test_create_duplicate_name_per_company_is_rejected(self):
        Category.objects.create(company=self.company, name="Dup")
        res = self.client.post(
            "/api/categories/",
            {"company": str(self.company.id), "name": "Dup"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res2 = self.client.post(
            "/api/categories/",
            {"company": str(self.other_company.id), "name": "Dup"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

    # 失敗系：自己参照は400
    def test_update_self_parent_is_rejected(self):
        cat = Category.objects.create(company=self.company, name="Self")
        res = self.client.patch(
            f"/api/categories/{cat.id}/",
            {"parent_category": str(cat.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", res.json())

    # 失敗系：親は同一 company 必須（作成）
    def test_create_parent_must_be_same_company(self):
        parent_other = Category.objects.create(company=self.other_company, name="P-Other")
        res = self.client.post(
            "/api/categories/",
            {"company": str(self.company.id), "name": "Child", "parent_category": str(parent_other.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", res.json())

    # 失敗系：親は同一 company 必須（更新）
    def test_update_parent_must_be_same_company(self):
        child = Category.objects.create(company=self.company, name="Child")
        parent_other = Category.objects.create(company=self.other_company, name="P-Other")
        res = self.client.patch(
            f"/api/categories/{child.id}/",
            {"parent_category": str(parent_other.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", res.json())

    # 失敗系：循環参照の検出（A->B->C があるときに A の親を C に設定）
    def test_cycle_detection_on_update(self):
        A = Category.objects.create(company=self.company, name="A")
        B = Category.objects.create(company=self.company, name="B", parent_category=A)
        C = Category.objects.create(company=self.company, name="C", parent_category=B)
        res = self.client.patch(
            f"/api/categories/{A.id}/",
            {"parent_category": str(C.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", res.json())

    # 参考：存在しないIDは404
    def test_retrieve_not_found(self):
        res = self.client.get(f"/api/categories/{uuid4()}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # 参考：存在しない外部キー(company)は400
    def test_create_invalid_foreign_keys(self):
        res = self.client.post(
            "/api/categories/",
            {"company": str(uuid4()), "name": "X"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # 重要：作成後の company 変更を禁止（400で拒否）
    def test_update_company_is_read_only(self):
        cat = Category.objects.create(company=self.company, name="Fixed")
        res = self.client.patch(
            f"/api/categories/{cat.id}/",
            {"company": str(self.other_company.id), "name": "Updated"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        cat.refresh_from_db()
        self.assertEqual(cat.company.id, self.company.id)
        self.assertEqual(cat.name, "Fixed")
