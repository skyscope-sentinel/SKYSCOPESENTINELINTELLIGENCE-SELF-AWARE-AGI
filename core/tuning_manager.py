import os
import json
import shutil # Not used in the current plan, but good for future file ops
import uuid # For unique output directory names if needed
import time # For monitoring sleep
import threading # For monitoring thread
import subprocess # For calling ollama create
import tempfile # For temporary Modelfile

class TuningManager:
    def __init__(self):
        self._monitoring_thread = None
        self._stop_monitoring_event = threading.Event()

    def prepare_conversation_data_for_script(self, conversation_filepaths: list[str], temp_jsonl_path: str) -> bool:
        """
        Loads conversations from individual JSON files, formats them, and writes to a single JSONL file.
        Each line in the output JSONL file will be a JSON object: {"text": "formatted_conversation_string"}
        The formatted_conversation_string is "<s>[INST] prompt [/INST] response </s>..." for all turns in one conversation.
        """
        try:
            os.makedirs(os.path.dirname(temp_jsonl_path), exist_ok=True)
            with open(temp_jsonl_path, "w", encoding="utf-8") as outfile:
                for filepath in conversation_filepaths:
                    try:
                        with open(filepath, "r", encoding="utf-8") as conv_file:
                            conv_data = json.load(conv_file)

                        messages = conv_data.get("messages", [])
                        if not messages:
                            print(f"Warning: No messages found in {filepath}, skipping.")
                            continue

                        # Concatenate messages into a single string for the entire conversation
                        # Example format: "<s>[INST] prompt1 [/INST] response1 </s><s>[INST] prompt2 [/INST] response2 </s>"
                        # This assumes alternating user/assistant roles.
                        formatted_conversation_string = ""
                        current_prompt = None
                        for i, message in enumerate(messages):
                            role = message.get("role")
                            content = message.get("content", "")

                            if role == "user":
                                current_prompt = content
                            elif role == "assistant" and current_prompt is not None:
                                formatted_conversation_string += f"<s>[INST] {current_prompt} [/INST] {content} </s>"
                                current_prompt = None # Reset prompt after a pair
                            elif role == "assistant" and current_prompt is None and i == 0: # Handle assistant starting convo
                                # This case is less common for training, usually starts with user.
                                # Decide how to handle, e.g. prepend a generic user turn or skip.
                                # For now, we'll assume user starts or we only take valid pairs.
                                print(f"Warning: Conversation {filepath} has an initial assistant message without a preceding user prompt. This part may be skipped.")

                        if formatted_conversation_string: # Only write if we formed valid pairs
                            outfile.write(json.dumps({"text": formatted_conversation_string.strip()}) + "\n")
                        elif not messages and not formatted_conversation_string:
                            print(f"Warning: No valid user/assistant pairs to format in {filepath}")


                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON from {filepath}: {e}. Skipping this file.")
                        continue
                    except IOError as e:
                        print(f"Error reading file {filepath}: {e}. Skipping this file.")
                        continue
            print(f"Successfully prepared conversation data at: {temp_jsonl_path}")
            return True
        except Exception as e:
            print(f"Failed to prepare conversation data: {e}")
            return False

    def generate_training_script(self, parameters: dict, script_save_path: str,
                                 conversation_jsonl_path: str or None,
                                 adapter_output_path: str,
                                 local_files_list: list[str]) -> bool:
        """
        Generates a Python training script based on the provided parameters.
        """
        try:
            os.makedirs(os.path.dirname(script_save_path), exist_ok=True)
            os.makedirs(adapter_output_path, exist_ok=True) # Ensure adapter output dir also exists

            # Prepare parameters for template insertion
            base_model = parameters.get('base_model', 'default_model_path')
            lora_rank = int(parameters.get('lora_rank', 16))
            learning_rate_str = parameters.get('learning_rate', "5e-5")
            try:
                learning_rate = float(learning_rate_str)
            except ValueError:
                print(f"Warning: Invalid learning rate '{learning_rate_str}'. Defaulting to 5e-5.")
                learning_rate = 5e-5
            num_epochs = int(parameters.get('num_epochs', 3))

            # Handle path escaping for string literals in the script
            # JSON dumping handles this well for lists/strings within the script content.
            # For paths directly in f-string literals, ensure they are correctly formatted.
            # os.path.normpath and then replacing \ with / for cross-platform script path consistency
            # is good, but here paths are for the user's environment.
            # Safest is to use raw strings or ensure backslashes are doubled if on Windows and paths are manually constructed.
            # For this template, simple string insertion should be okay if paths are posix-like or correctly escaped by user.

            script_template = f"""#!/usr/bin/env python
# Generated Training Script by Skyscope Sentient AI Platform
import os
import json
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import fitz # PyMuPDF

# --- Configuration (Hardcoded from UI) ---
BASE_MODEL_PATH = r"{base_model}"
ADAPTER_OUTPUT_DIR = r"{adapter_output_path}"
# Ensure CONVERSATION_JSONL_FILE is None (the Python None type) if path is 'None' (the string)
CONVERSATION_JSONL_FILE_STR = "{conversation_jsonl_path if conversation_jsonl_path else 'None'}"
CONVERSATION_JSONL_FILE = None if CONVERSATION_JSONL_FILE_STR == 'None' else CONVERSATION_JSONL_FILE_STR
ADDITIONAL_TEXT_FILES = {json.dumps(local_files_list)} # Safely dump list as Python list string
LORA_RANK = {lora_rank}
LEARNING_RATE = {learning_rate}
NUM_EPOCHS = {num_epochs}
MAX_LENGTH = {parameters.get('max_token_length', 512)} # Example: make this configurable later
PER_DEVICE_TRAIN_BATCH_SIZE = {parameters.get('batch_size', 1)}
GRADIENT_ACCUMULATION_STEPS = {parameters.get('gradient_accumulation', 4)}

def load_and_prepare_data():
    print("Loading and preparing data...")
    all_texts = []

    # Load from JSONL conversation file
    if CONVERSATION_JSONL_FILE:
        print(f"Loading conversations from {{CONVERSATION_JSONL_FILE}}")
        try:
            with open(CONVERSATION_JSONL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if "text" in data:
                            all_texts.append(data["text"])
                        else:
                            print(f"Warning: 'text' field missing in line: {{line.strip()}}")
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON from line: {{line.strip()}}")
        except IOError as e:
            print(f"Error reading conversation file {{CONVERSATION_JSONL_FILE}}: {{e}}")

    # Load from additional text and PDF files
    print(f"Loading additional text files: {{ADDITIONAL_TEXT_FILES}}")
    for file_path in ADDITIONAL_TEXT_FILES:
        try:
            if file_path.lower().endswith(".pdf"):
                print(f"Extracting text from PDF: {{file_path}}")
                doc = fitz.open(file_path)
                text = ""
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text += page.get_text()
                all_texts.append(text)
                doc.close()
            elif file_path.lower().endswith(".txt"):
                print(f"Reading text from TXT: {{file_path}}")
                with open(file_path, "r", encoding="utf-8") as f:
                    all_texts.append(f.read())
            else:
                print(f"Warning: Unsupported file type {{file_path}}, skipping.")
        except Exception as e:
            print(f"Error processing file {{file_path}}: {{e}}")

    if not all_texts:
        print("Error: No text data loaded. Exiting.")
        exit(1)

    print(f"Total text segments loaded: {{len(all_texts)}}")
    # Create a Hugging Face Dataset
    # Each item in all_texts is a document/conversation string.
    # The "text" key is expected by the tokenizer function.
    data_dict = {{"text": all_texts}}
    dataset = Dataset.from_dict(data_dict)
    print("Dataset created successfully.")
    return dataset

def main():
    print("--- Starting Fine-Tuning Script ---")
    print(f"Base Model: {{BASE_MODEL_PATH}}")
    print(f"Adapter Output Dir: {{ADAPTER_OUTPUT_DIR}}")

    dataset = load_and_prepare_data()

    print("Initializing tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        print("Pad token not set. Setting pad_token to eos_token.")
        tokenizer.pad_token = tokenizer.eos_token

    print("Tokenizing dataset...")
    def tokenize_function(examples):
        # Tokenize the "text" field. texts are already formatted "<s>[INST]...</s>"
        tokenized_output = tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length", # Pad to max_length
            max_length=MAX_LENGTH, # Use a configurable max_length
            # return_attention_mask=True # Trainer handles this if not explicitly given
        )
        return tokenized_output

    tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
    print("Dataset tokenized.")

    print("Setting up QLoRA configuration...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 # or torch.float16
    )

    print(f"Loading base model ({{BASE_MODEL_PATH}}) with quantization...")
    # device_map="auto" should work for multi-GPU, or specify a device
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        quantization_config=bnb_config,
        device_map="auto", # Automatically distribute model on available GPUs
        trust_remote_code=True
    )
    # model.config.use_cache = False # Recommended for training

    print("Setting up LoRA config...")
    # Target modules depend on the model architecture.
    # Common for Llama-like models:
    target_modules = ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    # For other models, inspect model.named_modules() to find appropriate linear layers.
    lora_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_RANK * 2, # Common practice: alpha = 2*r
        target_modules=target_modules,
        lora_dropout=0.05, # Common value
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )

    print("Applying PEFT to model...")
    peft_model = get_peft_model(model, lora_config)
    peft_model.print_trainable_parameters()

    print("Setting up Training Arguments...")
    training_args = TrainingArguments(
        output_dir=ADAPTER_OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=PER_DEVICE_TRAIN_BATCH_SIZE, # Adjust based on VRAM
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS, # Adjust based on VRAM
        logging_steps=10,
        save_strategy="epoch", # Saves a checkpoint at the end of each epoch
        # save_steps=50, # Alternative: save every N steps
        fp16=torch.cuda.is_available(), # Use mixed precision if GPU available
        report_to="none", # Disable wandb, tensorboard etc. for this script
        # optim="paged_adamw_8bit" # Can use paged optimizer for memory efficiency if bitsandbytes supports it well
    )

    print("Initializing Trainer...")
    trainer = Trainer(
        model=peft_model,
        args=training_args,
        train_dataset=tokenized_dataset,
        # eval_dataset=None, # Provide evaluation dataset if available
        tokenizer=tokenizer,
        # data_collator=None, # Default collator should be fine for text data
    )

    print("Starting training...")
    trainer.train()
    print("Training finished.")

    print(f"Saving LoRA adapter and tokenizer to {{ADAPTER_OUTPUT_DIR}}...")
    peft_model.save_pretrained(ADAPTER_OUTPUT_DIR)
    tokenizer.save_pretrained(ADAPTER_OUTPUT_DIR)
    print("Adapter and tokenizer saved.")
    print("--- Fine-Tuning Script Completed ---")

if __name__ == "__main__":
    # This script is intended to be configured and run by another process,
    # but can be run directly if parameters are manually set above or via CLI (not implemented here).
    # For CLI execution, one would typically use argparse to override the hardcoded configs.

    # Example of how to add argparse if needed directly in this script:
    # parser = argparse.ArgumentParser(description="Fine-tune a model with LoRA.")
    # parser.add_argument("--base_model_path", type=str, default=BASE_MODEL_PATH)
    # ... add other args ...
    # args = parser.parse_args()
    # Then use args.base_model_path etc. throughout the script.

    main()
"""
            with open(script_save_path, "w", encoding="utf-8") as f:
                f.write(script_template)

            # Make the script executable (optional, good practice)
            # This might fail on some systems or if permissions are restricted
            try:
                os.chmod(script_save_path, 0o755)
            except OSError as e:
                print(f"Warning: Could not make script executable: {e}")

            print(f"Successfully generated training script at: {script_save_path}")
            return True
        except Exception as e:
            print(f"Failed to generate training script: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            return False

    def start_fine_tuning_process(self, parameters: dict, log_callback: callable, completion_callback: callable):
        """
        This method is intended to start the generated training script as a subprocess.
        However, the subtask description for step 1 (this step) only covers
        prepare_conversation_data_for_script and generate_training_script.
        The subprocess execution logic will be part of a future step if based on original plan.
        For now, this method is a placeholder or will not be called by the current UI flow.
        """
        print("TuningManager.start_fine_tuning_process called (currently a placeholder).")
        # Actual implementation would involve:
        # 1. Setting up paths (as done in FineTuningHubWidget._start_fine_tuning)
        # 2. Calling prepare_conversation_data_for_script
        # 3. Calling generate_training_script
        # 4. Then, constructing the command: `[sys.executable, script_save_path, ...]`
        #    (Note: trainer.py as generated is not using argparse, it uses hardcoded values from generation step)
        # 5. Using subprocess.Popen and threading as described in the prompt.
        # This complex logic should be added when this method is actually used.

        # Placeholder return for adapter output path, will be determined by UI/this method properly later.
        # This method is NOT CALLED by the UI in the current subtask for actual process starting.
        # The UI calls generate_training_script then start_adapter_monitoring.
        # The actual subprocess launch is deferred.
        print("TuningManager.start_fine_tuning_process is a placeholder for launching the training script.")
        log_callback("INFO: Subprocess execution (actually running trainer.py) is not implemented in this step of TuningManager.")

        # Simulate a quick success for placeholder behavior if needed by some test (e.g. if UI called this)
        # completion_callback(True, "simulated_adapter_path_for_placeholder_execution_from_start_fine_tuning_process")
        return "simulated_adapter_path_for_placeholder_execution_from_start_fine_tuning_process"

    def start_adapter_monitoring(self, adapter_output_path: str, detection_callback: callable, stop_callback: callable):
        """
        Starts a thread to monitor the adapter_output_path for adapter files.
        Calls detection_callback when files are found, or stop_callback if monitoring is stopped.
        """
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            print("Warning: Monitoring thread is already running. Stopping it before starting a new one.")
            self.stop_adapter_monitoring() # Signal existing thread to stop
            # Give a moment for the thread to actually stop if it was in sleep or a short I/O operation
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                 self._monitoring_thread.join(timeout=2.0) # Attempt to join briefly
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                 print("Error: Could not stop previous monitoring thread. New monitoring not started.")
                 # Call stop_callback to inform UI that monitoring didn't start as expected
                 stop_callback("Failed to stop previous monitoring instance.")
                 return

        self._stop_monitoring_event.clear()
        print(f"Starting to monitor adapter output path: {adapter_output_path}")

        def _monitor_loop(stop_event_ref): # Use passed event reference
            print(f"Monitoring thread started for {adapter_output_path}.")
            try:
                loop_count = 0
                while not stop_event_ref.is_set():
                    loop_count += 1
                    # print(f"Monitor loop {adapter_output_path} - Iteration {loop_count}") # Verbose

                    adapter_model_file = os.path.join(adapter_output_path, "adapter_model.safetensors")
                    # Some older PEFT versions might save as .bin, or user might use .bin
                    adapter_model_file_bin = os.path.join(adapter_output_path, "adapter_model.bin")
                    adapter_config_file = os.path.join(adapter_output_path, "adapter_config.json")

                    model_exists = os.path.exists(adapter_model_file) or os.path.exists(adapter_model_file_bin)
                    config_exists = os.path.exists(adapter_config_file)

                    if model_exists and config_exists:
                        print(f"Adapter files DETECTED in {adapter_output_path}.")
                        detection_callback(adapter_output_path)
                        return # Exit thread function on detection

                    # Responsive wait: wait for 1 second up to 10 times, checking event each time
                    # This makes the thread check the stop event every second.
                    for _ in range(10):
                        if stop_event_ref.is_set():
                            # print(f"Stop event detected during inner wait for {adapter_output_path}")
                            break
                        time.sleep(1) # Wait 1 second

                    if stop_event_ref.is_set(): # Check after the inner loop (10s wait)
                        # print(f"Stop event detected after 10s wait cycle for {adapter_output_path}")
                        break

                # If loop finishes, it means it was stopped by the event
                if stop_event_ref.is_set():
                    print(f"Monitoring gracefully stopped for {adapter_output_path} by event.")
                    stop_callback("Monitoring was cancelled.") # Standard reason for event-triggered stop
                else:
                    # This case should ideally not be reached if detection or event set works.
                    print(f"Monitoring loop for {adapter_output_path} ended without detection or explicit stop event (should be rare).")
                    stop_callback("Monitoring loop ended unexpectedly without detection.")
            except Exception as e:
                print(f"Exception in monitoring thread for {adapter_output_path}: {e}")
                import traceback
                traceback.print_exc()
                stop_callback(f"Monitoring error: {e}")

        self._monitoring_thread = threading.Thread(target=_monitor_loop, args=(self._stop_monitoring_event,), daemon=True)
        self._monitoring_thread.start()

    def stop_adapter_monitoring(self):
        """Signals the monitoring thread to stop."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            print("Signalling adapter monitoring thread to stop...")
            self._stop_monitoring_event.set()
            # Do not join here from a UI-triggered call to avoid freezing the UI.
            # The thread is a daemon; it will exit. The stop_callback handles UI feedback.
        else:
            print("No active monitoring thread to stop, or thread already stopped.")
            # Optionally, could call stop_callback here if some UI state needs reset
            # and it relies on stop_callback for that. But typically, if no thread, no action.

    def create_ollama_model_with_adapter(self, new_model_name: str, base_model_name: str,
                                         adapter_path: str, system_prompt: str or None,
                                         example_messages: list[dict] or None,
                                         log_callback: callable) -> bool:
        log_callback(f"Attempting to create Ollama model '{new_model_name}' from base '{base_model_name}' using adapter at '{adapter_path}'.")

        modelfile_content = f"FROM {base_model_name}\n"

        # Determine the correct adapter model file to use
        adapter_model_safetensors = os.path.join(adapter_path, "adapter_model.safetensors")
        # Common alternative names for .bin, peft might save as pytorch_model.bin or adapter_model.bin
        adapter_model_bin_peft = os.path.join(adapter_path, "adapter_model.bin")
        adapter_model_bin_hf = os.path.join(adapter_path, "pytorch_model.bin")

        actual_adapter_file = ""
        if os.path.exists(adapter_model_safetensors):
            actual_adapter_file = adapter_model_safetensors
            log_callback(f"Using adapter file: {actual_adapter_file}")
        elif os.path.exists(adapter_model_bin_peft):
            actual_adapter_file = adapter_model_bin_peft
            log_callback(f"Using adapter file: {actual_adapter_file}")
        elif os.path.exists(adapter_model_bin_hf):
            actual_adapter_file = adapter_model_bin_hf
            log_callback(f"Using adapter file: {actual_adapter_file}")
        else:
            log_callback(f"ERROR: No adapter model file (adapter_model.safetensors, adapter_model.bin, or pytorch_model.bin) found in {adapter_path}")
            return False

        # Ensure path is quoted if it contains spaces, using Python's string repr for safety
        modelfile_content += f"ADAPTER {json.dumps(actual_adapter_file)}\n" # json.dumps will handle quotes and escapes

        if system_prompt:
            # For multi-line system prompts or prompts with quotes, use triple quotes in Modelfile
            # json.dumps is a safe way to get a string literal representation
            modelfile_content += f"SYSTEM {json.dumps(system_prompt)}\n"

        if example_messages and isinstance(example_messages, list):
            for msg in example_messages:
                role = msg.get("role", "").strip().lower()
                content = msg.get("content", "")
                if role and content: # Ensure both role and content exist
                    # Basic escaping for message content already handled by json.dumps
                    modelfile_content += f"MESSAGE {role} {json.dumps(content)}\n"
                else:
                    log_callback(f"Warning: Skipping malformed example message: {msg}")

        temp_modelfile_fd, temp_modelfile_path = tempfile.mkstemp(suffix=".modelfile", text=True)
        try:
            with os.fdopen(temp_modelfile_fd, 'w', encoding='utf-8') as tmp_file:
                tmp_file.write(modelfile_content)
            log_callback(f"Temporary Modelfile created at: {temp_modelfile_path}")
            log_callback(f"--- Modelfile Content ---\n{modelfile_content}\n--- End Modelfile ---")

            command = ["ollama", "create", new_model_name, "-f", temp_modelfile_path]
            log_callback(f"Executing command: {' '.join(command)}")

            process = subprocess.run(command, capture_output=True, text=True, check=False)

            log_callback("\n--- Ollama Create Output ---")
            log_callback(process.stdout.strip() if process.stdout and process.stdout.strip() else "(no stdout)")

            if process.stderr and process.stderr.strip():
                log_callback("\n--- Ollama Create Errors ---")
                log_callback(process.stderr.strip())

            if process.returncode == 0:
                log_callback(f"\nSUCCESS: Ollama model '{new_model_name}' created successfully.")
                return True
            else:
                log_callback(f"\nERROR: 'ollama create' command failed with return code {process.returncode}.")
                return False
        except FileNotFoundError:
            log_callback("ERROR: 'ollama' command not found. Please ensure Ollama is installed and in your system PATH.")
            return False
        except Exception as e:
            log_callback(f"ERROR: An unexpected exception occurred during 'ollama create': {e}")
            import traceback
            log_callback(traceback.format_exc())
            return False
        finally:
            if os.path.exists(temp_modelfile_path):
                try:
                    os.remove(temp_modelfile_path)
                    log_callback(f"Cleaned up temporary modelfile: {temp_modelfile_path}")
                except OSError as e:
                    log_callback(f"Warning: Could not remove temporary modelfile {temp_modelfile_path}: {e}")


# Example usage (for testing TuningManager methods directly)
if __name__ == '__main__':
    # --- Test adapter monitoring ---
    # Note: Commenting out previous tests for brevity during this subtask focus.
    # You can uncomment them to run a full test suite for TuningManager.

    # tm_old_tests = TuningManager()
    # print("\n--- Testing prepare_conversation_data_for_script (from previous tests) ---")
    # dummy_conv_dir_old = "temp_dummy_convs_old"
    # os.makedirs(dummy_conv_dir_old, exist_ok=True)
    # conv_file_paths_old = []
    # for i in range(1): # Simplified to one file for brevity
    #     fp_old = os.path.join(dummy_conv_dir_old, f"conv_{i}_old.json")
    #     # ... (rest of dummy file creation as in original)
    # # shutil.rmtree(dummy_conv_dir_old)

    # print("\n--- Testing generate_training_script (from previous tests) ---")
    # ... (rest of dummy script gen as in original) ...
    # shutil.rmtree(dummy_conv_dir_old_script_gen_path) # Example cleanup

    print("\n\n--- CURRENT TEST: Adapter Monitoring ---")
    tm_monitor_test = TuningManager()

    # Use a unique directory for each test run to avoid state clashes if not cleaned up
    test_run_id = str(uuid.uuid4())[:8]
    base_test_dir = os.path.join(os.getcwd(), f"temp_monitor_tests_{test_run_id}")
    os.makedirs(base_test_dir, exist_ok=True)

    test_adapter_dir_detect = os.path.join(base_test_dir, "detect_adapter_here")
    os.makedirs(test_adapter_dir_detect, exist_ok=True)

    detected_path_holder = []
    monitoring_stopped_reason_holder = []

    def _mock_detection_cb(path):
        print(f"TEST_CALLBACK (Detection): Adapter detected at -> {path}")
        detected_path_holder.append(path)

    def _mock_stop_cb(reason):
        print(f"TEST_CALLBACK (Stop): Monitoring stopped. Reason -> {reason}")
        monitoring_stopped_reason_holder.append(reason)

    print(f"Starting monitoring on (empty) directory: {test_adapter_dir_detect}")
    tm_monitor_test.start_adapter_monitoring(test_adapter_dir_detect, _mock_detection_cb, _mock_stop_cb)

    print("Simulating waiting for adapter files (will be created after ~5s)...")
    time.sleep(5)

    print(f"Creating dummy adapter files in {test_adapter_dir_detect} now...")
    with open(os.path.join(test_adapter_dir_detect, "adapter_model.safetensors"), "w") as f:
        f.write("dummy safetensors content")
    with open(os.path.join(test_adapter_dir_detect, "adapter_config.json"), "w") as f:
        json.dump({"config": "dummy"}, f)

    timeout_for_detection = 15
    start_wait_detection = time.time()
    print(f"Waiting up to {timeout_for_detection}s for detection callback...")
    while not detected_path_holder and (time.time() - start_wait_detection) < timeout_for_detection:
        time.sleep(0.5)

    if detected_path_holder:
        print(f"VERIFICATION SUCCESS: Detection callback was called with path: {detected_path_holder[0]}")
        assert detected_path_holder[0] == test_adapter_dir_detect
    else:
        print("VERIFICATION FAILURE: Detection callback was NOT called within timeout after creating files.")
        print("Attempting to stop the (potentially) hung monitor for cleanup...")
        tm_monitor_test.stop_adapter_monitoring()
        time.sleep(2) # Give stop a moment to propagate and call its callback

    # --- Test stopping the monitor before detection ---
    print("\n--- Testing Stopping the Monitor (before detection) ---")
    tm_monitor_stop_test = TuningManager()
    detected_path_holder.clear() # Reset for this test
    monitoring_stopped_reason_holder.clear()

    test_adapter_dir_stop_early = os.path.join(base_test_dir, "stop_early_adapter_here")
    os.makedirs(test_adapter_dir_stop_early, exist_ok=True)

    print(f"Starting monitoring on: {test_adapter_dir_stop_early} (will be stopped in ~3s)")
    tm_monitor_stop_test.start_adapter_monitoring(test_adapter_dir_stop_early, _mock_detection_cb, _mock_stop_cb)

    time.sleep(3) # Wait a bit
    print("Issuing stop_adapter_monitoring() now...")
    tm_monitor_stop_test.stop_adapter_monitoring()

    timeout_for_stop_cb = 5
    start_wait_stop_cb = time.time()
    print(f"Waiting up to {timeout_for_stop_cb}s for stop callback...")
    while not monitoring_stopped_reason_holder and (time.time() - start_wait_stop_cb) < timeout_for_stop_cb:
        time.sleep(0.5)

    if monitoring_stopped_reason_holder:
        print(f"VERIFICATION SUCCESS: Stop callback was called. Reason: {monitoring_stopped_reason_holder[0]}")
        assert "cancelled" in monitoring_stopped_reason_holder[0].lower() # Check for expected reason
    else:
        print("VERIFICATION FAILURE: Stop callback was NOT called within timeout after explicit stop.")

    assert not detected_path_holder, "VERIFICATION: Detection callback should NOT have been called for the early stop test."

    # Clean up test directory
    try:
        shutil.rmtree(base_test_dir)
        print(f"\nCleaned up test directory: {base_test_dir}")
    except OSError as e:
        print(f"Error cleaning up test directory {base_test_dir}: {e}")

    print("\n--- TuningManager Monitoring Test Suite End ---")

# Example usage (for testing TuningManager methods directly)
if __name__ == '__main__':
    tm = TuningManager()

    # --- Test prepare_conversation_data_for_script ---
    print("\n--- Testing prepare_conversation_data_for_script ---")
    # Create dummy conversation files
    dummy_conv_dir = "temp_dummy_convs"
    os.makedirs(dummy_conv_dir, exist_ok=True)
    conv_file_paths = []
    for i in range(2):
        fp = os.path.join(dummy_conv_dir, f"conv_{i}.json")
        conv_data = {
            "conversation_id": f"test_id_{i}",
            "model_name": "test_model",
            "messages": [
                {"role": "user", "content": f"User prompt {i}-1"},
                {"role": "assistant", "content": f"Assistant response {i}-1"},
                {"role": "user", "content": f"User prompt {i}-2"},
                {"role": "assistant", "content": f"Assistant response {i}-2"}
            ]
        }
        with open(fp, "w") as f:
            json.dump(conv_data, f)
        conv_file_paths.append(fp)

    # Add a conversation with only user message (should be skipped for formatting)
    fp_user_only = os.path.join(dummy_conv_dir, "conv_user_only.json")
    with open(fp_user_only, "w") as f:
        json.dump({"messages": [{"role": "user", "content": "This is a solo user message."}]}, f)
    conv_file_paths.append(fp_user_only)


    temp_jsonl = os.path.join(dummy_conv_dir, "prepared_data.jsonl")
    success_prepare = tm.prepare_conversation_data_for_script(conv_file_paths, temp_jsonl)
    print(f"Preparation success: {success_prepare}")
    if success_prepare and os.path.exists(temp_jsonl):
        print("Prepared JSONL content:")
        with open(temp_jsonl, "r") as f:
            for line in f:
                print(line.strip())

    # --- Test generate_training_script ---
    print("\n--- Testing generate_training_script ---")
    dummy_params = {
        "base_model": "NousResearch/Llama-2-7b-hf", # Example
        "lora_rank": 8,
        "learning_rate": "2e-4",
        "num_epochs": 1,
        # Potentially add other params like batch_size if your template uses them
    }
    dummy_script_path = os.path.join(dummy_conv_dir, "generated_trainer.py")
    dummy_adapter_out = os.path.join(dummy_conv_dir, "adapter_out")
    dummy_local_files = [os.path.join(dummy_conv_dir, "sample.txt")] # Assume sample.txt exists or script handles missing

    # Create a dummy sample.txt
    with open(os.path.join(dummy_conv_dir, "sample.txt"), "w") as f:
        f.write("This is sample text from a local file for training.")

    success_generate = tm.generate_training_script(dummy_params, dummy_script_path, temp_jsonl,
                                                 dummy_adapter_out, dummy_local_files)
    print(f"Script generation success: {success_generate}")
    if success_generate and os.path.exists(dummy_script_path):
        print(f"Script generated at: {dummy_script_path}")
        # print("First 10 lines of script:")
        # with open(dummy_script_path, "r") as f:
        #     for i in range(10): print(f.readline().strip())

    # Clean up dummy files and directory
    # shutil.rmtree(dummy_conv_dir) # Comment out to inspect files after test
    print(f"\nTest files are in: {dummy_conv_dir} (if not cleaned up)")
    print("TuningManager tests complete.")

    # Note: The start_fine_tuning_process is not fully tested here as it's a placeholder.
    # Full test would require mocking subprocess and threads.
    def log_cb(msg): print(f"LOG: {msg}")
    def complete_cb(succ, pth): print(f"COMPLETE: Success={succ}, Path={pth}")
    # tm.start_fine_tuning_process({}, log_cb, complete_cb) # Test placeholder execution
