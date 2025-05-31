import ollama

# Define the Ollama API base URL (host and port)
# This can be configured via environment variables or a config file in a real application.
OLLAMA_API_HOST = "http://localhost:11434"

# Initialize the Ollama client
# The client automatically constructs the full API URLs (e.g., OLLAMA_API_HOST + '/api/tags')
try:
    client = ollama.Client(host=OLLAMA_API_HOST)
except Exception as e:
    print(f"Error initializing Ollama client: {e}")
    client = None # Set client to None if initialization fails

def list_ollama_models():
    """
    Retrieves a list of available models from the local Ollama instance
    using the ollama library.

    Returns:
        list: A list of model names, or an empty list if an error occurs or client is not initialized.
    """
    if not client:
        print("Ollama client not initialized.")
        return []
    try:
        models_data = client.list()
        # Extract model names from the response
        # The structure from client.list() is a list of dicts,
        # e.g., [{'name': 'llama2:latest', 'model': 'llama2:latest', ...}]
        model_names = [model.get("name") for model in models_data.get("models", []) if model.get("name")]
        return model_names
    except ollama.ResponseError as e:
        print(f"Ollama API error while listing models: {e.status_code} - {e.error}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while listing models: {e}")
        return []

def generate_response(model_name, prompt):
    """
    Generates a response from the specified Ollama model using the ollama library.

    Args:
        model_name (str): The name of the model to use.
        prompt (str): The prompt to send to the model.

    Returns:
        str: The model's response, or an empty string if an error occurs or client is not initialized.
    """
    if not client:
        print("Ollama client not initialized.")
        return ""
    try:
        # Prepare messages for the client.chat method
        messages = [
            {
                'role': 'user',
                'content': prompt,
            }
        ]
        # stream=False to get the full response at once.
        response_data = client.chat(model=model_name, messages=messages, stream=False)

        # Extract the response content for non-streaming
        # return response_data.get("message", {}).get("content", "")

        # Streaming implementation
        full_response_content = ""
        if stream_callback: # Streaming path
            response_stream = client.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True
            )
            for chunk in response_stream:
                content_part = chunk.get('message', {}).get('content', '')
                if content_part:
                    full_response_content += content_part
                    stream_callback(content_part) # Call callback with the chunk

                if chunk.get('done', False): # Check 'done' field
                    if chunk.get('error'):
                        error_message = f"Stream error: {chunk.get('error')}"
                        print(error_message)
                        # Optionally call stream_callback with an error marker or append to full_response
                        # stream_callback(f"\nSTREAM_ERROR: {error_message}\n") # Example
                        full_response_content += f"\nSTREAM_ERROR: {error_message}" # Append error to final content
                    break # Exit loop once done
            return full_response_content
        else: # Non-streaming path (fallback if no callback provided)
            response_data = client.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt}],
                stream=False
            )
            return response_data.get("message", {}).get("content", "")

    except ollama.ResponseError as e:
        error_msg = f"Ollama API error: {e.status_code} - {e.error}"
        print(error_msg)
        if e.status_code == 404:
             print(f"Model '{model_name}' not found. Please ensure it is available.")
        if stream_callback:
            stream_callback(f"\nERROR: {error_msg}\n") # Send error via callback if streaming
        return f"ERROR: {error_msg}" # Return error string for non-streaming or as final content
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(error_msg)
        if stream_callback:
            stream_callback(f"\nERROR: {error_msg}\n")
        return f"ERROR: {error_msg}"


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

            # Test generating a response (replace with an actual model and prompt if needed)
            # Using the first available model for the test
            test_model = available_models[0]
            test_prompt = "Why is the sky blue?"

            print(f"\nTesting model: {test_model}")
            print(f"Prompt: {test_prompt}")

            generated_text = generate_response(test_model, test_prompt)

            if generated_text:
                print(f"Response: {generated_text}")
            else:
                print("Failed to generate a response or response was empty.")
        elif client: # client exists but no models
             print("\nNo Ollama models found. Make sure Ollama is running and you have pulled some models (e.g., `ollama pull llama2`).")
        # If client is None, the initial check handles it.
