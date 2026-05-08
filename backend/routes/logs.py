from fastapi import APIRouter, Depends, Query
from typing import Optional

import auth
import database

router = APIRouter(prefix="/api", dependencies=[Depends(auth.get_current_user)])


@router.get("/containers")
def list_containers() -> list[dict]:
    return database.get_containers()


@router.get("/logs")
def query_logs(
    container_name: Optional[str] = Query(None),
    since: Optional[float] = Query(None),
    until: Optional[float] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return database.query_logs(
        container_name=container_name,
        since=since,
        until=until,
        q=q,
        limit=limit,
        offset=offset,
    )
