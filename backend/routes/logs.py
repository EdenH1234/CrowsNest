from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

import auth
import database

router = APIRouter(prefix="/api", dependencies=[Depends(auth.get_current_user)])


class GroupRef(BaseModel):
    compose_project: Optional[str] = None


@router.get("/containers")
def list_containers() -> list[dict]:
    return database.get_containers()


@router.get("/containers/deleted")
def list_deleted_containers() -> list[dict]:
    return database.get_deleted_containers()


@router.post("/groups/delete")
def delete_group(body: GroupRef) -> dict:
    count = database.soft_delete_group(body.compose_project)
    if count == 0:
        raise HTTPException(status_code=404, detail="Group not found or already deleted")
    return {"deleted": count}


@router.post("/groups/recover")
def recover_group(body: GroupRef) -> dict:
    count = database.recover_group(body.compose_project)
    if count == 0:
        raise HTTPException(status_code=404, detail="Group not found or not deleted")
    return {"recovered": count}


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
