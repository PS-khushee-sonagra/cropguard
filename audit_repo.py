"""audit_repo.py - run from the project folder:  python audit_repo.py
Checks the repo against the Weekend Wizard lab pattern and basic hygiene. Read-only: it changes nothing."""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path.cwd()
results = []

def add(status, name, detail=""):
    results.append((status, name, detail))

def git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)
        return r.returncode, r.stdout
    except FileNotFoundError:
        return 1, ""

def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

# 1. required files
for f in ["README.md", "requirements.txt", ".gitignore", ".env.example", "server.py", "agent.py",
          "diagnose.py", "check_data.py"]:
    add("PASS" if (ROOT / f).exists() else "FAIL", f"file exists: {f}")
data_files = sorted((ROOT / "Data").glob("*.json")) if (ROOT / "Data").exists() else []
add("PASS" if data_files else "FAIL", "Data/ has crop JSON files", f"{len(data_files)} found")

# 2. git: tracked files and history
code, out = git("ls-files")
if code != 0:
    add("FAIL", "this folder is a git repository", "run git init, or run this script from the repo folder")
    tracked = []
else:
    tracked = out.splitlines()
    bad = [t for t in tracked if t == ".env" or t.startswith(("venv/", ".venv/", "Uploads/", "__pycache__/"))
           or t == "chats.json" or "/__pycache__/" in t]
    add("FAIL" if bad else "PASS", "no secrets, venv, uploads or chats tracked", ", ".join(bad[:6]))
    _, hist = git("log", "--all", "--pretty=format:", "--name-only")
    ever = sorted({h for h in hist.splitlines() if h.strip() in (".env", "chats.json") or h.startswith("Uploads/")})
    add("FAIL" if ever else "PASS", ".env / chats / uploads never committed in history", ", ".join(ever[:6]))

# 3. secret scan in tracked text files
PATTERNS = [r"AIza[0-9A-Za-z_\-]{30,}", r"AQ\.[A-Za-z0-9_\-]{30,}", r"sk-[A-Za-z0-9]{20,}", r"ghp_[A-Za-z0-9]{30,}",
            r"GEMINI_API_KEY\s*=\s*[\"']?(?!put-your-key-here)[A-Za-z0-9_\-\.]{25,}"]
hits = []
for t in tracked:
    if t.endswith((".png", ".jpg", ".jpeg", ".webp", ".pdf")):
        continue
    text = read(ROOT / t)
    for pat in PATTERNS:
        if re.search(pat, text):
            hits.append(t)
            break
add("FAIL" if hits else "PASS", "no API keys inside tracked files", ", ".join(hits[:6]))

# 4. README hygiene
readme = read(ROOT / "README.md")
leftovers = [p for p in ["<your-username>", "_fill in_", "TODO"] if p in readme]
add("WARN" if leftovers else "PASS", "README has no leftover placeholders", ", ".join(leftovers))
if "TESTS.md" in readme and not (ROOT / "TESTS.md").exists():
    add("WARN", "README mentions TESTS.md but the file is missing")
add("PASS" if re.search(r"1800-180-1551", readme) and re.search(r"not a replacement", readme, re.I) else "WARN",
    "README has the safety disclaimer and helpline")

# 5. Weekend Wizard pattern (heuristic text checks)
server, agent = read(ROOT / "server.py"), read(ROOT / "agent.py")
add("PASS" if re.search(r"FastMCP|MCPServer", server) else "FAIL", "server.py is an MCP server")
n_tools = len(re.findall(r"@mcp\.tool", server))
add("PASS" if n_tools >= 3 else "FAIL", "server.py exposes at least 3 MCP tools", f"{n_tools} found")
add("FAIL" if re.search(r"^\s*print\(", server, re.M) else "PASS", "server.py has no print() (breaks MCP stdio)")
add("PASS" if "list_tools" in agent else "FAIL", "agent.py discovers tools from the MCP server (list_tools)")
add("PASS" if "call_tool" in agent else "FAIL", "agent.py calls tools through MCP (call_tool)")
add("PASS" if re.search(r"[\"']final[\"']", agent) else "FAIL", "agent.py has the final/stop action in its loop")
add("PASS" if re.search(r"reflect", agent, re.I) else "FAIL", "agent.py has a reflection step")
add("PASS" if "input(" in agent else "WARN", "agent.py is a command-line loop (input())")
add("PASS" if re.search(r"range\(\s*\d+\s*\)", agent) else "WARN", "agent.py has a loop limit")
add("PASS" if "ollama" in agent.lower() else "WARN", "agent.py uses a local Ollama model")
add("PASS" if "Connected tools" in agent else "WARN", "agent.py prints the connected tool list (lab transcript)")

# 6. data files and stale references
bad_json = []
for f in data_files:
    try:
        json.load(open(f, encoding="utf-8"))
    except Exception as e:
        bad_json.append(f.name)
add("FAIL" if bad_json else "PASS", "all Data/*.json files are valid JSON", ", ".join(bad_json))
stale = [str(p.relative_to(ROOT)) for p in ROOT.glob("*.py") if "treatments.json" in read(p)]
stale += ["README.md"] if "treatments.json" in readme else []
add("WARN" if stale else "PASS", "no code still reads treatments.json", ", ".join(stale))

# 7. report
order = {"FAIL": 0, "WARN": 1, "PASS": 2}
for s, n, d in sorted(results, key=lambda r: order[r[0]]):
    print(f"[{s}] {n}" + (f"  ->  {d}" if d else ""))
print(f"\n{sum(r[0]=='PASS' for r in results)} pass, {sum(r[0]=='WARN' for r in results)} warn, "
      f"{sum(r[0]=='FAIL' for r in results)} fail")
sys.exit(1 if any(r[0] == "FAIL" for r in results) else 0)