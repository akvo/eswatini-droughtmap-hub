import io
from PIL import Image
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from api.v1.v1_activity import files


def _png(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return buf.getvalue()


class FilesTestCase(TestCase):
    def test_sanitize_filename_strips_paths(self):
        self.assertEqual(files.sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(files.sanitize_filename("a/b\\c.pdf"), "c.pdf")

    def test_reject_unknown_extension(self):
        f = SimpleUploadedFile(
            "x.exe", b"data", content_type="application/octet-stream"
        )
        with self.assertRaises(ValidationError):
            files.validate_source_file(f)

    def test_reject_oversized_image_dimensions(self):
        f = SimpleUploadedFile(
            "big.png", _png(1000, 500), content_type="image/png"
        )
        with self.assertRaises(ValidationError):
            files.validate_source_file(f)

    def test_accept_valid_image(self):
        f = SimpleUploadedFile(
            "ok.png", _png(400, 200), content_type="image/png"
        )
        files.validate_source_file(f)  # no raise

    def test_accept_pdf(self):
        f = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4 ...", content_type="application/pdf"
        )
        files.validate_source_file(f)  # no raise


@override_settings(USE_TZ=False, TEST_ENV=True)
class SaveSourceFileTestCase(TestCase):
    def test_save_returns_relative_path(self, *_):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(STORAGE_PATH=tmp):
                # storage.py caches STORAGE_PATH at import; patch it too.
                from utils import storage

                storage.STORAGE_PATH = tmp
                f = SimpleUploadedFile(
                    "ok.png", _png(100, 100), content_type="image/png"
                )
                rel = files.save_source_file(f, "ACT-WASH-1")
                self.assertEqual(rel, "activity/ACT-WASH-1/ok.png")
                self.assertTrue(storage.check(rel))
