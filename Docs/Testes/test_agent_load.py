import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import tea.agent...")
    from tea.agent import agent
    print(f"Successfully imported agent: {agent.name}")
    print(f"Agent model: {agent.model}")
    print(f"Number of tools: {len(agent.tools)}")
except Exception as e:
    print(f"Error importing agent: {e}")
    import traceback
    traceback.print_exc()
