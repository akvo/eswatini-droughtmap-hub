from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import Publication
from api.v1.v1_review.models import Review


class ReviewViewSetTestCase(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = SystemUser.objects._create_user(
            email="reviewer1@mail.com",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)

        # Create a publication
        self.publication = Publication.objects.create(
            year_month="2025-01",
            cdi_geonode_id=123,
            initial_values=[{"administration_id": 1, "value": 100}],
            due_date="2025-02-01",
        )

        # Create some reviews
        self.review1 = Review.objects.create(
            publication=self.publication,
            user=self.user,
            is_completed=False,
            suggestion_values=[{"reviewed": True}, {"reviewed": False}],
        )
        self.review2 = Review.objects.create(
            publication=self.publication,
            user=self.user,
            is_completed=True,
            suggestion_values=[{"reviewed": True}, {"reviewed": True}],
        )

        # URLs
        self.list_url = reverse("review-list")
        self.detail_url = lambda pk: reverse(
            "review-detail", kwargs={"pk": pk}
        )

    def test_list_reviews(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 2
        )  # Ensure 2 reviews are returned
        self.assertIn(
            "progress_review", response.data["results"][0]
        )  # Check custom field

    def test_retrieve_review(self):
        response = self.client.get(self.detail_url(self.review1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.review1.id)
        self.assertEqual(
            response.data["progress_review"], "1/2"
        )  # Check progress review

    def test_create_review(self):
        payload = {
            "publication": self.publication.id,
            "user": self.user.id,
            "is_completed": False,
            "suggestion_values": [{"reviewed": False}, {"reviewed": True}],
        }
        response = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 3)  # New review created

    def test_update_review(self):
        payload = {
            "publication": self.publication.id,
            "user": self.user.id,
            "is_completed": True,
            "suggestion_values": [
                {"reviewed": True},
                {"reviewed": True},
                {"reviewed": False},
            ],
        }
        response = self.client.put(
            self.detail_url(self.review1.id), data=payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_review = Review.objects.get(id=self.review1.id)
        self.assertTrue(updated_review.is_completed)
        self.assertEqual(len(updated_review.suggestion_values), 3)

    def test_delete_review(self):
        response = self.client.delete(self.detail_url(self.review1.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(id=self.review1.id).exists())

    def test_list_reviews_pagination(self):
        response = self.client.get(f"{self.list_url}?page=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)  # Pagination count
        self.assertEqual(
            response.data["count"], 2
        )  # Ensure total reviews count matches

    def test_permission_denied_for_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_review_creation(self):
        payload = {
            "publication": None,  # Missing required field
            "user": self.user.id,
            "is_completed": False,
        }
        response = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_progress_review_field_logic(self):
        response = self.client.get(self.detail_url(self.review2.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # All reviewed
        self.assertEqual(response.data["progress_review"], "2/2")
