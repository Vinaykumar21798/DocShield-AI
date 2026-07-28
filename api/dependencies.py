from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlalchemy.orm import Session

from core.database import get_db, get_redis


DatabaseSession = Annotated[Session, Depends(get_db)]

RedisClient = Annotated[Redis, Depends(get_redis)]