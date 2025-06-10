from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from core.ollama_integration import list_ollama_models

class ModelSelectionWidget(QWidget):
    """
    A widget for selecting an Ollama model from a list of available models.
    It provides a dropdown (QComboBox) to display model names and a button
    to refresh this list by querying the Ollama instance.
    """
    def __init__(self, parent=None):
        """
        Initializes the ModelSelectionWidget.
        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.current_selected_model = None # Stores the name of the currently selected model string
        self._init_ui()
        self.refresh_models_list() # Initial population

    def _init_ui(self):
        """Initializes the UI elements and layout for the model selection widget."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Styling placeholder:
        # self.setStyleSheet("""
        #     QWidget {
        #         background-color: #3c3c3c; /* Darker background for this widget */
        #         border-radius: 8px;
        #     }
        #     QLabel {
        #         color: #e0e0e0;
        #         font-size: 14px;
        #         padding-bottom: 5px;
        #     }
        #     QComboBox {
        #         background-color: #4a4a4a;
        #         color: #e0e0e0;
        #         border: 1px solid #555555;
        #         border-radius: 4px;
        #         padding: 5px;
        #     }
        #     QComboBox::drop-down {
        #         border: none;
        #     }
        #     QComboBox QAbstractItemView { /* Styling for the dropdown items */
        #         background-color: #4a4a4a;
        #         color: #e0e0e0;
        #         selection-background-color: #5a5a5a;
        #     }
        #     QPushButton {
        #         background-color: #5a5a5a;
        #         color: #e0e0e0;
        #         border: none;
        #         border-radius: 4px;
        #         padding: 8px;
        #         margin-top: 10px;
        #     }
        #     QPushButton:hover {
        #         background-color: #6a6a6a;
        #     }
        #     QPushButton:pressed {
        #         background-color: #4f4f4f;
        #     }
        # """)

        self.model_label = QLabel("Select Ollama Model:")
        layout.addWidget(self.model_label)

        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.model_combo)

        self.refresh_button = QPushButton("Refresh Models")
        self.refresh_button.clicked.connect(self.refresh_models_list)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)

    def _on_model_changed(self, model_name: str):
        """
        Slot connected to the QComboBox's currentTextChanged signal.
        Updates the internal tracking of the selected model.
        Args:
            model_name (str): The new model name selected in the QComboBox.
        """
        self.current_selected_model = model_name
        # This signal is connected in main.py to update ChatWindowWidget's display
        # print(f"INFO (ModelSelectionWidget): Model changed to {model_name}")

    def refresh_models_list(self):
        """
        Refreshes the list of available Ollama models in the QComboBox.
        Queries the Ollama instance and updates the dropdown.
        Handles errors if Ollama is not accessible.
        """
        print("INFO (ModelSelectionWidget): Refreshing Ollama models list...")
        # self._update_log_browser_placeholder("INFO: Refreshing Ollama models list...") # REMOVED
        try:
            models = list_ollama_models() # This now returns list of names directly
            self.model_combo.clear()
            if models:
                self.model_combo.addItems(models)
                if not self.current_selected_model and models: # Select first model if none selected
                    self.current_selected_model = models[0]
                    self.model_combo.setCurrentIndex(0)
                elif self.current_selected_model in models: # Reselect previous model if still exists
                    self.model_combo.setCurrentText(self.current_selected_model)
                print(f"Models loaded: {models}")
            else:
                self.model_combo.addItem("No models found") # Placeholder item
                self.model_combo.setEnabled(False)
                print("INFO (ModelSelectionWidget): No Ollama models found during refresh.") # Replaced placeholder
        except Exception as e: # General exception catch, as list_ollama_models handles ollama.ResponseError
            print(f"ERROR (ModelSelectionWidget): Error refreshing models list: {e}") # Replaced placeholder
            self.model_combo.clear()
            self.model_combo.addItem("Error loading models")
            self.model_combo.setEnabled(False)
            QMessageBox.warning(self, "Ollama Connection Error",
                                f"Could not fetch models from Ollama: {e}\n\n"
                                "Please ensure Ollama is running and accessible at the configured host.")
        finally:
            print("INFO (ModelSelectionWidget): Model refresh finished.") # Replaced placeholder

    def get_selected_model(self) -> str | None:
        """
        Returns the name of the currently selected model.
        Returns None if no valid model is selected or available.
        """
        if self.model_combo.isEnabled() and self.model_combo.count() > 0:
            current_text = self.model_combo.currentText()
            if current_text not in ["No models found", "Error loading models"]:
                return current_text
        return None

if __name__ == '__main__':
    # This is for testing the widget independently
    from PyQt6.QtWidgets import QApplication
    import sys

    # Mock list_ollama_models for standalone testing if Ollama isn't running
    original_list_models = list_ollama_models
    def mock_list_models_func():
        # return ["llama2:latest", "codellama:latest", "mistral:latest"]
        return [] # Test empty case
        # raise Exception("Test connection error") # Test error case

    # core.ollama_integration.list_ollama_models = mock_list_models_func # Uncomment to mock

    app = QApplication(sys.argv)
    widget = ModelSelectionWidget()
    widget.show()

    # Restore original function if mocked
    # core.ollama_integration.list_ollama_models = original_list_models

    sys.exit(app.exec())
