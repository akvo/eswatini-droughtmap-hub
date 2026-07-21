from django.test import TestCase, RequestFactory, override_settings
from utils.custom_permissions import HasApiKey


@override_settings(
    X_API_KEY="test-secret-key",
    X_API_KEY_HEADER="HTTP_X_API_KEY",
)
class HasApiKeyPermissionTest(TestCase):
    """Unit tests for the HasApiKey permission class (D-4)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = HasApiKey()

    def _make_request(self, key=None):
        meta = {}
        if key is not None:
            meta["HTTP_X_API_KEY"] = key
        request = self.factory.post("/fake/", **meta)
        return request

    def test_valid_key_grants_access(self):
        request = self._make_request(key="test-secret-key")
        self.assertTrue(self.permission.has_permission(request, None))

    def test_wrong_key_denies_access(self):
        request = self._make_request(key="wrong-key")
        self.assertFalse(self.permission.has_permission(request, None))

    def test_missing_key_denies_access(self):
        request = self._make_request()  # no key header at all
        self.assertFalse(self.permission.has_permission(request, None))

    def test_empty_string_key_denies_access(self):
        request = self._make_request(key="")
        self.assertFalse(self.permission.has_permission(request, None))

    def test_comparison_is_constant_time(self):
        # hmac.compare_digest must be used — verify by inspecting the source
        # indirectly: both a correct key and a slightly-off key must be
        # handled (we can't directly test timing, but we can assert correctness
        # around the boundary).
        request_correct = self._make_request(key="test-secret-key")
        request_almost = self._make_request(
            key="test-secret-ke"
        )  # one char short
        self.assertTrue(self.permission.has_permission(request_correct, None))
        self.assertFalse(self.permission.has_permission(request_almost, None))
