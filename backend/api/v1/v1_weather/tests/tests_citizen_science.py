from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_jobs.constants import JobTypes
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_publication.models import Administration
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.citizen_science import (
    latest_reportable_month,
    period_label,
    shift_month,
)
from api.v1.v1_weather.models import CitizenScienceReading

HHUKWINI_ADM = 4588078
KWALUSENI_ADM = 2042786


@override_settings(USE_TZ=False, TEST_ENV=True)
class CitizenScienceTests(APITestCase):
    def setUp(self):
        self.hhukwini = Administration.objects.create(
            pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho"
        )
        self.kwaluseni = Administration.objects.create(
            pk=KWALUSENI_ADM, name="Kwaluseni", region="Manzini"
        )
        self.observer = SystemUser.objects._create_user(
            email="sipho@example.sz",
            password="unused",
            name="Sipho",
            role=UserRoleTypes.observer,
            administration=self.hhukwini,
            station_name="Hhukwini Community",
        )
        self.reviewer = SystemUser.objects._create_user(
            email="reviewer@example.com", password="pass", name="Rev"
        )
        self.admin_user = SystemUser.objects.create_superuser(
            name="admin", email="admin@example.com", password="adminpass"
        )
        self.period = latest_reportable_month()
        self.period_str = period_label(self.period)

    # -- helpers ----------------------------------------------------------
    def put_reading(self, payload, period=None):
        return self.client.put(
            reverse(
                "cs-reading-detail",
                kwargs={
                    "version": "v1",
                    "period": period or self.period_str,
                },
            ),
            payload,
            format="json",
        )

    def get_serving(self, administration_id, **params):
        return self.client.get(
            reverse(
                "weather-administration-citizen-science",
                kwargs={
                    "version": "v1",
                    "administration_id": administration_id,
                },
            ),
            params,
        )

    def seed_reading(self, months_ago=0, submitted=True, **values):
        return CitizenScienceReading.objects.create(
            administration=self.hhukwini,
            year_month=shift_month(self.period, -months_ago),
            submitted_at=timezone.now() if submitted else None,
            **values,
        )

    # -- observer upsert ---------------------------------------------------
    def test_put_draft_then_submit(self):
        self.client.force_authenticate(user=self.observer)
        response = self.put_reading(
            {"min_temperature": 12.1, "precipitation": 55}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            (data["filled"], data["of"], data["submitted"]), (2, 5, False)
        )
        response = self.put_reading(
            {"min_temperature": 12.0, "precipitation": 60, "submit": True}
        )
        self.assertTrue(response.json()["submitted"])
        reading = CitizenScienceReading.objects.get(
            administration=self.hhukwini, year_month=self.period
        )
        self.assertEqual(reading.precipitation, 60)
        self.assertIsNotNone(reading.submitted_at)
        # One row only — the PUT is an upsert
        self.assertEqual(CitizenScienceReading.objects.count(), 1)

    def test_put_out_of_range_warns_but_saves(self):
        self.client.force_authenticate(user=self.observer)
        response = self.put_reading({"precipitation": 5000, "submit": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["warnings"])
        self.assertEqual(
            CitizenScienceReading.objects.get(
                administration=self.hhukwini, year_month=self.period
            ).precipitation,
            5000,
        )

    def test_put_requires_observer_role(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.put_reading({"precipitation": 10})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_requires_auth(self):
        response = self.put_reading({"precipitation": 10})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- observer history --------------------------------------------------
    def test_history_counts_submitted_only(self):
        self.seed_reading(months_ago=1, precipitation=10)
        self.seed_reading(months_ago=2, precipitation=20)
        self.seed_reading(months_ago=3, submitted=False, precipitation=30)
        self.client.force_authenticate(user=self.observer)
        response = self.client.get(
            reverse("cs-reading-list", kwargs={"version": "v1"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["completeness"], {"reported": 2, "of": 12})
        self.assertEqual(data["station"]["label"], "Hhukwini Community")
        self.assertEqual(len(data["data"]), 3)  # drafts visible to owner

    # -- review-page serving ----------------------------------------------
    def test_serving_submitted_reading(self):
        self.seed_reading(precipitation=55, min_temperature=12.1)
        self.client.force_authenticate(user=self.reviewer)
        response = self.get_serving(HHUKWINI_ADM, period=self.period_str)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        values = {row["key"]: row["value"] for row in data["data"]}
        self.assertEqual(values["precipitation"], 55)
        self.assertIsNone(values["soil_moisture"])
        self.assertEqual(data["meta"]["network"], "citizen_science")
        self.assertEqual(data["meta"]["station"], "Hhukwini Community")

    def test_serving_no_reading_and_draft_invisible(self):
        self.seed_reading(submitted=False, precipitation=99)
        self.client.force_authenticate(user=self.reviewer)
        for admin_id in (HHUKWINI_ADM, KWALUSENI_ADM):
            data = self.get_serving(
                admin_id, period=self.period_str
            ).json()
            self.assertIsNone(data["data"])
            self.assertEqual(
                data["meta"]["reason"], "no_citizen_science_for_period"
            )

    def test_serving_requires_valid_period_and_auth(self):
        self.assertEqual(
            self.get_serving(HHUKWINI_ADM).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.client.force_authenticate(user=self.reviewer)
        self.assertEqual(
            self.get_serving(HHUKWINI_ADM).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.get_serving(HHUKWINI_ADM, period="2026-13").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_serving_history_lists_submitted_months_only(self):
        self.seed_reading(months_ago=0, precipitation=50)
        self.seed_reading(months_ago=2, precipitation=30)
        self.seed_reading(months_ago=1, submitted=False, precipitation=40)
        self.client.force_authenticate(user=self.reviewer)
        data = self.get_serving(
            HHUKWINI_ADM, period=self.period_str, history=12
        ).json()
        periods = [row["period"] for row in data["history"]]
        self.assertEqual(
            periods,
            [
                period_label(shift_month(self.period, -2)),
                period_label(self.period),
            ],
        )

    # -- admin network -----------------------------------------------------
    def test_admin_stations_stats_and_rows(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            reverse("cs-stations", kwargs={"version": "v1"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["stats"]["stations"], 1)
        self.assertEqual(data["stats"]["reporting_well"], 0)
        self.assertEqual(data["stats"]["at_risk"], 1)
        row = data["data"][0]
        self.assertEqual(row["completeness"], {"reported": 0, "of": 12})
        self.assertIsNone(row["last_submission"])
        # Station name, Inkhundla and region are three separate things —
        # the admin table shows all three, so the row must carry all three.
        self.assertEqual(row["label"], "Hhukwini Community")
        self.assertEqual(row["administration"], "Hhukwini")
        self.assertEqual(row["group"], "Hhohho")
        # 10 of 12 submitted -> reporting well, not at risk
        for months_ago in range(10):
            self.seed_reading(months_ago=months_ago, precipitation=1)
        data = self.client.get(
            reverse("cs-stations", kwargs={"version": "v1"})
        ).json()
        self.assertEqual(data["stats"]["reporting_well"], 1)
        self.assertEqual(data["stats"]["at_risk"], 0)
        self.assertEqual(
            data["data"][0]["last_submission"], self.period_str
        )

    def test_admin_endpoints_reject_observer(self):
        self.client.force_authenticate(user=self.observer)
        for name in ("cs-stations", "cs-export"):
            response = self.client.get(
                reverse(name, kwargs={"version": "v1"})
            )
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN
            )

    # -- reminders ---------------------------------------------------------
    def test_reminders_all_due_skips_submitted(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("cs-reminders", kwargs={"version": "v1"})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.json()["dispatched"], 1)
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_reminder).count(), 1
        )
        self.seed_reading(precipitation=5)  # last month now submitted
        self.assertEqual(
            self.client.post(url, {}, format="json").json()["dispatched"],
            0,
        )
        # Row-level nudge targets the observer regardless
        response = self.client.post(
            url, {"user_ids": [self.observer.id]}, format="json"
        )
        self.assertEqual(response.json()["dispatched"], 1)

    def test_fake_citizen_weather_seeder_idempotent(self):
        call_command(
            "fake_citizen_weather_seeder", "--coverage", "100",
            "--test", "true",
        )
        # Skips the Inkhundla that already has an observer (setUp's),
        # fills the uncovered one — passwordless, sensors recorded
        seeded = SystemUser.objects.get(
            role=UserRoleTypes.observer, administration=self.kwaluseni
        )
        self.assertFalse(seeded.has_usable_password())
        self.assertIn("rain_gauge", seeded.station_sensors)
        self.assertTrue(
            CitizenScienceReading.objects.filter(
                administration=self.kwaluseni, submitted_at__isnull=False
            ).exists()
        )
        observers = SystemUser.objects.filter(
            role=UserRoleTypes.observer
        ).count()
        readings = CitizenScienceReading.objects.count()
        call_command(
            "fake_citizen_weather_seeder", "--coverage", "100",
            "--test", "true",
        )
        self.assertEqual(
            SystemUser.objects.filter(role=UserRoleTypes.observer).count(),
            observers,
        )
        self.assertEqual(CitizenScienceReading.objects.count(), readings)

    def test_send_cs_reminders_command(self):
        out = StringIO()
        call_command("send_cs_reminders", stdout=out)
        self.assertIn("Dispatched 1 reminder(s)", out.getvalue())
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_reminder).count(), 1
        )

    # -- unified add station + observer -----------------------------------
    def test_create_observer_passwordless_with_welcome(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {
                "name": "New Observer",
                "email": "new@example.sz",
                "administration_id": KWALUSENI_ADM,
                "station_name": "Kwaluseni Community",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json()["welcome_email_sent"])
        observer = SystemUser.objects.get(email="new@example.sz")
        self.assertEqual(observer.role, UserRoleTypes.observer)
        self.assertEqual(observer.administration_id, KWALUSENI_ADM)
        self.assertFalse(observer.has_usable_password())
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 1
        )

    def test_create_observer_with_sensors_and_type(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {
                "name": "Sensor Observer",
                "email": "sensor@example.sz",
                "administration_id": KWALUSENI_ADM,
                "station_name": "Kwaluseni Community",
                "sensors": ["min_temp", "rain_gauge", "min_temp"],
                "station_type": "Manual gauge + digital thermometer",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        # deduped, order kept
        self.assertEqual(data["sensors"], ["min_temp", "rain_gauge"])
        self.assertEqual(
            data["station_type"], "Manual gauge + digital thermometer"
        )
        unknown = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {
                "name": "Bad Sensor",
                "email": "bad@example.sz",
                "administration_id": KWALUSENI_ADM,
                "station_name": "X",
                "sensors": ["laser_rangefinder"],
            },
            format="json",
        )
        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_observer_multipart_comma_joined_sensors(self):
        # Swagger UI's form-data mode sends the array as one comma string
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {
                "name": "Form Observer",
                "email": "form@example.sz",
                "administration_id": KWALUSENI_ADM,
                "station_name": "Manzini Station",
                "sensors": "min_temp,max_temp,rain_gauge,wind_speed",
                "station_type": "Davis Vantage Pro2",
                "send_welcome_email": "true",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(
            data["sensors"],
            ["min_temp", "max_temp", "rain_gauge", "wind_speed"],
        )
        self.assertTrue(data["welcome_email_sent"])

    def test_put_progress_counts_sensor_gated_fields_only(self):
        self.observer.station_sensors = [
            "min_temp",
            "rain_gauge",
            "wind_speed",
        ]
        self.observer.save(update_fields=["station_sensors"])
        self.client.force_authenticate(user=self.observer)
        response = self.put_reading(
            {"min_temperature": 12.1, "soil_temperature": 17.0}
        )
        data = response.json()
        # of = min_temp + rain_gauge (wind_speed has no reading field);
        # the soil value is DISCARDED with a warning — this station has
        # no soil sensor, so the reading can never carry one
        self.assertEqual((data["filled"], data["of"]), (1, 2))
        self.assertTrue(
            any("soil_temperature ignored" in w for w in data["warnings"])
        )
        reading = CitizenScienceReading.objects.get(
            administration=self.hhukwini, year_month=self.period
        )
        self.assertIsNone(reading.soil_temperature)
        self.assertEqual(reading.min_temperature, 12.1)

    def test_history_station_block_includes_sensors(self):
        self.observer.station_sensors = ["min_temp"]
        self.observer.station_type = "school-built"
        self.observer.save(update_fields=["station_sensors", "station_type"])
        self.client.force_authenticate(user=self.observer)
        station = self.client.get(
            reverse("cs-reading-list", kwargs={"version": "v1"})
        ).json()["station"]
        self.assertEqual(station["sensors"], ["min_temp"])
        self.assertEqual(station["station_type"], "school-built")

    def test_create_observer_without_welcome_email(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {
                "name": "Quiet Observer",
                "email": "quiet@example.sz",
                "administration_id": KWALUSENI_ADM,
                "station_name": "Kwaluseni Community",
                "send_welcome_email": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.json()["welcome_email_sent"])
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 0
        )

    def test_create_observer_rejects_taken_inkhundla_and_email(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("cs-stations", kwargs={"version": "v1"})
        taken_inkhundla = self.client.post(
            url,
            {
                "name": "Dup",
                "email": "dup@example.sz",
                "administration_id": HHUKWINI_ADM,  # already has an observer
                "station_name": "Dup Station",
            },
            format="json",
        )
        self.assertEqual(
            taken_inkhundla.status_code, status.HTTP_400_BAD_REQUEST
        )
        taken_email = self.client.post(
            url,
            {
                "name": "Dup",
                "email": self.observer.email,
                "administration_id": KWALUSENI_ADM,
                "station_name": "Dup Station",
            },
            format="json",
        )
        self.assertEqual(
            taken_email.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(
            SystemUser.objects.filter(role=UserRoleTypes.observer).count(),
            1,
        )

    def test_create_observer_requires_admin(self):
        self.client.force_authenticate(user=self.observer)
        response = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- WX-7: edit / reassign / archive -----------------------------------
    def detail_url(self, administration_id=HHUKWINI_ADM):
        return reverse(
            "cs-station-detail",
            kwargs={
                "version": "v1",
                "administration_id": administration_id,
            },
        )

    def test_patch_station_and_observer_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        # Edit station fields
        response = self.client.patch(
            self.detail_url(),
            {
                "station_name": "Hhukwini Upgraded",
                "station_type": "Davis Vantage Pro2",
                "sensors": ["min_temp", "max_temp", "rain_gauge"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["station_name"], "Hhukwini Upgraded")
        self.assertEqual(data["station_type"], "Davis Vantage Pro2")
        self.assertEqual(
            data["sensors"], ["min_temp", "max_temp", "rain_gauge"]
        )
        # Edit observer name only
        response = self.client.patch(
            self.detail_url(), {"name": "Sipho Dlamini"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["observer"]["name"], "Sipho Dlamini")
        # DB reflects both changes
        self.observer.refresh_from_db()
        self.assertEqual(self.observer.station_name, "Hhukwini Upgraded")
        self.assertEqual(self.observer.name, "Sipho Dlamini")
        # Network table also reflects it
        network = self.client.get(
            reverse("cs-stations", kwargs={"version": "v1"})
        ).json()
        row = next(r for r in network["data"]
                   if r["key"] == HHUKWINI_ADM)
        self.assertEqual(row["label"], "Hhukwini Upgraded")
        # No email job created
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 0
        )

    def test_patch_moves_station_and_leaves_readings_behind(self):
        # Readings are keyed by administration, not by observer (D-6), so a
        # move must not drag the old Inkhundla's climate record with it.
        CitizenScienceReading.objects.create(
            administration=self.hhukwini,
            year_month=self.period,
            min_temperature=11.0,
            submitted_at=timezone.now(),
        )
        empty = Administration.objects.create(
            pk=999001, name="Lobamba", region="Hhohho"
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            self.detail_url(),
            {"administration_id": empty.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The response carries the new key — the old URL is now a 404
        self.assertEqual(response.json()["administration_id"], empty.pk)
        self.observer.refresh_from_db()
        self.assertEqual(self.observer.administration_id, empty.pk)
        self.assertEqual(
            self.client.patch(
                self.detail_url(), {"name": "X"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        # History stayed with the Inkhundla it was reported for
        self.assertEqual(
            CitizenScienceReading.objects.filter(
                administration=self.hhukwini
            ).count(),
            1,
        )
        self.assertEqual(
            CitizenScienceReading.objects.filter(
                administration=empty
            ).count(),
            0,
        )

    def test_patch_rejects_move_to_an_occupied_inkhundla(self):
        SystemUser.objects._create_user(
            email="other@example.sz",
            password="unused",
            name="Other",
            role=UserRoleTypes.observer,
            administration=self.kwaluseni,
            station_name="Kwaluseni Community",
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            self.detail_url(),
            {"administration_id": KWALUSENI_ADM},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.observer.refresh_from_db()
        self.assertEqual(self.observer.administration_id, HHUKWINI_ADM)

    def test_patch_accepts_the_stations_own_inkhundla(self):
        # Saving the edit form without touching the dropdown posts the
        # current Inkhundla back — that is a no-op, not a clash with itself.
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            self.detail_url(),
            {"administration_id": HHUKWINI_ADM, "station_name": "Renamed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["administration_id"], HHUKWINI_ADM)
        self.assertEqual(response.json()["station_name"], "Renamed")

    def test_patch_rejects_taken_email_allows_own(self):
        self.client.force_authenticate(user=self.admin_user)
        # Resending the observer's own address is fine
        response = self.client.patch(
            self.detail_url(),
            {"email": self.observer.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Another user's email is rejected
        response = self.client.patch(
            self.detail_url(),
            {"email": self.admin_user.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Soft-deleted user's email is also rejected
        deleted = SystemUser.objects._create_user(
            email="gone@example.sz", password=None, name="Gone",
            role=UserRoleTypes.observer,
            administration=self.kwaluseni,
        )
        deleted.soft_delete()
        response = self.client.patch(
            self.detail_url(),
            {"email": "gone@example.sz"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_rejects_unknown_sensor_and_dedupes(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            self.detail_url(),
            {"sensors": ["laser_rangefinder"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(
            self.detail_url(),
            {"sensors": ["min_temp", "min_temp"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["sensors"], ["min_temp"])

    def test_patch_empty_body_rejected(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            self.detail_url(), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reassign_archives_old_creates_new(self):
        self.seed_reading(precipitation=55)
        readings_before = CitizenScienceReading.objects.filter(
            administration=self.hhukwini
        ).count()
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.detail_url(),
            {"name": "Thabo Nkosi", "email": "thabo@example.sz"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["observer"]["name"], "Thabo Nkosi")
        self.assertNotEqual(data["observer"]["id"], self.observer.id)
        # Station fields carried over
        self.assertEqual(data["station_name"], "Hhukwini Community")
        # Old observer is soft-deleted
        self.observer.refresh_from_db()
        self.assertIsNotNone(self.observer.deleted_at)
        # New observer is active
        new_obs = SystemUser.objects.get(email="thabo@example.sz")
        self.assertIsNone(new_obs.deleted_at)
        self.assertEqual(new_obs.administration_id, HHUKWINI_ADM)
        # Welcome email dispatched
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 1
        )
        # Readings untouched
        self.assertEqual(
            CitizenScienceReading.objects.filter(
                administration=self.hhukwini
            ).count(),
            readings_before,
        )

    def test_reassign_without_welcome_email(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.detail_url(),
            {
                "name": "Silent Swap",
                "email": "silent@example.sz",
                "send_welcome_email": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 0
        )

    def test_archive_removes_station_keeps_readings(self):
        self.seed_reading(precipitation=55)
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Network table no longer shows the station
        network = self.client.get(
            reverse("cs-stations", kwargs={"version": "v1"})
        ).json()
        self.assertEqual(network["stats"]["stations"], 0)
        self.assertEqual(len(network["data"]), 0)
        # Readings survive
        self.assertEqual(
            CitizenScienceReading.objects.filter(
                administration=self.hhukwini
            ).count(),
            1,
        )
        # Inkhundla is now free — create succeeds
        response = self.client.post(
            reverse("cs-stations", kwargs={"version": "v1"}),
            {
                "name": "New Person",
                "email": "newperson@example.sz",
                "administration_id": HHUKWINI_ADM,
                "station_name": "Hhukwini Reborn",
                "send_welcome_email": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_station_detail_rejects_non_admin(self):
        url = self.detail_url()
        # Observer gets 403
        self.client.force_authenticate(user=self.observer)
        self.assertEqual(
            self.client.patch(url, {}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(url, {}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        # Reviewer gets 403
        self.client.force_authenticate(user=self.reviewer)
        self.assertEqual(
            self.client.patch(url, {}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        # Unknown Inkhundla is 404 for admin
        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(
            self.client.patch(
                self.detail_url(999999), {"name": "x"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # -- export + admin CSV backfill --------------------------------------
    def test_export_csv(self):
        self.seed_reading(precipitation=55, notes="gauge overflowed")
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            reverse("cs-export", kwargs={"version": "v1"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("administration_id", content)
        self.assertIn("Hhukwini Community", content)

    def test_admin_csv_template_and_import_upsert(self):
        self.client.force_login(self.admin_user)
        template = self.client.get(reverse("admin:cs_reading_csv_template"))
        self.assertEqual(template.status_code, status.HTTP_200_OK)
        header = template.content.decode().splitlines()[0]

        def upload(precipitation):
            body = (
                f"{header}\n"
                f"{HHUKWINI_ADM},2025-11,10.5,29,{precipitation},,15,ok\n"
                f"999999,2025-11,1,2,3,,4,bad-admin\n"
            )
            return self.client.post(
                reverse("admin:cs_reading_import_csv"),
                {
                    "csv_file": SimpleUploadedFile(
                        "readings.csv", body.encode()
                    )
                },
                follow=True,
            )

        upload(precipitation=44)
        reading = CitizenScienceReading.objects.get(
            administration=self.hhukwini, year_month="2025-11-01"
        )
        self.assertEqual(reading.precipitation, 44)
        self.assertIsNotNone(reading.submitted_at)
        # unknown administration row skipped, not created
        self.assertEqual(CitizenScienceReading.objects.count(), 1)
        # re-import updates in place (no duplicate)
        upload(precipitation=77)
        reading.refresh_from_db()
        self.assertEqual(reading.precipitation, 77)
        self.assertEqual(CitizenScienceReading.objects.count(), 1)
