from time import sleep
from django.utils import timezone
from django.conf import settings
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_jobs.constants import JobStatus
from api.v1.v1_users.models import SystemUser
from utils.email_helper import send_email, EmailTypes


def demo_q_func(name: str):
    sleep(10)
    return {"name": f"Hello {name}! from Django Queue"}


def demo_q_response_func(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    if task.success:
        job.status = JobStatus.done
        job.available = timezone.now()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def notify_verification_email(email: str, code: str):
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.verification_email,
            context={
                "send_to": [email],
                "verification_code": code,
            },
        )


def notify_forgot_password(user: SystemUser):
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.forgot_password,
            context={
                "send_to": [user.email],
                "name": user.name,
                "reset_password_code": user.reset_password_code,
            },
        )


def email_notification_results(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    if task.success:
        job.status = JobStatus.done
        job.available = timezone.now()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()
