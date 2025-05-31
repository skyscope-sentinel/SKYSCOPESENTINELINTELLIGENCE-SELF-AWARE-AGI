from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QListWidget,
                             QSpinBox, QTextBrowser, QFileDialog, QListWidgetItem, QMessageBox) # Added QMessageBox
from PyQt6.QtCore import Qt
from core.memory_manager import list_saved_conversations, MEMORY_DIR
from core.tuning_manager import TuningManager # Import TuningManager
import os

class FineTuningHubWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tuning_manager = TuningManager()
        self.detected_adapter_path = None # Initialize instance variable
        self._init_ui()
        self._connect_signals()
        self._refresh_conversation_list() # Initial population

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15) # Add some spacing between sections

        # --- Base Model Section ---
        base_model_group_layout = QFormLayout()
        base_model_group_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.base_model_path_edit = QLineEdit()
        self.base_model_path_edit.setPlaceholderText("HuggingFace Model Name or Path (e.g., meta-llama/Llama-2-7b-hf)")
        base_model_group_layout.addRow(QLabel("Base Model:"), self.base_model_path_edit)
        main_layout.addLayout(base_model_group_layout)

        # --- Data Sources Section ---
        data_sources_layout = QVBoxLayout()
        data_sources_layout.addWidget(QLabel("<b>Data Sources for Training</b>"))

        # Conversations
        data_sources_layout.addWidget(QLabel("Saved Conversations:"))
        self.conversations_list_widget = QListWidget()
        self.conversations_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        data_sources_layout.addWidget(self.conversations_list_widget)
        self.refresh_conv_button = QPushButton("Refresh Conversation List")
        data_sources_layout.addWidget(self.refresh_conv_button, 0, Qt.AlignmentFlag.AlignLeft) # Align button

        # Local Files
        data_sources_layout.addWidget(QLabel("Local TXT/PDF Files:"))
        self.local_files_list_widget = QListWidget()
        self.local_files_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        data_sources_layout.addWidget(self.local_files_list_widget)

        local_files_buttons_layout = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files...")
        self.clear_files_button = QPushButton("Clear Selected Files")
        local_files_buttons_layout.addWidget(self.add_files_button)
        local_files_buttons_layout.addWidget(self.clear_files_button)
        local_files_buttons_layout.addStretch()
        data_sources_layout.addLayout(local_files_buttons_layout)

        main_layout.addLayout(data_sources_layout)

        # --- LoRA Configuration Section ---
        lora_config_layout = QFormLayout()
        lora_config_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        lora_config_layout.addRow(QLabel("<b>LoRA Configuration</b>")) # Section title

        self.lora_rank_spinbox = QSpinBox()
        self.lora_rank_spinbox.setRange(1, 256)
        self.lora_rank_spinbox.setValue(16)
        self.lora_rank_spinbox.setToolTip("Rank for LoRA adaptation (e.g., 8, 16, 32). Higher rank means more parameters.")
        lora_config_layout.addRow(QLabel("LoRA Rank:"), self.lora_rank_spinbox)

        self.learning_rate_edit = QLineEdit("5e-5")
        self.learning_rate_edit.setPlaceholderText("e.g., 5e-5, 2e-4")
        self.learning_rate_edit.setToolTip("Learning rate for the optimizer.")
        lora_config_layout.addRow(QLabel("Learning Rate:"), self.learning_rate_edit)

        self.epochs_spinbox = QSpinBox()
        self.epochs_spinbox.setRange(1, 100)
        self.epochs_spinbox.setValue(3)
        self.epochs_spinbox.setToolTip("Number of training epochs.")
        lora_config_layout.addRow(QLabel("Epochs:"), self.epochs_spinbox)
        main_layout.addLayout(lora_config_layout)

        # --- Output Model Section ---
        output_model_layout = QFormLayout()
        output_model_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        output_model_layout.addRow(QLabel("<b>Output Model Configuration</b>")) #Section title

        self.new_model_name_edit = QLineEdit()
        self.new_model_name_edit.setPlaceholderText("e.g., MyStoryWriterLlama (no 'Skyscope-' prefix)")
        self.new_model_name_edit.setToolTip("Name for your new fine-tuned model.")
        output_model_layout.addRow(QLabel("New Model Name:"), self.new_model_name_edit)

        self.adapter_output_dir_label = QLabel("Adapter Output Directory:")
        self.adapter_output_dir_display = QLineEdit()
        self.adapter_output_dir_display.setReadOnly(True)
        self.adapter_output_dir_display.setPlaceholderText("Path will be determined before script generation.")
        self.adapter_output_dir_display.setToolTip("This is where the generated training script will be configured to save the LoRA adapter.")
        output_model_layout.addRow(self.adapter_output_dir_label, self.adapter_output_dir_display)

        main_layout.addLayout(output_model_layout)

        # --- Action Button ---
        action_button_layout = QHBoxLayout()
        self.start_tuning_button = QPushButton("Generate Training Script & Monitor") # Changed text
        self.start_tuning_button.setObjectName("StartTuningButton") # Object name for QSS
        self.start_tuning_button.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 10px;") # Make it prominent
        self.start_tuning_button.setToolTip("Click to generate the Python training script and instructions. The application will then monitor for the trained adapter.") # Added tooltip
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.start_tuning_button)
        action_button_layout.addStretch()
        main_layout.addLayout(action_button_layout)

        # --- Log Display Section ---
        log_display_layout = QVBoxLayout()
        log_display_layout.addWidget(QLabel("<b>Fine-Tuning Process Log</b>"))
        self.log_browser = QTextBrowser()
        self.log_browser.setObjectName("FineTuneLogBrowser") # Object name for QSS
        self.log_browser.setReadOnly(True)
        self.log_browser.setFixedHeight(150) # Give it a decent initial height
        log_display_layout.addWidget(self.log_browser)
        main_layout.addLayout(log_display_layout)

        main_layout.addStretch() # Pushes everything up if space allows
        self.setLayout(main_layout)

    def _connect_signals(self):
        self.refresh_conv_button.clicked.connect(self._refresh_conversation_list)
        self.add_files_button.clicked.connect(self._add_local_files)
        self.clear_files_button.clicked.connect(self._clear_local_files)
        self.start_tuning_button.clicked.connect(self._start_fine_tuning)

    def _refresh_conversation_list(self):
        self.log_browser.append("Refreshing conversation list...")
        self.conversations_list_widget.clear()
        try:
            conversation_files = list_saved_conversations()
            if conversation_files:
                for filename in sorted(conversation_files, reverse=True):
                    item = QListWidgetItem(filename)
                    full_filepath = os.path.join(MEMORY_DIR, filename)
                    item.setData(Qt.ItemDataRole.UserRole, full_filepath)
                    item.setToolTip(f"Path: {full_filepath}")
                    self.conversations_list_widget.addItem(item)
                self.log_browser.append(f"Found {len(conversation_files)} saved conversations.")
            else:
                self.conversations_list_widget.addItem("No saved conversations found.")
                self.log_browser.append("No saved conversations found.")
        except Exception as e:
            self.log_browser.append(f"Error refreshing conversation list: {e}")
            QMessageBox.critical(self, "History Error", f"Could not load conversation history: {e}")

    def _add_local_files(self):
        self.log_browser.append("Opening file dialog to select local files...")
        # Home directory or last used directory could be starting points
        # For filter, use "Text and PDF files (*.txt *.pdf);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Training Files", "",
                                                "Text files (*.txt);;PDF files (*.pdf);;All files (*)")
        if files:
            for file_path in files:
                self.local_files_list_widget.addItem(QListWidgetItem(file_path))
            self.log_browser.append(f"Added {len(files)} local files for training.")
        else:
            self.log_browser.append("No files selected.")

    def _clear_local_files(self):
        # Clear only selected items
        selected_items = self.local_files_list_widget.selectedItems()
        if not selected_items: # If no items are selected, clear all. Or change behavior.
            if self.local_files_list_widget.count() > 0:
                 reply = QMessageBox.question(self, 'Clear Files',
                                     "No files selected. Clear all local files from the list?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
                 if reply == QMessageBox.StandardButton.Yes:
                    self.local_files_list_widget.clear()
                    self.log_browser.append("Cleared all local files from the list.")
            else:
                self.log_browser.append("Local files list is already empty.")
            return

        for item in selected_items:
            self.local_files_list_widget.takeItem(self.local_files_list_widget.row(item))
        self.log_browser.append(f"Cleared {len(selected_items)} selected local files from the list.")


    def get_tuning_parameters(self):
        params = {
            "base_model": self.base_model_path_edit.text().strip(),
            "lora_rank": self.lora_rank_spinbox.value(),
            "learning_rate": self.learning_rate_edit.text().strip(),
            "epochs": self.epochs_spinbox.value(),
            "output_model_name": self.new_model_name_edit.text().strip(),
            "conversation_sources": [],
            "file_sources": []
        }
        # Collect selected conversation file paths
        selected_conversation_paths = []
        for i in range(self.conversations_list_widget.count()):
            item = self.conversations_list_widget.item(i)
            if item.isSelected():
                selected_conversation_paths.append(item.data(Qt.ItemDataRole.UserRole))
        params["selected_conversation_paths"] = selected_conversation_paths

        # Checkbox state for using conversations (assuming you might add a checkbox later)
        # For now, if paths are selected, we assume they are to be used.
        params["use_saved_conversations"] = bool(selected_conversation_paths)

        # Collect local file paths
        local_files_paths = []
        for i in range(self.local_files_list_widget.count()):
            item = self.local_files_list_widget.item(i)
            # Assuming all listed files are to be used (no isSelected check here, but could be added)
            local_files_paths.append(item.text())
        params["local_files_paths"] = local_files_paths

        return params

    def _update_log_browser(self, message):
        """Appends a message to the log browser on the UI thread."""
        # This method might be called from another thread (TuningManager's monitoring thread)
        # In a real Qt app, you'd use signals/slots for thread safety.
        # For this subtask, direct append if TuningManager calls are synchronous,
        # or make sure TuningManager's log_callback is Qt-aware if async.
        # For script generation, it's synchronous. For actual training monitoring, it would be async.
        self.log_browser.append(message)
        QApplication.instance().processEvents() # Keep UI responsive if logging many messages

    def _on_tuning_complete(self, success: bool, adapter_output_path: str):
        """Callback for when the tuning process (or script generation) finishes."""
        self.log_browser.append("\n--- Process Completion ---")
        if success:
            self.log_browser.append(f"Successfully completed. Adapter Path: {adapter_output_path}")
            QMessageBox.information(self, "Process Complete", f"Process finished successfully.\nAdapter saved to: {adapter_output_path}")
        else:
            self.log_browser.append("Process failed. Check logs for details.")
            QMessageBox.warning(self, "Process Failed", "The process encountered an error. Please review the logs.")
        self.start_tuning_button.setEnabled(True)


    def _start_fine_tuning(self):
        self.log_browser.clear()
        self.log_browser.append("Initiating training script generation...")
        self.start_tuning_button.setEnabled(False) # Disable button during processing

        params = self.get_tuning_parameters()

        # --- Basic UI Validation ---
        if not params["base_model"]:
            self._update_log_browser("ERROR: Base Model Path/Name cannot be empty.")
            QMessageBox.warning(self, "Input Error", "Base Model Path/Name cannot be empty.")
            self.start_tuning_button.setEnabled(True)
            return
        if not params["output_model_name"]:
            self._update_log_browser("ERROR: New Model Name cannot be empty.")
            QMessageBox.warning(self, "Input Error", "New Model Name cannot be empty.")
            self.start_tuning_button.setEnabled(True)
            return
        if not params["selected_conversation_paths"] and not params["local_files_paths"]:
            self._update_log_browser("ERROR: No data sources selected (conversations or files).")
            QMessageBox.warning(self, "Input Error", "Please select at least one data source for training.")
            self.start_tuning_button.setEnabled(True)
            return

        self._update_log_browser("\n--- Selected Parameters ---")
        for key, value in params.items():
            if isinstance(value, list) and value:
                self.log_browser.append(f"{key.replace('_', ' ').title()}:")
                for v_item in value:
                    self.log_browser.append(f"  - {v_item}")
            elif not isinstance(value, list):
                 self.log_browser.append(f"{key.replace('_', ' ').title()}: {value}")
            elif isinstance(value, list) and not value: # Empty list
                 self.log_browser.append(f"{key.replace('_', ' ').title()}: None selected")


        # Basic Validation (examples)
        if not params["base_model"]:
            self.log_browser.append("\nERROR: Base Model Path/Name cannot be empty.")
            QMessageBox.warning(self, "Input Error", "Base Model Path/Name cannot be empty.")
            return
        if not params["output_model_name"]:
            self.log_browser.append("\nERROR: New Model Name cannot be empty.")
            QMessageBox.warning(self, "Input Error", "New Model Name cannot be empty.")
            return
        if not params["conversation_sources"] and not params["file_sources"]:
            self.log_browser.append("\nERROR: No data sources selected (conversations or files).")
            QMessageBox.warning(self, "Input Error", "Please select at least one data source for training.")
            return

        self.log_browser.append("\nPlaceholder: Actual fine-tuning logic would be called here.")
        self.log_browser.append("This would involve preparing data, calling a training script/library, etc.")
        # Display parameters in log
        for key, value in params.items():
            if isinstance(value, list) and value:
                self._update_log_browser(f"{key.replace('_', ' ').title()}:")
                for v_item in value:
                    self._update_log_browser(f"  - {v_item}")
            elif not isinstance(value, list):
                 self._update_log_browser(f"{key.replace('_', ' ').title()}: {value}")
            elif isinstance(value, list) and not value:
                 self._update_log_browser(f"{key.replace('_', ' ').title()}: None selected")

        # --- Path Setup ---
        job_name = params.get('output_model_name', 'default_finetune_job').replace(' ', '_').lower()
        # Sanitize job_name further if needed (e.g., remove special chars)
        job_name = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in job_name)

        base_job_dir = os.path.join(os.path.expanduser("~"), "skyscope_training_jobs", job_name)
        try:
            os.makedirs(base_job_dir, exist_ok=True)
            self._update_log_browser(f"Base job directory: {base_job_dir}")
        except OSError as e:
            self._update_log_browser(f"ERROR: Could not create base job directory {base_job_dir}: {e}")
            QMessageBox.critical(self, "Directory Error", f"Failed to create job directory: {e}")
            self.start_tuning_button.setEnabled(True)
            return

        script_save_path = os.path.join(base_job_dir, "trainer_script.py")
        adapter_output_path = os.path.join(base_job_dir, "adapter_output") # Script will use this

        try:
            os.makedirs(adapter_output_path, exist_ok=True)
            self.adapter_output_dir_display.setText(adapter_output_path) # Display to user
            self._update_log_browser(f"Adapter output directory set to: {adapter_output_path}")
        except OSError as e:
            self._update_log_browser(f"ERROR: Could not create adapter output directory {adapter_output_path}: {e}")
            QMessageBox.critical(self, "Directory Error", f"Failed to create adapter output directory: {e}")
            self.start_tuning_button.setEnabled(True)
            return

        # --- Prepare Conversation Data ---
        conversation_jsonl_path = None
        if params.get("use_saved_conversations") and params.get("selected_conversation_paths"):
            self._update_log_browser("\nProcessing selected conversation files...")
            conversation_jsonl_path = os.path.join(base_job_dir, "prepared_conversations.jsonl")
            conv_success = self.tuning_manager.prepare_conversation_data_for_script(
                params['selected_conversation_paths'], conversation_jsonl_path
            )
            if not conv_success:
                self._update_log_browser("ERROR: Failed to prepare conversation data for training.")
                QMessageBox.critical(self, "Data Preparation Error", "Failed to prepare conversation data.")
                self.start_tuning_button.setEnabled(True)
                return
            self._update_log_browser(f"Conversation data prepared at: {conversation_jsonl_path}")
        else:
            self._update_log_browser("\nNo saved conversations selected for training or 'Use Saved Conversations' not specified.")


        # --- Generate Training Script ---
        self._update_log_browser("\nGenerating training script...")
        script_success = self.tuning_manager.generate_training_script(
            params,
            script_save_path,
            conversation_jsonl_path,
            adapter_output_path,
            params.get('local_files_paths', [])
        )

        if script_success:
            self._update_log_browser(f"\nSUCCESS: Training script generated at: {script_save_path}")
            self._update_log_browser("\n--- Next Steps ---")
            self._update_log_browser(f"1. Ensure you have a Python environment with all dependencies from requirements.txt installed (especially PyTorch with CUDA if using GPU, transformers, peft, bitsandbytes, accelerate, datasets, PyMuPDF).")
            self._update_log_browser(f"2. Open a terminal in that environment.")
            self._update_log_browser(f"3. Navigate to: cd {os.path.dirname(script_save_path)}")
            self._update_log_browser(f"4. Run the script: python {os.path.basename(script_save_path)}")
            self._update_log_browser(f"5. Monitor the terminal output for training progress.")
            self._update_log_browser(f"6. Once complete, the LoRA adapter will be saved in: {adapter_output_path}")
            self._update_log_browser("\n(Monitoring of this adapter path by the application is not yet implemented in this version.)")
            QMessageBox.information(self, "Script Generated", f"Training script has been generated successfully at:\n{script_save_path}\n\nSee log for instructions on how to run it.")
        else:
            self._update_log_browser("ERROR: Failed to generate training script.")
            QMessageBox.critical(self, "Script Generation Error", "Failed to generate the training script. Check logs.")

        # self.start_tuning_button.setEnabled(True) # Button is re-enabled by callbacks now

        if script_success:
            self._update_log_browser("\n--- Monitoring Adapter Output ---")
            self._update_log_browser(f"Monitoring for adapter files in: {adapter_output_path}")
            self._update_log_browser("You can now run the generated training script in your local environment.")
            self._update_log_browser("This application will wait for the adapter files to appear.")

            # Button remains disabled until monitoring stops or adapter is found
            self.tuning_manager.start_adapter_monitoring(
                adapter_output_path,
                self._on_adapter_detected, # Callback for success
                self._on_monitoring_stopped_ui_feedback # Callback for stop/error
            )
        else:
            # Script generation failed, re-enable button
            self.start_tuning_button.setEnabled(True)


    def _on_adapter_detected(self, adapter_path: str):
        """Callback when the TuningManager detects the adapter files."""
        self._update_log_browser(f"INFO: Adapter detected at {adapter_path}!") # Changed log level for clarity
        self.detected_adapter_path = adapter_path  # Store it

        params = self.get_tuning_parameters()
        base_model = params.get('base_model', '').strip()
        new_model_name_suffix = params.get('new_model_name', '').strip()

        if not base_model:
            self._update_log_browser("ERROR: Base Model Path/Name is not specified in the UI. Cannot create Ollama model.")
            QMessageBox.warning(self, "Model Creation Error", "Base Model Path/Name is missing. Cannot proceed with Ollama model creation.")
            if not self.start_tuning_button.isEnabled(): self.start_tuning_button.setEnabled(True)
            return

        if not new_model_name_suffix:
            self._update_log_browser("ERROR: New Model Name (suffix) is not specified in the UI. Cannot create Ollama model.")
            QMessageBox.warning(self, "Model Creation Error", "New Model Name is missing. Cannot proceed with Ollama model creation.")
            if not self.start_tuning_button.isEnabled(): self.start_tuning_button.setEnabled(True)
            return

        # Sanitize and prefix the model name
        sanitized_suffix = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in new_model_name_suffix.replace(' ', '_'))
        full_new_model_name = f"Skyscope-{sanitized_suffix}"

        self._update_log_browser(f"\n--- Ollama Model Creation ---")
        self._update_log_browser(f"Attempting to create Ollama model: '{full_new_model_name}'")
        self._update_log_browser(f"Using base model: '{base_model}'")
        self._update_log_browser(f"Using adapter from: '{self.detected_adapter_path}'")

        # Placeholders for system_prompt and example_messages from UI (future subtask)
        system_prompt_value = None
        example_messages_value = None
        # Example:
        # system_prompt_value = self.system_prompt_edit.toPlainText().strip() if hasattr(self, 'system_prompt_edit') else None
        # example_messages_value = self._get_example_messages_from_ui() # if UI for examples exists

        self._update_log_browser("Calling TuningManager to create Ollama model...")
        create_success = self.tuning_manager.create_ollama_model_with_adapter(
            full_new_model_name,
            base_model,
            self.detected_adapter_path,
            system_prompt_value,
            example_messages_value,
            self._update_log_browser # Pass log callback
        )

        if create_success:
            self._update_log_browser(f"SUCCESS: Ollama model '{full_new_model_name}' should now be available.")
            self._update_log_browser("You may need to refresh the model list in the 'Models' tab (main left panel) or restart Ollama to see it immediately.")
            QMessageBox.information(self, "Ollama Model Created",
                                    f"Ollama model '{full_new_model_name}' creation process initiated.\n"
                                    f"Check logs for 'ollama create' output and confirmation.\n"
                                    f"Refresh model list in 'Models' tab.")
        else:
            self._update_log_browser(f"ERROR: Failed to create Ollama model '{full_new_model_name}'. Review logs for details from 'ollama create'.")
            QMessageBox.critical(self, "Ollama Model Creation Failed",
                                 f"Failed to create Ollama model '{full_new_model_name}'.\n"
                                 "Please check the Fine-Tuning Process Log for detailed error messages from 'ollama create'.")

        if not self.start_tuning_button.isEnabled():
            self.start_tuning_button.setEnabled(True) # Re-enable button after attempt

    def _on_monitoring_stopped_ui_feedback(self, reason: str):
        """Callback when the TuningManager's monitoring stops for any reason other than detection."""
        self._update_log_browser(f"\n--- Monitoring Stopped ---") # Keep this part
        self._update_log_browser(f"INFO: Adapter monitoring stopped. Reason: {reason}")

        if not self.start_tuning_button.isEnabled():
             self.start_tuning_button.setEnabled(True)

        if "cancelled" not in reason.lower() and "error" not in reason.lower() : # Avoid pop-up if user just stopped it or it was a normal stop post-detection
            # This might be redundant if detection callback already showed a success message.
            # Only show if it's an unexpected stop.
            # Let's refine: only show message if it's an error or unexpected.
            # If detection happened, _on_adapter_detected handles the positive feedback.
            # If user cancels (hypothetically, if we add a cancel button), this provides feedback.
             pass # For now, just log. Can add QMessageBox if reason indicates an error.

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    # Apply a basic dark theme for standalone testing
    app.setStyleSheet("""
        QWidget { background-color: #2E2E2E; color: #E0E0E0; font-size: 10pt; }
        QLabel { padding: 2px; }
        QLineEdit, QSpinBox, QListWidget, QTextBrowser {
            background-color: #252525; color: #F0F0F0;
            border: 1px solid #404040; border-radius: 4px; padding: 5px;
        }
        QPushButton {
            background-color: #4A4A4A; border: 1px solid #555555;
            border-radius: 4px; padding: 8px 12px; min-width: 80px;
        }
        QPushButton:hover { background-color: #5A5A5A; }
        QPushButton:pressed { background-color: #404040; }
        QFormLayout QLabel { margin-top: 5px; } /* Add some top margin to labels in form layouts */
    """)

    widget = FineTuningHubWidget()
    widget.setWindowTitle("Fine-Tuning Hub Test")
    widget.setGeometry(100, 100, 700, 800) # Adjusted size for better visibility
    widget.show()

    sys.exit(app.exec())
