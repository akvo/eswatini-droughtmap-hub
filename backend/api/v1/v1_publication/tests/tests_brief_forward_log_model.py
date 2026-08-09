from django.test import TestCase
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import BriefForwardLog


class BriefForwardLogModelTests(TestCase):
    def test_create_brief_forward_log(self):
        user = SystemUser.objects.create(
            email="testsender@example.com",
            name="Test Sender",
            role=2,
            technical_working_group=1,
        )
        log = BriefForwardLog.objects.create(
            sender=user,
            recipients_payload=[
                {"email": "recipient@example.com", "name": "Recipient"}
            ],
            inkhundla_id=4588078,
            inkhundla_name="Big Bend",
            components=["cover_header", "kpi_tiles"],
            brief_url="http://localhost:3000/brief-builder?inkhundla=4588078",
            note="Test note",
        )
        self.assertIsNotNone(log.pk)
        self.assertEqual(log.sender, user)
        self.assertEqual(log.inkhundla_name, "Big Bend")
        self.assertEqual(len(log.recipients_payload), 1)
        self.assertEqual(
            str(log),
            f"BriefForward by {user.id} at {log.sent_at:%Y-%m-%d %H:%M}",
        )
