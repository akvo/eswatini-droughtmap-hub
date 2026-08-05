"""Filename parsing for a local pct-rank GeoTIFF archive.

No database: this is the layer that silently mislabels real data when it is
wrong, so it is worth testing on its own.
"""
import os
import tempfile

from django.test import SimpleTestCase

from api.v1.v1_publication.raster_archive import (
    indicator_from_path,
    scan_raster_archive,
)


class IndicatorFromPathTestCase(SimpleTestCase):
    def test_reads_the_indicator_from_the_directory(self):
        self.assertEqual(
            indicator_from_path(
                "/data/GeoTiffs/EVI2",
                "STEP_0303_EVI2_pct_rank_Eswatini_202604.tif",
            ),
            "evi2",
        )

    def test_reads_the_indicator_from_the_filename_alone(self):
        self.assertEqual(
            indicator_from_path(
                "/data", "STEP_0303_SPI_pct_rank_Eswatini_202604.tif"
            ),
            "spi",
        )

    def test_cdi_is_not_a_component_indicator(self):
        """The CDI composite lives in the same archive but is not one of the
        four components — mislabelling it would overwrite a component's
        values with the composite."""
        self.assertIsNone(
            indicator_from_path(
                "/data/GeoTiffs/CDI",
                "STEP_0303_CDI_pct_rank_Eswatini_202604.tif",
            )
        )

    def test_sm_does_not_match_inside_a_longer_token(self):
        """A bare substring test would label this SM."""
        self.assertIsNone(indicator_from_path("/data", "smoothed_202604.tif"))


class ScanRasterArchiveTestCase(SimpleTestCase):
    def _archive(self, tree):
        root = tempfile.mkdtemp()
        for relative in tree:
            path = os.path.join(root, relative)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").close()
        return root

    def test_maps_indicator_and_month_to_a_file(self):
        root = self._archive(
            [
                "EVI2/STEP_0303_EVI2_pct_rank_Eswatini_202604.tif",
                "EVI2/STEP_0303_EVI2_pct_rank_Eswatini_202605.tif",
                "SM/STEP_0303_SM_pct_rank_Eswatini_202604.tif",
            ]
        )
        archive = scan_raster_archive(root)
        self.assertEqual(len(archive), 3)
        self.assertIn(("evi2", "2026-04"), archive)
        self.assertIn(("evi2", "2026-05"), archive)
        self.assertIn(("sm", "2026-04"), archive)

    def test_ignores_the_cdi_directory(self):
        root = self._archive(
            [
                "CDI/STEP_0303_CDI_pct_rank_Eswatini_202604.tif",
                "ESI/STEP_0303_ESI_pct_rank_Eswatini_202604.tif",
            ]
        )
        self.assertEqual(
            set(scan_raster_archive(root)), {("esi", "2026-04")}
        )

    def test_explicit_cdi_finds_the_composite(self):
        """The CDI composite is NOT one of the four components, so it is
        absent from INDICATORS. Requiring membership made an explicit
        --category cdi scan return nothing at all, which the publication
        seeder reported as "no CDI rasters" against a full archive.
        """
        root = self._archive(
            [
                "CDI/STEP_0303_CDI_pct_rank_Eswatini_202604.tif",
                "CDI/STEP_0303_CDI_pct_rank_Eswatini_202605.tif",
                "ESI/STEP_0303_ESI_pct_rank_Eswatini_202604.tif",
            ]
        )
        archive = scan_raster_archive(root, "cdi")
        self.assertEqual(
            set(archive), {("cdi", "2026-04"), ("cdi", "2026-05")}
        )

    def test_explicit_indicator_does_not_sweep_in_siblings(self):
        """A single-indicator scan of a multi-indicator tree must stay in its
        own lane, or SPI values land in the ESI row."""
        root = self._archive(
            [
                "ESI/STEP_0303_ESI_pct_rank_Eswatini_202604.tif",
                "SPI/STEP_0303_SPI_pct_rank_Eswatini_202604.tif",
            ]
        )
        self.assertEqual(
            set(scan_raster_archive(root, "spi")), {("spi", "2026-04")}
        )

    def test_explicit_indicator_overrides_inference(self):
        """A single-indicator directory need not name the indicator in a way
        the inference can see."""
        root = self._archive(["rasters/pct_rank_202604.tif"])
        self.assertEqual(
            set(scan_raster_archive(root, "spi")), {("spi", "2026-04")}
        )

    def test_ignores_non_raster_files_and_unparseable_names(self):
        root = self._archive(
            [
                "ESI/STEP_0303_ESI_pct_rank_Eswatini_202604.tif",
                "ESI/notes.txt",
                "ESI/STEP_0303_ESI_pct_rank_Eswatini.tif",
                "ESI/STEP_0303_ESI_pct_rank_Eswatini_202613.tif",
            ]
        )
        # 202613 is not a month; accepting it would create a phantom period
        # that never matches a publication.
        self.assertEqual(
            set(scan_raster_archive(root)), {("esi", "2026-04")}
        )

    def test_accepts_the_tiff_suffix(self):
        root = self._archive(["esi_pct_rank_eswatini_202507.tiff"])
        self.assertEqual(
            set(scan_raster_archive(root)), {("esi", "2025-07")}
        )

    def test_duplicate_months_resolve_deterministically(self):
        root = self._archive(
            [
                "ESI/a_esi_202604.tif",
                "ESI/b_esi_202604.tif",
            ]
        )
        first = scan_raster_archive(root)
        second = scan_raster_archive(root)
        self.assertEqual(first, second)
        self.assertTrue(first[("esi", "2026-04")].endswith("a_esi_202604.tif"))

    def test_empty_archive_is_empty_not_an_error(self):
        self.assertEqual(scan_raster_archive(self._archive([])), {})
