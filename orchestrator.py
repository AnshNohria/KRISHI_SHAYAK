# orchestrator.py
from typing import List, Dict, Any
import json
import google.generativeai as genai
import re
from marketPrice import price_predict_tool, current_price_tool
from datetime import datetime
from scheme_search_tool import SchemeSearchTool
from maps.simple_maps_chatbot import SimpleMapsBot
# 
# GOOGLE_API_KEY = "AIzaSyCXwpZBTO5WaEyvFjhSLwTQDYeF_kp_rj4"
GOOGLE_API_KEY = "AIzaSyDmDWj8fbIEMIgFvF9lldf97WZIs3qDtXo"
GEMINI_MODEL_NAME = "gemini-1.5-flash"

class OrchestratorAgent:
    def __init__(self):
        """
        llm: your main LLM instance (e.g. Groq or Gemini)
        tools: dict of tool_name -> tool_instance
        """
        genai.configure(api_key=GOOGLE_API_KEY)
        self.llm = genai.GenerativeModel(model_name=GEMINI_MODEL_NAME)
        self.tools = {
            "price_predict_tool": {
                "description": "Using the district, state and commodity, the tool predicts if the modal price of the commodity could go up or down in the next 7 days, and whether the farmer should hold or sell his produce",
                "instance": price_predict_tool
            },
            "current_price_tool": {
                "description": "Using the district, state and commodity as inputs, this tool fetches the current or most recent price of the commodity in the said district.",
                "instance": current_price_tool
            },
            "scheme_search_tool": {
                "description": "Search for relevant agriculture schemes in different states of India based on user query and conversation history, passed together as one parameter. The tool optimises the query by itself",
                "instance": SchemeSearchTool()
            },
            "map_search_tool": {
                "description": "Search for nearest shops to sell agricultural produce, Krishi Vigyan Kendras (KVKs, that are help centers that help farmers register for FPOs, and other schemes), relevant maps and geographical information based on user query and conversation history.",
                "instance": SimpleMapsBot()
            }
        }
        self.conversation_history = []

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        First LLM call: analyze the query.
        Returns dict with:
        - type: "followup" or "tools"
        - tools_needed: list of tool names if applicable
        """
        tool_names = list(self.tools.keys())
        analysis_prompt = f"""
            You are the orchestrator agent.
            Task: Analyze the query and decide if it can be answered
            directly from history or if tools are needed.

            Available tools and their purpose:
            { {name: meta["description"] for name, meta in self.tools.items()} }

            Query: {query}
            History: {json.dumps(self.conversation_history)}

            Respond ONLY in JSON with keys:
            - "type": "followup" or "tools"
            - "tools_needed": list of tool names (from {tool_names})

            Examples:

            1. Tools case:
            Query: "What is the modal price of onions in Jaipur, Rajasthan?"
            History: []
            Response: {{
            "type": "tools",
            "tools_needed": ["current_price_tool"]
            }}

            2. Followup case:
            Query: "Can you repeat that?"
            History: [{{"role": "user", "content": "What is the modal price of onions in Jaipur, Rajasthan?"}},
                    {{"role": "assistant", "content": "The modal price of onions in Jaipur yesterday was Rs. 2000/quintal."}}]
            Response: {{
            "type": "followup",
            "tools_needed": []
            }}
            """
        response = self.llm.generate_content(contents=analysis_prompt)
        return self._safe_json(response.text)

    def resolve_query_with_history(self, query: str, tool_name: str) -> str:
        """
        Uses an LLM call to fill in missing details from the history and append them to the query.
        """
        tool_description = self.tools[tool_name]['description']
        prompt = f"""
        You are an intelligent assistant. Your task is to **resolve and augment a user's query** by finding any missing information (like commodity, district, or state) from the conversation history.

        **Tool Information:**
        Tool Name: {tool_name}
        Tool Description: {tool_description}
        The tool requires information about commodity, district, and state.

        **Conversation History (most recent info at the end):**
        {json.dumps(self.conversation_history)}

        **Current User Query:**
        "{query}"

        **Instructions:**
        1. Read the most recent conversation entries to find the latest-mentioned **commodity, district, and state**.
        2. If the **current query** is a follow-up (e.g., "how much?", "should I sell?"), use the information from the history to make the query complete.
        3. If the current query already contains the information, use it. Do not just repeat the history.
        4. The output must be a single, natural-language sentence or phrase that is a complete and unambiguous query for the tool. Do not just output JSON.

        **Examples:**
        History: [{{"role": "user", "content": "What is the price of onions in Jaipur, Rajasthan?"}}]
        Current Query: "Will it go up?"
        Correct Output: "Will the price of onions in Jaipur, Rajasthan go up?"

        History: [{{"role": "user", "content": "Price of tomatoes in Bangalore."}}]
        Current Query: "What about in Mysore?"
        Correct Output: "What is the price of tomatoes in Mysore, Karnataka?"

        **Now, resolve this query:**
        Augmented Query:
        """
        response = self.llm.generate_content(prompt)
        return response.text.strip()

    def call_tools(self, query: str, tools_needed: List[str]) -> Dict[str, Any]:
        results = {}
        for tool_name in tools_needed:
            tool_entry = self.tools.get(tool_name)
            if not tool_entry:
                continue
            tool_function = tool_entry["instance"]
            if tool_name == "scheme_search_tool":
                mod_qry = "\n".join(
                    f"{item['role'].capitalize()}: {item['content']}" for item in self.conversation_history
                ) + "\nCurrent Query: " + query
                results[tool_name] = tool_function.execute(mod_qry)
            # Call the tool function directly as it is not a class with a .run() method
            # This is a key fix based on your implementation
            elif tool_name == "map_search_tool":
                results[tool_name] = tool_function.get_maps_response(query, self.conversation_history)
            else:
                augmented_query = self.resolve_query_with_history(query, tool_name)
                print(f"Augmented query for {tool_name}: {augmented_query}")
                results[tool_name] = tool_function(augmented_query)
        return results

    def final_response(self, query: str, tool_results: Dict[str, Any]) -> str:
        """
        Last LLM call: weave tool results into farmer-friendly response.
        """
        prompt = f"""
        User query: {query}
        Conversation history: {json.dumps(self.conversation_history)}
        Tool results: {json.dumps(tool_results, indent=2)}

        Write a clear, concise, and crisp answer for the farmer, in simple language.
        Combine all the important information from the tool results into a single, cohesive response.
        If the 'scheme_search_tool' is used, ensure that all details of the schemes are included, and if applicable, provide a summary of the benefits and eligibility criteria.
        If a tool returned an error or an "unable to process" message, explain this to the farmer in a helpful way.
        """
        response = self.llm.generate_content(contents=prompt)
        return response.text

    def handle_query(self, query: str) -> str:
        """
        Main entry point: orchestrates everything.
        """
        self.conversation_history.append({"role": "user", "content": query})

        analysis = self.analyze_query(query)
        print(f"Analysis result: {analysis}")

        if analysis.get("type") == "followup":
            # Just generate response from history
            reply = self.llm.generate_content(
                f"Conversation so far: {json.dumps(self.conversation_history)}\n"
                f"Answer the last user query directly in a helpful way."
            ).text
        else:
            # Call tools
            tools_to_call = analysis.get("tools_needed", [])
            print(f"Tools to call: {tools_to_call}")
            if tools_to_call:
                tool_results = self.call_tools(query, tools_to_call)
                print(f"Tool results: {tool_results}")
                reply = self.final_response(query, tool_results)
            else:
                # Fallback if no tools were identified but type was not followup
                reply = "I'm sorry, I couldn't identify a specific action for this request. Can you please rephrase?"

        self.conversation_history.append({"role": "assistant", "content": reply})
        return reply

    def _safe_json(self, text: str) -> Dict[str, Any]:
        try:
            # Use regex to find the JSON object and strip surrounding text
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                json_string = json_match.group(0)
                return json.loads(json_string)
            else:
                print(f"Warning: No JSON object found in LLM response: {text}")
                return {"type": "followup", "tools_needed": []}
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e} | Raw text: {text}")
            return {"type": "followup", "tools_needed": []}
        except Exception as e:
            print(f"An unexpected error occurred in _safe_json: {e}")
            return {"type": "followup", "tools_needed": []}

# Note: The tool functions (price_predict_tool and current_price_tool) would need to be in
# a separate file (e.g., marketPrice.py) as indicated by your imports.