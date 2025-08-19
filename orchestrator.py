"""Orchestrator agent that routes farmer queries to the correct tools and
generates a concise natural-language response.

This version removes LangChain usage and directly calls google-generativeai.
It also adds defensive handling to avoid empty LLM responses (important for
the voice assistant flow where TTS expects non-empty text).
"""

from typing import List, Dict, Any
import json
import re
import os
from llm_client import generate_text

from marketPrice import price_predict_tool, current_price_tool
from maps.simple_maps_chatbot import SimpleMapsBot
from weather.simple_weather_chatbot import SimpleWeatherBot
from fpo.simple_fpo_chatbot import SimpleFPOBot
from Advisory.simple_chatbot import SimpleKrishiBot

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = "gemini-1.5-flash"


class OrchestratorAgent:
    def __init__(self):
        # central client handles absence of key (llm_client will lazily init)
        self.llm_available = bool(GOOGLE_API_KEY)
        from scheme_search_tool import SchemeSearchTool
        self.tools: Dict[str, Dict[str, Any]] = {
            "price_predict_tool": {
                "description": "Predicts 7‑day direction (hold/sell advice) using district, state, commodity.",
                "instance": price_predict_tool,
            },
            "current_price_tool": {
                "description": "Fetches latest/modal market price for a commodity in a district/state.",
                "instance": current_price_tool,
            },
            "scheme_search_tool": {
                "description": "Searches Indian government agriculture schemes, subsidies, loans, benefits, and programs using semantic and keyword matching.",
                "instance": SchemeSearchTool(),
            },
            "map_search_tool": {
                "description": "Nearby agri points: markets, KVKs, selling centers, geo info.",
                "instance": SimpleMapsBot(),
            },
            "weather_tool": {
                "description": "Weather conditions & simple advice for a location.",
                "instance": SimpleWeatherBot(),
            },
            "fpo_tool": {
                "description": "Nearest Farmer Producer Organisations (FPOs).",
                "instance": SimpleFPOBot(),
            },
            "Crop_Advisory_tool": {
                "description": "RAG based crop advisory (diseases, best practices).",
                "instance": SimpleKrishiBot(),
            },
        }
        self.conversation_history: List[Dict[str, str]] = []
        self.last_tool_results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Low-level LLM helpers
    # ------------------------------------------------------------------
    def _extract_text(self, resp) -> str:
        if resp is None:
            return ""
        try:
            if getattr(resp, "text", None):
                return resp.text.strip()
        except Exception:
            pass
        try:  # fallback aggregate
            candidates = getattr(resp, "candidates", []) or []
            if candidates:
                cand = candidates[0]
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", "")]
                    return "\n".join(t.strip() for t in texts if t.strip())
        except Exception:
            pass
        return ""

    def _llm(self, prompt: str) -> str:
        txt = generate_text(prompt, model_name=GEMINI_MODEL_NAME, retries=2)
        if not txt:
            return (
                "I gathered the data but the model returned an empty answer. "
                "Please rephrase or ask a follow-up."
            )
        return txt

    # ------------------------------------------------------------------
    # Orchestration steps
    # ------------------------------------------------------------------
    def analyze_query(self, query: str) -> Dict[str, Any]:
        tool_names = list(self.tools.keys())
        tool_desc_map = {name: meta["description"] for name, meta in self.tools.items()}
        prompt = (
            "You are a routing classifier. Decide if the query needs tools or is a follow-up.\n"
            f"Tools: {tool_desc_map}\n"
            f"History: {json.dumps(self.conversation_history)}\n"
            f"User Query: {query}\n\n"
            f"Return ONLY JSON with keys: 'type' (tools|followup) and 'tools_needed' (list subset of {tool_names}).\n"
            "If unsure which tool, choose the closest."
        )
        text = generate_text(prompt, model_name=GEMINI_MODEL_NAME, retries=1)
        return self._safe_json(text)

    def resolve_query_with_history(self, query: str, tool_name: str) -> str:
        tool_desc = self.tools[tool_name]["description"]
        prompt = f"""
Augment the user query with any missing (commodity, district, state) gleaned from history.
History: {json.dumps(self.conversation_history)}
Tool: {tool_name} - {tool_desc}
Original: {query}
Output a SINGLE natural language query (no JSON) that the tool can understand.
"""
        return self._llm(prompt).strip()

    def call_tools(self, query: str, tools_needed: List[str]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for name in tools_needed:
            entry = self.tools.get(name)
            if not entry:
                continue
            inst = entry["instance"]
            try:
                if name == "scheme_search_tool":
                    # Use the tool's execute method for scheme search
                    results[name] = inst.execute(query, conversation_history=self.conversation_history)
                elif name == "map_search_tool":
                    results[name] = inst.get_maps_response(query, self.conversation_history)
                elif name == "weather_tool":
                    results[name] = inst.get_weather_response(query, self.conversation_history)
                elif name == "fpo_tool":
                    results[name] = inst.get_fpo_response(query, self.conversation_history)
                elif name == "Crop_Advisory_tool":
                    results[name] = inst.get_rag_response(query, self.conversation_history)
                else:  # price tools
                    aug = self.resolve_query_with_history(query, name)
                    results[name] = inst(aug)
            except Exception as e:
                results[name] = f"Tool {name} failed: {e}"
        return results

    def final_response(self, query: str, tool_results: Dict[str, Any]) -> str:
        prompt = f"""
User query: {query}
History: {json.dumps(self.conversation_history)}
Tool results JSON: {json.dumps(tool_results, indent=2)}

Write a short, clear answer for a farmer in simple language combining the results.
If any tool failed, briefly mention it helpfully.
"""
        return self._llm(prompt)

    def handle_query(self, query: str) -> str:
        self.conversation_history.append({"role": "user", "content": query})
        analysis = self.analyze_query(query)
        print("Analysis:", analysis)

        if analysis.get("type") == "followup":
            reply = self._llm(
                f"Conversation so far: {json.dumps(self.conversation_history)}\n"
                f"Answer the last user query helpfully and concisely."
            )
        else:
            tools = analysis.get("tools_needed", [])
            print("Tools chosen:", tools)
            if tools:
                tool_results = self.call_tools(query, tools)
                self.last_tool_results = tool_results
                print("Tool results:", {k: (str(v)[:120] + '...') if isinstance(v, str) and len(v) > 120 else v for k, v in tool_results.items()})
                reply = self.final_response(query, tool_results)
            else:
                reply = "I couldn't determine the exact action. Please rephrase with more specifics."

        if not reply:
            reply = "I processed your request but couldn't form a full answer. Please ask again with more detail."

        self.conversation_history.append({"role": "assistant", "content": reply})
        return reply

    # ------------------------------------------------------------------
    # JSON safety helper
    # ------------------------------------------------------------------
    def _safe_json(self, text: str) -> Dict[str, Any]:
        try:
            m = re.search(r"\{.*?\}", text, re.DOTALL)
            if not m:
                print("No JSON found in analysis response:", text)
                return {"type": "followup", "tools_needed": []}
            data = json.loads(m.group(0))
            if data.get("type") not in ("tools", "followup"):
                data["type"] = "followup"
            if not isinstance(data.get("tools_needed"), list):
                data["tools_needed"] = []
            # keep only known tools
            data["tools_needed"] = [t for t in data["tools_needed"] if t in self.tools]
            return data
        except Exception as e:
            print("_safe_json error:", e, "| raw:", text)
            return {"type": "followup", "tools_needed": []}

# End of file
