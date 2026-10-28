# CropGuard

CropGuard is a Streamlit crop-assistance prototype for farmers in India. It combines an Ollama-powered agent, MCP tools, image analysis, weather observations, and crop-specific reference data. It is an informational project, not a substitute for an agricultural expert.

## Features

- **Photo assessment:** Sends a crop photo and the farmer's description to Gemini for a structured image assessment. The result is a possibility, not a confirmed diagnosis.
- **Tool-using agent:** The agent discovers tools from the MCP server at runtime, decides which tools are relevant, and uses their results as evidence for its reply. The loop is limited to eight steps.
- **Weather checks:** Looks up a named location when needed and fetches current humidity and recent rainfall from Open-Meteo. Weather is context only and does not establish a crop disease.
- **Follow-up safeguards:** Follow-up replies are checked against case evidence, crop context, and chemical/dose safety rules. If a weather-only draft cannot be accepted, the agent can return a fallback based on the fetched weather values.
- **Hindi and Gujarati interface:** The UI supports English, Hindi, and Gujarati; translation uses the configured local Ollama model.
- **Local chat interface:** Streamlit provides crop-specific chats, location settings, and photo upload.

## Architecture

```text
Streamlit UI (app.py)
    |
    +-- Agent loop (agent_core.py) -- Ollama: mistral:7b
    |       |
    |       +-- starts the stdio MCP server (server.py)
    |               +-- diagnose_image: Gemini image assessment
    |               +-- city_to_coords / get_weather: Open-Meteo
    |               +-- lookup_treatment: local Data/*.json files
    |
    +-- Hindi/Gujarati translation (lang.py) -- Ollama: gemma3:4b by default
```

The application starts the MCP server as a subprocess; you do not need to start it separately. The agent calls `list_tools()` to discover available tools and invokes selected tools through the MCP client. Weather-only replies are reviewed against the observations before being returned.

## Requirements

- Python with `pip`
- [Ollama](https://ollama.com/) running locally
- A Gemini API key for photo assessment
- Internet access for Gemini and Open-Meteo requests

The agent model is `mistral:7b`. The translation model defaults to `gemma3:4b` and can be changed with `TRANSLATE_MODEL`.

## Setup and run

From the repository root, create and activate a virtual environment, then install the pinned dependencies.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pull the local models:

```text
ollama pull mistral:7b
ollama pull gemma3:4b
```

Create a local `.env` file and set the Gemini key:

```text
GEMINI_API_KEY=your-gemini-api-key
```

`diagnose.py` loads `.env` from the repository root. Do not commit `.env` or share API keys. Weather and geocoding use Open-Meteo and do not require an API key.

Start the app from the repository root:

```text
streamlit run app.py
```

Streamlit prints a local URL in the terminal. Open it in your browser, start a chat for one crop, and optionally set a city or coordinates in the sidebar. For photo assessment, attach a crop photo and describe what you observe. For weather, ask about weather, humidity, or rainfall and provide a location.

## Data and safety limitations

**The crop-treatment data is not fully expert-reviewed.** Some entries are explicitly marked `verified_by: "not yet"` and describe themselves as drafts. The current lookup path can still return those entries, so do not treat treatment or pesticide information from this prototype as verified advice, and do not apply a product based on it. Confirm crop-specific and locally approved guidance with your KVK or agriculture officer before taking action.

`python check_data.py` checks the JSON data and prints warnings for entries not yet reviewed by an expert, but currently exits successfully even when such warnings are present. A successful command exit is not evidence that the data has been expert-approved.

Other important limits:

- Image results are automated hypotheses and may be incorrect; use a clear photo and verify uncertain findings with an agricultural expert.
- Weather-derived fungal risk is a rough rule-of-thumb indicator, not an agronomic forecast or disease diagnosis.
- The project does not replace professional diagnosis, product labels, or locally approved recommendations.

## Validation

Run the automated tests and basic checks from the repository root:

```text
python -m pytest -q
python -m compileall -q .
python audit_repo.py
python check_data.py
```

`audit_repo.py` and `check_data.py` may report warnings that need human review even if the commands exit successfully.

## Project structure

| Path | Purpose |
|---|---|
| `app.py` | Streamlit user interface |
| `agent_core.py` | Agent loop, MCP client, evidence checks, and follow-up safeguards |
| `server.py` | MCP server and diagnosis, weather, geocoding, and crop-data tools |
| `diagnose.py` | Gemini image assessment and response validation |
| `lang.py` | Hindi/Gujarati translation and multilingual chat support |
| `Data/` | Crop-specific JSON reference data |
| `tests/test_agent_core.py` | Agent behavior and safety tests |

## Author

**Khushee Sonagra** — [GitHub](https://github.com/PS-khushee-sonagra)
