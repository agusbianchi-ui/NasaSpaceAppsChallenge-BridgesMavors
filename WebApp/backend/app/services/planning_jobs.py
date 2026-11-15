"""Bounded cancellable planning jobs, no external calls inside search."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
import time, uuid, copy, json
from app.services.path_planning import solve_request, SearchStopped

pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mars-planner")
lock = Lock()
jobs = {}
cache = {}


def submit(service, request):
    key = (service.metadata or {}).get("source_sha256", "") + request.model_dump_json()
    with lock:
        for id in list(jobs):
            if time.monotonic() - jobs[id]["created"] > 600 and jobs[id][
                "status"
            ] not in ("queued", "running"):
                del jobs[id]
        if sum(j["status"] in ("queued", "running") for j in jobs.values()) >= 4:
            raise ValueError(
                "Planner is busy; cancel an existing calculation or retry."
            )
        if len(jobs) >= 40:
            for old in list(jobs):
                if jobs[old]["status"] not in ("queued", "running"):
                    del jobs[old]
                    if len(jobs) < 40:
                        break
        id = uuid.uuid4().hex
        job = {
            "id": id,
            "status": "queued",
            "created": time.monotonic(),
            "cancel": Event(),
            "result": None,
        }
        jobs[id] = job
        if key in cache:
            job.update(status="complete", result=copy.deepcopy(cache[key]))
            return {"id": id, "status": "complete", "cached": True}

    def run():
        try:
            if job["cancel"].is_set():
                job["status"] = "cancelled"
                return
            job["status"] = "running"
            result = solve_request(service, request, job["cancel"])
            if job["cancel"].is_set():
                job["status"] = "cancelled"
                return
            job.update(status="complete", result=result)
            with lock:
                if len(cache) >= 12:
                    cache.pop(next(iter(cache)))
                cache[key] = copy.deepcopy(result)
        except SearchStopped as e:
            job.update(
                status="cancelled" if job["cancel"].is_set() else "error", error=str(e)
            )
        except Exception as e:
            job.update(status="error", error=str(e))

    pool.submit(run)
    return {"id": id, "status": job["status"], "cached": False}


def get(id):
    with lock:
        j = jobs.get(id)
        return (
            {k: v for k, v in j.items() if k not in ("cancel", "created")}
            if j
            else None
        )


def cancel(id):
    with lock:
        j = jobs.get(id)
        if not j:
            return None
        j["cancel"].set()
        if j["status"] != "complete":
            j["status"] = "cancelled"
        return {"id": id, "status": j["status"]}
