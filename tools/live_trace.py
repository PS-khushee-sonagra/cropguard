import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path

# Configure stdout UTF-8 with errors="replace"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

class Tee(io.TextIOWrapper):
    def __init__(self, file_path, stream):
        self.file = open(file_path, "w", encoding="utf-8", errors="replace")
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.file.write(data)
        self.flush()

    def flush(self):
        self.stream.flush()
        self.file.flush()

    def close(self):
        self.file.close()

# Ensure docs directory exists
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
DOCS_DIR.mkdir(exist_ok=True)
TRACE_FILE = DOCS_DIR / "live_trace.txt"

tee = Tee(TRACE_FILE, sys.stdout)
sys.stdout = tee

# 1. Print header with metadata and library versions
import importlib.metadata
from datetime import datetime

try:
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception as e:
    commit_sha = f"Unknown: {e}"

def get_pkg_ver(pkg):
    try:
        return importlib.metadata.version(pkg)
    except Exception:
        if pkg == "fastmcp":
            try:
                return f"{importlib.metadata.version('mcp')} (fastmcp via mcp)"
            except Exception:
                pass
        return "N/A"

mcp_ver = get_pkg_ver("mcp")
ollama_ver = get_pkg_ver("ollama")
streamlit_ver = get_pkg_ver("streamlit")
fastmcp_ver = get_pkg_ver("fastmcp")
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print("================================================================================")
print("CROPGUARD LIVE END-TO-END EXECUTION TRACE")
print("================================================================================")
print(f"Git Commit SHA   : {commit_sha}")
print(f"Date and Time    : {now_str}")
print(f"Model Name       : mistral:7b")
print(f"Python Version   : {sys.version.splitlines()[0]}")
print(f"Library Versions : mcp={mcp_ver}, ollama={ollama_ver}, streamlit={streamlit_ver}, fastmcp={fastmcp_ver}")
print(f"Command          : {sys.executable} tools/live_trace.py")
print("Environment      : Windows, Local Ollama mistral:7b, FastMCP server.py, Open-Meteo API")
print("================================================================================\n")

# Set ample timeout for local Ollama mistral:7b inference
os.environ["OLLAMA_TIMEOUT"] = "180"

# Import agent_core from repo
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import agent_core

# Instrument logging hooks for tool calls, observations, and reflection
orig_llm_json = agent_core.llm_json
tools_called_in_turn = []

def logging_llm_json(messages, tool_names):
    decision = orig_llm_json(messages, tool_names)
    action = decision.get("action")
    if action and action != "final":
        tools_called_in_turn.append(action)
        print(f"MODEL SELECTED TOOL: {action}")
        print(f"TOOL ARGUMENTS     : {json.dumps(decision.get('args', {}), ensure_ascii=False)}")
    else:
        print("MODEL SELECTED ACTION: final")
    return decision

agent_core.llm_json = logging_llm_json

orig_validate_tool = agent_core._validate_tool_result
last_weather_observation = None

def logging_validate_tool(name, result, tool, crop="", disease_key=""):
    global last_weather_observation
    data = orig_validate_tool(name, result, tool, crop=crop, disease_key=disease_key)
    print(f"TOOL OBSERVATION ({name}):")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    if name == "get_weather":
        last_weather_observation = data
    return data

agent_core._validate_tool_result = logging_validate_tool

orig_reflect = agent_core._reflect

def logging_reflect(report, observations):
    res = orig_reflect(report, observations)
    print(f"REFLECTION EVALUATION:\n{res}")
    return res

agent_core._reflect = logging_reflect

async def main():
    global tools_called_in_turn, last_weather_observation

    # Conversation initialization
    conv = {
        "crop": "Tomato",
        "context": agent_core.new_context("Tomato"),
        "memory": [],
        "created": 1,
        "safety_version": 1,
    }
    conv["context"]["city"] = "New Delhi"

    # -------------------------------------------------------------------------
    # TURN (a): Weather query for tomato crop
    # -------------------------------------------------------------------------
    turn_a_query = "What is the current weather in New Delhi for my tomato crop? Report the humidity and rainfall."
    print("--------------------------------------------------------------------------------")
    print(f"TURN (a) USER MESSAGE: {turn_a_query}")
    print("--------------------------------------------------------------------------------")
    tools_called_in_turn = []
    last_weather_observation = None

    result_a = await agent_core.chat_turn(
        conversation=conv,
        user_text=turn_a_query,
        image_path=None,
        on_step=lambda s: print(f"STEP: {s}"),
    )

    print("\nFINAL REPLY (a):")
    print(result_a.get("reply", ""))
    print("--------------------------------------------------------------------------------\n")

    # Validate Turn (a)
    reply_a = result_a.get("reply", "")
    assert last_weather_observation is not None, "Turn (a) failed to fetch weather observation!"
    humidity = last_weather_observation.get("relative_humidity_2m")
    rainfall = last_weather_observation.get("rain_last_3_days_mm")
    assert humidity is not None, "Humidity missing in weather observation!"
    assert rainfall is not None, "Rainfall missing in weather observation!"

    humidity_str = f"{humidity:g}" if isinstance(humidity, (int, float)) else str(humidity)
    rainfall_str = f"{rainfall:g}" if isinstance(rainfall, (int, float)) else str(rainfall)

    print(f"[VALIDATION TURN (a)] Fetched humidity: {humidity_str}%, rain_last_3_days: {rainfall_str} mm")
    if humidity_str not in reply_a and str(humidity) not in reply_a:
        print(f"WARNING: humidity value {humidity} not explicitly matched verbatim in reply.")
    if rainfall_str not in reply_a and str(rainfall) not in reply_a:
        print(f"WARNING: rainfall value {rainfall} not explicitly matched verbatim in reply.")

    # -------------------------------------------------------------------------
    # TURN (b): Out-of-domain query
    # -------------------------------------------------------------------------
    turn_b_query = "Who won the cricket match?"
    print("--------------------------------------------------------------------------------")
    print(f"TURN (b) USER MESSAGE: {turn_b_query}")
    print("--------------------------------------------------------------------------------")
    tools_called_in_turn = []

    result_b = await agent_core.chat_turn(
        conversation=conv,
        user_text=turn_b_query,
        image_path=None,
        on_step=lambda s: print(f"STEP: {s}"),
    )

    print("\nFINAL REPLY (b):")
    print(result_b.get("reply", ""))
    print("--------------------------------------------------------------------------------\n")

    # Validate Turn (b)
    disallowed_tools = {"get_weather", "diagnose_image"}
    called_disallowed = disallowed_tools.intersection(tools_called_in_turn)
    print(f"[VALIDATION TURN (b)] Tools called in turn (b): {tools_called_in_turn}")
    assert not called_disallowed, f"Turn (b) inappropriately invoked tools: {called_disallowed}"

    print("================================================================================")
    print("LIVE TRACE COMPLETED AND VALIDATED SUCCESSFULLY")
    print("================================================================================")

if __name__ == "__main__":
    asyncio.run(main())
