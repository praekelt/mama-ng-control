import os
from redis import Redis
from celery import task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

redis = Redis(host=os.environ['MAMA_NG_CONTROL_REDIS_SERVICE'],
              port=int(os.environ['MAMA_NG_CONTROL_REDIS_PORT']))


@task()
def incr(what):
    counter = redis.incr(what)
    return "%s is now: %s" % (what, counter)
