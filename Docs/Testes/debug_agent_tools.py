import sys
import os
import importlib

# Add project root to path
sys.path.append(os.getcwd())

try:
    import tea.agent as agent
    print("Agent module imported.")
    
    # Reload to simulate app behavior
    importlib.reload(agent)
    
    fazenda = agent.sub_agents_map.get('secretaria_da_fazenda')
    if not fazenda:
        print("Agent 'secretaria_da_fazenda' not found in map.")
        # List available
        print("Available agents:", list(agent.sub_agents_map.keys()))
    else:
        print(f"Agent found: {fazenda.name}")
        print(f"Model: {fazenda.model}")
        print("Tools:")
        for tool in fazenda.tools:
            print(f" - {type(tool).__name__}")
            if hasattr(tool, 'file_search_store_names'):
                print(f"   Stores: {tool.file_search_store_names}")
                
except Exception as e:
    print(f"Error: {e}")
