"""
CropGuard Agent

Connects an Ollama-hosted local LLM to the CropGuard MCP server, so the
model can autonomously discover tools, decide when to call them, observe
results, and reflect once before giving the farmer a final answer.

Run with: python agent_cropguard.py
"""

import asyncio
import json
import sys

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL_NAME = "llama3.2:3b"  # change this to whatever model you've pulled in Ollama
MAX_TOOL_ITERATIONS = 5  # hard cap so the agent can't loop forever

SYSTEM_PROMPT = """You are CropGuard, an assistant that helps farmers assess \
POSSIBLE pest and disease risks on their crops. You are not a certified \
agronomist and must never claim a certain diagnosis.

CRITICAL TOOL WORKFLOW - You must CHAIN your tool calls:
1. If the farmer gives a crop and symptoms, FIRST call search_pest_disease.
2. If the farmer gives a location, ALSO call get_weather.
3. ONCE search_pest_disease returns matches, you MUST call get_ipm_guidance for the SINGLE top-ranked match ONLY (the first match in the matches array). Do NOT call get_ipm_guidance for secondary or multiple matches. NEVER skip this step. NEVER invent treatment plans.
4. Do not provide your final answer until you have collected IPM guidance for the top suspected issue and (if location is known) the weather.

Rules you must always follow:
- NEVER hallucinate pest names, disease names, or treatments. Use ONLY what the tools return.
- When calling search_pest_disease, use ONLY symptom details the farmer \
actually mentioned. If their description is vague, pass the vague terms as-is \
rather than inventing specific symptoms they never described.
- Use language like "possible", "consistent with", or "likely" — never \
state a pest or disease as certain.
- When a tool returns multiple candidate matches or mentions issues that \
are commonly confused with each other, mention that ambiguity to the farmer.
- If tools return no useful data, say so honestly instead of inventing \
information.
- Only name pests or diseases that appear in the tool results you actually \
received. Never invent a disease or pest name that wasn't returned by a tool.
- End with concrete, practical next steps for the farmer, drawn STRICTLY from the \
IPM guidance tool.
- Keep the final answer concise and farmer-friendly, not a wall of text.
"""


def mcp_tool_to_ollama_format(mcp_tool) -> dict:
    """Convert an MCP Tool definition into the JSON-schema tool format Ollama expects."""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": mcp_tool.input_schema or {"type": "object", "properties": {}},
    },
    }
class CropGuardAgent:
    """Wraps an MCP client session + Ollama chat loop."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.session: ClientSession | None = None
        self.ollama_tools: list[dict] = []
        self.tool_names: set[str] = set()

    async def connect(self, session: ClientSession):
        """Store an already-open MCP session and discover available tools."""
        self.session = session
        await self.session.initialize()

        tools_result = await self.session.list_tools()
        self.ollama_tools = [mcp_tool_to_ollama_format(t) for t in tools_result.tools]
        self.tool_names = {t.name for t in tools_result.tools}

        print(f"[connected] discovered {len(self.ollama_tools)} tools: "
              f"{', '.join(sorted(self.tool_names))}")

    async def call_tool(self, name: str, arguments: dict, trace: list[dict] | None = None) -> str:
        """Call an MCP tool and return its result as a JSON string for the LLM."""
        if name not in self.tool_names:
            return json.dumps({"status": "error", "message": f"unknown tool '{name}'"})

        # Normalization for get_ipm_guidance arguments to ensure exact parameters (crop, issue_id)
        if name == "get_ipm_guidance":
            if isinstance(arguments, dict):
                if "issue_id" not in arguments or not arguments.get("issue_id"):
                    for alt_key in ("id", "issue", "pest_id", "disease_id", "issue_name"):
                        if alt_key in arguments and arguments[alt_key]:
                            arguments["issue_id"] = str(arguments.pop(alt_key))
                            break
                if ("crop" not in arguments or not arguments.get("crop")) and trace:
                    for step in reversed(trace):
                        prev_args = step.get("arguments", {})
                        if isinstance(prev_args, dict) and prev_args.get("crop"):
                            arguments["crop"] = prev_args["crop"]
                            break
        # A handful of place names are ambiguous across countries (e.g. Punjab
        # exists in both India and Pakistan). Since this project targets Indian
        # agriculture, default to India when no country is specified.
        if name == "get_weather" and isinstance(arguments, dict):
            location = arguments.get("location", "")
            ambiguous_names = {"punjab", "bengal", "kashmir", "sindh"}
            if location.strip().lower() in ambiguous_names:
                arguments["location"] = f"{location.strip()}, India"
        try:
            result = await self.session.call_tool(name, arguments)
            # MCP tool results come back as a list of content blocks; our tools
            # return a single JSON-serializable dict via FastMCP/MCPServer's
            # structured output, exposed as result.structuredContent when present.
            if getattr(result, "structured_content", None) is not None:
                return json.dumps(result.structured_content)
            # Fallback: concatenate any text content blocks
            text_parts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(text_parts) if text_parts else json.dumps({"status": "error", "message": "empty tool result"})
        except Exception as e:
            return json.dumps({"status": "error", "message": f"tool call failed: {e}"})


    async def run_loop(self, user_question: str) -> tuple[str, list[dict]]:
        """
        Run the decide -> call tool -> observe -> repeat loop, capped at
        MAX_TOOL_ITERATIONS rounds. Returns (draft_answer, trace) where
        trace is a list of {tool, arguments, result} dicts for the demo log.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_question},
        ]
        trace: list[dict] = []

        for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                tools=self.ollama_tools,
            )
            msg = response.message
            messages.append(msg)

            if not msg.tool_calls:
                # Model decided it has enough info to answer directly.
                tools_used = {t["tool"] for t in trace}
                
                                # Force chaining if it stopped prematurely — but only when
                # there's actually a strong match worth drilling into.
                has_strong_match = any(
                    '"match_type": "strong"' in t["result"]
                    for t in trace if t["tool"] == "search_pest_disease"
                )
                if has_strong_match and "search_pest_disease" in tools_used and "get_ipm_guidance" not in tools_used:
                    print("  [nudge] model stopped after search_pest_disease. Nudging to call get_ipm_guidance...")
                    # Remove the model's premature hallucinated answer from context
                    messages.pop()
                    messages.append({
                        "role": "user",
                        "content": "Do NOT give a final answer yet. You must call `get_ipm_guidance` for ONLY the single top-ranked match (the first match in the matches list) using its exact `crop` and `issue_id`. Do NOT call get_ipm_guidance for secondary matches. Also call `get_weather` if I mentioned a location."
                    })
                    continue
                
                return msg.content or "", trace

            print(f"[iteration {iteration}] model requested {len(msg.tool_calls)} tool call(s)")

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                arguments = tool_call.function.arguments or {}
                print(f"  -> calling {name}({arguments})")

                result_str = await self.call_tool(name, arguments, trace)
                trace.append({"tool": name, "arguments": arguments, "result": result_str})

                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": result_str,
                })

        # Hit MAX_TOOL_ITERATIONS without the model producing a final answer.
        # Force one last call with tools disabled so it MUST answer in text.
        print(f"[warning] hit max iterations ({MAX_TOOL_ITERATIONS}); forcing a final answer")
        messages.append({
            "role": "user",
            "content": "Please give your best final answer now, using only the "
                        "information already gathered above. Do not request more tools.",
        })
        final_response = ollama.chat(model=self.model_name, messages=messages)
        return final_response.message.content or "", trace


    async def reflect(self, user_question: str, draft_answer: str, trace: list[dict]) -> str:
        """
        One explicit reflection pass: check the draft answer against the
        gathered tool evidence and the safety rules, then produce the final
        answer. This is a single extra LLM call, not another tool-call round.
        """
        tools_used = ", ".join(sorted({t["tool"] for t in trace})) or "none"

        evidence_summary = "\n\n".join(
            f"Tool: {t['tool']}({t['arguments']})\nResult: {t['result']}"
            for t in trace
        ) or "No tools were called."

        reflection_prompt = f"""You previously drafted this answer to a farmer's question.
Before sending it, review it against these checks:

1. Does it avoid stating any pest or disease as a certain diagnosis? It must
   use hedging language like "possible", "consistent with", or "likely".
2. Does it use the ACTUAL DATA from the tool results below, rather than
   vague references to "checking weather" or "future IPM guidance" when
   that data was already retrieved? Pull real numbers, names, and steps
   from the evidence into the answer. If key tools were never called and
   would have helped, say so as a gap instead.
3. Does it mention other possible causes if the evidence was ambiguous or a
   knowledge base entry listed things it could be confused with?
4. Does it end with concrete, practical next steps the farmer can act on?
5. Is it concise and farmer-friendly, not overly technical or long?

Actual tool evidence gathered (use this real data, don't just describe that it exists):
{evidence_summary}

Farmer's original question:
{user_question}

Your draft answer:
{draft_answer}

Now write the FINAL answer to give the farmer. If the draft already meets
all checks, you may keep it mostly as-is. If it fails any check, rewrite it
to fix that issue. Respond with ONLY the final answer text, no commentary
about the review process itself.
"""

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": reflection_prompt},
            ],
        )
        return response.message.content or draft_answer

async def main():
    server_log = open("server_stderr.log", "w")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server_cropguard.py"],
        errlog=server_log,
    )

    print("CropGuard — AI Crop Pest & Disease Risk Advisor")
    print(f"Model: {MODEL_NAME}  |  Type 'exit' or 'quit' to stop.\n")

    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            agent = CropGuardAgent()
            await agent.connect(session)

            while True:
                try:
                    user_question = input("\nFarmer question> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting CropGuard.")
                    break

                if not user_question:
                    continue
                if user_question.lower() in {"exit", "quit"}:
                    print("Exiting CropGuard.")
                    break

                print("\n--- Agent working ---")
                draft_answer, trace = await agent.run_loop(user_question)

                print("\n--- Reflection pass ---")
                final_answer = await agent.reflect(user_question, draft_answer, trace)

                print("\n--- Tool call trace (for demo/debugging) ---")
                if not trace:
                    print("  (no tools were called — model answered from its own knowledge)")
                for i, step in enumerate(trace, 1):
                    print(f"  {i}. {step['tool']}({step['arguments']})")
                    print(f"     -> {step['result'][:200]}{'...' if len(step['result']) > 200 else ''}")

                print("\n=== Final answer to farmer ===")
                print(final_answer)


if __name__ == "__main__":
    asyncio.run(main())