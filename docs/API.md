# AgentOS API reference

_Generated from the running app by `docs/generate_api_docs.py`. Do not edit by hand._

Interactive version (try the endpoints in the browser): http://localhost:8000/docs

**Login:** call `POST /auth/login`, copy the `token`, and send it with every request as `Authorization: Bearer <token>`. In `/docs` press the **Authorize** button and paste the token.

Total: 35 endpoints.

## agents

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/agents` | List Agents | yes |
| POST | `/agents` | Create Agent | yes |
| DELETE | `/agents/{agent_id}` | Delete Agent | yes |
| GET | `/agents/{agent_id}` | Get Agent | yes |
| PUT | `/agents/{agent_id}` | Update Agent | yes |

## approval

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/runs/{run_id}/approvals` | Pending Approvals | yes |
| POST | `/runs/{run_id}/steps/{step_id}/approve` | Approve | yes |
| POST | `/runs/{run_id}/steps/{step_id}/reject` | Reject | yes |

## auth

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| POST | `/auth/login` | Login | no |
| GET | `/auth/me` | Me | yes |
| POST | `/auth/register` | Register | no |

## files

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/agents/{agent_id}/files` | List Files | yes |
| POST | `/agents/{agent_id}/files` | Upload File | yes |
| DELETE | `/agents/{agent_id}/files/{name}` | Delete File | yes |

## knowledge

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/agents/{agent_id}/knowledge` | List Knowledge | yes |
| POST | `/agents/{agent_id}/knowledge` | Upload Knowledge | yes |
| GET | `/agents/{agent_id}/knowledge/search` | Search Knowledge | yes |
| DELETE | `/agents/{agent_id}/knowledge/{doc_id}` | Delete Knowledge | yes |

## memory

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/agents/{agent_id}/memory` | List Memory | yes |
| POST | `/agents/{agent_id}/memory` | Add Memory | yes |
| DELETE | `/memory/{memory_id}` | Remove Memory | yes |

## metrics

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/metrics` | Metrics | yes |

## other

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/health` | Health | no |

## runs

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/agents/{agent_id}/runs` | Agent Runs | yes |
| POST | `/agents/{agent_id}/runs` | Start Run | yes |
| GET | `/llm/status` | Llm Status | yes |
| GET | `/runs` | My Runs | yes |
| GET | `/runs/{run_id}` | Run Detail | yes |
| POST | `/runs/{run_id}/stop` | Stop | yes |
| GET | `/runs/{run_id}/stream` | Stream | yes |

## schedule

| Method | Path | What it does | Login needed |
| --- | --- | --- | --- |
| GET | `/schedules` | List Schedules | yes |
| POST | `/schedules` | Create Schedule | yes |
| DELETE | `/schedules/{schedule_id}` | Delete Schedule | yes |
| PATCH | `/schedules/{schedule_id}` | Set Enabled | yes |
| POST | `/schedules/{schedule_id}/run-now` | Run Now | yes |
