"""FastAPI server: a live (Server-Sent Events) research endpoint + the static frontend."""
import asyncio
import json
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query, Request  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from .pipeline import Cancelled, run_pipeline  # noqa: E402

app = FastAPI(title="ResearchMind")

MAX_TOPIC_LENGTH = 200
MAX_CONCURRENT_RUNS = 3
active_runs = 0


@app.get("/api/health")
def health():
    return {"ok": True, "openai": bool(os.getenv("OPENAI_API_KEY")), "tavily": bool(os.getenv("TAVILY_API_KEY"))}


@app.get("/api/research")
async def research(request: Request, topic: str = Query(""), revise: bool = False):
    topic = topic.strip()
    if not topic:
        return JSONResponse({"error": "Enter a research topic."}, status_code=400)
    if len(topic) > MAX_TOPIC_LENGTH:
        return JSONResponse({"error": f"Keep the topic under {MAX_TOPIC_LENGTH} characters."}, status_code=400)
    if active_runs >= MAX_CONCURRENT_RUNS:
        return JSONResponse({"error": "The server is busy. Try again in a minute."}, status_code=429)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    cancelled = threading.Event()

    def emit(event):  # called from the worker thread
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def worker():
        try:
            run_pipeline(topic, 7 if revise else None, emit, cancelled)
        except Cancelled:
            pass
        except Exception as e:  # e.g. missing key, no credits, rate limit
            emit({"type": "error", "message": (str(e) or "Something went wrong.")[:400]})
        finally:
            emit(None)  # end of stream

    async def stream():
        global active_runs
        active_runs += 1
        loop.run_in_executor(None, worker)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            cancelled.set()  # browser left (or finished): stop before the next LLM call
            active_runs -= 1

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


# Serve the HTML/CSS/JS frontend from the same server (must be mounted last).
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
