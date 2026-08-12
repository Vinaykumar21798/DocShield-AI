from typing import Optional
from sqlalchemy.orm import Session
from database.models import Run, RunSequence
from database.repositories.base_repository import BaseRepository

class RunRepository(BaseRepository[Run]):
    def __init__(self, db: Session):
        super().__init__(Run, db)

    def create_run(self, total_files: int) -> Run:
        # Atomic sequence increment
        run_seq = self.db.query(RunSequence).with_for_update().first()
        if run_seq is None:
            run_seq = RunSequence(last_value=0)
            self.db.add(run_seq)
            self.db.flush()
        
        run_seq.last_value += 1
        human_run_id = f"RUN-{run_seq.last_value:06d}"
        
        run = Run(
            run_id=human_run_id,
            total_files=total_files,
            status="QUEUED",
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get_by_run_id(self, run_id: str) -> Optional[Run]:
        return self.db.query(Run).filter(Run.run_id == run_id).first()

    def update_status(self, run: Run, status: str) -> Run:
        run.status = status
        self.db.add(run)
        self.db.flush()
        return run

    def increment_completed(self, run_id: str) -> Run:
        run = self.get_by_run_id(run_id)
        if run:
            run.completed_files += 1
            if run.completed_files + run.failed_files == run.total_files:
                run.status = "COMPLETED"
            self.db.add(run)
            self.db.flush()
        return run

    def increment_failed(self, run_id: str) -> Run:
        run = self.get_by_run_id(run_id)
        if run:
            run.failed_files += 1
            if run.completed_files + run.failed_files == run.total_files:
                run.status = "FAILED"
            self.db.add(run)
            self.db.flush()
        return run
