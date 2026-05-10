import asyncio
import logging
import threading
import time

import docker
from docker.models.containers import Container

import database

logger = logging.getLogger(__name__)

_subscribers: dict[str, set[asyncio.Queue]] = {}
_collector_tasks: dict[str, asyncio.Task] = {}
_docker_client: docker.DockerClient | None = None
_loop: asyncio.AbstractEventLoop | None = None

BATCH_SIZE = 50
BATCH_INTERVAL = 0.5


def _get_client() -> docker.DockerClient:
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client


def _container_meta(container: Container) -> dict:
    labels = container.labels or {}
    return {
        "container_id": container.id,
        "container_name": container.name.lstrip("/"),
        "compose_project": labels.get("com.docker.compose.project"),
        "compose_service": labels.get("com.docker.compose.service"),
        "image_tag": container.attrs.get("Config", {}).get("Image", ""),
    }


def subscribe(container_name: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.setdefault(container_name, set()).add(q)
    return q


def unsubscribe(container_name: str, q: asyncio.Queue) -> None:
    _subscribers.get(container_name, set()).discard(q)


# ── Thread-safe helpers ────────────────────────────────────────────────────────

def _broadcast(container_name: str, entry: dict) -> None:
    if _loop is None:
        return
    for q in list(_subscribers.get(container_name, set())):
        _loop.call_soon_threadsafe(q.put_nowait, entry)


def _schedule_container_task(container: Container) -> None:
    """Called from a worker thread — schedules a new tail task on the event loop."""
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(_start_container_task(container), _loop)


# ── Worker threads (blocking I/O — never touch the event loop directly) ───────

def _tail_thread(container: Container, stop: threading.Event) -> None:
    meta = _container_meta(container)
    is_restart = database.upsert_container(
        meta["container_id"], meta["container_name"],
        meta["compose_project"], meta["compose_service"],
        status="running",
        image_tag=meta["image_tag"],
    )
    if is_restart:
        divider = {
            **meta,
            "timestamp": time.time(),
            "stream": "system",
            "message": "Container restarted",
        }
        database.insert_logs([divider])
        _broadcast(meta["container_name"], divider)

    batch: list[dict] = []
    last_flush = time.monotonic()

    try:
        log_stream = container.logs(stream=True, follow=True, timestamps=True)
        for raw in log_stream:
            if stop.is_set():
                break
            if len(raw) < 8:
                continue

            stream = "stderr" if raw[0] == 2 else "stdout"
            payload = raw[8:].decode("utf-8", errors="replace").rstrip("\n")
            parts = payload.split(" ", 1)
            ts_str, message = (parts[0], parts[1]) if len(parts) == 2 else ("", payload)

            try:
                from datetime import datetime
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            except Exception:
                ts = time.time()

            entry = {**meta, "timestamp": ts, "stream": stream, "message": message}
            batch.append(entry)
            _broadcast(meta["container_name"], entry)

            now = time.monotonic()
            if len(batch) >= BATCH_SIZE or (now - last_flush) >= BATCH_INTERVAL:
                database.insert_logs(batch)
                batch = []
                last_flush = now

    except Exception as e:
        logger.warning("Log tail ended for %s: %s", meta["container_name"], e)
    finally:
        if batch:
            try:
                database.insert_logs(batch)
            except Exception:
                pass
        database.upsert_container(
            meta["container_id"], meta["container_name"],
            meta["compose_project"], meta["compose_service"],
            status="stopped",
            image_tag=meta["image_tag"],
        )


def _events_thread() -> None:
    while True:
        try:
            client = _get_client()
            for event in client.events(decode=True, filters={"type": "container"}):
                action = event.get("Action", "")
                cid = event.get("id", "")
                if action == "start" and cid:
                    try:
                        container = client.containers.get(cid)
                        _schedule_container_task(container)
                    except Exception as e:
                        logger.warning("Could not attach to container %s: %s", cid, e)
                elif action in ("stop", "die", "destroy") and cid:
                    if _loop is None:
                        continue
                    task = _collector_tasks.get(cid)
                    if task and not task.done():
                        _loop.call_soon_threadsafe(task.cancel)
        except Exception as e:
            logger.error("Docker event stream error: %s — retrying in 5s", e)
            time.sleep(5)


# ── Async wrappers (only schedule work — no blocking I/O) ─────────────────────

async def _tail_container(container: Container) -> None:
    stop = threading.Event()
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _tail_thread, container, stop)
    except asyncio.CancelledError:
        stop.set()


async def _start_container_task(container: Container) -> None:
    cid = container.id
    if cid in _collector_tasks and not _collector_tasks[cid].done():
        return
    _collector_tasks[cid] = asyncio.create_task(
        _tail_container(container), name=f"tail-{container.name}"
    )


async def start_collector() -> None:
    global _loop
    _loop = asyncio.get_event_loop()
    client = _get_client()

    running = client.containers.list(all=False)
    for container in running:
        await _start_container_task(container)

    threading.Thread(target=_events_thread, daemon=True, name="docker-events").start()
    logger.info("Collector started, watching %d containers", len(running))


async def stop_collector() -> None:
    for task in _collector_tasks.values():
        if not task.done():
            task.cancel()
    await asyncio.gather(*_collector_tasks.values(), return_exceptions=True)
    _collector_tasks.clear()
    if _docker_client:
        _docker_client.close()
