"""The workers: two LangChain agents (search, reader) and three prompt chains (writer, critic, reviser)."""
import json

from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .llm import get_model
from .tools import scrape_url, web_search


# ---------------- helpers ----------------

class ToolProgress(BaseCallbackHandler):
    """LangChain callback that reports every tool call so the UI can show live progress."""

    raise_error = True  # lets a cancellation raised in on_tool propagate and stop the agent

    def __init__(self, on_tool):
        self.on_tool = on_tool

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or ""
        args = kwargs.get("inputs")
        if not isinstance(args, dict):
            try:
                args = json.loads(input_str)
            except (TypeError, ValueError):
                args = {}
        self.on_tool(name, args)


def _last_text(result: dict) -> str:
    content = result["messages"][-1].content
    if isinstance(content, list):  # some models return content blocks
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content


def _run_agent(agent, user_message: str, on_tool) -> str:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"callbacks": [ToolProgress(on_tool)], "recursion_limit": 12},
    )
    return _last_text(result)


def _run_chain(prompt, variables: dict) -> str:
    return (prompt | get_model() | StrOutputParser()).invoke(variables)


# ---------------- Agents (they choose which tools to call) ----------------

def search_agent(topic: str, on_tool) -> str:
    agent = create_agent(
        model=get_model(),
        tools=[web_search],
        system_prompt=(
            "You are a research assistant. Use the web_search tool (you may call it more than once "
            "with different queries) and return the findings as a list of Title / URL / key facts."
        ),
    )
    return _run_agent(agent, f"Find recent, reliable, detailed information about: {topic}", on_tool)


def reader_agent(topic: str, search_results: str, on_tool) -> str:
    agent = create_agent(
        model=get_model(),
        tools=[scrape_url],
        system_prompt=(
            "You are a careful reader. Scrape the 2-3 most relevant URLs with the scrape_url tool, then "
            "summarise the key facts, figures and quotes from each page, keeping the source URL next to each summary."
        ),
    )
    return _run_agent(
        agent,
        f"Topic: {topic}\n\nSearch results:\n{search_results}\n\nPick the most relevant URLs and read them in depth.",
        on_tool,
    )


# ---------------- Chains (single prompt -> single answer) ----------------

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured, insightful reports."),
    ("human", """Write a detailed research report.

Topic: {topic}

Research gathered:
{research}

Structure (use Markdown headings):
## Introduction
## Key Findings  (at least 3 well-explained points)
## Conclusion
## Sources  (list every URL you relied on)

Only state facts supported by the research above."""),
])

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp, constructive research critic. Be honest and specific."),
    ("human", """Review this report strictly.

Report:
{report}

Respond in exactly this format:
Score: X/10
Strengths:
- ...
Areas to Improve:
- ...
One line verdict:
..."""),
])

reviser_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert editor improving research reports."),
    ("human", """Rewrite the report so it addresses the critic's feedback.
Keep the same structure and do not invent new facts or sources.

Report:
{report}

Critic feedback:
{feedback}"""),
])


def write_report(topic: str, research: str) -> str:
    return _run_chain(writer_prompt, {"topic": topic, "research": research})


def critique(report: str) -> str:
    return _run_chain(critic_prompt, {"report": report})


def revise(report: str, feedback: str) -> str:
    return _run_chain(reviser_prompt, {"report": report, "feedback": feedback})
