import json
import os
import uuid
from datetime import datetime

# Directory to store conversation files
MEMORY_DIR = "conversations"

# JSON Structure for Conversations:
# {
#   "conversation_id": "string (uuid or timestamp_based_unique_id)",
#   "model_name": "string (e.g., 'ollama_model_name')",
#   "timestamp_start": "string (ISO 8601 datetime)",
#   "timestamp_last_exchange": "string (ISO 8601 datetime)",
#   "title": "string (optional, short summary or user-defined title)",
#   "messages": [
#     {"role": "user", "content": "User's first prompt"},
#     {"role": "assistant", "content": "AI's first response"},
#     ...
#     # Additional roles like 'system' could be added if needed
#   ],
#   "learned_summary": "string (nullable, placeholder for future learned info/summary of chat)",
#   "tags": ["list_of_strings (optional, for categorization)"]
# }

def _ensure_memory_dir_exists():
    """Ensures the MEMORY_DIR exists, creating it if necessary."""
    if not os.path.exists(MEMORY_DIR):
        try:
            os.makedirs(MEMORY_DIR)
            print(f"Created memory directory: {MEMORY_DIR}")
        except OSError as e:
            print(f"Error creating memory directory {MEMORY_DIR}: {e}")
            return False
    return True

def save_conversation(conversation_data):
    """
    Saves a conversation dictionary to a JSON file in the MEMORY_DIR.

    Args:
        conversation_data (dict): The conversation data, matching the defined structure.
                                  It must include 'conversation_id'.

    Returns:
        str: The path to the saved file, or None on error.
    """
    if not _ensure_memory_dir_exists():
        return None

    if not isinstance(conversation_data, dict):
        print("Error: conversation_data must be a dictionary.")
        return None

    conversation_id = conversation_data.get("conversation_id")
    if not conversation_id:
        print("Error: conversation_id is missing in conversation_data.")
        # Potentially generate one if missing: conversation_id = str(uuid.uuid4())
        # For now, require it to be set by the caller.
        return None

    # Sanitize conversation_id to be a valid filename component (optional, UUIDs are generally safe)
    filename = f"conversation_{conversation_id}.json"
    filepath = os.path.join(MEMORY_DIR, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        print(f"Conversation saved to {filepath}")
        return filepath
    except IOError as e:
        print(f"Error saving conversation file {filepath}: {e}")
        return None
    except TypeError as e:
        print(f"Error serializing conversation data to JSON: {e}")
        return None

def load_conversation(filepath):
    """
    Loads and parses JSON data from a conversation file.

    Args:
        filepath (str): The full path to the conversation JSON file.

    Returns:
        dict: The Python dictionary of the conversation, or None on error.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            conversation_data = json.load(f)
        return conversation_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
        return None
    except IOError as e:
        print(f"Error loading conversation file {filepath}: {e}")
        return None

def list_saved_conversations(directory=MEMORY_DIR):
    """
    Scans the specified directory for .json conversation files.

    Returns:
        list: A list of filenames (not full paths) of .json files in the directory.
              Returns an empty list if the directory doesn't exist or no files are found.
    """
    if not os.path.exists(directory):
        print(f"Memory directory {directory} not found.")
        return []

    try:
        files = [f for f in os.listdir(directory) if f.startswith("conversation_") and f.endswith(".json")]
        return files
    except OSError as e:
        print(f"Error listing files in directory {directory}: {e}")
        return []

# update_conversation can be managed by the UI by loading, modifying, and then saving.
# For simplicity, the ChatWindowWidget will manage the current conversation object
# and call save_conversation with the full updated data.

if __name__ == "__main__":
    print("Running Simplified Memory Manager Test...")

    if not _ensure_memory_dir_exists():
        print("Failed to create or access memory directory. Exiting test.")
        exit(1) # Exit if directory creation fails

    sample_id = "test_001" # Using a fixed ID for simplicity in a minimal test
    sample_conversation = {
        "conversation_id": sample_id,
        "model_name": "simple_test_model",
        "timestamp_start": datetime.now().isoformat(),
        "timestamp_last_exchange": datetime.now().isoformat(),
        "messages": [{"role": "user", "content": "Minimal test prompt."}],
    }

    print(f"Attempting to save conversation: {sample_id}")
    saved_path = save_conversation(sample_conversation)

    if saved_path:
        print(f"Save reported success. Path: {saved_path}")
        if os.path.exists(saved_path):
            print(f"File successfully created at: {saved_path}")

            print(f"Attempting to load conversation from: {saved_path}")
            loaded_conv = load_conversation(saved_path)
            if loaded_conv:
                print(f"Successfully loaded conversation: {loaded_conv.get('conversation_id')}")
                if loaded_conv.get("conversation_id") == sample_id:
                    print("Content verification (ID match) successful.")
                else:
                    print("Content verification (ID match) FAILED.")
            else:
                print(f"Failed to load conversation from {saved_path}")
        else:
            print(f"File NOT found at reported save path: {saved_path}")
    else:
        print(f"Save reported failure for conversation: {sample_id}")

    print("\nListing conversations...")
    all_convs = list_saved_conversations()
    print(f"Found: {all_convs}")
    if f"conversation_{sample_id}.json" in all_convs:
        print(f"Test conversation 'conversation_{sample_id}.json' found in list.")
    else:
        print(f"Test conversation 'conversation_{sample_id}.json' NOT found in list.")

    print("\nSimplified Memory Manager Test Completed.")
