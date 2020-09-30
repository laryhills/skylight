import os
from signal import SIGTERM
from multiprocessing import Process
from rq import Connection, Worker

from sms.config import redis_conn
from sms.models.user import User


def _start_redis_worker(user: User):
    with Connection(redis_conn):
        worker = Worker(user.get_queue())
        worker.work()


def start_redis_worker(user: User):
    process = Process(target=_start_redis_worker, args=(user,))
    process.start()


def stop_redis_worker(user: User):
    workers = Worker.all(queue=user.get_queue())
    for worker in workers:
        os.kill(worker.pid, SIGTERM)
