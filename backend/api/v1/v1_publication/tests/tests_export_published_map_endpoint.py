import geopandas as gpd
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError
from PIL import Image
from zipfile import ZipFile
from io import BytesIO
from unittest.mock import patch
from shapely.geometry import Point, Polygon
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import DroughtCategory, PublicationStatus


@override_settings(USE_TZ=False, TEST_ENV=True)
class ExportMapAPITest(APITestCase):
    def setUp(self):
        """
        Set up the test environment.
        """
        # Create a mock GeoDataFrame
        self.mock_gdf = gpd.GeoDataFrame({
            "name": ["Area1", "Area2"],
            "category": [0, 1],
            "geometry": [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),  # Valid polygon
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])   # Valid polygon
            ],
        })

        # Set a valid CRS for the GeoDataFrame
        self.mock_gdf.set_crs("EPSG:4326", inplace=True)

        self.published = Publication.objects.create(
            year_month="2025-02-01",
            cdi_geonode_id=44,
            due_date="2025-03-29",
            initial_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d4},
            ],
            validated_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d1},
            ],
            status=PublicationStatus.published,
            narrative="Lorem ipsum dolor amet...",
            published_at=timezone.now(),
        )
        self.url = reverse(
            "map-export", kwargs={"version": "v1", "pk": self.published.id}
        )

    def _debug_extent(self, gdf):
        """
        Print the bounding box and extent of the GeoDataFrame for debugging.
        """
        bounds = gdf.total_bounds
        print(f"Bounding box: {bounds}")
        print(f"Width: {bounds[2] - bounds[0]}, Height: {bounds[3] - bounds[1]}")

    @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    def test_export_geojson(self, mock_load_gdf):
        """
        Test exporting the map as GeoJSON.
        """
        mock_load_gdf.return_value = self.mock_gdf

        # Create a GET request
        response = self.client.get(f"{self.url}?export_type=geojson")

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn(
            "cdi_map_2025-02.geojson",
            response["Content-Disposition"]
        )

        # Check the content
        geojson_data = response.content.decode("utf-8")
        self.assertIn('"type": "FeatureCollection"', geojson_data)

    @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    def test_export_shapefile(self, mock_load_gdf):
        """
        Test exporting the map as a Shapefile (zipped).
        """
        mock_load_gdf.return_value = self.mock_gdf

        # Create a GET request
        response = self.client.get(f"{self.url}?export_type=shapefile")

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("cdi_map_2025-02.zip", response["Content-Disposition"])

        # Check the content (ensure it's a valid zip file)

        zip_file = ZipFile(BytesIO(response.content))
        self.assertIn("cdi_map_2025-02.shp", zip_file.namelist())
        self.assertIn("cdi_map_2025-02.shx", zip_file.namelist())
        self.assertIn("cdi_map_2025-02.dbf", zip_file.namelist())

    # @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    # def test_export_png(self, mock_load_gdf):
    #     """
    #     Test exporting the map as a PNG image.
    #     """
    #     mock_load_gdf.return_value = self.mock_gdf

    #     # Debug the extent
    #     self._debug_extent(self.mock_gdf)

    #     # Create a GET request
    #     response = self.client.get(f"{self.url}?export_type=png")
    #     print(response.data)

        # # Validate the response
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response["Content-Type"], "image/png")
        # self.assertIn("cdi_map_2025-02.png", response["Content-Disposition"])

        # # Check the content (ensure it's a valid PNG image)
        # img = Image.open(BytesIO(response.content))
        # self.assertEqual(img.format, "PNG")

    def test_invalid_format(self):
        """
        Test handling of an invalid export format.
        """
        # Create a GET request with an invalid format
        response = self.client.get(f"{self.url}?export_type=invalid")
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_default_format(self):
        """
        Test default export format (GeoJSON).
        """
        # Create a GET request without specifying a format
        response = self.client.get(self.url)

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/json")
