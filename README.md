# CropGuard — AI Crop Pest & Disease Risk Advisor 🌾

CropGuard is a grounded agricultural pest and disease advisory system built for farmers and extension officers. It combines an MCP knowledge server, live Open-Meteo weather intelligence, and an autonomous AI agent to assess crop damage and deliver verified Integrated Pest Management (IPM) guidance.

---

## 🚀 Farmer-Friendly Web UI

CropGuard includes a modern, accessible web interface tailored for farmers:

- **Instant Crop Diagnosis (Wizard):** Select Cotton, Tomato, or Wheat, choose affected plant parts (leaves, fruits, stems, flowers), and tap or describe symptoms to get immediate scientific matching, weather vulnerability analysis, and IPM actions.
- **Microphone Voice Input (Speech-to-Text):** Farmers can speak their plant symptoms in English or regional languages without needing to type on small keyboards.
- **Audio Readout (Text-to-Speech):** Listen to diagnostic findings and IPM advice spoken out loud.
- **Multilingual Support:** Available in **English**, **हिंदी (Hindi)**, **मराठी (Marathi)**, **ગુજરાતી (Gujarati)**, **ਪੰਜਾਬੀ (Punjabi)**, and **తెలుగు (Telugu)**.
- **Live Weather & Pest Risk Index:** Real-time Open-Meteo weather integration for Nashik, Ahmedabad, Ludhiana, Pune, Guntur, or any Indian district.
- **Autonomous AI Agronomist Chat:** Interactive copilot powered by Ollama (`llama3.2:3b`) with live multi-step tool execution visualization and transparency inspection.
- **Pest & Disease Field Guide:** Searchable encyclopedia of verified pests, diseases, symptoms, lookalikes, and prevention methods.
- **Farmer Sunlight Day Mode & Agro Dark Mode:** High-contrast toggle for clear visibility under outdoor sunlight.
- **Kisan Call Centre (1800-180-1551) & KVK Directory:** Instant access to district agricultural science centres.

### Starting the Web UI

```bash
# Start the web server
python web_server.py
```

Then open your browser at:
👉 **`http://localhost:8000`**

---

## Demo transcript

Real terminal run, unedited, demonstrating MCP connection, tool discovery,
multi-step tool chaining (search → weather → IPM guidance), the nudge
mechanism correcting a premature stop, and a correctly hedged final answer
grounded in real knowledge-base and weather data.

```
CropGuard — AI Crop Pest & Disease Risk Advisor
Model: llama3.2:3b  |  Type 'exit' or 'quit' to stop.

[connected] discovered 4 tools: get_crop_info, get_ipm_guidance, get_weather, search_pest_disease

Farmer question> My cotton plants in Nashik have small holes bored into the bolls and flowers, with visible caterpillars inside when I open them up.

--- Agent working ---
[iteration 1] model requested 1 tool call(s)
  -> calling search_pest_disease({'crop': 'cotton', 'symptoms': 'small holes in bolls and flowers with visible caterpillars inside'})
  [nudge] model stopped after search_pest_disease. Nudging to call get_ipm_guidance...
[iteration 3] model requested 1 tool call(s)
  -> calling get_weather({'days': '3', 'location': 'Nashik'})
[iteration 4] model requested 1 tool call(s)
  -> calling get_ipm_guidance({'crop_id': 'cotton', 'issue_id': 'cotton_bollworm'})

--- Reflection pass ---

--- Tool call trace (for demo/debugging) ---
  1. search_pest_disease({'crop': 'cotton', 'symptoms': 'small holes in bolls and flowers with visible caterpillars inside'})
     -> {"status": "ok", "crop": "cotton", "matches": [{"id": "cotton_bollworm", "name": "Cotton Bollworm / American Bollworm (Helicoverpa armigera)", "type": "pest", "match_type": "strong", "matched_symptom_...
  2. get_weather({'days': '3', 'location': 'Nashik'})
     -> {"status": "ok", "location_query": "Nashik", "location_resolved": "Nashik, Maharashtra, India", "latitude": 19.99727, "longitude": 73.79096, "units": {"temperature": "\u00b0C", "humidity": "%", "preci...
  3. get_ipm_guidance({'crop_id': 'cotton', 'issue_id': 'cotton_bollworm', 'crop': 'cotton'})
     -> {"status": "ok", "id": "cotton_bollworm", "name": "Cotton Bollworm / American Bollworm (Helicoverpa armigera)", "type": "pest", "symptoms": ["circular holes bored into squares, flowers, and bolls", "f...

=== Final answer to farmer ===
Based on the guidance provided by IPM for Cotton Bollworm, it is likely that the cotton plants in Nashik are infested with the Cotton Bollworm, which is consistent with the presence of small holes bored into the bolls and flowers, with visible caterpillars inside. The current weather forecast for Nashik shows temperatures above 25°C and humidity levels above 40%, favoring the development of this pest.

It's essential to note that Pink Bollworm is also a possible cause of these symptoms, especially in warm weather. To confirm the diagnosis, further inspection is necessary.

To manage this issue, we recommend:

*   Monitoring with pheromone traps to track adult moth activity
*   Scouting squares and bolls weekly for eggs and small larvae before they bore in
*   Encouraging natural enemies such as Trichogramma wasps and predatory bugs
*   Using Bt cotton varieties where locally approved, as a resistance-management component, not a sole strategy
*   Practicing crop rotation and destroying crop residue after harvest to reduce carryover
*   Applying targeted insecticide only when the economic threshold is reached, and rotating modes of action to limit resistance
```