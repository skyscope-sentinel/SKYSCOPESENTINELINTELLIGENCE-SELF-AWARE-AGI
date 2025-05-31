import ollama

# Define the Ollama API base URL (host and port)
OLLAMA_API_HOST = "http://localhost:11434"

# Initialize the Ollama client
# The client automatically constructs the full API URLs
try:
    client = ollama.Client(host=OLLAMA_API_HOST)
except Exception as e:
    print(f"ERROR (ollama_integration): Error initializing Ollama client: {e}")
    client = None

def list_ollama_models() -> list[str]:
    """
    Retrieves a list of available models from the local Ollama instance.

    Uses the `ollama` library.

    Returns:
        list[str]: A list of model names (e.g., ["llama2:latest", "mistral:latest"]).
                   Returns an empty list if an error occurs or the client is not initialized.
    """
    if not client:
        print("ERROR (ollama_integration): Ollama client not initialized in list_ollama_models.")
        return []
    try:
        models_data = client.list()
        # Extract model names from the response
        # The structure from client.list() is like: {'models': [{'name': 'model1', ...}, {'name': 'model2', ...}]}
        model_names = [model.get("name") for model in models_data.get("models", []) if model.get("name")]
        return model_names
    except ollama.ResponseError as e:
        print(f"ERROR (ollama_integration): Ollama API error while listing models: {e.status_code} - {e.error}")
        return []
    except Exception as e:
        print(f"ERROR (ollama_integration): An unexpected error occurred while listing models: {e}")
        return []

def generate_response(model_name: str, prompt: str, stream_callback: callable = None) -> str:
    """
    Generates a response from the specified Ollama model using the ollama library.

    If `stream_callback` is provided, it's called incrementally with parts of the response.
    The full response is returned at the end regardless of streaming.

    Args:
        model_name (str): The name of the Ollama model to use.
        prompt (str): The user's prompt.
        stream_callback (callable, optional): A function to call with each streamed chunk of content.
                                              Defaults to None.

    Returns:
        str: The full response content from the model, or an error message string.
    """
    if not client:
        error_msg = "Ollama client not initialized in generate_response."
        print(f"ERROR (ollama_integration): {error_msg}")
        if stream_callback:
            stream_callback(f"\nERROR: {error_msg}\n")
        return f"ERROR: {error_msg}"

    messages = [{'role': 'user', 'content': prompt}]
    full_response_content = ""

    try:
        if stream_callback: # Streaming path
            response_stream = client.chat(model=model_name, messages=messages, stream=True)
            for chunk in response_stream:
                content_part = chunk.get('message', {}).get('content', '')
                if content_part:
                    full_response_content += content_part
                    stream_callback(content_part)

                if chunk.get('done', False):
                    if chunk.get('error'):
                        error_message = f"Stream error: {chunk.get('error')}"
                        print(f"ERROR (ollama_integration): {error_message}")
                        full_response_content += f"\nSTREAM_ERROR: {error_message}"
                    break
            return full_response_content
        else: # Non-streaming path
            response_data = client.chat(model=model_name, messages=messages, stream=False)
            return response_data.get("message", {}).get("content", "")

    except ollama.ResponseError as e:
        error_msg = f"Ollama API error: {e.status_code} - {e.error}"
        print(f"ERROR (ollama_integration): {error_msg}")
        if e.status_code == 404:
             print(f"ERROR (ollama_integration): Model '{model_name}' not found. Please ensure it is available.")
        if stream_callback:
            stream_callback(f"\nERROR: {error_msg}\n")
        return f"ERROR: {error_msg}"
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(f"ERROR (ollama_integration): {error_msg}")
        if stream_callback:
            stream_callback(f"\nERROR: {error_msg}\n")
        return f"ERROR: {error_msg}"

def show_model_info(model_name: str) -> dict:
    """
    Retrieves detailed information for a specific model from Ollama.

    Args:
        model_name (str): The name of the model to get information for.

    Returns:
        dict: A dictionary containing model information (including 'modelfile', 'details', 'parameters'),
              or a dictionary with an "error" key if an issue occurs.
    """
    if not client:
        print("ERROR (ollama_integration): Ollama client not initialized in show_model_info.")
        return {"error": "Ollama client not initialized."}
    try:
        return client.show(model_name)
    except ollama.ResponseError as e:
        print(f"ERROR (ollama_integration): Ollama API error showing info for '{model_name}': {e.status_code} - {e.error}")
        return {"error": f"Ollama API error: {e.status_code} - {e.error}"}
    except Exception as e:
        print(f"ERROR (ollama_integration): Unexpected error showing info for '{model_name}': {e}")
        return {"error": f"Unexpected error: {e}"}

def delete_model(model_name: str) -> bool:
    """
    Deletes a specified model from the local Ollama instance.

    Args:
        model_name (str): The name of the model to delete.

    Returns:
        bool: True if the model was successfully deleted (or didn't exist), False otherwise.
    """
    if not client:
        print("ERROR (ollama_integration): Ollama client not initialized in delete_model.")
        return False
    try:
        client.delete(model_name)
        print(f"INFO (ollama_integration): Model '{model_name}' deleted successfully from Ollama.")
        return True
    except ollama.ResponseError as e:
        if e.status_code == 404:
            print(f"INFO (ollama_integration): Model '{model_name}' not found in Ollama (already deleted or never existed). Considered successful deletion.")
            return True
        print(f"ERROR (ollama_integration): Ollama API error deleting model '{model_name}': {e.status_code} - {e.error}")
        return False
    except Exception as e:
        print(f"ERROR (ollama_integration): Unexpected error deleting model '{model_name}': {e}")
        return False

if __name__ == '__main__':
    if not client:
        print("Exiting: Ollama client could not be initialized.")
    else:
        print("Attempting to connect to Ollama...")
        available_models = list_ollama_models()

        if available_models:
            print("\nAvailable Ollama models:")
            for model in available_models:
                print(f"- {model}")

            test_model = available_models[0]
            print(f"\n--- Testing show_model_info for: {test_model} ---")
            info = show_model_info(test_model)
            if "error" not in info:
                print(f"Modelfile: {info.get('modelfile', 'N/A')[:100]}...") # Print first 100 chars
                print(f"Parameters: {info.get('parameters', 'N/A')[:100]}...")
            else:
                print(f"Error getting info: {info['error']}")

            print(f"\n--- Testing generate_response (non-streaming) for: {test_model} ---")
            prompt = "Why is the sky blue?"
            response = generate_response(test_model, prompt)
            print(f"Prompt: {prompt}\nResponse: {response}")

            print(f"\n--- Testing generate_response (streaming) for: {test_model} ---")
            def my_stream_callback(chunk_content):
                print(f"Stream chunk: '{chunk_content}'", end='', flush=True)

            full_streamed_response = generate_response(test_model, "Tell me a short joke.", stream_callback=my_stream_callback)
            print(f"\nFull streamed response collected: {full_streamed_response}")

            # Example of delete (use with caution, maybe a test model)
            # test_delete_model_name = "test-delete-me-model"
            # print(f"\n--- Testing delete_model for: {test_delete_model_name} ---")
            # print(f"(Note: This will attempt to delete {test_delete_model_name} if it exists or was created by mistake)")
            # delete_model(test_delete_model_name)

        elif client:
             print("\nNo Ollama models found. Make sure Ollama is running and you have pulled some models (e.g., `ollama pull llama2`).")
        # If client is None, the initial check handles it.
