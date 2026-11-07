# GPT: read this on every wake-up

You act for the developer. He talks to you; you work through this repo.
A daemon on his PC (D:\gitlink) runs tasks from ue_tasks/inbox and reports back.

## Every wake-up
1. Read docs/REQUESTS.md (his requests, newest at the bottom).
2. Read ue_tasks/STATUS.md and any new ue_tasks/results/*.json.
3. Continue the newest open request, otherwise the first open item in docs/BACKLOG.md.
4. If nothing is new and nothing is waiting, do nothing. No empty commits.

## Rules
- Run things on the PC only through ue_tasks/inbox (see ue_tasks/PROTOCOL.md).
- Never edit ue_tasks/done/, ue_tasks/results/ or ue_tasks/STATUS.md.
- Wait for a result before sending a task that depends on it.
- Stay inside D:\gitlink. Ask in REQUESTS.md before installing software or deleting anything.
- Engine is Unreal 5.8. Check Python API names against ue_tasks/reference/unreal_api.py once it exists.
- Put every non-obvious choice in docs/DECISIONS.md. Keep docs/BACKLOG.md up to date.
- Under each request in REQUESTS.md, add a short "-> done: ..." or "-> blocked: ..." line.
