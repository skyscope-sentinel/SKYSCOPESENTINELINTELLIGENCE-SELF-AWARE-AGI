from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QPushButton,
                             QLabel, QHBoxLayout, QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt
from core.memory_manager import list_saved_conversations, MEMORY_DIR
import os # For joining paths

class ConversationHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.populate_history_list() # Initial population

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Add some margins

        self.title_label = QLabel("Conversation History")
        self.title_label.setStyleSheet("font-size: 12pt; font-weight: bold; padding-bottom: 5px;")
        layout.addWidget(self.title_label)

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._on_double_click_load) # Allow double click to load
        layout.addWidget(self.history_list)

        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.clicked.connect(self.populate_history_list)
        button_layout.addWidget(self.refresh_button)

        self.load_button = QPushButton("Load Selected")
        # The actual load action is connected in main.py, here we just ensure the button exists.
        # self.load_button.clicked.connect(self._emit_load_selected_signal_or_handle_directly)
        button_layout.addWidget(self.load_button)

        # Optional Delete Button (functionality can be added later)
        # self.delete_button = QPushButton("Delete Selected")
        # self.delete_button.clicked.connect(self._on_delete_selected)
        # self.delete_button.setStyleSheet("background-color: #8B0000; color: white;") # Dark red
        # button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Styling (can be part of global stylesheet)
        # self.setStyleSheet("""
        #     QLabel { padding-top: 5px; }
        #     QListWidget { border-radius: 4px; }
        # """)

    def populate_history_list(self):
        print("Refreshing conversation history list...")
        self.history_list.clear()
        try:
            conversation_files = list_saved_conversations()
            if conversation_files:
                for filename in sorted(conversation_files, reverse=True): # Show newest first
                    # Create a QListWidgetItem
                    # We can try to extract a more friendly name or timestamp from filename if needed
                    # For now, filename is fine.
                    item = QListWidgetItem(filename)
                    # Store the full filepath as data with the item
                    full_filepath = os.path.join(MEMORY_DIR, filename)
                    item.setData(Qt.ItemDataRole.UserRole, full_filepath)
                    item.setToolTip(f"Path: {full_filepath}") # Show full path on hover
                    self.history_list.addItem(item)
                print(f"Found {len(conversation_files)} conversations.")
            else:
                self.history_list.addItem(QListWidgetItem("No saved conversations found."))
                self.history_list.setEnabled(False) # Disable list if empty
                print("No saved conversations found.")
        except Exception as e:
            error_item_text = "Error loading history"
            error_item = QListWidgetItem(error_item_text)
            error_item.setData(Qt.ItemDataRole.UserRole, None) # No filepath for error
            self.history_list.addItem(error_item)
            self.history_list.setEnabled(False)
            print(f"Error populating conversation history: {e}")
            QMessageBox.critical(self, "History Error", f"Could not load conversation history: {e}")
        finally:
            if self.history_list.count() > 0 and \
               self.history_list.item(0).text() not in ["No saved conversations found.", "Error loading history"]:
                self.history_list.setEnabled(True)


    def _on_double_click_load(self, item):
        # This will trigger the load_button's connected slot in main.py
        # if the main window is set up to listen to this widget's load_button.
        # Or, if load_button has its own signal, emit it.
        # For now, we assume main.py handles load_button.clicked.
        # If load_button is available and connected, we can programmatically click it.
        if self.load_button and self.load_button.isEnabled():
             print(f"Item double-clicked: {item.text()}. Simulating load button click.")
             self.load_button.click()

    # def _on_delete_selected(self):
    #     selected_item = self.history_list.currentItem()
    #     if not selected_item or not selected_item.data(Qt.ItemDataRole.UserRole):
    #         QMessageBox.warning(self, "Delete Error", "No conversation selected or invalid item.")
    #         return
    #     filepath = selected_item.data(Qt.ItemDataRole.UserRole)
    #     # Confirmation dialog
    #     reply = QMessageBox.question(self, 'Delete Conversation',
    #                                  f"Are you sure you want to delete this conversation?\n{filepath}",
    #                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    #                                  QMessageBox.StandardButton.No)
    #     if reply == QMessageBox.StandardButton.Yes:
    #         try:
    #             os.remove(filepath)
    #             self.populate_history_list() # Refresh list
    #             print(f"Deleted conversation: {filepath}")
    #         except Exception as e:
    #             print(f"Error deleting conversation {filepath}: {e}")
    #             QMessageBox.critical(self, "Delete Error", f"Failed to delete conversation: {e}")


if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    # Ensure conversations directory exists for testing
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
        # Create some dummy files for testing list population
        for i in range(3):
            with open(os.path.join(MEMORY_DIR, f"conversation_test_history_{i}.json"), 'w') as f:
                f.write(f'{{"conversation_id": "test_history_{i}", "messages": []}}')

    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background-color: #2E2E2E; color: #E0E0E0; } QPushButton { min-width: 100px; padding: 8px; }") # Basic style

    widget = ConversationHistoryWidget()
    widget.setWindowTitle("Conversation History Test")
    widget.setGeometry(100, 100, 400, 600)
    widget.show()

    sys.exit(app.exec())
