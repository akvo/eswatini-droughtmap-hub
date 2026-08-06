import os
import tempfile
from collections import Counter
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_iks.models import IKSIndicator, IKSValue, KoboData, KoboForm
from api.v1.v1_iks.utils import label_soil_moisture, label_vegetation

MONTHS = 6


@override_settings(STORAGE_PATH=tempfile.mkdtemp())
class GenerateIksSeederTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def seed(self, *extra):
        out = StringIO()
        call_command(
            "generate_iks_seeder", "--months", MONTHS, *extra, stdout=out
        )
        return out.getvalue()

    def test_creates_submissions_and_extracted_values(self):
        self.seed()
        self.assertTrue(KoboData.objects.exists())
        # The point of routing through download_iks_data._map_iks_values: if
        # the question keys drift, submissions still store fine but produce
        # zero values, which looks like an empty explorer rather than a bug.
        self.assertTrue(IKSValue.objects.exists())

    def test_covers_all_three_questionnaire_sections(self):
        self.seed()
        sections = Counter(
            IKSIndicator.objects.values_list("section", flat=True)
        )
        for section in ("B", "C", "D"):
            self.assertGreater(sections[section], 0, f"section {section}")

    def test_section_d_values_resolve_to_real_labels(self):
        """Catches choice-vocabulary drift.

        label_soil_moisture/label_vegetation match on siSwati substrings; a
        renamed choice returns None and the Section D cards silently empty.
        """
        self.seed()
        soil = IKSValue.objects.filter(
            iks_indicator__name="soil_moisture"
        ).values_list("value", flat=True)
        vegetation = IKSValue.objects.filter(
            iks_indicator__name="vegetation_greenness"
        ).values_list("value", flat=True)
        self.assertTrue(soil)
        self.assertTrue(vegetation)
        self.assertNotIn(None, {label_soil_moisture(v) for v in soil})
        self.assertNotIn(None, {label_vegetation(v) for v in vegetation})

    def test_deactivates_any_other_active_form(self):
        """Two active forms merge into the public IKS aggregations — there is
        no single-active constraint to stop it."""
        existing = KoboForm.objects.create(
            uuid="real-form", name="Real", active=True
        )
        output = self.seed()
        existing.refresh_from_db()
        self.assertFalse(existing.active)
        self.assertIn("Deactivating", output)
        self.assertEqual(KoboForm.objects.filter(active=True).count(), 1)

    def test_attaches_photos_and_stages_the_files(self):
        from django.conf import settings

        self.seed()
        with_attachments = [
            data
            for data in KoboData.objects.all()
            if data.raw_data.get("_attachments")
        ]
        self.assertTrue(with_attachments)
        name = with_attachments[0].raw_data["_attachments"][0]["filename"]
        base = name.split("/")[-1]
        # IKSPhotoFileView serves by basename out of STORAGE_PATH, so the file
        # must actually be there or every photo URL 404s.
        self.assertTrue(
            os.path.exists(os.path.join(settings.STORAGE_PATH, base))
        )

    def test_no_photos_flag_skips_attachments(self):
        self.seed("--no-photos")
        self.assertFalse(
            any(
                data.raw_data.get("_attachments")
                for data in KoboData.objects.all()
            )
        )

    def test_submissions_span_the_whole_window(self):
        """D-13: not confined to the May-Jul band the IKS aggregations are
        hardcoded around, so the invariant figures stay visible as such."""
        self.seed()
        months = {
            data.submission_time.month for data in KoboData.objects.all()
        }
        self.assertGreater(len(months), 3)

    def test_is_idempotent(self):
        self.seed()
        first = (KoboData.objects.count(), IKSValue.objects.count())
        self.seed()
        self.assertEqual(
            (KoboData.objects.count(), IKSValue.objects.count()), first
        )

    def test_same_seed_reproduces_identical_submissions(self):
        self.seed("--seed", 7)
        first = list(
            KoboData.objects.order_by("kobo_id").values_list(
                "raw_data", flat=True
            )
        )
        KoboForm.objects.all().delete()
        self.seed("--seed", 7)
        second = list(
            KoboData.objects.order_by("kobo_id").values_list(
                "raw_data", flat=True
            )
        )
        self.assertEqual(first, second)

    def test_clean_removes_the_seeded_form_and_its_data(self):
        self.seed()
        other = KoboForm.objects.create(uuid="keep-me", name="Keep")
        call_command("generate_iks_seeder", "--clean")
        self.assertFalse(
            KoboForm.objects.filter(uuid="demo-iks-form").exists()
        )
        self.assertTrue(KoboForm.objects.filter(pk=other.pk).exists())
        self.assertEqual(KoboData.objects.count(), 0)
        self.assertEqual(IKSValue.objects.count(), 0)
