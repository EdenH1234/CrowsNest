import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

import docker
import auth
import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(auth.get_current_user)])


class GroupRef(BaseModel):
    compose_project: Optional[str] = None


@router.get("/containers")
def list_containers() -> list[dict]:
    return database.get_containers()


@router.get("/containers/stats")
async def container_stats() -> list[dict]:
    loop = asyncio.get_event_loop()

    def fetch_all():
        try:
            client = docker.from_env()
        except Exception as e:
            logger.warning("Docker unavailable for stats: %s", e)
            return []

        running = client.containers.list(all=False)
        if not running:
            client.close()
            return []

        def fetch_one(c):
            try:
                c.reload()
                stats = c.stats(stream=False)

                cpu_d = (
                    stats["cpu_stats"]["cpu_usage"]["total_usage"]
                    - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                )
                sys_d = stats["cpu_stats"].get("system_cpu_usage", 0) - stats["precpu_stats"].get("system_cpu_usage", 0)
                ncpu = stats["cpu_stats"].get("online_cpus") or len(
                    stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [None])
                )
                cpu_pct = (cpu_d / sys_d * ncpu * 100) if sys_d > 0 else 0.0

                mem = stats.get("memory_stats", {})
                mem_usage = mem.get("usage", 0)
                mem_limit = mem.get("limit", 0)
                cache = mem.get("stats", {}).get(
                    "inactive_file", mem.get("stats", {}).get("cache", 0)
                )
                mem_usage = max(0, mem_usage - cache)
                mem_pct = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0.0

                labels = c.labels or {}
                return {
                    "container_name": c.name.lstrip("/"),
                    "compose_project": labels.get("com.docker.compose.project"),
                    "started_at": c.attrs.get("State", {}).get("StartedAt", ""),
                    "cpu_pct": round(cpu_pct, 1),
                    "mem_mb": round(mem_usage / 1024 / 1024, 1),
                    "mem_limit_mb": round(mem_limit / 1024 / 1024, 0),
                    "mem_pct": round(mem_pct, 1),
                }
            except Exception as e:
                logger.warning("Stats fetch failed for %s: %s", c.name, e)
                return None

        with ThreadPoolExecutor(max_workers=min(len(running), 10)) as pool:
            results = list(pool.map(fetch_one, running))

        client.close()
        return [r for r in results if r is not None]

    return await loop.run_in_executor(None, fetch_all)


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
