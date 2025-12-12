import os
import sys
import json
import importlib
from google.genai import types

# Add current directory to path
sys.path.append(os.getcwd())

# Load config and set API Key
CONFIG_PATH = os.path.join(os.getcwd(), 'dados', 'config.json')
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            c = json.load(f)
            if c.get('api_key'):
                os.environ['GOOGLE_API_KEY'] = c.get('api_key')
                print(f"API Key loaded from config: {c.get('api_key')[:5]}...")
    except Exception as e:
        print(f"Error loading config: {e}")

# Import tea.agent
import tea.agent
# tea.agent = importlib.reload(tea.agent) # Ensure we have latest

from google.adk.runners import InMemoryRunner
import asyncio

async def run_chat_async():
    print("Initializing Runner...")
    
    # Setup runner
    runner = InMemoryRunner(agent=tea.agent.root_agent, app_name='tia')
    
    # Create session
    session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
    
    msg = "o que é o O e-DOCS ?"
    user_content = types.Content(role='user', parts=[types.Part(text=msg)])
    
    print(f"Sending message: {msg}")
    
    try:
        events = []
        async for event in runner.run_async(
            session_id=session_id,
            user_id='user',
            new_message=user_content
        ):
            events.append(event)
            
        # The last event usually contains the final model response?
        # Or we need to look for 'model_response' type event
        
        print(f"Received {len(events)} events")
        
        for i, ev in enumerate(events):
            print(f"Event {i}: {ev}")
            # Inspect event structure
            if hasattr(ev, 'model_response') and ev.model_response:
                print("Model used:", ev.model_response.model)
                text_parts = []
                for part in ev.model_response.parts:
                    if part.text:
                        text_parts.append(part.text)
                print("Response received:")
                print("".join(text_parts))
                break
            elif hasattr(ev, 'text') and ev.text: # Fallback if event is just text
                 print("Response text:", ev.text)

    except Exception as e:
        print(f"Error running chat: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_chat_async())