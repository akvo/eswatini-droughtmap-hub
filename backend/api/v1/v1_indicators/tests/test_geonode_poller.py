from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase

from api.v1.v1_indicators import geonode
from api.v1.v1_indicators.constants import UploadOrigin, UploadStatus
from api.v1.v1_indicators.datasets import DATASETS
from api.v1.v1_indicators.models import DatasetUpload, Indicator
from api.v1.v1_indicators.notifications import operator_recipients
from api.v1.v1_publication.models import Administration
from api.v1.v1_users.models import SystemUser

CATTLE_CATEGORY = DATASETS["cattle"].geonode_category


def document(pk=7, title="Livestock census", date="2024-06-01",
             email="dwa@example.org", org="Ministry of Agriculture"):
    return {
        "pk": pk,
        "title": title,
        # As GeoNode really reports a CSV document: resource_type is
        # "document", subtype is the FILE kind. A mock saying
        # subtype="document" is what let the wrong filter ship.
        "resource_type": "document",
        "subtype": "other",
        "date": date,
        "download_url": f"https://geonode.test/documents/{pk}/download",
        "owner": {"email": email, "organization": org},
    }


class ResourceMetadataTestCase(TestCase):
    def test_source_label_carries_title_org_and_id(self):
        label = geonode.resource_source_label(document())
        self.assertIn("Livestock census", label)
        self.assertIn("Ministry of Agriculture", label)
        self.assertIn("#7", label)

    def test_as_of_prefers_date_then_falls_back(self):
        self.assertEqual(geonode.resource_as_of(document()), "2024-06-01")
        self.assertEqual(
            geonode.resource_as_of(
                {"date": None, "last_updated": "2025-02-03T10:00:00Z"}
            ),
            "2025-02-03",
        )

    def test_as_of_is_none_when_the_resource_has_no_date(self):
        """Guessing would stamp a fabricated vintage on published figures."""
        self.assertIsNone(geonode.resource_as_of({"pk": 1}))

    def test_category_map_covers_every_dataset(self):
        mapping = geonode.category_map()
        self.assertEqual(len(mapping), len(DATASETS))
        self.assertEqual(mapping[CATTLE_CATEGORY], "cattle")


class CatalogueQueryTestCase(TestCase):
    """The query string itself, because mocking `list_documents` hides it.

    Shipped filtering on `filter{subtype}=document`, which matched nothing:
    GeoNode reports subtype="other" for a CSV and resource_type="document".
    Every poller test passed regardless, because they all mocked the function
    that builds this URL. Verified against resource 708 on cdie-geonode-prod.
    """

    def _query(self, calls):
        with patch.object(geonode, "_get", side_effect=calls) as get:
            geonode.list_documents(CATTLE_CATEGORY)
        return get.call_args[0][0]

    def test_filters_on_resource_type_not_subtype(self):
        query = self._query([{"resources": [], "total": 0}])
        self.assertIn("filter{resource_type}=document", query)
        self.assertNotIn("filter{subtype}", query)

    def test_filters_on_the_category_identifier(self):
        query = self._query([{"resources": [], "total": 0}])
        self.assertIn(f"filter{{category.identifier}}={CATTLE_CATEGORY}", query)

    def test_pages_until_the_total_is_covered(self):
        pages = [
            {"resources": [document(pk=1)], "total": 2, "page_size": 1},
            {"resources": [document(pk=2)], "total": 2, "page_size": 1},
        ]
        with patch.object(geonode, "_get", side_effect=pages):
            found = geonode.list_documents(CATTLE_CATEGORY)
        self.assertEqual([r["pk"] for r in found], [1, 2])

    def test_a_real_geonode_document_payload_is_recognised(self):
        """Shape copied from GET /api/v2/resources/708 — subtype is 'other'."""
        payload = {
            "resources": [{
                "pk": "708",
                "subtype": "other",
                "resource_type": "document",
                "title": "dih_data_cattle.csv",
                "date": "2026-08-25T02:57:00Z",
                "download_url": "https://geonode.test/documents/708/download",
                "owner": {"email": "iwan@akvo.org"},
            }],
            "total": 1,
            "page_size": 10,
        }
        with patch.object(geonode, "_get", return_value=payload):
            found = geonode.list_documents(CATTLE_CATEGORY)
        self.assertEqual(len(found), 1)
        self.assertEqual(geonode.resource_as_of(found[0]), "2026-08-25")
        self.assertEqual(
            geonode.resource_owner_email(found[0]), "iwan@akvo.org"
        )


class PollerTestCase(TestCase):
    def setUp(self):
        self.a = Administration.objects.create(name="Hhukwini", region="H")
        self.b = Administration.objects.create(name="Lobamba", region="H")
        self.csv = (
            "administration_id,inkhundla_name,cattle\n"
            f"{self.a.id},Hhukwini,120\n"
            f"{self.b.id},Lobamba,80\n"
        ).encode()

    def run_poller(self, listing, payload=None, **opts):
        out, err = StringIO(), StringIO()
        with patch.object(geonode, "list_documents", side_effect=listing), \
                patch.object(geonode, "download",
                             return_value=payload or self.csv):
            call_command(
                "fetch_dataset_uploads", stdout=out, stderr=err,
                no_email=True, **opts,
            )
        return out.getvalue(), err.getvalue()

    def only_cattle(self, resources):
        return lambda category: (
            resources if category == CATTLE_CATEGORY else []
        )

    def test_fetches_and_validates_but_does_not_apply(self):
        self.run_poller(self.only_cattle([document()]))
        upload = DatasetUpload.objects.get()
        self.assertEqual(upload.dataset, "cattle")
        self.assertEqual(upload.origin, UploadOrigin.geonode)
        self.assertEqual(upload.geonode_id, 7)
        self.assertEqual(upload.status, UploadStatus.validated)
        # The whole point: publishing to GeoNode does not change figures.
        self.assertFalse(Indicator.objects.exists())

    def test_provenance_comes_from_the_resource(self):
        self.run_poller(self.only_cattle([document()]))
        upload = DatasetUpload.objects.get()
        self.assertIn("Livestock census", upload.source_label)
        self.assertEqual(str(upload.as_of), "2024-06-01")

    def test_publisher_recorded_but_not_emailed(self):
        self.run_poller(self.only_cattle([document()]))
        upload = DatasetUpload.objects.get()
        self.assertEqual(upload.report["published_by"], "dwa@example.org")
        self.assertEqual(len(mail.outbox), 0)

    def test_same_file_twice_creates_one_row(self):
        listing = self.only_cattle([document()])
        self.run_poller(listing)
        self.run_poller(listing)
        self.assertEqual(DatasetUpload.objects.count(), 1)

    def test_replaced_document_same_id_is_fetched_again(self):
        """A provider can correct a document in place; dedupe is on content,
        so the correction must not be hidden by the resource id."""
        listing = self.only_cattle([document()])
        self.run_poller(listing)
        corrected = self.csv.replace(b",120", b",999")
        self.run_poller(listing, payload=corrected)
        self.assertEqual(DatasetUpload.objects.count(), 2)

    def test_resource_without_a_date_is_skipped_loudly(self):
        _, err = self.run_poller(
            self.only_cattle([document(date=None) | {"last_updated": None,
                                                     "created": None}])
        )
        self.assertIn("no date", err)
        self.assertFalse(DatasetUpload.objects.exists())

    def test_unreadable_category_does_not_abort_the_run(self):
        def listing(category):
            if category == CATTLE_CATEGORY:
                raise geonode.GeoNodeError("boom")
            if category == DATASETS["taps"].geonode_category:
                return [document(pk=9, title="Taps")]
            return []

        payload = (
            "administration_id,taps\n"
            f"{self.a.id},5\n"
        ).encode()
        _, err = self.run_poller(listing, payload=payload)
        self.assertIn("unreadable", err)
        self.assertEqual(DatasetUpload.objects.get().dataset, "taps")

    def test_dry_run_stores_nothing(self):
        out, _ = self.run_poller(
            self.only_cattle([document()]), dry_run=True
        )
        self.assertIn("would fetch", out)
        self.assertIn("[new]", out)
        self.assertFalse(DatasetUpload.objects.exists())

    def test_dry_run_marks_an_already_seen_resource(self):
        listing = self.only_cattle([document()])
        self.run_poller(listing)
        out, _ = self.run_poller(listing, dry_run=True)
        self.assertIn("seen before", out)
        self.assertEqual(DatasetUpload.objects.count(), 1)

    def test_bad_file_is_stored_as_rejected(self):
        out, _ = self.run_poller(
            self.only_cattle([document()]),
            payload=b"administration_id,cattle\n999999,5\n",
        )
        upload = DatasetUpload.objects.get()
        self.assertEqual(upload.status, UploadStatus.rejected)

    def test_dataset_filter_limits_the_walk(self):
        seen = []

        def listing(category):
            seen.append(category)
            return []

        self.run_poller(listing, dataset="cattle")
        self.assertEqual(seen, [CATTLE_CATEGORY])

    def test_unknown_dataset_is_refused(self):
        out, err = StringIO(), StringIO()
        call_command(
            "fetch_dataset_uploads", dataset="nope", stdout=out, stderr=err
        )
        self.assertIn("Unknown dataset", err.getvalue())


class CategoryCheckTestCase(TestCase):
    def test_check_names_the_missing_categories(self):
        out = StringIO()
        with patch.object(
            geonode, "existing_categories", return_value={CATTLE_CATEGORY}
        ):
            call_command("fetch_dataset_uploads", check=True, stdout=out)
        report = out.getvalue()
        self.assertIn(f"OK      {CATTLE_CATEGORY}", report)
        self.assertIn("MISSING", report)
        self.assertIn("must be created in", report)

    def test_check_reports_an_unreadable_catalogue(self):
        err = StringIO()
        with patch.object(
            geonode, "existing_categories",
            side_effect=geonode.GeoNodeError("down"),
        ):
            call_command("fetch_dataset_uploads", check=True, stderr=err)
        self.assertIn("Could not read categories", err.getvalue())


class NotificationTestCase(TestCase):
    def setUp(self):
        self.a = Administration.objects.create(name="Hhukwini", region="H")
        self.operator = SystemUser.objects.create(
            email="operator@example.org", name="Op", is_staff=True
        )
        self.operator.groups.add(Group.objects.get(name="Data operators"))
        self.csv = (
            f"administration_id,cattle\n{self.a.id},12\n"
        ).encode()

    def poll(self):
        with patch.object(
            geonode, "list_documents",
            side_effect=lambda c: (
                [document()] if c == CATTLE_CATEGORY else []
            ),
        ), patch.object(geonode, "download", return_value=self.csv):
            call_command("fetch_dataset_uploads", stdout=StringIO(),
                         stderr=StringIO())

    def test_operators_are_notified(self):
        self.poll()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("operator@example.org", mail.outbox[0].to)

    def test_the_message_says_waiting_not_applied(self):
        self.poll()
        body = mail.outbox[0].alternatives[0][0]
        self.assertIn("waiting", mail.outbox[0].subject)
        self.assertIn("Nothing has been applied", body)

    def test_group_members_preferred_over_superusers(self):
        SystemUser.objects.create(
            email="root@example.org", name="Root", is_superuser=True
        )
        self.assertEqual(operator_recipients(), ["operator@example.org"])

    def test_superusers_are_the_fallback(self):
        self.operator.groups.clear()
        SystemUser.objects.create(
            email="root@example.org", name="Root", is_superuser=True
        )
        self.assertEqual(operator_recipients(), ["root@example.org"])

    def test_nothing_fetched_means_no_mail(self):
        with patch.object(geonode, "list_documents", return_value=[]):
            call_command("fetch_dataset_uploads", stdout=StringIO(),
                         stderr=StringIO())
        self.assertEqual(len(mail.outbox), 0)
