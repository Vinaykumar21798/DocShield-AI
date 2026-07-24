import time

from redis.exceptions import TimeoutError

from core.database import SessionLocal
from database.repositories.processing_job_repository import (
    processing_job_repository,
)
from redis_queue.consumer import RedisConsumer
from redis_queue.redis_client import redis_client


class Worker:
    """
    Background worker that continuously processes Redis jobs.
    """

    def __init__(self):
        self.consumer = RedisConsumer(redis_client)

    def start(self):
        print("=" * 60)
        print("Worker Started...")
        print("Waiting for jobs...")
        print("=" * 60)

        while True:

            try:

                job = self.consumer.consume()

                if job is None:
                    continue

                db = SessionLocal()

                try:

                    processing_job = (
                        processing_job_repository.get_latest_job_by_document(
                            db,
                            str(job.document_id),
                        )
                    )

                    if processing_job is None:
                        print(
                            f"Processing job not found for {job.document_id}"
                        )
                        continue

                    processing_job_repository.assign_worker(
                        db,
                        processing_job,
                        "worker-1",
                    )

                    processing_job_repository.update_job_status(
                        db,
                        processing_job,
                        "PROCESSING",
                    )

                    print(f"\nProcessing {job.document_id}")

                    #
                    # Week-1 Simulation
                    #
                    time.sleep(5)

                    processing_job_repository.mark_completed(
                        db,
                        processing_job,
                    )

                    print(f"Completed {job.document_id}")

                except Exception as e:

                    if processing_job:

                        processing_job_repository.mark_failed(
                            db,
                            processing_job,
                            str(e),
                        )

                    print(e)

                finally:

                    db.close()

            except TimeoutError:
                continue

            except KeyboardInterrupt:
                print("\nWorker stopped.")
                break

            except Exception as e:
                print(e)


if __name__ == "__main__":

    worker = Worker()
    worker.start()