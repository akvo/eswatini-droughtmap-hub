from datetime import date
from django.test import TestCase
from api.v1.v1_publication.models import PublicationGeonode
from api.v1.v1_publication.constants import CDIGeonodeCategory


class PublicationGeonodeModelTest(TestCase):
    """Tests for the PublicationGeonode DB cache model (D-1/D-2)."""

    def _make(self, **kwargs):
        defaults = dict(
            geonode_id=4021,
            category=CDIGeonodeCategory.cdi,
            title="step_0303_cdi_pct_rank_eswatini_202605",
            year_month=date(2026, 5, 1),
        )
        defaults.update(kwargs)
        return PublicationGeonode.objects.create(**defaults)

    def test_create_minimal_row(self):
        obj = self._make()
        self.assertEqual(obj.geonode_id, 4021)
        self.assertEqual(obj.category, CDIGeonodeCategory.cdi)
        self.assertEqual(obj.title, "step_0303_cdi_pct_rank_eswatini_202605")
        self.assertEqual(obj.year_month, date(2026, 5, 1))
        self.assertIsNone(obj.file_size)
        self.assertIsNone(obj.download_url)
        self.assertIsNotNone(obj.synced_at)

    def test_create_full_row(self):
        obj = self._make(
            detail_url=("https://geonode.example" "/catalogue/#/dataset/4021"),
            embed_url=(
                "https://geonode.example" "/datasets/geonode:step/embed"
            ),
            thumbnail_url=(
                "https://geonode.example" "/uploaded/thumbs/dataset.jpg"
            ),
            download_url=(
                "https://geonode.example"
                "/datasets/geonode:step/dataset_download"
            ),
            file_size=204800,
            raw={"pk": 4021, "title": "step_0303"},
        )
        self.assertEqual(obj.file_size, 204800)
        self.assertEqual(
            obj.download_url,
            (
                "https://geonode.example"
                "/datasets/geonode:step/dataset_download"
            ),
        )
        self.assertIsNotNone(obj.raw)

    def test_geonode_id_unique_constraint(self):
        self._make(geonode_id=9001)
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            self._make(geonode_id=9001)  # same geonode_id → must fail

    def test_update_or_create_upsert(self):
        self._make(geonode_id=7777, title="original")
        obj, created = PublicationGeonode.objects.update_or_create(
            geonode_id=7777,
            defaults={"title": "updated"},
        )
        self.assertFalse(created)
        self.assertEqual(obj.title, "updated")
        self.assertEqual(
            PublicationGeonode.objects.filter(geonode_id=7777).count(), 1
        )

    def test_db_table_name(self):
        self.assertEqual(
            PublicationGeonode._meta.db_table, "publication_geonodes"
        )

    def test_category_index_exists(self):
        index_fields = [
            list(idx.fields) for idx in PublicationGeonode._meta.indexes
        ]
        self.assertIn(["category", "year_month"], index_fields)
