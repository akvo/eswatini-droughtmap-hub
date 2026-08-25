import io

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase
from rest_framework.exceptions import ValidationError

from api.v1.v1_indicators import parsers, uploads
from api.v1.v1_indicators.constants import UploadStatus
from api.v1.v1_indicators.datasets import DATASETS, lookup, normalise_header
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_publication.models import Administration
from api.v1.v1_users.models import SystemUser


def csv_file(text, name="upload.csv"):
    return SimpleUploadedFile(name, text.encode("utf-8"), "text/csv")


class RegistryTestCase(TestCase):
    def test_every_field_exists_on_indicator(self):
        columns = {f.name for f in Indicator._meta.get_fields()}
        for definition in DATASETS.values():
            self.assertIn(definition.field, columns, definition.slug)

    def test_registry_ranges_match_db_constraints(self):
        self.assertEqual(DATASETS["ipc-phase"].minimum, 1)
        self.assertEqual(DATASETS["ipc-phase"].maximum, 5)
        self.assertEqual(DATASETS["land-use-dvi-agri"].maximum, 1)

    def test_header_normalisation(self):
        self.assertEqual(normalise_header("  Water  Demand "), "water_demand")
        self.assertEqual(normalise_header("IPC-Phase"), "ipc_phase")
        self.assertEqual(lookup("Under Five").field, "under_five")
        self.assertIsNone(lookup("households"))


class ParserTestCase(TestCase):
    def setUp(self):
        self.a = Administration.objects.create(name="Hhukwini", region="H")
        self.b = Administration.objects.create(name="Lobamba", region="H")
        self.admins = [self.a, self.b]

    def parse(self, text):
        return parsers.parse(io.BytesIO(text.encode("utf-8")), self.admins)

    def test_header_declares_the_dataset(self):
        reports = self.parse(
            "administration_id,inkhundla_name,water_demand\n"
            f"{self.a.id},Hhukwini,120\n"
        )
        self.assertEqual(list(reports), ["water_demand"])

    def test_multi_column_yields_one_report_each(self):
        reports = self.parse(
            "administration_id,under_five,elderly\n"
            f"{self.a.id},10,4\n{self.b.id},20,8\n"
        )
        self.assertEqual(sorted(reports), ["elderly", "under_five"])
        self.assertEqual(len(reports["under_five"]["diff"]), 2)

    def test_unknown_column_is_ignored_and_reported(self):
        reports = self.parse(
            "administration_id,population,households\n"
            f"{self.a.id},100,55\n"
        )
        self.assertEqual(list(reports), ["population"])
        codes = [w["code"] for w in reports["population"]["warnings"]]
        self.assertIn("ignored_columns", codes)

    def test_no_recognised_column_returns_nothing(self):
        self.assertEqual(
            self.parse(f"administration_id,households\n{self.a.id},5\n"), {}
        )

    def test_blank_is_skipped_not_zero(self):
        reports = self.parse(
            "administration_id,cattle\n"
            f"{self.a.id},\n{self.b.id},7\n"
        )
        report = reports["cattle"]
        self.assertEqual(report["blank"], 1)
        self.assertEqual([r["after"] for r in report["diff"]], [7])

    def test_out_of_range_is_an_error(self):
        report = self.parse(
            f"administration_id,ipc_phase\n{self.a.id},7\n"
        )["ipc_phase"]
        self.assertEqual(report["errors"][0]["code"], "out_of_range")
        self.assertEqual(report["errors"][0]["column"], "ipc_phase")

    def test_non_numeric_is_an_error(self):
        report = self.parse(
            f"administration_id,population\n{self.a.id},n/a\n"
        )["population"]
        self.assertEqual(report["error_total"], 1)

    def test_unknown_inkhundla_named(self):
        report = self.parse(
            "inkhundla_name,population\nMbabane West,10\n"
        )["population"]
        self.assertIn("does not match", report["errors"][0]["detail"])

    def test_id_and_name_disagreement_is_an_error(self):
        report = self.parse(
            "administration_id,inkhundla_name,population\n"
            f"{self.a.id},Lobamba,10\n"
        )["population"]
        self.assertEqual(
            report["errors"][0]["code"], "unknown_administration"
        )
        self.assertIn("sorted", report["errors"][0]["detail"])

    def test_name_only_matching_is_tolerant(self):
        report = self.parse(
            "inkhundla_name,population\n  hhukwini \n".replace(
                "\n  hhukwini \n", "\n  hhukwini ,42\n"
            )
        )["population"]
        self.assertEqual(report["diff"][0]["after"], 42)

    def test_duplicate_row_is_an_error(self):
        report = self.parse(
            "administration_id,population\n"
            f"{self.a.id},1\n{self.a.id},2\n"
        )["population"]
        self.assertEqual(
            report["errors"][0]["code"], "duplicate_administration"
        )

    def test_bom_is_handled(self):
        raw = ("administration_id,population\n"
               f"{self.a.id},5\n").encode("utf-8-sig")
        reports = parsers.parse(io.BytesIO(raw), self.admins)
        self.assertEqual(list(reports), ["population"])

    def test_too_many_rows_rejected(self):
        body = "".join(
            f"{self.a.id},1\n" for _ in range(parsers.MAX_ROWS + 1)
        )
        with self.assertRaises(parsers.ParseError):
            self.parse("administration_id,population\n" + body)

    def test_missing_key_column_rejected(self):
        with self.assertRaises(parsers.ParseError):
            self.parse("population\n5\n")

    def test_before_reflects_stored_value(self):
        Indicator.objects.create(administration=self.a, population=99)
        report = self.parse(
            f"administration_id,population\n{self.a.id},120\n"
        )["population"]
        self.assertEqual(report["diff"][0]["before"], 99)


class UploadFlowTestCase(TestCase):
    def setUp(self):
        self.a = Administration.objects.create(name="Hhukwini", region="H")
        self.b = Administration.objects.create(name="Lobamba", region="H")
        self.user = SystemUser.objects.create(
            email="op@example.org", name="Op"
        )

    def make(self, text, source="CSO census", as_of="2024-01-01"):
        return uploads.create_uploads(
            csv_file(text), source, as_of, self.user
        )

    def test_validate_writes_nothing_to_indicator(self):
        created = self.make(
            f"administration_id,population\n{self.a.id},100\n"
        )
        self.assertEqual(created[0].status, UploadStatus.validated)
        self.assertFalse(Indicator.objects.exists())

    def test_xlsx_rejected_with_instructions(self):
        with self.assertRaises(ValidationError) as ctx:
            uploads.create_uploads(
                SimpleUploadedFile("a.xlsx", b"x"), "s", "2024-01-01",
                self.user,
            )
        self.assertIn("Save As", str(ctx.exception.detail))

    def test_siblings_share_a_checksum(self):
        created = self.make(
            f"administration_id,under_five,elderly\n{self.a.id},5,2\n"
        )
        self.assertEqual(len(created), 2)
        self.assertEqual(len({u.checksum for u in created}), 1)

    def test_one_bad_column_does_not_block_its_sibling(self):
        created = self.make(
            f"administration_id,under_five,elderly\n{self.a.id},5,oops\n"
        )
        by_slug = {u.dataset: u.status for u in created}
        self.assertEqual(by_slug["under-five"], UploadStatus.validated)
        self.assertEqual(by_slug["elderly"], UploadStatus.rejected)

    def test_no_recognised_column_is_stored_as_rejected(self):
        created = self.make(f"administration_id,households\n{self.a.id},5\n")
        self.assertEqual(created[0].status, UploadStatus.rejected)
        self.assertEqual(
            created[0].report["errors"][0]["code"], "no_dataset_column"
        )

    def test_apply_writes_values_and_provenance(self):
        upload = self.make(
            f"administration_id,population\n{self.a.id},1234\n"
        )[0]
        result = uploads.apply_upload(upload, self.user)
        indicator = Indicator.objects.get(administration=self.a)
        self.assertEqual(result.written, 1)
        self.assertEqual(indicator.population, 1234)
        self.assertFalse(indicator.is_placeholder)
        self.assertEqual(indicator.source, "CSO census (2024-01)")
        self.assertEqual(str(indicator.as_of), "2024-01-01")

    def test_apply_leaves_blank_tinkhundla_untouched(self):
        Indicator.objects.create(administration=self.b, population=7)
        upload = self.make(
            "administration_id,population\n"
            f"{self.a.id},50\n{self.b.id},\n"
        )[0]
        uploads.apply_upload(upload, self.user)
        self.assertEqual(
            Indicator.objects.get(administration=self.b).population, 7
        )

    def test_apply_is_idempotent(self):
        upload = self.make(
            f"administration_id,population\n{self.a.id},10\n"
        )[0]
        uploads.apply_upload(upload, self.user)
        upload.refresh_from_db()
        upload.status = UploadStatus.validated
        upload.save(update_fields=["status"])
        uploads.apply_upload(upload, self.user)
        self.assertEqual(
            Indicator.objects.get(administration=self.a).population, 10
        )

    def test_apply_refuses_non_validated(self):
        upload = self.make(
            f"administration_id,population\n{self.a.id},10\n"
        )[0]
        uploads.apply_upload(upload, self.user)
        with self.assertRaises(ValidationError):
            uploads.apply_upload(upload, self.user)

    def test_previous_applied_becomes_superseded(self):
        first = self.make(
            f"administration_id,population\n{self.a.id},10\n"
        )[0]
        uploads.apply_upload(first, self.user)
        second = self.make(
            f"administration_id,population\n{self.a.id},20\n"
        )[0]
        uploads.apply_upload(second, self.user)
        first.refresh_from_db()
        self.assertEqual(first.status, UploadStatus.superseded)

    def test_revert_restores_and_is_append_only(self):
        Indicator.objects.create(administration=self.a, population=5)
        upload = self.make(
            f"administration_id,population\n{self.a.id},900\n"
        )[0]
        uploads.apply_upload(upload, self.user)
        self.assertEqual(
            Indicator.objects.get(administration=self.a).population, 900
        )
        reversal = uploads.revert_upload(upload, self.user)
        self.assertEqual(
            Indicator.objects.get(administration=self.a).population, 5
        )
        self.assertNotEqual(reversal.pk, upload.pk)
        self.assertEqual(reversal.status, UploadStatus.applied)

    def test_revert_of_null_before_uses_column_default(self):
        """An eligibility column is NOT NULL with default 0, so replaying a
        None `before` must not raise IntegrityError."""
        upload = self.make(
            f"administration_id,under_five\n{self.a.id},40\n"
        )[0]
        uploads.apply_upload(upload, self.user)
        uploads.revert_upload(upload, self.user)
        self.assertEqual(
            Indicator.objects.get(administration=self.a).under_five, 0
        )

    def test_file_is_stored_and_retrievable(self):
        upload = self.make(
            f"administration_id,population\n{self.a.id},10\n"
        )[0]
        self.assertTrue(upload.file.name.startswith("datasets/"))
        upload.file.open("rb")
        self.assertIn(b"population", upload.file.read())


class SeederGuardTestCase(TestCase):
    def test_seeder_leaves_applied_values_alone(self):
        adm = Administration.objects.create(name="Hhukwini", region="H")
        Indicator.objects.create(
            administration=adm,
            population=4242,
            source="CSO census (2024-01)",
            is_placeholder=False,
        )
        call_command("generate_indicators_seeder", "--test", True)
        indicator = Indicator.objects.get(administration=adm)
        self.assertEqual(indicator.population, 4242)
        self.assertFalse(indicator.is_placeholder)


class EmptyColumnTestCase(TestCase):
    """D-15: the template carries every dataset column, so an operator who
    fills one must not generate ten empty upload rows to clear by hand."""

    def setUp(self):
        self.a = Administration.objects.create(name="Hhukwini", region="H")
        self.user = SystemUser.objects.create(
            email="op2@example.org", name="Op"
        )

    def make(self, text):
        return uploads.create_uploads(
            csv_file(text), "src", "2026-03-01", self.user
        )

    def test_all_blank_columns_are_skipped(self):
        created = self.make(
            "administration_id,water_demand,cattle,population\n"
            f"{self.a.id},1000,,\n"
        )
        self.assertEqual([u.dataset for u in created], ["water-demand"])

    def test_a_wholly_empty_file_is_rejected_not_silent(self):
        created = self.make(
            "administration_id,water_demand,cattle\n" f"{self.a.id},,\n"
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].status, UploadStatus.rejected)
        self.assertEqual(created[0].report["errors"][0]["code"], "no_values")

    def test_filled_but_unchanged_column_still_creates_a_row(self):
        Indicator.objects.create(administration=self.a, population=100)
        created = self.make(
            f"administration_id,population\n{self.a.id},100\n"
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].status, UploadStatus.validated)
        self.assertEqual(created[0].changed_count, 0)


class OperatorPermissionsTestCase(TestCase):
    """D-13: the operator reaches this screen without is_superuser, and
    reaches nothing else."""

    def setUp(self):
        self.group = Group.objects.get(name="Data operators")
        self.operator = SystemUser.objects.create(
            email="operator@example.org", name="Operator", is_staff=True
        )
        self.operator.groups.add(self.group)
        self.outsider = SystemUser.objects.create(
            email="outsider@example.org", name="Outsider", is_staff=True
        )

    def test_group_grants_only_dataset_upload(self):
        codenames = set(
            self.group.permissions.values_list("codename", flat=True)
        )
        self.assertEqual(
            codenames, {"add_datasetupload", "view_datasetupload"}
        )

    def test_operator_can_reach_the_changelist(self):
        client = Client()
        client.force_login(self.operator)
        self.assertEqual(
            client.get("/admin/v1_indicators/datasetupload/").status_code, 200
        )

    def test_operator_cannot_reach_user_admin(self):
        client = Client()
        client.force_login(self.operator)
        response = client.get("/admin/v1_users/systemuser/")
        self.assertIn(response.status_code, (302, 403))

    def test_staff_without_the_group_is_shut_out(self):
        client = Client()
        client.force_login(self.outsider)
        response = client.get("/admin/v1_indicators/datasetupload/")
        self.assertIn(response.status_code, (302, 403))

    def test_non_staff_cannot_reach_admin_at_all(self):
        plain = SystemUser.objects.create(
            email="plain@example.org", name="Plain"
        )
        client = Client()
        client.force_login(plain)
        response = client.get("/admin/v1_indicators/datasetupload/")
        self.assertIn(response.status_code, (302, 403))
