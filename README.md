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

- Python 3.14 with `pip`
- [Ollama](https://ollama.com/) running locally
- A Gemini API key for photo assessment
- Internet access for Gemini and Open-Meteo requests

The agent model is `mistral:7b`. The translation model defaults to `gemma3:4b` and can be changed with `TRANSLATE_MODEL`.

## Setup and run

### Supported platforms

Tested on Windows 11; macOS/Linux not yet verified.

From the repository root, create and activate a virtual environment, then install the pinned dependencies.

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Command Prompt (cmd.exe)**

```cmd
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
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

Or set the environment variable in your Windows terminal:

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key"

# Command Prompt (cmd.exe)
set GEMINI_API_KEY=your-gemini-api-key
```

`diagnose.py` loads `.env` from the repository root. Do not commit `.env` or share API keys. Weather and geocoding use Open-Meteo and do not require an API key.

Start the app from the repository root:

```text
streamlit run app.py
```

App start command: `streamlit run app.py`

Streamlit prints a local URL in the terminal. Open it in your browser, start a chat for one crop, and optionally set a city or coordinates in the sidebar. For photo assessment, attach a crop photo and describe what you observe. For weather, ask about weather, humidity, or rainfall and provide a location.

## Data and safety limitations

**The crop-treatment data is not fully expert-reviewed.** Some entries are explicitly marked `verified_by: "not yet"` and describe themselves as drafts. The current lookup path can still return those entries, so do not treat treatment or pesticide information from this prototype as verified advice, and do not apply a product based on it. Confirm crop-specific and locally approved guidance with your KVK or agriculture officer before taking action.

`python check_data.py` checks the JSON data and prints warnings for entries not yet reviewed by an expert, but currently exits successfully even when such warnings are present. A successful command exit is not evidence that the data has been expert-approved.
Use `python check_data.py --strict` to exit with status 1 when any treatment entry is unreviewed.

Other important limits:

- Image results are automated hypotheses and may be incorrect; use a clear photo and verify uncertain findings with an agricultural expert.
- Weather-derived fungal risk is a rough rule-of-thumb indicator, not an agronomic forecast or disease diagnosis.
- The project does not replace professional diagnosis, product labels, or locally approved recommendations.

## Worked Example

Illustrative example only; values are not from a real run.

**Farmer Prompt:**
> "I am growing tomatoes in Pune. I see dark concentric rings on the lower leaves. What should I do?"

**Agent Reasoning & Tool Calls:**
1. Discovers connected tools via FastMCP `list_tools`: `diagnose_image`, `city_to_coords`, `get_weather`, `lookup_treatment`.
2. Coordinates lookup: Calls `city_to_coords(city="Pune")` &rarr; Lat: 18.5204, Lon: 73.8567.
3. Weather fetch: Calls `get_weather(latitude=18.5204, longitude=73.8567)` &rarr; Temp: 27.5 °C, Humidity: 68%, Rain (3d): 4.2 mm &rarr; Fungal risk: **MODERATE**.
4. Treatment lookup: Calls `lookup_treatment(disease="tomato early blight")`.
5. Reflection & Safety review: The agent verifies treatment metadata. If the entry has not completed expert agronomic review (`verified_by: "not yet"`), actionable chemical doses are withheld and flagged as draft guidance.

**Output Response:**
> **Possible condition:** Tomato Early Blight (*Alternaria solani*)<br>
> **Observed Symptoms:** Dark concentric target-like rings on lower foliage.<br>
> **Local Weather Risk:** Pune — Moderate fungal development risk due to humidity (68%).<br>
> **Management Guidance:** Remove and destroy infected lower leaves. Ensure proper spacing to improve airflow. Avoid overhead irrigation.<br>
> **Safety Notice:** Treatment guidance withheld or labeled draft pending agronomic verification. Please consult your local Krishi Vigyan Kendra (KVK) or call the Kisan Call Centre at 1800-180-1551 before applying chemical fungicides.

## Troubleshooting

- **Ollama Not Running:**
  - *Symptom:* Connection errors or timeouts (`ConnectionRefusedError: [Errno 111]`) when submitting a prompt.
  - *Fix:* Ensure the Ollama daemon is active. Run `ollama serve` in a terminal or launch the Ollama desktop app, and verify that `ollama list` shows `mistral:7b` and `gemma3:4b`.
- **Gemini API Key Missing:**
  - *Symptom:* Photo diagnosis fails with an error stating `GEMINI_API_KEY is not set`.
  - *Fix:* Create a `.env` file in the project root containing `GEMINI_API_KEY=your_actual_key`, or export the variable in your shell (`$env:GEMINI_API_KEY="..."` on PowerShell).
- **MCP Server Failed to Start:**
  - *Symptom:* Stdio communication failure or subprocess exit when initializing `server.py`.
  - *Fix:* Verify your virtual environment is activated and all dependencies in `requirements.txt` are installed. Run `python server.py` directly to identify any missing module or syntax error.
- **Unknown Treatment or Unreviewed Entry:**
  - *Symptom:* Chat reply states "No verified entry. Contact your KVK" or UI card displays "Treatment guidance withheld pending review".
  - *Fix:* This is an intended safety behavior. When a disease is unlisted or reference data is marked `verified_by: "not yet"`, actionable pesticide advice is withheld to prevent unverified chemical application. Contact your local agricultural extension officer.

## Data and Privacy

- **Local Storage:** Uploaded crop images are saved locally to `Uploads/` with unique identifiers, and chat history is saved locally to `chats.json`.
- **External Transmission:** Only image files and accompanying farmer descriptions submitted for diagnosis are transmitted via encrypted HTTPS to Google's Gemini API. No location data or chat history is transmitted to third parties except coordinate lookups to Open-Meteo.
- **Git Hygiene:** Neither `Uploads/`, `chats.json`, nor `.env` are ever committed to the repository. They are ignored by `.gitignore` and verified by `audit_repo.py`.

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
| `cards.py` | UI card components and rendering logic |
| `agent_core.py` | Agent loop, MCP client, evidence checks, and follow-up safeguards |
| `server.py` | MCP server and diagnosis, weather, geocoding, and crop-data tools |
| `diagnose.py` | Gemini image assessment and response validation |
| `lang.py` | Hindi/Gujarati translation and multilingual chat support |
| `Data/` | Crop-specific JSON reference data |
| `tests/test_agent_core.py` | Agent behavior and safety tests |

## Author

**Khushee Sonagra** — [GitHub](https://github.com/PS-khushee-sonagra)
