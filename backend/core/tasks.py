from celery import shared_task

from .services import process_pending_payouts, retry_stuck_payouts


@shared_task(name="core.tasks.process_pending_payouts_task")
def process_pending_payouts_task() -> int:
    return process_pending_payouts()


@shared_task(name="core.tasks.retry_stuck_payouts_task")
def retry_stuck_payouts_task() -> int:
    return retry_stuck_payouts()
