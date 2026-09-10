"""SwaziMet historical station records via the admin CSV import (WX-11 D-13)."""
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

MBABANE = "0-20000-0-68391"
MOTI = "0-748-0-68384"
HEADER = "wigos_id,station_name,date,parameter,value,readings_count"


class StationHistoryAdminImportTests(TestCase):
    def setUp(self):
        self.admin_user = SystemUser.objects.create_superuser(
            name="admin", email="admin@example.com", password="adminpass"
        )
        WeatherSource.objects.all().delete()
        source = WeatherSource.objects.create(
            base_url="http://wis2.test", collection_id="obs"
        )
        self.mbabane = WeatherStation.objects.create(
            source=source,
            wigos_id=MBABANE,
            name="MBABANE",
            region="Hhohho",
            latitude=-26.336,
            longitude=31.1427,
        )
        self.moti = WeatherStation.objects.create(
            source=source,
            wigos_id=MOTI,
            name="MOTI",
            region="Shiselweni",
            latitude=-26.7042,
            longitude=31.4255,
        )
        self.client.force_login(self.admin_user)

    def _upload(self, *lines):
        body = "\n".join([HEADER, *lines]) + "\n"
        return self.client.post(
            reverse("admin:station_history_import_csv"),
            {"csv_file": SimpleUploadedFile("history.csv", body.encode())},
            follow=True,
        )

    def _message(self, response) -> str:
        return " ".join(str(m) for m in response.context["messages"])

    def test_template_matches_the_partner_pack(self):
        response = self.client.get(
            reverse("admin:station_history_csv_template")
        )
        self.assertEqual(response.status_code, 200)
        lines = response.content.decode().splitlines()
        self.assertEqual(lines[0], HEADER)
        # the example rows show a value row and an empty (missing) day
        self.assertIn("2023-01-01,precipitation,0.0,1", lines[1])
        self.assertTrue(any(line.endswith(",,") for line in lines[1:]))

    def test_import_page_lists_the_known_stations(self):
        response = self.client.get(
            reverse("admin:station_history_import_csv")
        )
        self.assertContains(response, MBABANE)
        self.assertContains(response, "MOTI")

    def test_rows_land_as_real_daily_values(self):
        response = self._upload(
            f"{MBABANE},MBABANE,2023-01-01,precipitation,12.6,1",
            f"{MBABANE},MBABANE,2023-01-01,tmax,27.4,1",
            f"{MBABANE},MBABANE,2023-01-01,tmin,16.2,1",
            f"{MOTI},MOTI,2023-01-01,precipitation,3.2,",
        )
        self.assertIn("Imported 4 station-days", self._message(response))
        rain = StationDailyAggregate.objects.get(
            station=self.mbabane,
            date=date(2023, 1, 1),
            parameter=WeatherParameter.precipitation,
        )
        self.assertEqual(rain.value, 12.6)
        self.assertFalse(rain.is_seeded)
        self.assertEqual(rain.readings_count, 1)
        self.assertEqual(rain.expected_count, 1)
        moti = StationDailyAggregate.objects.get(station=self.moti)
        self.assertEqual(moti.readings_count, 1)  # blank count -> 1

    def test_station_matched_by_name_when_wigos_id_is_blank(self):
        self._upload(",mbabane,2023-01-01,precipitation,5.0,1")
        self.assertEqual(
            StationDailyAggregate.objects.get(station=self.mbabane).value, 5.0
        )

    def test_empty_value_is_a_missing_day_not_zero(self):
        response = self._upload(f"{MBABANE},MBABANE,2023-01-03,precipitation,,")
        self.assertFalse(StationDailyAggregate.objects.exists())
        self.assertIn("1 empty values skipped", self._message(response))

    def test_existing_days_are_kept_not_overwritten(self):
        """A day the WIS2 ingester wrote must survive a history upload."""
        StationDailyAggregate.objects.create(
            station=self.mbabane,
            date=date(2026, 6, 1),
            parameter=WeatherParameter.precipitation,
            value=15.8,
            readings_count=24,
        )
        response = self._upload(
            f"{MBABANE},MBABANE,2026-06-01,precipitation,99.0,1",
            f"{MBABANE},MBABANE,2026-06-02,precipitation,1.0,1",
        )
        self.assertIn("Imported 1 station-days", self._message(response))
        self.assertIn("1 already present (kept)", self._message(response))
        self.assertEqual(
            StationDailyAggregate.objects.get(date=date(2026, 6, 1)).value,
            15.8,
        )

    def test_bad_rows_are_reported_and_good_rows_still_land(self):
        response = self._upload(
            f"{MBABANE},MBABANE,2023-01-01,precipitation,12.6,1",
            "0-0-0-0,NOWHERE,2023-01-01,precipitation,1.0,1",
            f"{MBABANE},MBABANE,2023-01-01,humidity,80,1",
            f"{MBABANE},MBABANE,01/02/2023,precipitation,1.0,1",
            f"{MBABANE},MBABANE,2023-01-02,precipitation,abc,1",
            f"{MBABANE},MBABANE,2023-01-02,precipitation,-4,1",
        )
        message = self._message(response)
        self.assertIn("Imported 1 station-days", message)
        self.assertIn("5 rows rejected", message)
        self.assertIn("unknown station", message)
        self.assertIn("not allowed", message)
        self.assertIn("YYYY-MM-DD", message)
        self.assertIn("not a number", message)
        self.assertIn("negative rainfall", message)
        self.assertEqual(StationDailyAggregate.objects.count(), 1)

    def test_import_requires_admin_login(self):
        self.client.logout()
        response = self.client.get(
            reverse("admin:station_history_import_csv")
        )
        self.assertEqual(response.status_code, 302)
