from datetime import date
from unittest.mock import patch

import requests
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_publication.constants import CDIGeonodeCategory
from api.v1.v1_publication.models import (
    Publication,
    PublicationGeonode,
    PublicationRaster,
)
from api.v1.v1_publication.utils import (
    attach_component_rasters,
    find_component_resource,
)


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class ComponentResourceCacheFallbackTestCase(TestCase):
    """
    The GeoNode catalogue API and the raster file host fail independently
    (D-7). Production hit exactly that on 2026-08-11: the CDI raster
    downloaded fine while every /api/v2/resources call timed out, so no
    component raster attached — and with no SPI raster the confidence score
    has no satellite side, which blanks the High/Medium/Low band on all 59
    Tinkhundla. The cached row was there the whole time.
    """

    def setUp(self):
        self.publication = Publication.objects.create(
            year_month=date(2026, 5, 1),
            cdi_geonode_id=691,
            initial_values=[{"administration_id": 1, "value": 0.9}],
            due_date=date(2026, 6, 1),
        )
        PublicationGeonode.objects.create(
            geonode_id=694,
            category=CDIGeonodeCategory.spi,
            title="SPI 2026-05",
            year_month=date(2026, 5, 1),
            download_url="http://geonode:8000/d/694",
        )

    def test_cached_row_is_used_without_touching_the_catalogue(self):
        with patch("api.v1.v1_publication.utils.requests.get") as mock_get:
            resource = find_component_resource(
                CDIGeonodeCategory.spi, "2026-05"
            )
        self.assertEqual(resource["pk"], 694)
        self.assertEqual(resource["download_url"], "http://geonode:8000/d/694")
        mock_get.assert_not_called()

    def test_a_timing_out_catalogue_no_longer_blocks_the_attach(self):
        with patch(
            "api.v1.v1_publication.utils.requests.get",
            side_effect=requests.ReadTimeout("read timed out"),
        ), patch(
            "api.v1.v1_publication.utils.async_task", return_value="t-1"
        ):
            attached = attach_component_rasters(self.publication)

        # Only SPI is cached, so only SPI attaches; the other three time out
        # and are skipped exactly as before.
        self.assertEqual(attached, ["spi"])
        raster = PublicationRaster.objects.get(publication=self.publication)
        self.assertEqual(raster.indicator, "spi")
        self.assertEqual(raster.geonode_id, 694)

    def test_a_month_with_no_cached_row_still_falls_back_to_the_network(self):
        with patch(
            "api.v1.v1_publication.utils.requests.get"
        ) as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "total": 1,
                "page_size": 20,
                "resources": [{
                    "pk": 777,
                    "date": "2026-06-15T00:00:00Z",
                    "download_url": "http://geonode:8000/d/777",
                }],
            }
            resource = find_component_resource(
                CDIGeonodeCategory.spi, "2026-06"
            )
        self.assertEqual(resource["pk"], 777)
        mock_get.assert_called()

    def test_a_cached_row_without_a_download_url_is_ignored(self):
        PublicationGeonode.objects.update(download_url="")
        with patch(
            "api.v1.v1_publication.utils.requests.get",
            side_effect=requests.ReadTimeout("read timed out"),
        ):
            self.assertIsNone(
                find_component_resource(CDIGeonodeCategory.spi, "2026-05")
            )
