# Polls GitHub, runs tasks on this PC, pushes results back. Standard library + Pillow.
import json, os, sys, shutil, subprocess, time, traceback, datetime, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
CFG = load(HERE / "config.json")
if (HERE / "local.json").exists():
    CFG.update(load(HERE / "local.json"))

ROOT, REPO, PROJECT, ENGINE = (Path(CFG[k]) for k in ("root", "repo_dir", "project", "engine"))
EDITOR     = ENGINE / "Engine/Binaries/Win64/UnrealEditor.exe"
EDITOR_CMD = ENGINE / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
BUILD_BAT  = ENGINE / "Engine/Build/BatchFiles/Build.bat"
RC, POLL, GIT = CFG.get("rc_url", "http://127.0.0.1:30010"), CFG.get("poll_sec", 15), CFG.get("git_exe", "git")
NOWIN = 0x08000000  # no console window flashes

TASKS = REPO / "ue_tasks"
INBOX, DONE, RESULTS, RUN = (TASKS / d for d in ("inbox", "done", "results", "run"))
LOGS = ROOT / "logs"
for d in (INBOX, DONE, RESULTS, RUN, LOGS):
    d.mkdir(parents=True, exist_ok=True)
UE_LOG = PROJECT.parent / "Saved" / "Logs" / (PROJECT.stem + ".log")

def now(): return datetime.datetime.now().isoformat(timespec="seconds")
def tail(text, n=200): return "\n".join(text.splitlines()[-n:])
def log(msg):
    with open(LOGS / "daemon.log", "a", encoding="utf-8") as f:
        f.write(f"{now()} {msg}\n")

def run(cmd, timeout=None):
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, errors="replace",
                       timeout=timeout, creationflags=NOWIN)
    return p.returncode, p.stdout + p.stderr

def git(*args): return run([GIT, *args])

def require_unreal():
    if not EDITOR.exists():  raise RuntimeError(f"Unreal Engine not found at {ENGINE}")
    if not PROJECT.exists(): raise RuntimeError(f"Project not found at {PROJECT}")

# ---------- Unreal helpers ----------
def editor_alive():
    try:
        urllib.request.urlopen(RC + "/remote/info", timeout=2)
        return True
    except Exception:
        return False

def rc_python(code):
    body = json.dumps({"objectPath": "/Script/PythonScriptPlugin.Default__PythonScriptLibrary",
                       "functionName": "ExecutePythonCommand",
                       "parameters": {"PythonCommand": code}}).encode()
    req = urllib.request.Request(RC + "/remote/object/call", data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}

def log_size(): return UE_LOG.stat().st_size if UE_LOG.exists() else 0
def log_since(offset):
    if not UE_LOG.exists(): return ""
    if UE_LOG.stat().st_size < offset: offset = 0
    with open(UE_LOG, "rb") as f:
        f.seek(offset)
        return f.read().decode("utf-8", "replace")

# ---------- task handlers: return (ok, output) ----------
def t_ping(task):
    free_gb = shutil.disk_usage(ROOT).free / 1e9
    return True, "\n".join([
        f"daemon alive: {now()}",
        f"engine installed: {EDITOR.exists()} ({ENGINE})",
        f"project exists: {PROJECT.exists()} ({PROJECT})",
        f"editor running: {editor_alive()}",
        f"python: {sys.version.split()[0]}",
        f"free space on {ROOT.drive}: {free_gb:.0f} GB"])

def t_powershell(task):
    code, out = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", task["code"]],
                    timeout=task.get("timeout", 1800))
    return code == 0, tail(out)

def t_python(task):
    require_unreal()
    script = RUN / f"{task['id']}.py"
    script.write_text(task["code"], encoding="utf-8")
    if editor_alive():
        start = log_size()
        resp = rc_python(f'exec(open(r"{script}", encoding="utf-8").read())')
        time.sleep(1)
        return bool(resp.get("ReturnValue", False)), tail(log_since(start))
    code, out = run([str(EDITOR_CMD), str(PROJECT), "-run=pythonscript", f"-script={script}",
                     "-unattended", "-nopause", "-nosplash"], timeout=3600)
    return code == 0, tail(out)

def t_launch_editor(task):
    require_unreal()
    if editor_alive(): return True, "Editor already running"
    subprocess.Popen([str(EDITOR), str(PROJECT), "-ExecCmds=WebControl.StartServer"])
    for _ in range(120):
        time.sleep(5)
        if editor_alive(): return True, "Editor running, Remote Control up"
    return False, "Timed out waiting for Remote Control (is the RemoteControl plugin enabled?)"

def t_close_editor(task):
    if not editor_alive(): return True, "Editor was not running"
    try:
        rc_python("import unreal\nunreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)\n"
                  "unreal.SystemLibrary.quit_editor()")
    except Exception:
        pass  # connection drops when the editor quits
    for _ in range(60):
        time.sleep(2)
        if not editor_alive(): return True, "Editor closed"
    return False, "Editor still running (a dialog may be open; send a screenshot task)"

def t_build(task):
    require_unreal()
    target = task.get("target", PROJECT.stem + "Editor")
    code, out = run([str(BUILD_BAT), target, "Win64", task.get("config", "Development"),
                     f"-Project={PROJECT}", "-WaitMutex"], timeout=7200)
    return code == 0, tail(out, 150)

def t_screenshot(task):
    from PIL import ImageGrab
    out = RESULTS / f"{task['id']}.png"
    ImageGrab.grab().save(out)
    return True, f"Saved {out.relative_to(REPO).as_posix()}"

def t_restart_daemon(task): return True, "Restarting with the latest code"

HANDLERS = {"ping": t_ping, "powershell": t_powershell, "python": t_python,
            "launch_editor": t_launch_editor, "close_editor": t_close_editor, "build": t_build,
            "screenshot": t_screenshot, "restart_daemon": t_restart_daemon}

# ---------- main loop ----------
def process(path):
    try:
        task = load(path)
    except Exception:
        task = {}
    task.setdefault("id", path.stem)
    ttype = task.get("type", "missing")
    try:
        if ttype not in HANDLERS: raise RuntimeError(f"Unknown task type: {ttype}")
        ok, out = HANDLERS[ttype](task)
    except Exception as e:
        ok, out = False, f"{type(e).__name__}: {e}\n{tail(traceback.format_exc(), 20)}"
    result = {"id": task["id"], "type": ttype, "ok": ok, "finished": now(), "output": out}
    (RESULTS / f"{task['id']}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    path.replace(DONE / path.name)
    log(f"{task['id']} {ttype} ok={ok}")
    return result

def write_status(history):
    lines = ["# Daemon status", "", f"- Updated: {now()}",
             f"- Engine installed: {EDITOR.exists()}", f"- Project exists: {PROJECT.exists()}",
             f"- Editor running: {editor_alive()}", "", "## Recent tasks"]
    lines += [f"- `{r['id']}` {r['type']}: {'OK' if r['ok'] else 'FAILED'}" for r in history[-15:]]
    (TASKS / "STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def push(msg):
    git("add", "-A", "ue_tasks")
    if git("commit", "-m", msg)[0] != 0:
        return  # nothing to commit
    if git("push")[0] != 0:
        git("pull", "--rebase", "--autostash")
        git("push")

def main():
    log("daemon started")
    history, first = [], True
    while True:
        restart = False
        try:
            git("pull", "--rebase", "--autostash")
            tasks = sorted(INBOX.glob("*.json"))
            for t in tasks:
                r = process(t)
                history.append(r)
                if r["type"] == "restart_daemon":
                    restart = True
                    break
            if tasks or first:
                write_status(history)
                push("daemon: " + (f"{len(tasks)} task(s)" if tasks else "started"))
                first = False
        except Exception:
            log(traceback.format_exc())
        if restart:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        time.sleep(POLL)

if __name__ == "__main__":
    main()
