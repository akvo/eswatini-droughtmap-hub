from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_jobs.models import Jobs, JobTypes
from api.v1.v1_publication.constants import CDIGeonodeCategory
from api.v1.v1_publication.models import Publication, PublicationGeonode


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class PublicationsSeederCacheSourceTestCase(TestCase):
    """
    `auto` prefers the cached resource list over the live catalogue. The two
    are the same data, but only the live one can be down — and when it is, the
    seeder creates nothing and the failure shows up pages away as an empty
    review queue.
    """

    def setUp(self):
        self._task_seq = 0
        for offset, geonode_id in enumerate([691, 690]):
            PublicationGeonode.objects.create(
                geonode_id=geonode_id,
                category=CDIGeonodeCategory.cdi,
                title=f"CDI {geonode_id}",
                year_month=date(2026, 5 - offset, 1),
                download_url=f"http://geonode:8000/d/{geonode_id}",
            )

    def _task_id(self, *args, **kwargs):
        self._task_seq += 1
        return f"cache-task-{self._task_seq}"

    def _run(self, *args):
        # One patch, not one per module: the seeder and utils both do
        # `import requests`, so they share the single module object and a
        # second patch of the same attribute would silently shadow the first.
        out = StringIO()
        with patch("requests.get") as mock_get, patch(
            "api.v1.v1_publication.management.commands."
            "generate_publications_seeder.async_task",
            side_effect=self._task_id,
        ):
            call_command(
                "generate_publications_seeder",
                "--repeat", 1,
                *args,
                stdout=out,
            )
        return out.getvalue(), mock_get

    def test_auto_prefers_the_cache_over_the_cdi_catalogue(self):
        output, mock_get = self._run()
        self.assertIn("Publication source: cache", output)
        # Component discovery still walks GeoNode — those categories are
        # barely cached in practice, so a cache-first lookup there would miss
        # and fall through anyway. It is timed out and failure-tolerant.
        # What must be gone is the CDI resource-list request.
        requested = [call.args[0] for call in mock_get.call_args_list]
        self.assertFalse(
            [url for url in requested if CDIGeonodeCategory.cdi in url],
            f"cache source still queried the CDI catalogue: {requested}",
        )

    def test_publications_are_created_from_the_cached_resources(self):
        self._run()
        self.assertEqual(
            sorted(
                Publication.objects.values_list("cdi_geonode_id", flat=True)
            ),
            [690, 691],
        )
        # Real data, so the raster still has to be downloaded and extracted;
        # the cache only replaces the catalogue lookup.
        queued = Jobs.objects.filter(type=JobTypes.download_geonode_dataset)
        self.assertEqual(
            sorted(job.info["filename"].split("_")[1] for job in queued),
            ["690", "691"],
        )

    def test_rows_without_a_download_url_are_not_used(self):
        """They could only ever produce the empty initial_values this
        ordering exists to avoid."""
        PublicationGeonode.objects.update(download_url="")
        output, mock_get = self._run()
        # Cache unusable -> auto falls through to the live catalogue.
        self.assertIn("Publication source: geonode", output)
        mock_get.assert_called()

    def test_explicit_cache_source_without_rows_fails_loudly(self):
        PublicationGeonode.objects.all().delete()
        with self.assertRaises(Exception) as ctx:
            self._run("--source", "cache")
        self.assertIn("sync_publication_geonodes", str(ctx.exception))

    def test_unreachable_geonode_does_not_abort_the_seeder(self):
        """Previously untimed and unhandled: a refused connection ended the
        run with a raw traceback part-way through."""
        import requests

        PublicationGeonode.objects.all().delete()
        out = StringIO()
        with patch(
            "api.v1.v1_publication.management.commands."
            "generate_publications_seeder.requests.get",
            side_effect=requests.ConnectionError("refused"),
        ):
            call_command(
                "generate_publications_seeder",
                "--source", "geonode", "--repeat", 1, stdout=out,
            )
        self.assertIn("GeoNode unreachable", out.getvalue())
        self.assertEqual(Publication.objects.count(), 0)
