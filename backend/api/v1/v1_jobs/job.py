from time import sleep
from django.utils import timezone
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_jobs.constants import JobStatus


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
