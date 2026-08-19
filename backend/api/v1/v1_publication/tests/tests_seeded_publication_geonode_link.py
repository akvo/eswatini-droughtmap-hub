"""Every seeded publication resolves to a GeoNode row (DEMO-1 D-2).

The CDI publication list is `PublicationGeonode` joined to `Publication` on
`geonode_id == cdi_geonode_id`. Seeded rows used to be minted in a reserved
900000+ range with no matching cache row, so that join never hit: the list
offered "Start new publication" for months that already had a publication in
review on /validations. These tests pin the join, not the ids.
"""
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    DEMO_GEONODE_ID_BASE,
)
from api.v1.v1_publication.models import Publication, PublicationGeonode
from api.v1.v1_publication.utils import cached_geonode_id


@override_settings(TEST_ENV=True, USE_TZ=False, GEONODE_BASE_URL=None)
class GeonodeMonthKeyTestCase(TestCase):
    """Every reader keys on `<YYYY-MM>-01`; GeoNode's `date` is a full date."""

    def test_a_resource_dated_late_in_the_month_is_still_found(self):
        row = PublicationGeonode.objects.create(
            geonode_id=690,
            category=CDIGeonodeCategory.cdi,
            title="step_0303_cdi_pct_rank_eswatini_202601",
            year_month="2026-01-31",
        )
        row.refresh_from_db()
        self.assertEqual(row.year_month.day, 1)
        self.assertEqual(
            cached_geonode_id(CDIGeonodeCategory.cdi, "2026-01"), 690
        )


@override_settings(TEST_ENV=True, USE_TZ=False, GEONODE_BASE_URL=None)
class SeededPublicationGeonodeLinkTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def _seed(self):
        call_command(
            "generate_publications_seeder",
            "--source", "synthetic",
            "--repeat", 2,
            "--seed", 42,
            verbosity=0,
        )

    def test_every_seeded_publication_has_a_geonode_row(self):
        self._seed()
        publications = Publication.objects.filter(is_seeded=True)
        self.assertTrue(publications.exists())
        cached = set(
            PublicationGeonode.objects.values_list("geonode_id", flat=True)
        )
        for publication in publications:
            self.assertIn(publication.cdi_geonode_id, cached)

    def test_the_real_asset_wins_over_a_stand_in(self):
        """A month GeoNode already has must not get a second, demo row."""
        month = self._latest_seeded_month()
        PublicationGeonode.objects.create(
            geonode_id=707,
            category=CDIGeonodeCategory.cdi,
            title="step_0303_cdi_pct_rank_eswatini",
            year_month=f"{month}-01",
        )
        self._seed()
        publication = Publication.objects.get(year_month=f"{month}-01")
        self.assertEqual(publication.cdi_geonode_id, 707)
        self.assertEqual(
            PublicationGeonode.objects.filter(
                year_month=f"{month}-01"
            ).count(),
            1,
        )

    def test_stand_in_ids_are_derived_from_the_month_not_the_run(self):
        """Two runs over different ranges must not re-point one stub row."""
        self._seed()
        first = {
            publication.year_month: publication.cdi_geonode_id
            for publication in Publication.objects.filter(is_seeded=True)
        }
        call_command(
            "generate_publications_seeder",
            "--source", "synthetic",
            "--repeat", 4,
            "--seed", 42,
            verbosity=0,
        )
        for publication in Publication.objects.filter(is_seeded=True):
            if publication.year_month in first:
                self.assertEqual(
                    publication.cdi_geonode_id,
                    first[publication.year_month],
                )
            self.assertGreaterEqual(
                publication.cdi_geonode_id, DEMO_GEONODE_ID_BASE
            )
            row = PublicationGeonode.objects.get(
                geonode_id=publication.cdi_geonode_id
            )
            self.assertEqual(row.year_month, publication.year_month)

    def _latest_seeded_month(self) -> str:
        """The most recent month the seeder covers — last calendar month."""
        from datetime import datetime

        from dateutil.relativedelta import relativedelta

        now = datetime.now()
        previous = datetime(now.year, now.month, 1) - relativedelta(months=1)
        return previous.strftime("%Y-%m")
