# Task protocol
One task = one NEW file: ue_tasks/inbox/NNNN.json (4 digits, next free number).
Result appears in ue_tasks/results/NNNN.json ("ok", "output"), usually within 30 s.

| type | fields | does |
|---|---|---|
| ping | | Daemon alive + engine/project/editor state + free disk |
| powershell | code, timeout? | Runs PowerShell in D:\gitlink\ToolShed (git, files, installs) |
| python | code | Unreal Python in the open editor, or headless if the editor is closed |
| launch_editor | | Opens the editor with Remote Control on |
| close_editor | | Saves everything, closes the editor |
| build | target?, config? | Compiles C++ (editor must be closed) |
| screenshot | | Whole-screen PNG to results/NNNN.png |
| restart_daemon | | Reloads tools/ue_daemon.py after you edit it |

Examples:
{"id":"0001","type":"ping"}
{"id":"0002","type":"powershell","code":"git add ToolShedGame; git commit -m 'Add Unreal project'; git push"}
{"id":"0003","type":"python","code":"import unreal\nprint(unreal.SystemLibrary.get_engine_version())"}
