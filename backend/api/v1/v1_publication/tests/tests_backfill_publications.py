"""backfill_publications — the command run by hand on a live server.

Its whole value is what it refuses to do, so most of these assert absences:
no write without --apply, no invented classes without --source synthetic,
no second row for a month somebody is still working on.
"""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication


class BackfillPublicationsTests(TestCase):
    def existing(self, year_month, status=PublicationStatus.published):
        return Publication.objects.create(
            cdi_geonode_id=int(year_month.replace("-", "")),
            year_month=f"{year_month}-01",
            due_date=date(2026, 12, 31),
            status=status,
            initial_values=[],
            validated_values=[],
        )

    def run_command(self, *args, expect_error=False, **kwargs):
        out = StringIO()
        if expect_error:
            with self.assertRaises(CommandError) as caught:
                call_command(
                    "backfill_publications", *args, stdout=out, **kwargs
                )
            return str(caught.exception)
        call_command("backfill_publications", *args, stdout=out, **kwargs)
        return out.getvalue()

    def months(self):
        return sorted(
            p.year_month.strftime("%Y-%m") for p in Publication.objects.all()
        )

    # -- refusals ---------------------------------------------------------

    def test_reports_without_writing_by_default(self):
        output = self.run_command(
            "--from", "2026-01", "--to", "2026-02", "--source", "synthetic"
        )
        self.assertIn("Dry run", output)
        self.assertEqual(Publication.objects.count(), 0)

    def test_a_source_must_be_named(self):
        """No --source means no values, and argparse says so before any
        month is touched."""
        with self.assertRaises(CommandError):
            self.run_command("--from", "2026-01", "--to", "2026-02", "--apply")
        self.assertEqual(Publication.objects.count(), 0)

    def test_an_empty_archive_names_the_directory_and_the_keyword(self):
        """A --source that is not the keyword is read as a directory, so a
        typo has to say which of the two it failed as."""
        output = self.run_command(
            "--from", "2026-01", "--to", "2026-02",
            "--source", "/nonexistent",
            expect_error=True,
        )
        self.assertIn("No CDI pct-rank GeoTIFFs", output)
        self.assertIn("/nonexistent", output)
        self.assertIn("synthetic", output)
        self.assertEqual(Publication.objects.count(), 0)

    def test_rejects_a_malformed_month(self):
        with self.assertRaises(CommandError):
            self.run_command("--from", "Jan 2026", "--to", "2026-02")

    def test_rejects_a_reversed_range(self):
        with self.assertRaises(CommandError):
            self.run_command("--from", "2026-05", "--to", "2026-01")

    # -- skipping ---------------------------------------------------------

    def test_never_touches_a_month_already_in_review(self):
        """A month in review is unfinished work, not a gap — a second row
        for it would be a duplicate."""
        self.existing("2026-01", PublicationStatus.in_review)

        output = self.run_command(
            "--from", "2026-01", "--to", "2026-01",
            "--source", "synthetic", "--apply",
        )

        self.assertIn("skip — already In Review", output)
        self.assertEqual(Publication.objects.count(), 1)
        self.assertEqual(
            Publication.objects.get().status, PublicationStatus.in_review
        )

    def test_fills_only_the_gaps(self):
        self.existing("2026-01")
        self.existing("2026-03")

        self.run_command(
            "--from", "2026-01", "--to", "2026-04",
            "--source", "synthetic", "--apply",
        )

        self.assertEqual(
            self.months(), ["2026-01", "2026-02", "2026-03", "2026-04"]
        )

    # -- writing ----------------------------------------------------------

    def test_backfilled_months_publish_with_a_plain_narrative(self):
        self.run_command(
            "--from", "2026-02", "--to", "2026-02",
            "--source", "synthetic", "--apply",
        )

        publication = Publication.objects.get()
        self.assertEqual(publication.status, PublicationStatus.published)
        self.assertIsNotNone(publication.published_at)
        self.assertTrue(publication.validated_values)
        self.assertTrue(publication.is_seeded)
        # The hero injects this with dangerouslySetInnerHTML after a slice.
        self.assertNotIn("<", publication.narrative)
        self.assertIn("February 2026", publication.narrative)

    def test_rerunning_creates_nothing_further(self):
        args = (
            "--from", "2026-02", "--to", "2026-02",
            "--source", "synthetic", "--apply",
        )
        self.run_command(*args)
        self.run_command(*args)
        self.assertEqual(Publication.objects.count(), 1)
