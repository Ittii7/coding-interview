from rest_framework.test import APITestCase
from rest_framework import status
from api.models import Company, Category
from uuid import uuid4

class CategoryViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="Demo Co")
        cls.other_company = Company.objects.create(name="Other Co")

    # 成功系
    def test_list(self):
        Category.objects.create(company=self.company, name="A")
        Category.objects.create(company=self.company, name="B")
        res = self.client.get("/api/categories/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.json()), 2)

    def test_retrieve(self):
        cat = Category.objects.create(company=self.company, name="Beverages")
        res = self.client.get(f"/api/categories/{cat.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["name"], "Beverages")

    def test_create(self):
        payload = {"company": str(self.company.id), "name": "  Snacks  "}
        res = self.client.post("/api/categories/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()["name"], "Snacks")  # 前後空白は除去される

    def test_update(self):
        cat = Category.objects.create(company=self.company, name="Food")
        res = self.client.patch(f"/api/categories/{cat.id}/", {"name": "Groceries"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["name"], "Groceries")

    def test_destroy(self):
        cat = Category.objects.create(company=self.company, name="Temp")
        res = self.client.delete(f"/api/categories/{cat.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    # 失敗系
    def test_create_blank_name_is_rejected(self):
        res = self.client.post(
            "/api/categories/",
            {"company": str(self.company.id), "name": "   "},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", res.json())

    def test_create_duplicate_name_per_company_is_rejected(self):
        Category.objects.create(company=self.company, name="Dup")
        res = self.client.post(
            "/api/categories/",
            {"company": str(self.company.id), "name": "Dup"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # 会社が違えば同名でも作成可能
        res2 = self.client.post(
            "/api/categories/",
            {"company": str(self.other_company.id), "name": "Dup"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

    def test_update_self_parent_is_rejected(self):
        cat = Category.objects.create(company=self.company, name="Self")
        res = self.client.patch(
            f"/api/categories/{cat.id}/",
            {"parent_category": str(cat.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", res.json())

    # 追加で押さえておくと安心（存在しないIDは404／存在しないFKは400）
    def test_retrieve_not_found(self):
        res = self.client.get(f"/api/categories/{uuid4()}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_invalid_foreign_keys(self):
        res = self.client.post(
            "/api/categories/",
            {"company": str(uuid4()), "name": "X"},  # 存在しない company
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
