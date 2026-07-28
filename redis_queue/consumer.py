import json

from redis import Redis

from redis_queue.job_schema import DocumentJob

QUEUE_NAME = "document_processing"


class RedisConsumer:
    """
    Consumes jobs from Redis queue.
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def consume(self) -> DocumentJob | None:
        """
        Wait for a job for up to 5 seconds.
        """

        result = self.redis.blpop(QUEUE_NAME, timeout=5)

        if result is None:
            return None

        _, payload = result

        data = json.loads(payload)

        return DocumentJob.model_validate(data)