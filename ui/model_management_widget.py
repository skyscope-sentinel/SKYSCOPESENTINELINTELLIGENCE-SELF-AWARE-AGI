from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QTextBrowser, QMessageBox, QApplication,
                             QLabel) # Added QLabel for potential titles
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
# Assuming ollama_integration is a module with functions, not a class instance passed directly.
# If it were a class, the import and usage would change.
from core import ollama_integration # Import the module
# import ollama # For ollama.ResponseError, if we catch it directly here.

class ModelManagementWidget(QWidget):
    """
    A widget for managing local Ollama models.
    It allows users to list available models, view their Modelfiles and details,
    and delete models from their local Ollama instance.
    """
    def __init__(self, parent=None):
        """
        Initializes the ModelManagementWidget.
        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        self._populate_model_list()

    def _init_ui(self):
        """Initializes the UI elements and layout for the widget."""
        main_layout = QVBoxLayout(self)

        # Title Label (Optional, but good for context)
        # title_label = QLabel("Manage Local Ollama Models")
        # title_label.setStyleSheet("font-size: 12pt; font-weight: bold; padding-bottom: 10px;")
        # main_layout.addWidget(title_label)

        # Button layout
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh List")
        self.view_modelfile_button = QPushButton("View Modelfile")
        self.delete_model_button = QPushButton("Delete Selected Model")
        self.delete_model_button.setStyleSheet("background-color: #C0392B; color: white;") # Warning color

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.view_modelfile_button)
        button_layout.addStretch() # Pushes delete button to the right
        button_layout.addWidget(self.delete_model_button)
        main_layout.addLayout(button_layout)

        # Model List
        self.model_list_widget = QListWidget()
        self.model_list_widget.setToolTip("List of locally available Ollama models.")
        main_layout.addWidget(self.model_list_widget, 1) # Stretch factor for list

        # Modelfile Display Area
        modelfile_label = QLabel("Modelfile / Details:")
        main_layout.addWidget(modelfile_label)
        self.modelfile_display_area = QTextBrowser()
        self.modelfile_display_area.setObjectName("ModelfileDisplayBrowser") # For QSS styling
        self.modelfile_display_area.setReadOnly(True)
        monospace_font = QFont("Monospace")
        monospace_font.setStyleHint(QFont.StyleHint.Monospace)
        monospace_font.setPointSize(9) # Slightly smaller for dense text
        self.modelfile_display_area.setFont(monospace_font)
        self.modelfile_display_area.setToolTip("Shows the Modelfile and other details of the selected model.")
        main_layout.addWidget(self.modelfile_display_area, 2) # More stretch

        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connects UI element signals to their respective slots."""
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        self.view_modelfile_button.clicked.connect(self._on_view_modelfile_clicked)
        self.delete_model_button.clicked.connect(self._on_delete_model_clicked)
        self.model_list_widget.itemSelectionChanged.connect(self._on_model_selection_changed)


    def _populate_model_list(self):
        """
        Populates the list widget with locally available Ollama models.
        Clears any previously displayed model details.
        """
        self.model_list_widget.clear()
        self.modelfile_display_area.clear()
        self.view_modelfile_button.setEnabled(False)
        self.delete_model_button.setEnabled(False) # Disable until item selected

        try:
            # Using the direct function call from the imported module
            models = ollama_integration.list_ollama_models()
            if models: # list_ollama_models now returns a list of names
                self.model_list_widget.addItems(sorted(models))
                # self.view_modelfile_button.setEnabled(True) # Enable only when an item is selected
                # self.delete_model_button.setEnabled(True)
            else:
                self.model_list_widget.addItem("No models found or Ollama not running.")
        # Catching general Exception as ollama_integration functions now return error dicts or handle internally
        except Exception as e:
            QMessageBox.critical(self, "Error Listing Models",
                                 f"Could not retrieve model list from Ollama:\n{e}\n\n"
                                 "Please ensure Ollama is running and accessible.")
            self.model_list_widget.addItem("Error connecting to Ollama.")

    def _on_model_selection_changed(self):
        """
        Handles changes in model selection in the list widget.
        Enables/disables action buttons based on whether an item is selected.
        """
        selected_items = self.model_list_widget.selectedItems()
        is_item_selected = bool(selected_items)
        self.view_modelfile_button.setEnabled(is_item_selected)
        self.delete_model_button.setEnabled(is_item_selected)
        if is_item_selected:
            # Optionally auto-view modelfile on selection, or wait for button click
            # self._on_view_modelfile_clicked()
            pass
        else:
            self.modelfile_display_area.clear()


    def _on_refresh_clicked(self):
        """Handles the 'Refresh List' button click; repopulates the model list."""
        self._populate_model_list()

    def _on_view_modelfile_clicked(self):
        """
        Handles the 'View Modelfile' button click.
        Fetches and displays the Modelfile and other details of the selected model.
        """
        current_item = self.model_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "View Modelfile", "Please select a model from the list.")
            return

        model_name = current_item.text()
        if model_name in ["Error connecting to Ollama.", "No models found or Ollama not running."]:
            QMessageBox.warning(self, "View Modelfile", "Cannot view details for this placeholder item.")
            return

        self.modelfile_display_area.setText(f"Fetching details for {model_name}...")
        QApplication.processEvents() # Update UI

        try:
            info = ollama_integration.show_model_info(model_name) # Direct function call
            if "error" in info:
                error_msg = info["error"]
                QMessageBox.critical(self, "Error", f"Failed to get model info for '{model_name}':\n{error_msg}")
                self.modelfile_display_area.setText(f"Error fetching details for {model_name}:\n{error_msg}")
            else:
                # Display a formatted summary of model info
                modelfile_content = info.get('modelfile', '# Modelfile not available')
                details_content = info.get('details', {})
                parameters_content = info.get('parameters', '')

                display_text = f"--- Modelfile for {model_name} ---\n{modelfile_content}\n\n"
                display_text += f"--- Parameters ---\n{parameters_content}\n\n"
                display_text += f"--- Details ---\n"
                if isinstance(details_content, dict):
                    for key, value in details_content.items():
                        display_text += f"{key.replace('_', ' ').title()}: {value}\n"
                else:
                    display_text += str(details_content)

                self.modelfile_display_area.setText(display_text.strip())
        except Exception as e: # Should be caught by show_model_info, but as safeguard
            QMessageBox.critical(self, "Error", f"Unexpected error fetching model info for '{model_name}': {e}")
            self.modelfile_display_area.setText(f"Error fetching details for {model_name}:\n{e}")


    def _on_delete_model_clicked(self):
        """
        Handles the 'Delete Selected Model' button click.
        Confirms deletion with the user and then attempts to delete the model via OllamaIntegration.
        """
        current_item = self.model_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Delete Model", "Please select a model to delete.")
            return

        model_name = current_item.text()
        if model_name in ["Error connecting to Ollama.", "No models found or Ollama not running."]:
            QMessageBox.warning(self, "Delete Model", "Cannot delete this placeholder item.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete the Ollama model '{model_name}'?\n"
                                     "This action cannot be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.modelfile_display_area.setText(f"Deleting model {model_name}...")
            QApplication.processEvents() # Update UI
            try:
                success = ollama_integration.delete_model(model_name) # Direct function call
                if success:
                    QMessageBox.information(self, "Success", f"Model '{model_name}' has been deleted.")
                    self._populate_model_list() # Refresh the list
                else:
                    # Error message should be printed by ollama_integration.delete_model
                    # Or it could return more detailed error info.
                    QMessageBox.critical(self, "Error", f"Failed to delete model '{model_name}'.\n"
                                         "Check application logs or Ollama server status.")
                    # Re-populate to reflect current state even on failure (e.g. if model was already gone)
                    self._populate_model_list()
            except Exception as e: # Safeguard
                QMessageBox.critical(self, "Error", f"An unexpected error occurred while trying to delete '{model_name}': {e}")
                self._populate_model_list()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    # Basic styling for standalone test
    app.setStyleSheet("""
        QWidget { background-color: #2E2E2E; color: #E0E0E0; font-size: 10pt; }
        QPushButton { padding: 8px; background-color: #4A4A4A; border-radius: 4px; }
        QPushButton:hover { background-color: #5A5A5A; }
        QListWidget { background-color: #252525; border-radius: 4px; padding: 5px; }
        QTextBrowser { background-color: #202020; border-radius: 4px; padding: 5px; }
        QMessageBox { background-color: #3E3E3E; }
    """)

    # In a real app, ollama_integration.client would be initialized.
    # For standalone test, we might need to mock ollama_integration functions or ensure Ollama is running.
    # This test will try to use the actual Ollama instance if available.

    main_widget = ModelManagementWidget()
    main_widget.setWindowTitle("Ollama Model Management Test")
    main_widget.setGeometry(200, 200, 700, 500)
    main_widget.show()
    sys.exit(app.exec())
