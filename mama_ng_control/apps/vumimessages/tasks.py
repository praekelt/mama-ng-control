from celery import task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@task()
def send_message(message_id):
    # make client

    # send message

    # update status
    pass
