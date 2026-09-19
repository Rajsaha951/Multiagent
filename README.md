# ResearchMind – Multi-Agent Research System (LangChain)

Enter a topic and four LangChain workers run in sequence while you watch live in the browser.

| Stage | Type | Job |
|-------|------|-----|
| 1. Search | LangChain agent + `web_search` (Tavily) | Finds recent sources |
| 2. Reader | LangChain agent + `scrape_url` | Opens the best pages and takes notes |
| 3. Writer | Prompt chain | Drafts a structured Markdown report |
| 4. Critic | Prompt chain | Scores it out of 10 and lists fixes |
| 5. Reviser | Prompt chain (optional) | Rewrites the report if the score is below 7 |

**Stack:** Python · LangChain (`create_agent`, `ChatPromptTemplate`, `StrOutputParser`) · FastAPI · plain HTML/CSS/JS · OpenAI API · Tavily API

## Run with Docker
```bash
cp .env.example .env          # Windows: copy .env.example .env   -> then add your API keys
docker compose up --build     # open http://localhost:8000
```
Keys are read from `.env` at runtime and are **not** baked into the image.
Stop: `Ctrl+C` (or `docker compose down`). After editing `.env`: `docker compose up -d --force-recreate`.

## Run without Docker
```bash
python -m venv .venv
.venv\Scripts\activate         # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # add your keys
python -m uvicorn app.main:app --reload     # open http://localhost:8000
```
Command-line only (no browser): `python -m app.pipeline`

## How it works
1. The browser opens `GET /api/research?topic=…` as an `EventSource` (Server-Sent Events).
2. FastAPI runs the LangChain pipeline in a worker thread and streams one event per step (`step_start`, `tool`, `step_done`, `done`, `error`).
3. A LangChain callback (`on_tool_start`) reports each tool call, so the UI shows "Searching …" / "Reading …" live.
4. `frontend/app.js` turns those events into the progress trace, the report and the critic's score.
5. If the browser tab closes, the pipeline stops before its next step.

## Files
```
app/
  main.py       FastAPI app: /api/health, /api/research (SSE), serves the frontend
  pipeline.py   Runs the stages in order and emits progress events
  agents.py     LangChain agents (create_agent) + prompt chains for every stage
  llm.py        get_model(): the ChatOpenAI model shared by all stages
  tools.py      LangChain tools: web_search (Tavily) and scrape_url (with SSRF protection)
frontend/
  index.html  style.css  app.js  vendor/ (marked + DOMPurify for safe Markdown)
Dockerfile  docker-compose.yml  requirements.txt  .env.example
```

## Using Google Gemini (free tier) instead of OpenAI
Put your Gemini key in `OPENAI_API_KEY` and set `OPENAI_BASE_URL` and `MODEL_NAME` as shown in `.env.example`.
