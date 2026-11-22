# Wireframes

Plain-text layouts of each screen. [ ] is a button, ( ) a field, * marks the primary action.

## Layout (all logged-in pages)

+----------+----------------------------------------------+
| AgentOS  |                                              |
| Dashboard|   page content (p-8, gray-50)                |
| Agents   |                                              |
| Runs     |                                              |
| Knowledge|                                              |
| Memory   |                                              |
| Schedule |                                              |
| [Logout] |                                              |
+----------+----------------------------------------------+

## Login / Register

+------------------------------+
|        [logo] AgentOS        |
|  Email    (_______________)  |
|  Password (_______________)  |
|  [*Log in]   Create account  |
+------------------------------+

## Agents list

Agents                                   [*New agent]
+---------------------------------------------------+
| Research Bot   web_search  csv_reader  [Run][Edit][Delete] |
| Instructions: first line...                        |
+---------------------------------------------------+
(empty: "No agents yet. Create your first agent.")

## Create / edit agent

Name         (_____________)
Instructions (multi-line)
Tools        [x] Web search  [x] Calculator  [x] CSV reader  [ ] Code
Permissions  each ticked tool: ( Auto | Ask | Blocked )
[*Save]  [Cancel]

CSV files (edit page only)
  sales.csv (12 KB)                    [Delete]
  [Upload CSV]

## Runs list

Runs                                     [*New run]
+---------------------------------------------------+
| Summarise Sales.csv                        [Done] |
| Research Bot - 22 Nov 2026, 10:42                 |
+---------------------------------------------------+

## New run

Model ready: qwen2.5   (or an amber warning)
Agent (Research Bot v)
Task  (multi-line, max 2000 characters)
[*Start run]

## Run page

< All runs
Summarise Sales.csv
[Running] Agent: Research Bot  Started 10:42  Running for 12s      [Stop run]

+- Approval card (amber, only when a tool asks) ---------+
| The agent wants to use Code                           |
| { "code": "print(1+1)" }                              |
| [*Approve] [Reject]                                   |
+-------------------------------------------------------+

Result (green) or error (red) card when finished

Steps                              Details
+-----------+                      +--------------------------+
| Task      |                      | Code  [Done]  0.4s       |
+-----------+                      | Why: need the total      |
     v                             | Input: { ... }           |
+-----------+                      | Output: { ... }          |
| Plan      |                      +--------------------------+
+-----------+
     v
+-----------+
| Code      |  <- click to see details
+-----------+
     v
+-----------+
| Answer    |
+-----------+

## Knowledge (planned)

Upload (drop a PDF or text file)  [*Upload]
Documents: name - size - date - [Delete]

## Memory (planned)

List of saved memories per agent: text - date - [Delete]

## Schedule (planned)

New schedule: Agent, Task, Repeat (daily / weekly), Time   [*Save]
List: next run time, last status, [Pause] [Delete]

## Dashboard (planned)

[Agents: 3] [Runs today: 7] [Success rate: 86%] [Waiting approval: 1]
Chart: runs per day (last 7 days)
Recent runs (5)
