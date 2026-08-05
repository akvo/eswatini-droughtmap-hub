from unittest.mock import patch, call
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import BriefForwardLog
from utils.email_helper import EmailTypes, email_context


class BriefForwardAPITestCase(APITestCase):
    def setUp(self):
        self.twg_user = SystemUser.objects.create(
            email="twg_member@example.com",
            name="TWG Member",
            role=2,
            technical_working_group=1,
        )
        self.non_twg_user = SystemUser.objects.create(
            email="non_twg@example.com",
            name="Non TWG Member",
            role=2,
            technical_working_group=None,
        )
        self.url = reverse("brief-forward", kwargs={"version": "v1"})
        self.valid_payload = {
            "inkhundla_id": 4588078,
            "inkhundla_name": "Big Bend",
            "components": ["cover_header", "kpi_tiles"],
            "recipients": [
                {"email": "recipient1@example.com", "name": "Recipient One"},
                {"email": "recipient2@example.com", "name": "Recipient Two"},
            ],
            "note": "Please review before Friday.",
            "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
        }

    def test_unauthenticated_returns_401(self):
        res = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_twg_user_returns_403(self):
        self.client.force_authenticate(user=self.non_twg_user)
        res = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            res.data.get("detail"),
            "TWG membership required to forward briefs.",
        )

    def test_empty_recipients_returns_400(self):
        self.client.force_authenticate(user=self.twg_user)
        invalid_payload = {**self.valid_payload, "recipients": []}
        res = self.client.post(self.url, invalid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recipients", res.data)

    def test_invalid_recipient_email_returns_400(self):
        self.client.force_authenticate(user=self.twg_user)
        invalid_payload = {
            **self.valid_payload,
            "recipients": [{"email": "not-an-email", "name": "Invalid"}],
        }
        res = self.client.post(self.url, invalid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recipients", res.data)

    def test_missing_required_fields_returns_400(self):
        self.client.force_authenticate(user=self.twg_user)
        for field in [
            "inkhundla_id",
            "inkhundla_name",
            "components",
            "brief_url",
        ]:
            payload = {**self.valid_payload}
            del payload[field]
            res = self.client.post(self.url, payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_method_not_allowed(self):
        self.client.force_authenticate(user=self.twg_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_invalid_url_format_returns_400(self):
        self.client.force_authenticate(user=self.twg_user)
        payload = {**self.valid_payload, "brief_url": "not-a-valid-url"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("brief_url", res.data)

    def test_recipient_without_name_is_valid(self):
        self.client.force_authenticate(user=self.twg_user)
        payload = {
            **self.valid_payload,
            "recipients": [{"email": "noname@example.com"}],
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)

    @patch("api.v1.v1_publication.brief.view.async_task")
    def test_valid_forward_creates_log_and_queues_task(self, mock_async_task):
        self.client.force_authenticate(user=self.twg_user)
        res = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(res.data, {"queued": True, "recipient_count": 2})

        log = BriefForwardLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.sender, self.twg_user)
        self.assertEqual(log.inkhundla_name, "Big Bend")
        mock_async_task.assert_called_once_with(
            "api.v1.v1_publication.brief.tasks.send_brief_forward_emails",
            log.pk,
        )


class EmailHelperBriefForwardTests(APITestCase):
    def test_email_context_brief_forward(self):
        context = {
            "inkhundla_name": "Big Bend",
            "sender_name": "TWG Member",
            "note": "Please check this out",
            "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
        }
        result = email_context(context, EmailTypes.brief_forward)
        self.assertEqual(result["subject"], "EDM — Inkhundla Brief: Big Bend")
        self.assertIn("Forwarded by TWG Member", result["body"])
        self.assertIn("Please check this out", result["body"])
        self.assertEqual(result["cta_text"], "View the brief")
        self.assertEqual(
            result["cta_url"],
            "http://localhost:3000/brief-builder?inkhundla=4588078",
        )

    def test_email_context_brief_forward_no_note(self):
        context = {
            "inkhundla_name": "Big Bend",
            "sender_name": "TWG Member",
            "note": "",
            "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
        }
        result = email_context(context, EmailTypes.brief_forward)
        self.assertNotIn("<blockquote", result["body"])


class SendBriefForwardEmailsTaskTests(APITestCase):
    def setUp(self):
        self.user = SystemUser.objects.create(
            email="sender@example.com",
            name="Sender User",
            role=2,
            technical_working_group=1,
        )
        self.log = BriefForwardLog.objects.create(
            sender=self.user,
            recipients_payload=[
                {"email": "r1@example.com", "name": "Recipient One"},
                {"email": "r2@example.com", "name": "Recipient Two"},
            ],
            inkhundla_id=4588078,
            inkhundla_name="Big Bend",
            components=["cover_header"],
            brief_url="http://localhost:3000/brief-builder?inkhundla=4588078",
            note="Important note",
        )

    @patch("api.v1.v1_publication.brief.tasks.send_email")
    def test_send_brief_forward_emails_sends_email_per_recipient(
        self, mock_send_email
    ):
        from api.v1.v1_publication.brief.tasks import send_brief_forward_emails

        send_brief_forward_emails(self.log.pk)

        self.assertEqual(mock_send_email.call_count, 2)
        mock_send_email.assert_has_calls(
            [
                call(
                    context={
                        "send_to": ["r1@example.com"],
                        "recipient_name": "Recipient One",
                        "sender_name": "Sender User",
                        "inkhundla_name": "Big Bend",
                        "note": "Important note",
                        "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
                    },
                    type=EmailTypes.brief_forward,
                ),
                call(
                    context={
                        "send_to": ["r2@example.com"],
                        "recipient_name": "Recipient Two",
                        "sender_name": "Sender User",
                        "inkhundla_name": "Big Bend",
                        "note": "Important note",
                        "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
                    },
                    type=EmailTypes.brief_forward,
                ),
            ]
        )

    @patch("api.v1.v1_publication.brief.tasks.send_email")
    def test_send_brief_forward_emails_fallback_sender_when_deleted(
        self, mock_send_email
    ):
        from api.v1.v1_publication.brief.tasks import send_brief_forward_emails

        self.log.sender = None
        self.log.save()

        send_brief_forward_emails(self.log.pk)

        self.assertEqual(mock_send_email.call_count, 2)
        first_call_context = mock_send_email.call_args_list[0][1]["context"]
        self.assertEqual(first_call_context["sender_name"], "A TWG member")

    @patch("api.v1.v1_publication.brief.tasks.send_email")
    def test_send_brief_forward_emails_non_existent_log_pk(
        self, mock_send_email
    ):
        from api.v1.v1_publication.brief.tasks import send_brief_forward_emails

        # Non-existent log_pk should return gracefully without
        # raising error or sending email
        send_brief_forward_emails(999999)
        mock_send_email.assert_not_called()

    @patch("api.v1.v1_publication.brief.tasks.send_email")
    def test_send_brief_forward_emails_recipient_without_name_uses_email(
        self, mock_send_email
    ):
        from api.v1.v1_publication.brief.tasks import send_brief_forward_emails

        no_name_log = BriefForwardLog.objects.create(
            sender=self.user,
            recipients_payload=[{"email": "nameless@example.com"}],
            inkhundla_id=4588078,
            inkhundla_name="Big Bend",
            components=["cover_header"],
            brief_url="http://localhost:3000/brief-builder?inkhundla=4588078",
            note="",
        )

        send_brief_forward_emails(no_name_log.pk)

        mock_send_email.assert_called_once_with(
            context={
                "send_to": ["nameless@example.com"],
                "recipient_name": "nameless@example.com",
                "sender_name": "Sender User",
                "inkhundla_name": "Big Bend",
                "note": "",
                "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
            },
            type=EmailTypes.brief_forward,
        )
