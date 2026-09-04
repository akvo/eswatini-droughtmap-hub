"""The hero description a seeded publication publishes.

HeroSection does `summary.slice(0, OVERVIEW_NARRATIVE_MAX_CHARS)` and hands
the result to `dangerouslySetInnerHTML`, so this string is injected as markup
after a blind character cut. Everything asserted here is about surviving that:
no tags to cut through, no length to be cut at, and no fabricated person to
put on a public page.
"""
from datetime import date

from django.test import TestCase

from api.v1.v1_publication.constants import (
    DroughtCategory,
    NARRATIVE_MAX_CHARS,
    PublicationStatus,
)
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.utils import generate_narrative, squish


class SeededNarrativeTests(TestCase):
    def publication(self, categories, year_month=date(2026, 5, 1)):
        return Publication.objects.create(
            cdi_geonode_id=abs(hash(str(categories))) % 100000,
            year_month=year_month,
            due_date=year_month,
            status=PublicationStatus.published,
            initial_values=[],
            validated_values=[
                {"administration_id": i, "value": 0.1, "category": category}
                for i, category in enumerate(categories, start=1)
            ],
        )

    def test_carries_no_markup(self):
        """It is injected with dangerouslySetInnerHTML after a slice, so a
        tag would be cut in half and rendered broken."""
        narrative = generate_narrative(
            self.publication([DroughtCategory.normal] * 3)
        )
        self.assertNotIn("<", narrative)
        self.assertNotIn(">", narrative)

    def test_fits_under_the_hero_ceiling(self):
        narrative = generate_narrative(
            self.publication([DroughtCategory.d0] * 59)
        )
        self.assertLessEqual(len(narrative), NARRATIVE_MAX_CHARS)

    def test_describes_the_classes_actually_published(self):
        narrative = generate_narrative(
            self.publication(
                [DroughtCategory.normal] * 2 + [DroughtCategory.d1]
            )
        )
        self.assertIn("May 2026", narrative)
        self.assertIn("3 Tinkhundla", narrative)
        self.assertIn("2 wet/normal conditions", narrative)
        # The scale is written D1 everywhere else in the product; a flat
        # .lower() on the label renders it "d1".
        self.assertIn("1 D1 moderate drought", narrative)

    def test_no_data_rows_are_not_counted_as_a_class(self):
        """-9999 is raster output where the CDI had no signal, never a
        decision — so it must not appear as a seventh class in the count."""
        narrative = generate_narrative(
            self.publication(
                [DroughtCategory.normal, DroughtCategory.none, None]
            )
        )
        self.assertIn("1 Tinkhundla", narrative)
        self.assertNotIn("No Data", narrative)

    def test_a_month_with_no_classes_says_so(self):
        narrative = generate_narrative(
            self.publication([DroughtCategory.none])
        )
        self.assertIn("No Inkhundla", narrative)
        self.assertLessEqual(len(narrative), NARRATIVE_MAX_CHARS)

    def test_squish_collapses_whitespace_and_cuts_on_a_word(self):
        self.assertEqual(squish("  a\n\n b  c ", 80), "a b c")
        cut = squish("alpha beta gamma delta", 12)
        self.assertLessEqual(len(cut), 13)  # +1 for the ellipsis
        self.assertTrue(cut.endswith("…"))
        self.assertNotIn("gamm…", cut)
