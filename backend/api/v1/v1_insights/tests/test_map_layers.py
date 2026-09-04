"""The National Overview map layer contract (INS-3)."""
import json
import os
import tempfile
from datetime import date

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.v1.v1_indicators.constants import IndicatorSource
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_insights import map_layers
from api.v1.v1_insights.chirps_extract import (
    read_sidecar,
    sidecar_path,
    write_sidecar,
)
from api.v1.v1_insights.constants import (
    BUILDABLE,
    DESCRIPTIONS,
    LAYERS,
    REGION_PROPERTY,
    REGION_TOPOJSON,
)
from api.v1.v1_insights.map_layers import continuous_legend
from api.v1.v1_publication.constants import (
    AdministrationZones,
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationRaster,
)


class MapLayerContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Administration.objects.create(
            name="Mhlume",
            region="Lubombo",
            zone=AdministrationZones.WESTERN_LOWVELD.value,
        )
        self.other = Administration.objects.create(
            name="Lobamba",
            region="Hhohho",
            zone=AdministrationZones.HIGHVELD.value,
        )
        self.pub = Publication.objects.create(
            cdi_geonode_id=1,
            year_month=date(2026, 5, 1),
            due_date=date(2026, 5, 15),
            status=PublicationStatus.published,
            published_at=timezone.now(),
            initial_values=[],
            validated_values=[],
        )

    def url(self, key, query=""):
        return f"/api/v1/insights/map-layer/{key}{query}"

    # --- inventory ---------------------------------------------------------

    def test_map_data_lists_esi_not_temperature(self):
        """The tab shows a percentile rank, so it cannot read 'Temperature'."""
        response = self.client.get("/api/v1/insights/map-data")
        keys = [layer["key"] for layer in response.json()["layers"]]
        self.assertIn("esi", keys)
        self.assertNotIn("temperature", keys)

    def test_month_varying_flag_matches_the_data(self):
        """Regions and Agro-eco paint the D-class, so they DO vary by month.

        Only Land use and Population are genuinely time-invariant.
        """
        varying = {
            layer["key"] for layer in LAYERS if layer["monthVarying"]
        }
        self.assertEqual(
            varying,
            {"drought-class", "precipitation", "esi", "regions", "agro-eco"},
        )

    def test_every_month_varying_layer_actually_honours_the_month(self):
        """The flag and the builder signature must not drift.

        A layer advertised as month-varying whose builder ignores year_month
        silently pins the map to the latest publication while the date
        selector appears to work — which is exactly what happened once.
        """
        for key in sorted(BUILDABLE):
            varying = next(
                layer["monthVarying"] for layer in LAYERS
                if layer["key"] == key
            )
            with self.subTest(key=key):
                self.assertEqual(
                    key in map_layers._MONTHLY,
                    varying,
                    f"'{key}' is monthVarying={varying} but "
                    f"{'is not' if varying else 'is'} dispatched with a "
                    "month.",
                )

    def test_every_buildable_key_is_in_the_inventory(self):
        """A builder with no tab, or a tab with no builder, is a dead end."""
        inventory = {layer["key"] for layer in LAYERS}
        self.assertTrue(BUILDABLE.issubset(inventory))
        self.assertEqual(inventory - BUILDABLE, {"drought-class"})

    def test_unknown_layer_is_404(self):
        response = self.client.get(self.url("not-a-layer"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_every_buildable_key_returns_a_known_type(self):
        for key in sorted(BUILDABLE):
            with self.subTest(key=key):
                response = self.client.get(self.url(key))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn(
                    response.json()["type"],
                    {"choropleth", "image", "vector", "empty"},
                )

    # --- provisional badge (D-9) -------------------------------------------

    def test_provisional_is_true_while_is_placeholder_is_true(self):
        Indicator.objects.create(
            administration=self.admin,
            population=1000,
            source=IndicatorSource.HANDOVER_2026_07,
            is_placeholder=True,
        )
        payload = self.client.get(self.url("population")).json()
        self.assertEqual(payload["type"], "choropleth")
        self.assertTrue(payload["meta"]["provisional"])
        self.assertTrue(payload["meta"]["note"])

    def test_provisional_clears_itself_when_the_row_is_sourced(self):
        """The whole point of D-9: no code change clears the badge.

        PA-4 writes is_placeholder=False, and the badge must disappear on the
        strength of that alone.
        """
        indicator = Indicator.objects.create(
            administration=self.admin,
            population=1000,
            source=IndicatorSource.HANDOVER_2026_07,
            is_placeholder=True,
        )
        self.assertTrue(
            self.client.get(self.url("population")).json()["meta"][
                "provisional"
            ]
        )

        indicator.is_placeholder = False
        indicator.source = "WorldPop wpgp 2020"
        indicator.save()

        meta = self.client.get(self.url("population")).json()["meta"]
        self.assertNotIn("provisional", meta)
        self.assertEqual(meta["source"], "WorldPop wpgp 2020")

    def test_population_with_no_rows_is_empty_not_500(self):
        payload = self.client.get(self.url("population")).json()
        self.assertEqual(payload["type"], "empty")
        self.assertTrue(payload["reason"])

    # --- ESI ---------------------------------------------------------------

    def test_esi_reads_the_already_extracted_values(self):
        PublicationRaster.objects.create(
            publication=self.pub,
            indicator=RasterIndicatorTypes.esi,
            geonode_id=99,
            values=[
                {"administration_id": self.admin.id, "value": 0.4},
                {"administration_id": self.other.id, "value": 0.8},
            ],
        )
        payload = self.client.get(self.url("esi")).json()
        self.assertEqual(payload["type"], "choropleth")
        self.assertEqual(len(payload["data"]), 2)
        # Percentile rank, not degrees — the unit is what keeps the renamed
        # tab honest.
        self.assertEqual(payload["legend"]["unit"], "percentile rank")
        self.assertEqual(payload["legend"]["min"], 0.4)
        self.assertEqual(payload["legend"]["max"], 0.8)

    def test_esi_without_an_extracted_raster_is_empty(self):
        payload = self.client.get(self.url("esi")).json()
        self.assertEqual(payload["type"], "empty")

    def test_esi_ignores_unpublished_months(self):
        """An in-review month must not leak through a public endpoint."""
        draft = Publication.objects.create(
            cdi_geonode_id=2,
            year_month=date(2026, 6, 1),
            due_date=date(2026, 6, 15),
            status=PublicationStatus.in_review,
            initial_values=[],
        )
        PublicationRaster.objects.create(
            publication=draft,
            indicator=RasterIndicatorTypes.esi,
            geonode_id=100,
            values=[{"administration_id": self.admin.id, "value": 0.9}],
        )
        payload = self.client.get(self.url("esi")).json()
        self.assertEqual(payload["type"], "empty")

    # --- boundaries --------------------------------------------------------

    def _publish_categories(self, values):
        self.pub.validated_values = values
        self.pub.save()

    def test_regions_draws_region_polygons_not_tinkhundla(self):
        """The tab used to paint the region verdict onto all 59 Tinkhundla.

        A region read as one colour, but the boundaries on screen were still
        Inkhundla boundaries — so Regions and the default tab drew the same
        map in different palettes, and no region outline appeared anywhere.
        """
        third = Administration.objects.create(name="Sithobela",
                                              region="Lubombo")
        self._publish_categories([
            {"administration_id": self.admin.id, "category": 3},
            {"administration_id": third.id, "category": 3},
            {"administration_id": self.other.id, "category": 1},
        ])
        payload = self.client.get(self.url("regions")).json()

        self.assertEqual(payload["type"], "vector")
        self.assertEqual(payload["url"], "/api/v1/insights/geo/regions")
        # Joined on the geometry's own property, never on feature order.
        self.assertEqual(payload["property"], REGION_PROPERTY)
        # One row per region, not one per Inkhundla.
        self.assertEqual(len(payload["data"]), 2)
        # No hex: the D-class palette has one definition, in the frontend.
        self.assertEqual(payload["legend"], {"scheme": "drought"})
        self.assertNotIn("colors", payload["legend"])

        by_region = {r["key"]: r for r in payload["data"]}
        self.assertEqual(by_region["Lubombo"]["value"], 3)
        self.assertEqual(by_region["Lubombo"]["label"], "Lubombo")
        self.assertEqual(by_region["Lubombo"]["confidence"], 100)
        # A different region keeps its own verdict.
        self.assertEqual(by_region["Hhohho"]["value"], 1)

    def test_region_rows_key_on_the_geometry_property(self):
        """The join fails silently if these drift: every region paints grey.

        `region` is what the topojson carries and what Administration.region
        holds, so the two are asserted against each other here.
        """
        self._publish_categories(
            [{"administration_id": self.admin.id, "category": 3}]
        )
        payload = self.client.get(self.url("regions")).json()

        geometry = json.loads(
            open(
                os.path.join(settings.BASE_DIR, REGION_TOPOJSON)
            ).read()
        )
        available = {
            g["properties"][REGION_PROPERTY]
            for obj in geometry["objects"].values()
            for g in obj["geometries"]
        }
        for row in payload["data"]:
            self.assertIn(row["key"], available)

    def test_region_confidence_is_a_share_of_the_whole_region(self):
        """One of two Tinkhundla reporting is 50% agreement, not 100%."""
        Administration.objects.create(name="Sithobela", region="Lubombo")
        self._publish_categories(
            [{"administration_id": self.admin.id, "category": 3}]
        )
        payload = self.client.get(self.url("regions")).json()
        row = next(r for r in payload["data"] if r["key"] == "Lubombo")
        self.assertEqual(row["confidence"], 50)

    def test_geometry_endpoints_serve_committed_files(self):
        """Both used to depend on a deploy step; agro's no longer does.

        `generate_agro_geojson` wrote a gitignored artefact, so forgetting it
        left the tab 404ing with nothing in the repo to explain why. Both
        geometries are committed now, and this fails if either is removed.
        """
        for name in ("regions", "agro-eco"):
            response = self.client.get(f"/api/v1/insights/geo/{name}")
            self.assertEqual(
                response.status_code, status.HTTP_200_OK, msg=name
            )
            body = json.loads(b"".join(response.streaming_content))
            # Served as TopoJSON, which the frontend decodes itself.
            self.assertEqual(body["type"], "Topology", msg=name)
            # Degrees, not the source's Transverse Mercator metres — served
            # unprojected, Leaflet draws Eswatini off the African coast.
            lon, lat = body["transform"]["translate"]
            self.assertTrue(30 < lon < 33, msg=f"{name} lon {lon}")
            self.assertTrue(-28 < lat < -25, msg=f"{name} lat {lat}")

    def test_described_layers_cite_their_upstream_dataset(self):
        """The tooltip must name the dataset, not the upload label.

        `Indicator.source` is free text typed at upload time and currently
        reads "JRBA (2026-08)" for both exposure layers, while the handover
        CSVs record WorldPop and Dynamic World. Citing the stored label would
        publish an attribution we know to be wrong.
        """
        Indicator.objects.create(
            administration=self.admin,
            population=1000,
            land_use_dvi_agri=0.5,
            source="JRBA (2026-08)",
            is_placeholder=False,
        )
        expected = {
            "land-use": "Dynamic World",
            "population": "WorldPop",
        }
        for key, upstream in expected.items():
            meta = self.client.get(self.url(key)).json()["meta"]
            self.assertIn(upstream, meta["description"], msg=key)
            self.assertNotIn("JRBA", meta["description"], msg=key)

    def test_esi_description_does_not_claim_a_temperature(self):
        """The tab was labelled Temperature once; the raster is a rank."""
        description = DESCRIPTIONS["esi"]
        self.assertIn("percentile rank", description)
        self.assertIn("not degrees", description)

    def test_regions_without_a_published_map_is_empty(self):
        payload = self.client.get(self.url("regions")).json()
        self.assertEqual(payload["type"], "empty")

    def test_regions_follows_the_selected_month(self):
        """The date selector must actually move the aggregated map.

        This regressed once: the rollup always read the newest published
        month, so picking an older date changed the drought-class tab but
        left Regions and Agro-eco showing today's verdict.
        """
        self._publish_categories(
            [{"administration_id": self.admin.id, "category": 4}]
        )
        older = Publication.objects.create(
            cdi_geonode_id=7,
            year_month=date(2025, 11, 1),
            due_date=date(2025, 11, 15),
            status=PublicationStatus.published,
            published_at=timezone.now(),
            initial_values=[],
            validated_values=[
                {"administration_id": self.admin.id, "category": 1}
            ],
        )

        current = self.client.get(self.url("regions")).json()
        self.assertEqual(current["meta"]["asOf"], "2026-05-01")
        by_region = {r["key"]: r for r in current["data"]}
        self.assertEqual(by_region["Lubombo"]["value"], 4)

        past = self.client.get(
            self.url("regions", "?year_month=2025-11")
        ).json()
        self.assertEqual(past["meta"]["asOf"], "2025-11-01")
        by_region = {r["key"]: r for r in past["data"]}
        self.assertEqual(by_region["Lubombo"]["value"], 1)
        self.assertEqual(older.year_month.strftime("%Y-%m"), "2025-11")

    def test_agro_eco_follows_the_selected_month(self):
        self._publish_categories(
            [{"administration_id": self.admin.id, "category": 4}]
        )
        Publication.objects.create(
            cdi_geonode_id=8,
            year_month=date(2025, 11, 1),
            due_date=date(2025, 11, 15),
            status=PublicationStatus.published,
            published_at=timezone.now(),
            initial_values=[],
            validated_values=[
                {"administration_id": self.admin.id, "category": 2}
            ],
        )
        payload = self.client.get(
            self.url("agro-eco", "?year_month=2025-11")
        ).json()
        by_zone = {row["key"]: row for row in payload["data"]}
        # self.admin is Western Lowveld.
        self.assertEqual(by_zone["LW"]["value"], 2)
        self.assertEqual(payload["meta"]["asOf"], "2025-11-01")

    def test_agro_eco_paints_the_drought_class_per_zone(self):
        self._publish_categories([
            {"administration_id": self.admin.id, "category": 4},
            {"administration_id": self.other.id, "category": 2},
        ])
        payload = self.client.get(self.url("agro-eco")).json()
        self.assertEqual(payload["type"], "vector")
        # Joined on the property the geometry itself carries.
        self.assertEqual(payload["property"], "LEVEL1")
        self.assertEqual(payload["legend"], {"scheme": "drought"})

        by_zone = {row["key"]: row for row in payload["data"]}
        self.assertEqual(len(by_zone), 6)
        # self.admin is Western Lowveld (LW), self.other is Highveld (HV).
        self.assertEqual(by_zone["LW"]["value"], 4)
        self.assertEqual(by_zone["HV"]["value"], 2)
        self.assertEqual(by_zone["HV"]["label"], "Highveld")

    def test_agro_eco_states_that_zones_are_approximated(self):
        """Most Tinkhundla span several zones; the payload must say so."""
        self.assertIn(
            "dominant zone",
            self.client.get(self.url("agro-eco")).json()["meta"]["note"],
        )

    # --- year_month validation (§8) ----------------------------------------

    def test_year_month_rejects_traversal_and_nonsense(self):
        """This parameter reaches the filesystem, so it is validated first."""
        for bad in ["../../etc/passwd", "2026-13", "2026", "'; DROP", "x"]:
            with self.subTest(value=bad):
                response = self.client.get(
                    self.url("precipitation", f"?year_month={bad}")
                )
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )

    def test_year_month_accepts_a_real_month(self):
        response = self.client.get(
            self.url("precipitation", "?year_month=2026-05")
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_precipitation_without_a_stored_raster_is_empty(self):
        payload = self.client.get(self.url("precipitation")).json()
        self.assertEqual(payload["type"], "empty")

    def test_precipitation_is_a_choropleth_over_the_tinkhundla(self):
        """Not a pixel overlay: a bbox raster at national zoom read as noise.

        The extract is written beside the raster at fetch time, so this path
        never opens a GeoTIFF.
        """
        path = map_layers.chirps_monthly_path("2026-05")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rows = [
            {"administration_id": self.admin.id, "name": "Mhlume",
             "value": 8.3},
            {"administration_id": self.other.id, "name": "Lobamba",
             "value": 20.8},
        ]
        # The raster only has to exist; the layer reads the extract.
        open(path, "a").close()
        write_sidecar(path, rows)
        self.addCleanup(os.remove, sidecar_path(path))
        self.addCleanup(os.remove, path)

        payload = self.client.get(
            self.url("precipitation", "?year_month=2026-05")
        ).json()
        self.assertEqual(payload["type"], "choropleth")
        self.assertEqual(len(payload["data"]), 2)
        self.assertEqual(payload["legend"]["unit"], "mm")
        self.assertEqual(payload["legend"]["min"], 8.3)
        self.assertEqual(payload["legend"]["max"], 20.8)
        # No bounds, no image url — the render mode changed on purpose.
        self.assertNotIn("bounds", payload)
        self.assertNotIn("url", payload)


class LegendTests(TestCase):
    def test_continuous_legend_uses_the_data_range(self):
        legend = continuous_legend([0.2, 0.5, 0.9], "unit", ["#000", "#fff"])
        self.assertEqual((legend["min"], legend["max"]), (0.2, 0.9))

    def test_a_single_repeated_value_does_not_produce_a_zero_range(self):
        """A zero-width range would make the frontend divide by zero."""
        legend = continuous_legend([5, 5, 5], "unit", ["#000", "#fff"])
        self.assertLess(legend["min"], legend["max"])

    def test_all_null_values_have_no_legend(self):
        self.assertIsNone(
            continuous_legend([None, None], "unit", ["#000", "#fff"])
        )


class ChirpsSidecarTests(TestCase):
    """The extract that lets the web process avoid opening a GeoTIFF."""

    def test_sidecar_sits_beside_its_raster(self):
        self.assertEqual(
            sidecar_path("/x/ESW_CHIRPS_precip_mm_2026-06.tif"),
            "/x/ESW_CHIRPS_precip_mm_2026-06.json",
        )

    def test_round_trips_the_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            raster = os.path.join(tmp, "ESW_CHIRPS_precip_mm_2026-06.tif")
            rows = [{"administration_id": 1, "name": "Mhlume", "value": 8.3}]
            write_sidecar(raster, rows)
            self.assertEqual(read_sidecar(raster), rows)

    def test_a_month_with_no_extract_reads_as_none(self):
        """None, not an exception: the tab reports it as an empty layer."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                read_sidecar(os.path.join(tmp, "missing.tif"))
            )

    def test_a_corrupt_extract_reads_as_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            raster = os.path.join(tmp, "ESW_CHIRPS_precip_mm_2026-06.tif")
            with open(sidecar_path(raster), "w") as f:
                f.write("{not json")
            self.assertIsNone(read_sidecar(raster))

    def test_extract_is_json_serialisable_as_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            raster = os.path.join(tmp, "ESW_CHIRPS_precip_mm_2026-06.tif")
            path = write_sidecar(raster, [{"administration_id": 1,
                                           "value": 8.3}])
            with open(path) as f:
                self.assertEqual(json.load(f)[0]["value"], 8.3)
