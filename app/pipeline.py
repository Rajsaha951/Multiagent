"""Runs the stages in order and reports progress through `emit`.

Events:  {"type": "step_start", "step"}  ·  {"type": "tool", "step", "name", "arg"}
         {"type": "step_done", "step", "output", "score"?}  ·  {"type": "done"}
"""
import re
import threading

from .agents import critique, reader_agent, revise, search_agent, write_report


class Cancelled(Exception):
    """Raised when the browser disconnects, so we stop spending tokens."""


def parse_score(feedback: str):
    m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback, re.I)
    return float(m.group(1)) if m else None


def run_pipeline(topic: str, revise_below, emit, cancelled: threading.Event):
    def check():
        if cancelled.is_set():
            raise Cancelled()

    def start(step):
        check()
        emit({"type": "step_start", "step": step})

    def done(step, output, **extra):
        emit({"type": "step_done", "step": step, "output": output, **extra})

    def on_tool(step):
        def handler(name, args):
            check()
            emit({"type": "tool", "step": step, "name": name, "arg": args.get("query") or args.get("url") or ""})
        return handler

    start("search")
    search = search_agent(topic, on_tool("search"))
    done("search", search)

    start("reader")
    reader = reader_agent(topic, search, on_tool("reader"))
    done("reader", reader)

    research = f"SEARCH RESULTS:\n{search}\n\nDETAILED PAGE CONTENT:\n{reader}"

    start("writer")
    report = write_report(topic, research)
    done("writer", report)

    start("critic")
    feedback = critique(report)
    score = parse_score(feedback)
    done("critic", feedback, score=score)

    if revise_below is not None and score is not None and score < revise_below:
        start("revise")
        done("revise", revise(report, feedback))

    emit({"type": "done"})


if __name__ == "__main__":  # command-line use:  python -m app.pipeline
    from dotenv import load_dotenv

    load_dotenv()
    topic = input("Enter a research topic: ")

    def show(event):
        if event["type"] == "step_done":
            print(f"\n{'=' * 50}\n{event['step'].upper()}\n{'=' * 50}\n{event['output']}")

    run_pipeline(topic, 7, show, threading.Event())
