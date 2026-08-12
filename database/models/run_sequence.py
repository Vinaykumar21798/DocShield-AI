from sqlalchemy import Column, Integer
from core.database import Base


class RunSequence(Base):
    __tablename__ = "run_sequence"

    id = Column(Integer, primary_key=True)
    last_value = Column(Integer, default=0, nullable=False)
