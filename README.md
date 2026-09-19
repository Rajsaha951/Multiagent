# ResearchMind — Multi-Agent Research System

ResearchMind is a multi-agent AI research system that automates the process of researching a topic, extracting information from web sources, generating a structured report, and critically reviewing the result.

The system uses LangChain agents and prompt chains coordinated through a FastAPI backend, while the frontend provides a live view of the research pipeline using Server-Sent Events (SSE).

## Features

* Web Search Agent — searches the web for relevant and recent sources using Tavily.
* Reader Agent — opens selected sources and extracts useful information.
* Writer Agent — generates a structured Markdown research report.
* Critic Agent — evaluates the generated report and provides a score with improvement suggestions.
* Reviser Agent — improves the report when the critic's score is below the required threshold.
* Real-Time Progress — streams agent activity to the browser using Server-Sent Events.
* SSRF Protection — validates URLs before allowing the scraping tool to access them.
* Docker Support — run the application using Docker Compose.
* LLM Flexibility — supports OpenAI-compatible APIs and Google Gemini.

## Architecture

```text
                         User
                           |
                           v
                    +-------------+
                    |  Web Client |
                    +------+------+
                           | SSE
                           v
                    +-------------+
                    |   FastAPI   |
                    +------+------+
                           |
                           v
                  +------------------+
                  | Research Pipeline|
                  +--------+---------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
      +--------+      +--------+      +--------+
      | Search | ---> | Reader | ---> | Writer |
      +--------+      +--------+      +----+---+
                                          |
                                          v
                                     +---------+
                                     |  Critic |
                                     +----+----+
                                          |
                              Score below threshold?
                                    |          |
                                   Yes         No
                                    |          |
                                    v          v
                               +---------+   Report
                               | Reviser |
                               +----+----+
                                    |
                                    v
                                  Report
```

## How It Works

1. The user enters a research topic through the web interface.
2. The Search Agent finds relevant web sources using Tavily.
3. The Reader Agent opens selected pages and extracts useful information.
4. The Writer Agent combines the collected information into a structured Markdown report.
5. The Critic Agent evaluates the report and identifies weaknesses or missing information.
6. If the report does not meet the required quality threshold, the Reviser Agent improves it.
7. The final report and pipeline progress are streamed back to the browser in real time.

## Tech Stack

| Layer              | Technology                      |
| ------------------ | ------------------------------- |
| Language           | Python                          |
| Agent Framework    | LangChain                       |
| Backend            | FastAPI                         |
| LLM                | OpenAI / OpenAI-compatible APIs |
| Alternative LLM    | Google Gemini                   |
| Web Search         | Tavily                          |
| Web Scraping       | Custom LangChain Tool           |
| Communication      | Server-Sent Events (SSE)        |
| Frontend           | HTML, CSS, JavaScript           |
| Containerization   | Docker, Docker Compose          |
| Markdown Rendering | Marked.js                       |
| Sanitization       | DOMPurify                       |

## Future Improvements

* Parallel execution of independent research tasks
* Persistent research history
* Source citation management
* More specialized research agents
* Human-in-the-loop review
* Authentication and user accounts
* Background job processing
* Improved source quality evaluation
* Observability and agent execution metrics

## License

This project is intended for educational and experimental purposes.
