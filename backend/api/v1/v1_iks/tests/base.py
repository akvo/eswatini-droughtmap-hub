from rest_framework.test import APITestCase
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import Administration
from api.v1.v1_iks.models import KoboAdapter, KoboForm


class BaseIKSTestCase(APITestCase):
    """Shared fixtures for IKS tests: authenticated user, an administration
    area, an active Kobo adapter, and a registered Kobo form."""

    def setUp(self):
        # Create test user
        self.user = SystemUser.objects.create_superuser(
            name="Test User",
            email="testuser@akvo.org",
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

        # Create test administration
        self.admin_area = Administration.objects.create(
            id=1621199, name="Nkwene", region="Shiselweni"
        )

        # Create active Kobo Adapter
        self.adapter = KoboAdapter.objects.create(
            server_url="https://kf.kobotoolbox.org",
            username="test_kobo_user",
            password="test_kobo_password",
            active=True,
        )

        # Create Kobo Form
        self.form = KoboForm.objects.create(
            uuid="a3ytas3GLhSewNTZByCCsd",
            name="CDI-E - IKS by Akvo",
            description="IKS Form",
            questions={},
            options={},
            languages=["en"],
        )

    def month_idx(self, payload, when):
        """Position of `when`'s month in a trend response's 12-month window.

        The window is anchored on timezone.now(), so a literal index would
        only be right during the month the test was written.  Raises
        ValueError if `when` has aged out of the window entirely.
        """
        return payload["weeks"].index(when.strftime("%b %Y"))
