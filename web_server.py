"""
CropGuard Web Server
Provides a modern, farmer-friendly Web UI and REST API for CropGuard.
Backed by the CropGuard MCP knowledge base and Ollama AI Agent.
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

import base64
import server_cropguard as sc
import agent_cropguard as ac
import vision
import translate

BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cropguard_server")

# ---------------------------------------------------------------------------
# API Handlers
# ---------------------------------------------------------------------------

async def get_crops_api(request: Request) -> JSONResponse:
    """Return all available crops with scientific names and issue summaries."""
    crop_keys = sc._available_crops()
    results = []
    for ck in crop_keys:
        info = sc.get_crop_info(ck)
        data = sc._load_crop(ck)
        pests = data.get("pests", []) if data else []
        diseases = data.get("diseases", []) if data else []
        
        # Collect distinct symptom phrases for easy one-tap chips
        all_symptoms = []
        for issue in (pests + diseases):
            for s in issue.get("symptoms", []):
                if s not in all_symptoms:
                    all_symptoms.append(s)
        
        results.append({
            "id": ck,
            "name": ck.capitalize(),
            "scientific_name": info.get("scientific_name", ""),
            "pest_count": len(pests),
            "disease_count": len(diseases),
            "pests": [{"id": p["id"], "name": p["name"]} for p in pests],
            "diseases": [{"id": d["id"], "name": d["name"]} for d in diseases],
            "sample_symptoms": all_symptoms[:8],
        })
    return JSONResponse({"status": "ok", "crops": results})


async def get_crop_detail_api(request: Request) -> JSONResponse:
    """Return full knowledge base details for a specific crop."""
    crop_name = request.path_params.get("crop", "")
    data = sc._load_crop(crop_name)
    if not data:
        return JSONResponse({"status": "not_found", "message": f"Crop '{crop_name}' not found"}, status_code=404)
    return JSONResponse({"status": "ok", "crop_data": data})


async def get_weather_api(request: Request) -> JSONResponse:
    """Fetch Open-Meteo weather and evaluate pest weather favorability."""
    location = request.query_params.get("location", "Nashik, India")
    days = int(request.query_params.get("days", 3))
    crop = request.query_params.get("crop", "").strip().lower()

    weather_data = sc.get_weather(location=location, days=days)
    if weather_data.get("status") != "ok":
        return JSONResponse(weather_data, status_code=400 if weather_data.get("status") == "error" else 404)

    # Evaluate pest/disease risk based on current weather
    current_temp = weather_data.get("current", {}).get("temperature_c")
    current_humidity = weather_data.get("current", {}).get("humidity_pct")

    risk_alerts = []
    target_crops = [crop] if crop and sc._load_crop(crop) else sc._available_crops()

    for ck in target_crops:
        cdata = sc._load_crop(ck)
        if not cdata:
            continue
        for issue in sc._all_issues(cdata):
            fc = issue.get("favorable_conditions") or {}
            t_min = fc.get("temp_c_min")
            t_max = fc.get("temp_c_max")
            h_min = fc.get("humidity_pct_min")
            h_max = fc.get("humidity_pct_max")

            is_temp_fav = (t_min is None or current_temp is None or (t_min <= current_temp <= t_max))
            is_hum_fav = (h_min is None or current_humidity is None or (h_min <= current_humidity <= h_max))

            if is_temp_fav and is_hum_fav and (t_min is not None or h_min is not None):
                risk_alerts.append({
                    "crop": ck,
                    "issue_id": issue["id"],
                    "issue_name": issue["name"],
                    "type": issue["type"],
                    "temp_range": f"{t_min}°C - {t_max}°C" if t_min and t_max else "Any",
                    "humidity_range": f"{h_min}% - {h_max}%" if h_min and h_max else "Any",
                    "notes": fc.get("notes", ""),
                    "risk_level": "Elevated",
                })

    weather_data["risk_alerts"] = risk_alerts
    return JSONResponse(weather_data)


async def diagnose_api(request: Request) -> JSONResponse:
    """
    Direct agronomist diagnosis pipeline:
    1. Search pest/disease matches from symptoms
    2. Fetch weather for location
    3. Retrieve full IPM guidance for top match
    4. Correlate with weather conditions and confusable issues
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON body"}, status_code=400)

    crop = body.get("crop", "").strip()
    symptoms = body.get("symptoms", "")
    location = body.get("location", "").strip()

    if not crop:
        return JSONResponse({"status": "error", "message": "Please select a crop"}, status_code=400)
    if not symptoms:
        return JSONResponse({"status": "error", "message": "Please provide symptoms"}, status_code=400)

    # 1. Search knowledge base
    search_res = sc.search_pest_disease(crop=crop, symptoms=symptoms)
    if search_res.get("status") != "ok":
        return JSONResponse(search_res, status_code=400)

    matches = search_res.get("matches", [])
    top_match = matches[0] if matches else None

    # 2. Fetch IPM guidance for top match if found
    ipm_guidance = None
    if top_match:
        ipm_res = sc.get_ipm_guidance(crop=crop, issue_id=top_match["id"])
        if ipm_res.get("status") == "ok":
            ipm_guidance = ipm_res

    # 3. Weather check
    weather_info = None
    weather_risk_assessment = None
    if location:
        w_res = sc.get_weather(location=location, days=3)
        if w_res.get("status") == "ok":
            weather_info = w_res
            cur_temp = w_res.get("current", {}).get("temperature_c")
            cur_hum = w_res.get("current", {}).get("humidity_pct")
            
            if top_match and cur_temp is not None:
                fc = top_match.get("favorable_conditions") or {}
                t_min = fc.get("temp_c_min")
                t_max = fc.get("temp_c_max")
                h_min = fc.get("humidity_pct_min")
                h_max = fc.get("humidity_pct_max")

                t_match = (t_min is None or (t_min <= cur_temp <= t_max))
                h_match = (h_min is None or cur_hum is None or (h_min <= cur_hum <= h_max))

                if t_match and h_match:
                    verdict = "Current weather conditions strongly favor development and spread of this issue."
                    level = "High Risk"
                elif t_match or h_match:
                    verdict = "Weather conditions partially align with favorable ranges."
                    level = "Moderate Risk"
                else:
                    verdict = "Current weather is outside peak favorable parameters for rapid outbreak."
                    level = "Low/Mild Risk"

                weather_risk_assessment = {
                    "level": level,
                    "verdict": verdict,
                    "temp_actual": f"{cur_temp}°C",
                    "temp_favorable": f"{t_min}°C - {t_max}°C" if t_min else "N/A",
                    "humidity_actual": f"{cur_hum}%",
                    "humidity_favorable": f"{h_min}% - {h_max}%" if h_min else "N/A",
                    "notes": fc.get("notes", ""),
                }

    # 4. Formulate farmer summary
    response_payload = {
        "status": "ok",
        "crop": crop,
        "query_symptoms": symptoms,
        "location": location,
        "matches_count": len(matches),
        "top_match": top_match,
        "other_matches": matches[1:4] if len(matches) > 1 else [],
        "ipm_guidance": ipm_guidance,
        "weather": weather_info,
        "weather_risk_assessment": weather_risk_assessment,
        "confusable_with": top_match.get("confusable_with", []) if top_match else [],
        "disclaimer": "CropGuard provides risk assessments based on verified agricultural guidelines. It is not a certified lab diagnosis. Please consult your local Krishi Vigyan Kendra (KVK) or extension officer for field verification.",
    }

    return JSONResponse(response_payload)


# ---------------------------------------------------------------------------
# Crop Resolution & Conflict Gate (Fix 1)
# ---------------------------------------------------------------------------

CROPS = ["cotton", "tomato", "wheat"]

CROP_ALIASES = {
    "tomato": ["tomato", "tomatoes", "tamatar", "tomota", "tomater", "tometo"],
    "cotton": ["cotton", "kapas", "kapaas"],
    "wheat": ["wheat", "gehu", "gehun", "kanak"]
}


def guess_crop(text: str) -> str | None:
    if not text:
        return None
    lower = text.lower()
    for crop, aliases in CROP_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", lower):
                return crop
    return None


def resolve_crop(selected: str | None, typed_crop: str | None, seen_crop: str | None) -> tuple[str | None, str | None]:
    """Returns (crop, conflict_message_or_None)."""
    candidates = {c for c in (selected, typed_crop, seen_crop) if c in CROPS}
    if len(candidates) == 1:
        return candidates.pop(), None
    if len(candidates) > 1:
        return None, (
            f"The crop is unclear: your selection, message and photo point to "
            f"{' / '.join(sorted(candidates))}. Please tell me which crop this is."
        )
    return None, None


async def chat_api(request: Request) -> JSONResponse:
    """
    Interactive AI Agronomist chat endpoint.
    Chains MCP tools and Ollama model, returning structured answer & live trace.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

    user_message = body.get("message", "").strip()
    history = body.get("history", [])
    client_crop = body.get("crop", "").strip().lower()
    client_lang = body.get("lang", "").strip().lower()
    image_base64 = body.get("image")

    if not user_message and not image_base64:
        return JSONResponse({"status": "error", "message": "Please enter a message or upload an image"}, status_code=400)

    trace: list[dict] = []

    # Selected crop from client UI (if valid)
    selected_crop = client_crop if client_crop in CROPS else None

    # Detect typed crop from current turn or prior turns
    typed_crop = guess_crop(user_message)
    if not typed_crop and history and isinstance(history, list):
        for past in reversed(history):
            c = guess_crop(past.get("content", ""))
            if c:
                typed_crop = c
                break

    # Process image if provided
    vision_analysis = None
    visual_symptoms_text = ""
    seen_crop = None

    if image_base64 and isinstance(image_base64, str):
        try:
            raw_b64 = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
            img_bytes = base64.b64decode(raw_b64)
            loop = asyncio.get_running_loop()
            obs = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: vision.describe_image(img_bytes, crop_hint=selected_crop or typed_crop, timeout=300.0)),
                timeout=300.0
            )
            visual_symptoms_text = vision.observation_to_text(obs)
            vision_analysis = {
                "crop_visible": obs.get("crop_visible", "unclear"),
                "plant_part": obs.get("plant_part", "unclear"),
                "symptoms": obs.get("symptoms", []),
                "spot_color": obs.get("spot_color", ""),
                "spot_shape_and_size": obs.get("spot_shape_and_size", ""),
                "pattern": obs.get("pattern", ""),
                "insects_visible": obs.get("insects_visible", False),
                "insect_description": obs.get("insect_description", ""),
                "image_quality": obs.get("image_quality", "good"),
                "summary": visual_symptoms_text or ("Visual inspection recorded" if obs.get("image_quality") == "good" else "Vision analysis could not identify clear symptoms"),
                "notes": obs.get("notes", "")
            }
            if obs.get("crop_visible") in CROPS:
                seen_crop = obs["crop_visible"]
        except Exception as ve:
            logger.warning("Vision analysis error/timeout: %s", ve)
            obs = {"image_quality": "poor", "symptoms": [], "crop_visible": "unclear"}
            vision_analysis = {
                "crop_visible": selected_crop or typed_crop or "unclear",
                "plant_part": "unclear",
                "symptoms": [],
                "spot_color": "",
                "spot_shape_and_size": "",
                "pattern": "",
                "insects_visible": False,
                "insect_description": "",
                "image_quality": "poor",
                "summary": "",
                "notes": f"Vision analysis failed: {ve}"
            }

        # Fix 2: Evidence Gate - require real evidence before searching
        has_real_evidence = (obs.get("image_quality") != "poor" and bool(obs.get("symptoms")))
        if not has_real_evidence:
            # If farmer did not provide detailed written symptoms, ask for a retake or text description
            if not user_message or len(user_message.split()) < 3:
                reply = (
                    "I could not clearly detect the plant symptoms in this photo (the image quality is low or no distinct symptoms could be identified).\n\n"
                    "📸 **For an accurate diagnosis:**\n"
                    "- Please upload a clear, well-lit close-up photo showing the affected leaves, fruit, or stem.\n"
                    "- Or describe the symptoms in text (e.g., spots, wilting, insects, rotting) along with the crop name (Cotton, Tomato, or Wheat)."
                )
                return JSONResponse({
                    "status": "ok",
                    "reply": reply,
                    "trace": [],
                    "engine": "evidence_gate",
                    "vision_analysis": vision_analysis,
                })

    # Fix 1: Resolve crop across selected, typed, and seen, and stop on conflicts
    resolved_crop, conflict_msg = resolve_crop(selected_crop, typed_crop, seen_crop)
    if conflict_msg:
        return JSONResponse({
            "status": "ok",
            "reply": conflict_msg,
            "trace": [],
            "engine": "crop_conflict_resolver",
            "vision_analysis": vision_analysis,
        })

    # If crop is completely unknown across selection, text and photo, ask instead of guessing!
    if not resolved_crop:
        reply = (
            "Which crop would you like advice on? CropGuard currently supports **Tomato**, **Cotton**, and **Wheat**.\n\n"
            "Please mention your crop in your message so I can search the verified agricultural database."
        )
        return JSONResponse({
            "status": "ok",
            "reply": reply,
            "trace": [],
            "engine": "crop_gate",
            "vision_analysis": vision_analysis,
        })

    if not user_message:
        if visual_symptoms_text:
            user_message = f"Please diagnose my {resolved_crop} plant based on this photo showing: {visual_symptoms_text}"
        else:
            user_message = f"Please diagnose my {resolved_crop} plant based on the submitted photo."

    query_for_tools = user_message
    if visual_symptoms_text and visual_symptoms_text not in user_message:
        query_for_tools = f"{user_message}. Crop: {resolved_crop}. Observed in photo: {visual_symptoms_text}"

    # Target language detection
    target_lang = client_lang or translate.detect_lang(user_message)
    if target_lang != "en" and target_lang in translate.LANGS:
        try:
            detected_script = translate.detect_lang(user_message)
            if detected_script != "en":
                en_msg = translate.to_english(user_message, detected_script)
                if en_msg:
                    query_for_tools = en_msg
        except Exception as te:
            logger.warning("Translation to English failed: %s", te)

    # Extract location if mentioned in current turn or prior turns
    detected_location = None
    lower_msg = user_message.lower()
    known_locations = ["nashik", "ahmedabad", "ludhiana", "pune", "guntur", "delhi", "mumbai", "rajkot", "nagpur", "jaipur", "bhopal", "patna"]
    for loc in known_locations:
        if loc in lower_msg:
            detected_location = loc.capitalize()
            break
    if not detected_location and history and isinstance(history, list):
        for past in reversed(history):
            past_text = past.get("content", "").lower()
            for loc in known_locations:
                if loc in past_text:
                    detected_location = loc.capitalize()
                    break
            if detected_location:
                break

    # Run Ollama AI Agent with timeout safeguard
    try:
        import ollama
        messages = [{"role": "system", "content": ac.SYSTEM_PROMPT}]
        if history and isinstance(history, list):
            for turn in history[-6:]:
                role = "assistant" if turn.get("role") in ("assistant", "bot") else "user"
                content = str(turn.get("content", "")).strip()
                if content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": query_for_tools})
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather forecast for location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location name"},
                            "days": {"type": "integer", "description": "Forecast days (1-7)"}
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_crop_info",
                    "description": "Get general crop info.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "crop": {"type": "string", "description": "Crop name"}
                        },
                        "required": ["crop"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_pest_disease",
                    "description": "Search pest/disease matches from crop and symptoms.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "crop": {"type": "string", "description": "Crop name"},
                            "symptoms": {"type": "string", "description": "Symptom description"}
                        },
                        "required": ["crop", "symptoms"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_ipm_guidance",
                    "description": "Get IPM treatment guidance for crop and issue_id.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "crop": {"type": "string", "description": "Crop name"},
                            "issue_id": {"type": "string", "description": "Issue ID from search results"}
                        },
                        "required": ["crop", "issue_id"]
                    }
                }
            }
        ]

        # Call Ollama in thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()

        def _run_ollama():
            nudge_count = 0
            cur_trace = []
            
            for iteration in range(1, ac.MAX_TOOL_ITERATIONS + 1):
                resp = ollama.chat(
                    model="llama3.2:3b",
                    messages=messages,
                    tools=tools,
                )
                msg = resp.message
                messages.append(msg)

                if not msg.tool_calls:
                    tools_used = {t["tool"] for t in cur_trace}
                    has_strong = any(
                        '"match_type": "strong"' in (t.get("result") or "")
                        for t in cur_trace if t.get("tool") == "search_pest_disease"
                    )
                    if has_strong and "search_pest_disease" in tools_used and "get_ipm_guidance" not in tools_used:
                        if nudge_count >= 1:
                            # Force IPM call directly
                            search_step = next((json.loads(t["result"]) for t in reversed(cur_trace) if t.get("tool") == "search_pest_disease"), None)
                            if search_step and search_step.get("matches"):
                                top = search_step["matches"][0]
                                c_name = search_step.get("crop") or detected_crop or "cotton"
                                ipm_data = sc.get_ipm_guidance(crop=c_name, issue_id=top["id"])
                                res_str = json.dumps(ipm_data)
                                cur_trace.append({"tool": "get_ipm_guidance", "arguments": {"crop": c_name, "issue_id": top["id"]}, "result": res_str})
                                messages.pop()
                                messages.append({
                                    "role": "assistant",
                                    "content": "",
                                    "tool_calls": [{"function": {"name": "get_ipm_guidance", "arguments": {"crop": c_name, "issue_id": top["id"]}}}]
                                })
                                messages.append({"role": "tool", "tool_name": "get_ipm_guidance", "content": res_str})
                                continue
                        
                        messages.pop()
                        messages.append({
                            "role": "user",
                            "content": "Do NOT give a final answer yet. Call get_ipm_guidance for the top match and get_weather if location was provided."
                        })
                        nudge_count += 1
                        continue

                    return msg.content or "", cur_trace

                for tc in msg.tool_calls:
                    t_name = tc.function.name
                    t_args = tc.function.arguments or {}

                    # Execute tool
                    if t_name == "search_pest_disease":
                        t_res = sc.search_pest_disease(crop=t_args.get("crop", ""), symptoms=t_args.get("symptoms", ""))
                    elif t_name == "get_weather":
                        t_res = sc.get_weather(location=t_args.get("location", ""), days=int(t_args.get("days", 3)))
                    elif t_name == "get_crop_info":
                        t_res = sc.get_crop_info(crop=t_args.get("crop", ""))
                    elif t_name == "get_ipm_guidance":
                        t_res = sc.get_ipm_guidance(crop=t_args.get("crop", ""), issue_id=t_args.get("issue_id", ""))
                    else:
                        t_res = {"status": "error", "message": f"unknown tool '{t_name}'"}

                    res_str = json.dumps(t_res)
                    cur_trace.append({"tool": t_name, "arguments": t_args, "result": res_str})
                    messages.append({"role": "tool", "tool_name": t_name, "content": res_str})

            # Force answer if iterations reached
            messages.append({"role": "user", "content": "Please give your final farmer-friendly answer using the tool evidence gathered above."})
            f_resp = ollama.chat(model="llama3.2:3b", messages=messages)
            return f_resp.message.content or "", cur_trace

        # Run with 25 second timeout safeguard
        draft_answer, trace = await asyncio.wait_for(loop.run_in_executor(None, _run_ollama), timeout=25.0)

        # Reflection pass
        kind, data = ac._search_outcome(trace)
        if kind in {"empty", "weak", "unknown_crop"}:
            final_answer = ac._clarification_reply(kind, data, final_round=False)
        else:
            def _reflect():
                evidence_summary = "\n\n".join(
                    f"Tool: {t['tool']}({t['arguments']})\nResult: {t['result']}" for t in trace
                )
                r_prompt = f"""Review your draft answer against safety rules and evidence:
Evidence:
{evidence_summary}

Farmer's question:
{user_message}

Draft answer:
{draft_answer}

Produce the concise, grounded, farmer-friendly final answer."""
                ref_resp = ollama.chat(
                    model="llama3.2:3b",
                    messages=[
                        {"role": "system", "content": ac.SYSTEM_PROMPT},
                        {"role": "user", "content": r_prompt}
                    ]
                )
                return ref_resp.message.content or draft_answer

            final_answer = await asyncio.wait_for(loop.run_in_executor(None, _reflect), timeout=15.0)

        # Regional language translation if requested
        if target_lang and target_lang != "en" and target_lang in translate.LANGS:
            try:
                terms = translate.collect_protected_terms(final_answer)
                prot_text, mapping = translate.protect(final_answer, terms)
                trans_answer = translate.from_english(prot_text, target_lang)
                final_answer = translate.restore(trans_answer, mapping)
            except Exception as te:
                logger.warning("Translation of answer to %s failed: %s", target_lang, te)

        return JSONResponse({
            "status": "ok",
            "reply": final_answer,
            "trace": trace,
            "engine": "llama3.2:3b (Ollama)",
            "vision_analysis": vision_analysis,
        })

    except Exception as e:
        logger.warning("Ollama agent direct loop timed out or failed (%s). Using deterministic agronomist engine fallback.", e)
        # Fast deterministic fallback: use the verified knowledge base and weather tools directly!
        fallback_trace = []
        c = resolved_crop
        s = query_for_tools
        if history and isinstance(history, list) and len(user_message.split()) < 6:
            past_user = next((p.get("content", "") for p in reversed(history) if p.get("role") in ("user", "farmer")), "")
            if past_user and past_user != user_message:
                s = f"{past_user}. Additional detail: {query_for_tools}"
        s_clean = re.sub(r'\(Farm Location:[^)]*\)', '', s, flags=re.I).strip()
        s_res = sc.search_pest_disease(crop=c, symptoms=s_clean)
        fallback_trace.append({"tool": "search_pest_disease", "arguments": {"crop": c, "symptoms": s_clean}, "result": json.dumps(s_res)})

        w_res = None
        if detected_location:
            w_res = sc.get_weather(location=detected_location, days=3)
            fallback_trace.append({"tool": "get_weather", "arguments": {"location": detected_location, "days": 3}, "result": json.dumps(w_res)})

        matches = s_res.get("matches", [])
        if matches:
            top = matches[0]
            ipm_res = sc.get_ipm_guidance(crop=c, issue_id=top["id"])
            fallback_trace.append({"tool": "get_ipm_guidance", "arguments": {"crop": c, "issue_id": top["id"]}, "result": json.dumps(ipm_res)})

            weather_note = ""
            if w_res and w_res.get("status") == "ok":
                cur_t = w_res.get("current", {}).get("temperature_c")
                cur_h = w_res.get("current", {}).get("humidity_pct")
                fav = top.get("favorable_conditions", {})
                t_min = fav.get("temp_c_min")
                t_max = fav.get("temp_c_max")
                h_min = fav.get("humidity_pct_min")
                h_max = fav.get("humidity_pct_max")

                # Fix 5: Only make weather claims the data supports
                if t_min is not None and t_max is not None and h_min is not None and h_max is not None and cur_t is not None and cur_h is not None:
                    temp_favorable = (t_min <= cur_t <= t_max)
                    hum_favorable = (h_min <= cur_h <= h_max)
                    if temp_favorable and hum_favorable:
                        weather_note = f"\n\n🌤️ **Weather Assessment ({detected_location}):** Current weather ({cur_t}°C, {cur_h}% RH) falls within known favorable conditions for {top['name']} ({t_min}–{t_max}°C, {h_min}–{h_max}% RH)."
                    elif temp_favorable or hum_favorable:
                        weather_note = f"\n\n🌤️ **Weather Assessment ({detected_location}):** Current conditions are {cur_t}°C and {cur_h}% RH (partially conducive; optimal range is {t_min}–{t_max}°C, {h_min}–{h_max}% RH)."
                    else:
                        weather_note = f"\n\n🌤️ **Weather Assessment ({detected_location}):** Current conditions are {cur_t}°C and {cur_h}% RH (peak favorable conditions for {top['name']} are {t_min}–{t_max}°C, {h_min}–{h_max}% RH)."
                elif fav.get("notes"):
                    weather_note = f"\n\n🌤️ **Weather Context ({detected_location}):** Current temperature is {cur_t}°C and humidity is {cur_h}%. {fav['notes']}"

            steps_formatted = "\n".join(f"* {step}" for step in ipm_res.get("ipm_steps", []))
            confusable = top.get("confusable_with", [])
            confusable_note = f"\n*Note: Symptoms may also resemble {', '.join(confusable)}.*" if confusable else ""

            # Fix 3: Make "strong match" earn its name
            is_strong = (top.get("match_type") == "strong")
            if is_strong:
                intro = f"Based on verified agricultural records for **{c.capitalize()}**, the observed symptoms are a **strong match** with **{top['name']}**."
            else:
                intro = (
                    f"Based on verified agricultural records for **{c.capitalize()}**, the observed symptoms are a **possible match** with **{top['name']}**.\n"
                    f"*Note: Because evidence is partial or symptoms overlap with other conditions, please confirm the affected plant parts before applying treatments.*"
                )

            reply = (
                f"{intro}{confusable_note}"
                f"{weather_note}\n\n"
                f"**Recommended Integrated Pest Management (IPM) Next Steps:**\n"
                f"{steps_formatted}\n\n"
                f"⚠️ *Disclaimer: This is a risk assessment, not a certified agronomic diagnosis. For severe or rapid spread, please contact your nearest Krishi Vigyan Kendra (KVK).*"
            )
        else:
            reply = (
                f"I could not find a confirmed pest or disease match in the knowledge base for '{user_message}'.\n\n"
                f"Could you please share more specific details?\n"
                f"- Which part of the plant is affected (leaves, stems, bolls, flowers)?\n"
                f"- What colors, spots, or insects do you see?\n\n"
                f"For urgent field issues, please consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer."
            )

        if target_lang and target_lang != "en" and target_lang in translate.LANGS:
            try:
                terms = translate.collect_protected_terms(reply)
                prot_text, mapping = translate.protect(reply, terms)
                trans_reply = translate.from_english(prot_text, target_lang)
                reply = translate.restore(trans_reply, mapping)
            except Exception as te:
                logger.warning("Translation of fallback to %s failed: %s", target_lang, te)

        return JSONResponse({
            "status": "ok",
            "reply": reply,
            "trace": fallback_trace,
            "engine": "Deterministic Agronomist Engine (Direct Tool Chain)",
            "vision_analysis": vision_analysis,
        })


async def health_api(request: Request) -> JSONResponse:
    """Check health of backend, MCP knowledge base, and Ollama."""
    import ollama
    ollama_ok = False
    try:
        models = ollama.list()
        ollama_ok = True
    except Exception:
        ollama_ok = False

    return JSONResponse({
        "status": "healthy",
        "knowledge_crops": sc._available_crops(),
        "ollama_connected": ollama_ok,
        "tools_available": ["get_crop_info", "search_pest_disease", "get_weather", "get_ipm_guidance"],
    })


# ---------------------------------------------------------------------------
# Static Web App Routes
# ---------------------------------------------------------------------------

async def index_page(request: Request) -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


routes = [
    Route("/", index_page),
    Route("/api/crops", get_crops_api),
    Route("/api/crop/{crop:str}", get_crop_detail_api),
    Route("/api/weather", get_weather_api),
    Route("/api/diagnose", diagnose_api, methods=["POST"]),
    Route("/api/chat", chat_api, methods=["POST"]),
    Route("/api/health", health_api),
    Mount("/static", StaticFiles(directory=STATIC_DIR), name="static"),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n=======================================================")
    print(f"  🌾 CropGuard AI Web UI Server running on:")
    print(f"  👉 http://localhost:{port}")
    print(f"=======================================================\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
