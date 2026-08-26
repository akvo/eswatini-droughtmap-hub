from datetime import date

from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_users.models import SystemUser as User
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

MBABANE = "0-20000-0-68391"
LUBOVANE = "0-20000-0-68394"
HHUKWINI_ADM = 4588078  # Hhohho
KWALUSENI_ADM = 2042786  # Manzini — no station in region


@override_settings(USE_TZ=False, TEST_ENV=True)
class WeatherEndpointTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            name="admin", email="admin@example.com", password="adminpass"
        )
        self.reviewer = User.objects._create_user(
            name="reviewer", email="reviewer@example.com", password="pass"
        )
        # the 0002 data migration seeds a source when WIS2_* env is set;
        # tests own their fixtures
        WeatherSource.objects.all().delete()
        self.source = WeatherSource.objects.create(
            base_url="http://wis2.test", collection_id="obs"
        )
        self.mbabane = WeatherStation.objects.create(
            source=self.source,
            wigos_id=MBABANE,
            name="MBABANE",
            region="Hhohho",
            latitude=-26.336,
            longitude=31.1427,
            elevation_m=1221,
        )
        self.lubovane = WeatherStation.objects.create(
            source=self.source,
            wigos_id=LUBOVANE,
            name="LUBOVANE",
            region="Lubombo",
            latitude=-26.7358,
            longitude=31.7022,
        )
        Administration.objects.create(
            pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho"
        )
        Administration.objects.create(
            pk=KWALUSENI_ADM, name="Kwaluseni", region="Manzini"
        )
        # April 2026 data for MBABANE only
        for day in (1, 2):
            StationDailyAggregate.objects.create(
                station=self.mbabane,
                date=date(2026, 4, day),
                parameter=WeatherParameter.precipitation,
                value=10.0 * day,
                readings_count=24,
            )
            StationDailyAggregate.objects.create(
                station=self.mbabane,
                date=date(2026, 4, day),
                parameter=WeatherParameter.tmin,
                value=13.0 + day,
                readings_count=24,
            )
            StationDailyAggregate.objects.create(
                station=self.mbabane,
                date=date(2026, 4, day),
                parameter=WeatherParameter.tmax,
                value=23.0 + day,
                readings_count=24,
            )

    # --- stations list -----------------------------------------------------

    def test_stations_list_public_omits_health_meta(self):
        response = self.client.get(
            reverse("weather-stations", kwargs={"version": "v1"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["data"]), 2)
        for item in body["data"]:
            self.assertNotIn("meta", item)
        self.assertEqual(body["meta"]["source"], "http://wis2.test")

    def test_stations_list_authenticated_includes_health_meta(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(
            reverse("weather-stations", kwargs={"version": "v1"})
        )
        body = response.json()
        mbabane = next(
            item for item in body["data"] if item["key"] == MBABANE
        )
        self.assertIn("status", mbabane["meta"])
        self.assertIn("completeness_30d", mbabane["meta"])
        self.assertEqual(mbabane["label"], "Mbabane")
        self.assertEqual(mbabane["group"], "Hhohho")

    # --- monthly series ----------------------------------------------------

    def test_monthly_precipitation_series(self):
        response = self.client.get(
            reverse(
                "weather-station-monthly",
                kwargs={"version": "v1", "wigos_id": MBABANE},
            ),
            {"parameter": "precipitation"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(
            body["data"], [{"period": "2026-04", "value": 30.0}]
        )
        self.assertEqual(body["meta"]["units"], "mm")
        self.assertEqual(body["meta"]["aggregation"], "monthly_sum_of_daily")
        self.assertEqual(body["meta"]["from"], "2026-04-01")
        self.assertEqual(body["meta"]["months_covered"], 1)

    def test_monthly_unknown_parameter_is_400(self):
        response = self.client.get(
            reverse(
                "weather-station-monthly",
                kwargs={"version": "v1", "wigos_id": MBABANE},
            ),
            {"parameter": "soil_moisture"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monthly_unknown_station_is_404(self):
        response = self.client.get(
            reverse(
                "weather-station-monthly",
                kwargs={"version": "v1", "wigos_id": "0-0-0-0"},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- per-administration latest (D-5 ladder) ----------------------------

    def test_administration_latest_requires_auth(self):
        response = self.client.get(
            reverse(
                "weather-administration-latest",
                kwargs={
                    "version": "v1",
                    "administration_id": HHUKWINI_ADM,
                },
            )
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_own_region_station_resolution(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(
            reverse(
                "weather-administration-latest",
                kwargs={
                    "version": "v1",
                    "administration_id": HHUKWINI_ADM,
                },
            )
        )
        body = response.json()
        self.assertEqual(body["group"], "Hhohho")
        self.assertEqual(body["meta"]["resolution"], "region_station")
        self.assertEqual(body["meta"]["station"], "Mbabane")
        self.assertEqual(body["meta"]["station_code"], "68391")
        self.assertEqual(body["meta"]["period"], "2026-04")
        values = {item["key"]: item["value"] for item in body["data"]}
        self.assertEqual(values["precipitation"], 30.0)
        self.assertEqual(values["min_temperature"], 14.5)
        self.assertEqual(values["max_temperature"], 24.5)
        # design row set (Figma 3317-56561): rows exist even without data,
        # value null renders as the "— —" empty state
        self.assertIsNone(values["air_temperature"])
        self.assertIsNone(values["relative_humidity"])
        self.assertIsNone(values["wind_speed"])
        soil = next(
            item for item in body["data"]
            if item["key"] == "soil_temperature"
        )
        self.assertIsNone(soil["value"])
        self.assertEqual(soil["meta"]["reason"], "pending_sensor")

    def test_manzini_uses_nearest_station_fallback(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(
            reverse(
                "weather-administration-latest",
                kwargs={
                    "version": "v1",
                    "administration_id": KWALUSENI_ADM,
                },
            )
        )
        body = response.json()
        self.assertEqual(body["group"], "Manzini")
        self.assertEqual(
            body["meta"]["resolution"], "nearest_station_fallback"
        )
        # LUBOVANE has no data, so the ladder lands on MBABANE
        self.assertEqual(body["meta"]["station"], "Mbabane")
        self.assertEqual(body["meta"]["station_region"], "Hhohho")
        self.assertGreater(body["meta"]["distance_km"], 0)
        self.assertIsNotNone(body["data"])

    def test_no_station_data_returns_explicit_empty_payload(self):
        StationDailyAggregate.objects.all().delete()
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(
            reverse(
                "weather-administration-latest",
                kwargs={
                    "version": "v1",
                    "administration_id": KWALUSENI_ADM,
                },
            )
        )
        body = response.json()
        self.assertIsNone(body["data"])
        self.assertEqual(
            body["meta"]["reason"], "no_station_data_for_period"
        )

    def test_unknown_administration_is_404(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(
            reverse(
                "weather-administration-latest",
                kwargs={"version": "v1", "administration_id": 999},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- source config -----------------------------------------------------

    def test_source_get_admin_only(self):
        url = reverse("weather-source", kwargs={"version": "v1"})
        self.client.force_authenticate(user=self.reviewer)
        self.assertEqual(
            self.client.get(url).status_code, status.HTTP_403_FORBIDDEN
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["base_url"], "http://wis2.test")

    def test_source_put_updates_active_source(self):
        url = reverse("weather-source", kwargs={"version": "v1"})
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            url, {"base_url": "http://new-wis2.test"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.source.refresh_from_db()
        self.assertEqual(self.source.base_url, "http://new-wis2.test")
