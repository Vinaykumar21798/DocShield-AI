import json

from redis import Redis

from redis_queue.job_schema import DocumentJob

QUEUE_NAME = "document_processing"


class RedisProducer:

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def publish(self, job: DocumentJob):

        self.redis.rpush(
            QUEUE_NAME,
            job.model_dump_json()
        )

        return True