from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QListWidget,
                             QSpinBox, QTextBrowser, QFileDialog, QListWidgetItem, QMessageBox,
                             QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QTextEdit)
from PyQt6.QtCore import Qt
# from PyQt6.QtWidgets import QApplication # No longer needed for processEvents
from core.memory_manager import list_saved_conversations, MEMORY_DIR
from core.tuning_manager import TuningManager
import os
# import json # No longer needed

class FineTuningHubWidget(QWidget):
    """
    Widget for configuring and managing fine-tuning tasks.
    Allows users to select models, data sources (conversations, files),
    set LoRA parameters, output model names, and behavior customizations like
    system prompts and example conversation turns. It then generates a
    training script and can monitor for the resulting adapter, finally
    allowing the creation of a new Ollama model.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tuning_manager = TuningManager()
        self.detected_adapter_path = None
        # self.current_adapter_output_path_for_simulation = None # REMOVED
        self._init_ui()
        self._connect_signals()
        self._refresh_conversation_list()

    def _init_ui(self):
        """
        Initializes and arranges all UI elements (widgets, layouts, groups)
        for the Fine-Tuning Hub tab.
        """
        main_layout = QVBoxLayout(self)
        # self.main_layout = main_layout # Not needed as instance member if only used here
        main_layout.setSpacing(15)

        # --- Base Model Section ---
        base_model_group_layout = QFormLayout()
        base_model_group_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.base_model_path_edit = QLineEdit()
        self.base_model_path_edit.setPlaceholderText("HuggingFace Model Name or Path (e.g., meta-llama/Llama-2-7b-hf)")
        base_model_group_layout.addRow(QLabel("Base Model:"), self.base_model_path_edit)
        main_layout.addLayout(base_model_group_layout)

        # --- Data Sources Section ---
        data_sources_layout = QVBoxLayout()
        ds_title_label = QLabel("<b>Data Sources for Training</b>")
        ds_title_label.setObjectName("SectionTitleLabel")
        data_sources_layout.addWidget(ds_title_label)
        data_sources_layout.addWidget(QLabel("Saved Conversations:"))
        self.conversations_list_widget = QListWidget()
        self.conversations_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        data_sources_layout.addWidget(self.conversations_list_widget)
        self.refresh_conv_button = QPushButton("Refresh Conversation List")
        data_sources_layout.addWidget(self.refresh_conv_button, 0, Qt.AlignmentFlag.AlignLeft)
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
        lora_title_label = QLabel("<b>LoRA Configuration</b>")
        lora_title_label.setObjectName("SectionTitleLabel")
        lora_config_layout.addRow(lora_title_label)
        self.lora_rank_spinbox = QSpinBox()
        self.lora_rank_spinbox.setRange(1, 256); self.lora_rank_spinbox.setValue(16)
        self.lora_rank_spinbox.setToolTip("Rank for LoRA adaptation (e.g., 8, 16, 32). Higher rank means more parameters.")
        lora_config_layout.addRow(QLabel("LoRA Rank:"), self.lora_rank_spinbox)
        self.learning_rate_edit = QLineEdit("5e-5")
        self.learning_rate_edit.setPlaceholderText("e.g., 5e-5, 2e-4")
        self.learning_rate_edit.setToolTip("Learning rate for the optimizer.")
        lora_config_layout.addRow(QLabel("Learning Rate:"), self.learning_rate_edit)
        self.epochs_spinbox = QSpinBox()
        self.epochs_spinbox.setRange(1, 100); self.epochs_spinbox.setValue(3)
        self.epochs_spinbox.setToolTip("Number of training epochs.")
        lora_config_layout.addRow(QLabel("Epochs:"), self.epochs_spinbox)
        main_layout.addLayout(lora_config_layout)

        # --- Output Model Section ---
        output_model_layout = QFormLayout()
        output_model_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        om_title_label = QLabel("<b>Output Model Configuration</b>")
        om_title_label.setObjectName("SectionTitleLabel")
        output_model_layout.addRow(om_title_label)
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

        # --- Behavior Customization Section (Optional) ---
        behavior_groupbox = QGroupBox("Behavior Customization (Optional)")
        behavior_groupbox.setToolTip("Define a system prompt and/or example conversation turns to guide the model's behavior and response style.")
        behavior_layout = QVBoxLayout()
        behavior_layout.addWidget(QLabel("System Prompt:"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlaceholderText("e.g., You are a helpful AI assistant specialized in creative writing.")
        self.system_prompt_input.setFixedHeight(80)
        behavior_layout.addWidget(self.system_prompt_input)
        behavior_layout.addWidget(QLabel("Example Conversation Turns:"))
        self.example_messages_table = QTableWidget()
        self.example_messages_table.setColumnCount(2)
        self.example_messages_table.setHorizontalHeaderLabels(["Role", "Content"])
        self.example_messages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.example_messages_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.example_messages_table.setMinimumHeight(150)
        behavior_layout.addWidget(self.example_messages_table)
        example_buttons_layout = QHBoxLayout()
        self.add_example_turn_button = QPushButton("Add Example Turn")
        self.remove_example_turn_button = QPushButton("Remove Selected Turn")
        example_buttons_layout.addWidget(self.add_example_turn_button)
        example_buttons_layout.addWidget(self.remove_example_turn_button)
        example_buttons_layout.addStretch()
        behavior_layout.addLayout(example_buttons_layout)
        behavior_groupbox.setLayout(behavior_layout)
        main_layout.addWidget(behavior_groupbox)

        # --- Action Button ---
        action_button_layout = QHBoxLayout()
        self.start_tuning_button = QPushButton("Generate Training Script & Monitor")
        self.start_tuning_button.setObjectName("StartTuningButton")
        self.start_tuning_button.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 10px;")
        self.start_tuning_button.setToolTip("Click to generate the Python training script and instructions. The application will then monitor for the trained adapter.")
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.start_tuning_button)
        action_button_layout.addStretch()
        main_layout.addLayout(action_button_layout)

        # --- Log Display Section ---
        log_display_layout = QVBoxLayout()
        log_title_label = QLabel("<b>Fine-Tuning Process Log</b>")
        log_title_label.setObjectName("SectionTitleLabel")
        log_display_layout.addWidget(log_title_label)
        self.log_browser = QTextBrowser()
        self.log_browser.setObjectName("FineTuneLogBrowser")
        self.log_browser.setReadOnly(True)
        self.log_browser.setFixedHeight(150)
        log_display_layout.addWidget(self.log_browser)
        main_layout.addLayout(log_display_layout)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _connect_signals(self):
        """
        Connects signals from various UI elements (buttons, etc.)
        to their corresponding slot methods in this widget.
        """
        self.refresh_conv_button.clicked.connect(self._refresh_conversation_list)
        self.add_files_button.clicked.connect(self._add_local_files)
        self.clear_files_button.clicked.connect(self._clear_local_files)
        self.start_tuning_button.clicked.connect(self._start_fine_tuning)
        self.add_example_turn_button.clicked.connect(self._add_example_turn)
        self.remove_example_turn_button.clicked.connect(self._remove_selected_turn)

    def _add_example_turn(self):
        """Adds a new, empty row to the example messages table for user input."""
        row_position = self.example_messages_table.rowCount()
        self.example_messages_table.insertRow(row_position)
        role_combo = QComboBox()
        role_combo.addItems(["user", "assistant", "system"])
        self.example_messages_table.setCellWidget(row_position, 0, role_combo)
        content_item = QTableWidgetItem("")
        self.example_messages_table.setItem(row_position, 1, content_item)
        self.example_messages_table.scrollToBottom()

    def _remove_selected_turn(self):
        """Removes the currently selected row from the example messages table."""
        current_row = self.example_messages_table.currentRow()
        if current_row >= 0:
            self.example_messages_table.removeRow(current_row)
        else:
            QMessageBox.information(self, "Remove Turn", "Please select a row to remove.")

    def _refresh_conversation_list(self):
        """Clears and repopulates the list of saved conversations."""
        self._update_log_browser("INFO: Refreshing conversation list...")
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
                self._update_log_browser(f"INFO: Found {len(conversation_files)} saved conversations.")
            else:
                self.conversations_list_widget.addItem("No saved conversations found.")
                self._update_log_browser("INFO: No saved conversations found.")
        except Exception as e: # General catch-all for robustness
            self._update_log_browser(f"ERROR: Error refreshing conversation list: {e}")
            QMessageBox.critical(self, "History Error", f"Could not load conversation history: {e}")

    def _add_local_files(self):
        """Opens a file dialog for selecting local TXT/PDF files to add to the training data list."""
        self._update_log_browser("INFO: Opening file dialog to select local files...")
        files, _ = QFileDialog.getOpenFileNames(self, "Select Training Files", "", "Text files (*.txt);;PDF files (*.pdf);;All files (*)")
        if files:
            for file_path in files:
                self.local_files_list_widget.addItem(QListWidgetItem(file_path))
            self._update_log_browser(f"INFO: Added {len(files)} local files for training.")
        else:
            self._update_log_browser("INFO: No files selected.")

    def _clear_local_files(self):
        """Clears selected (or all, with confirmation) local files from the list widget."""
        selected_items = self.local_files_list_widget.selectedItems()
        if not selected_items:
            if self.local_files_list_widget.count() > 0:
                 reply = QMessageBox.question(self, 'Clear Files', "No files selected. Clear all local files from the list?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                 if reply == QMessageBox.StandardButton.Yes:
                    self.local_files_list_widget.clear()
                    self._update_log_browser("INFO: Cleared all local files from the list.")
            else:
                self._update_log_browser("INFO: Local files list is already empty.")
            return
        for item in selected_items:
            self.local_files_list_widget.takeItem(self.local_files_list_widget.row(item))
        self._update_log_browser(f"INFO: Cleared {len(selected_items)} selected local files from the list.")

    def get_tuning_parameters(self) -> dict:
        """
        Collects all fine-tuning parameters from the UI fields.

        Returns:
            dict: A dictionary containing all the parameters.
        """
        params = {
            "base_model": self.base_model_path_edit.text().strip(),
            "lora_rank": self.lora_rank_spinbox.value(),
            "learning_rate": self.learning_rate_edit.text().strip(),
            "epochs": self.epochs_spinbox.value(),
            "output_model_name": self.new_model_name_edit.text().strip(),
        }
        selected_conversation_paths = []
        for i in range(self.conversations_list_widget.count()):
            item = self.conversations_list_widget.item(i)
            if item.isSelected():
                selected_conversation_paths.append(item.data(Qt.ItemDataRole.UserRole))
        params["selected_conversation_paths"] = selected_conversation_paths
        params["use_saved_conversations"] = bool(selected_conversation_paths)
        local_files_paths = []
        for i in range(self.local_files_list_widget.count()):
            item = self.local_files_list_widget.item(i)
            local_files_paths.append(item.text())
        params["local_files_paths"] = local_files_paths
        system_prompt_text = self.system_prompt_input.toPlainText().strip()
        params["system_prompt"] = system_prompt_text if system_prompt_text else None
        example_messages = []
        for row in range(self.example_messages_table.rowCount()):
            role_widget = self.example_messages_table.cellWidget(row, 0)
            content_item = self.example_messages_table.item(row, 1)
            role = role_widget.currentText() if role_widget else None
            content = content_item.text().strip() if content_item else None
            if role and content:
                example_messages.append({"role": role, "content": content})
        params["example_messages"] = example_messages if example_messages else None
        return params

    def _show_error_and_log(self, message: str):
        """Helper function to log an error and show a critical QMessageBox."""
        self._update_log_browser(f"ERROR: {message}")
        QMessageBox.critical(self, "Error", message)
        if self.start_tuning_button and not self.start_tuning_button.isEnabled():
            self.start_tuning_button.setEnabled(True)
        # Dev simulate button is removed, no need to manage its state here.

    def _update_log_browser(self, message: str):
        """
        Appends a message to the log browser.
        This method is intended to be called from the UI thread.
        """
        self.log_browser.append(message)

    def _on_tuning_complete(self, success: bool, adapter_output_path: str):
        """
        Callback for when the tuning process (or script generation) finishes.
        Note: Currently, this is a placeholder as the actual training process
        is run manually by the user. This might be used in future for automated steps.
        """
        self._update_log_browser("\n--- Process Completion (Placeholder Hook) ---")
        if success:
            self._update_log_browser(f"Successfully completed. Adapter Path: {adapter_output_path}") # Corrected log
            QMessageBox.information(self, "Process Complete", f"Process finished successfully.\nAdapter saved to: {adapter_output_path}")
        else:
            self._update_log_browser("Process failed. Check logs for details.") # Corrected log
            QMessageBox.warning(self, "Process Failed", "The process encountered an error. Please review the logs.")
        self.start_tuning_button.setEnabled(True)

    def _start_fine_tuning(self):
        """Handles the 'Generate Training Script & Monitor' button click."""
        self.log_browser.clear()
        self._update_log_browser("INFO: Initiating training script generation...")
        self.start_tuning_button.setEnabled(False)
        # self.simulate_success_button.setEnabled(False) # REMOVED

        params = self.get_tuning_parameters()

        if not params.get('base_model'):
            self._show_error_and_log("Base Model Path/Name cannot be empty.")
            return
        if not params.get('new_model_name'):
            self._show_error_and_log("New Model Name cannot be empty.")
            return

        has_convos = bool(params.get('selected_conversation_paths'))
        has_local_files = bool(params.get('local_files_paths'))
        if not has_convos and not has_local_files:
            self._show_error_and_log("At least one data source (saved conversations or local files) must be selected for training.")
            return

        self._update_log_browser("\n--- Selected Parameters (Validated) ---")
        for key, value in params.items():
            if isinstance(value, list) and value:
                self._update_log_browser(f"{key.replace('_', ' ').title()}:")
                for v_item in value: self._update_log_browser(f"  - {v_item}")
            elif isinstance(value, str) and value.strip() or not isinstance(value, (list, str)):
                 self._update_log_browser(f"{key.replace('_', ' ').title()}: {value}")
            elif isinstance(value, list) and not value:
                 self._update_log_browser(f"{key.replace('_', ' ').title()}: None provided")

        job_name = params.get('output_model_name', 'default_finetune_job').replace(' ', '_').lower()
        job_name = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in job_name)
        if not job_name: job_name = "untitled_finetune_job"

        base_job_dir = os.path.join(os.path.expanduser("~"), "skyscope_training_jobs", job_name)

        try:
            os.makedirs(base_job_dir, exist_ok=True)
            self._update_log_browser(f"INFO: Base job directory: {base_job_dir}")
        except OSError as e:
            self._show_error_and_log(f"Failed to create base job directory {base_job_dir}: {e}")
            return

        script_save_path = os.path.join(base_job_dir, "trainer_script.py")
        adapter_output_path = os.path.join(base_job_dir, "adapter_output")

        try:
            os.makedirs(adapter_output_path, exist_ok=True)
            self.adapter_output_dir_display.setText(adapter_output_path)
            self._update_log_browser(f"INFO: Adapter output directory set to: {adapter_output_path}")
            # self.current_adapter_output_path_for_simulation = adapter_output_path # REMOVED
        except OSError as e:
            self._show_error_and_log(f"Failed to create adapter output directory {adapter_output_path}: {e}")
            return

        conversation_jsonl_path = None
        if params.get("use_saved_conversations") and params.get("selected_conversation_paths"):
            self._update_log_browser("\nINFO: Processing selected conversation files...")
            conversation_jsonl_path = os.path.join(base_job_dir, "prepared_conversations.jsonl")
            conv_success = self.tuning_manager.prepare_conversation_data_for_script(
                params['selected_conversation_paths'], conversation_jsonl_path
            )
            if not conv_success:
                self._show_error_and_log("Failed to prepare conversation data. Check application console/logs for details from TuningManager.")
                return
            self._update_log_browser(f"INFO: Conversation data prepared at: {conversation_jsonl_path}")
        else:
            self._update_log_browser("\nINFO: No saved conversations selected for training.")

        self._update_log_browser("\nINFO: Generating training script...")
        script_success = self.tuning_manager.generate_training_script(
            params, script_save_path, conversation_jsonl_path,
            adapter_output_path, params.get('local_files_paths', [])
        )

        if script_success:
            self._update_log_browser(f"SUCCESS: Training script generated at: {script_save_path}")
            self._update_log_browser("\n--- Next Steps (User Action Required) ---")
            self._update_log_browser("1. Ensure a Python environment with all dependencies from requirements.txt is active (specifically: transformers, peft, torch, PyMuPDF, bitsandbytes, accelerate, datasets). PyTorch should be installed with CUDA support if GPU training is desired.") # Corrected dependency list
            self._update_log_browser(f"2. Open a terminal in that environment and navigate to: cd \"{os.path.dirname(script_save_path)}\"")
            self._update_log_browser(f"3. Run the script: python \"{os.path.basename(script_save_path)}\"")
            self._update_log_browser("4. Monitor the terminal for training progress.")
            self._update_log_browser(f"5. The LoRA adapter will be saved in: \"{adapter_output_path}\"")

            QMessageBox.information(self, "Script Generated",
                                    f"Training script generated at:\n{script_save_path}\n\n"
                                    "Please see the log for instructions on how to run it.")

            self._update_log_browser("\n--- Monitoring Adapter Output ---")
            self._update_log_browser(f"INFO: Monitoring for adapter files in: {adapter_output_path}")
            self._update_log_browser("INFO: This application will wait for the adapter files to appear there.")

            self.tuning_manager.start_adapter_monitoring(
                adapter_output_path,
                self._on_adapter_detected,
                self._on_monitoring_stopped_ui_feedback
            )
            # self.simulate_success_button.setEnabled(True) # REMOVED
            # self._update_log_browser("DEV: 'Simulate Trainer Success' button enabled.") # REMOVED
        else:
            self._show_error_and_log("Failed to generate training script. Check application console/logs for details from TuningManager.")

    def _on_adapter_detected(self, adapter_path: str):
        # self.simulate_success_button.setEnabled(False) # REMOVED
        self._update_log_browser(f"INFO: Adapter detected at {adapter_path}!")
        self.detected_adapter_path = adapter_path

        params = self.get_tuning_parameters()
        base_model = params.get('base_model', '').strip()
        new_model_name_suffix = params.get('new_model_name', '').strip()

        if not base_model:
            self._show_error_and_log("Base Model Path/Name is not specified. Cannot create Ollama model.")
            return

        if not new_model_name_suffix:
            self._show_error_and_log("New Model Name (suffix) is not specified. Cannot create Ollama model.")
            return

        sanitized_suffix = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in new_model_name_suffix.replace(' ', '_'))
        if not sanitized_suffix: sanitized_suffix = "custommodel"
        full_new_model_name = f"Skyscope-{sanitized_suffix}"

        self._update_log_browser(f"\n--- Ollama Model Creation ---")
        self._update_log_browser(f"Attempting to create Ollama model: '{full_new_model_name}'")
        self._update_log_browser(f"Using base model: '{base_model}'")
        self._update_log_browser(f"Using adapter from: '{self.detected_adapter_path}'")

        system_prompt_value = params.get('system_prompt')
        example_messages_value = params.get('example_messages')

        self._update_log_browser("Calling TuningManager to create Ollama model...")
        create_success = self.tuning_manager.create_ollama_model_with_adapter(
            full_new_model_name,
            base_model,
            self.detected_adapter_path,
            system_prompt_value,
            example_messages_value,
            self._update_log_browser
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
            self.start_tuning_button.setEnabled(True)

    def _on_monitoring_stopped_ui_feedback(self, reason: str):
        # self.simulate_success_button.setEnabled(False) # REMOVED
        self._update_log_browser(f"\n--- Monitoring Stopped ---")
        self._update_log_browser(f"INFO: Adapter monitoring stopped. {reason}")

        if not self.start_tuning_button.isEnabled():
             self.start_tuning_button.setEnabled(True)

        if "error" in reason.lower():
             QMessageBox.warning(self, "Monitoring Stopped", f"Adapter monitoring stopped: {reason}")
        elif "cancelled" in reason.lower() and "detected" not in reason.lower() :
             QMessageBox.information(self, "Monitoring Stopped", f"Adapter monitoring was cancelled. {reason}")

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication # Moved import here
    import sys

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #2E2E2E; color: #E0E0E0; font-size: 10pt; }
        QLabel { padding: 2px; }
        QLineEdit, QSpinBox, QListWidget, QTextBrowser, QTextEdit {
            background-color: #252525; color: #F0F0F0;
            border: 1px solid #404040; border-radius: 4px; padding: 5px;
        }
        QPushButton {
            background-color: #4A4A4A; border: 1px solid #555555;
            border-radius: 4px; padding: 8px 12px; min-width: 80px;
        }
        QPushButton:hover { background-color: #5A5A5A; }
        QPushButton:pressed { background-color: #404040; }
        QFormLayout QLabel { margin-top: 5px; }
        QGroupBox { border: 1px solid gray; border-radius: 5px; margin-top: 1ex; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }
        QTableWidget { gridline-color: #5A5A5A; }
    """)

    widget = FineTuningHubWidget()
    widget.setWindowTitle("Fine-Tuning Hub Test")
    widget.setGeometry(100, 100, 700, 900)
    widget.show()

    sys.exit(app.exec())
