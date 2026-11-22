# AgentOS demo script (about 6 minutes)

## Before you start

1. docker compose up -d (Postgres and Redis), then python -m contracts.seed (creates tables).
2. Start the backend: uvicorn backend.main:app --reload (port 8000).
3. Start the frontend: npm run dev inside frontend (port 3000).
4. Start Ollama and make sure the model is pulled: ollama pull qwen2.5
5. Keep a small CSV ready, for example sales.csv with columns date, product, amount.
6. Open http://localhost:3000, register a new user, log in.

## Script

| Time | Say | Do |
|------|-----|----|
| 0:00 | "AgentOS lets you build an AI agent and watch every step it takes." | Show the Dashboard and the sidebar. |
| 0:30 | "First I create an agent." | Agents > New agent. Name: Data Helper. Tick Calculator, CSV reader and Code. Leave Code on Ask. Save. |
| 1:15 | "Now I give it a file to read." | Open the agent (Edit), upload sales.csv in the CSV files panel. |
| 1:45 | "Let us give it a task." | Runs > New run. Agent: Data Helper. Task: "Read sales.csv and tell me the total amount per product." Point at the green "Model ready" line. Start run. |
| 2:15 | "The graph updates live: plan, then tool calls." | Show the Plan node, then the CSV reader node. Click it and show Input and Output. |
| 3:15 | "Code is a risky tool, so the run pauses and asks me." | Show the amber approval card. Read the code aloud. Click Approve. |
| 4:00 | "The agent continues and gives the final answer." | Show the green Result card and the Final answer node. |
| 4:30 | "I can reject or stop at any time." | Start a second run with a task that needs code. Click Reject, show the run explains what happened. (Or click Stop run.) |
| 5:15 | "Everything is saved." | Open Runs list and show both runs with their status. |
| 5:45 | "Tech: Next.js, FastAPI, LangGraph and a local Ollama model, 84 backend tests." | Show the slides, last two slides. |

## If something goes wrong

- Amber "model is not ready" warning: Ollama is not running or the model is missing. Run: ollama serve and ollama pull qwen2.5.
- Run fails with a format error: the model gave a bad reply twice. Start the run again, or use a shorter task.
- Nothing happens after Approve: refresh the run page; it falls back to polling and shows the latest state.
- Keep a screen recording of one good run as a backup.

## Questions to expect

- Where does data go? Nowhere outside the machine; the model is local.
- What stops the agent looping? A limit of 8 steps and 5 minutes per run.
- Can a user see another user's agents? No; every endpoint checks the owner.
