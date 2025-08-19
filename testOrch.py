from orchestrator import OrchestratorAgent
orch = OrchestratorAgent()

# Directly test with the real tools
query1 = "tell me about some crop insurance schemes"
print("\nQuery 1:", query1)
print("Response:", orch.handle_query(query1))

query3 = "Can you repeat that?"
print("\nQuery 3:", query3)
print("Response:", orch.handle_query(query3))
