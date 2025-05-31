import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QLabel, QSplitter) # Added QTabWidget, QLabel, QSplitter
from PyQt6.QtCore import Qt # For Qt.Horizontal / Qt.Vertical if needed for splitter orientation

# Import necessary modules from core and ui
from core.ollama_integration import list_ollama_models, generate_response # Keep
from core.memory_manager import load_conversation # Added for history loading

from ui.model_selection import ModelSelectionWidget # Existing
from ui.chat_window import ChatWindowWidget # Existing
# Import new UI components (will be created in subsequent steps)
# These will be uncommented as the files are created.
from ui.verbose_display import VerboseDisplayWidget
from ui.conversation_history import ConversationHistoryWidget
from ui.fine_tuning_hub import FineTuningHubWidget # Import new widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sentient AI Platform")
        # Increased default size to better accommodate three panels
        self.setGeometry(100, 100, 1400, 800)

        # Central widget will hold the main QSplitter
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        # Layout for the main_widget that contains the splitter
        self.main_layout = QHBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0,0,0,0) # Use full space

        # Global stylesheet - can be moved to a styles.py if it grows large
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B; /* Base dark background for the main window */
            }

            /* Styling for panels and central widget areas if they are QWidget/QFrame directly */
            /* Use object names if more specific containers are used, e.g. QWidget#CentralChatWidget */
            QWidget { /* General default for QWidget, might need to be more specific */
                background-color: rgba(45, 45, 45, 230); /* semi-transparent dark gray */
                color: #E0E0E0; /* Light gray text for general widgets */
                border-radius: 8px;
                /* border: 1px solid rgba(70, 70, 70, 150); */ /* Subtle border - disable if too much */
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }

            /* Ensure specific panel container QWidgets get this if they are not styled by more specific rules */
            /* Example: self.left_panel_container.setObjectName("LeftPanelContainer") */
            QWidget#LeftPanelContainer, QWidget#RightPanelContainer, QWidget#CenterPanelContainer {
                 background-color: rgba(45, 45, 45, 230);
                 border-radius: 8px;
                 border: 1px solid rgba(70, 70, 70, 150);
            }


            QTabWidget::pane {
                border: 1px solid rgba(70, 70, 70, 150);
                border-radius: 6px;
                background-color: rgba(40, 40, 40, 220);
            }
            QTabBar::tab {
                background: rgba(30, 30, 30, 200);
                color: #BBBBBB;
                padding: 8px 15px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid rgba(70, 70, 70, 150);
                border-bottom: none; /* Important for tab connection illusion */
                margin-right: 1px;
            }
            QTabBar::tab:selected {
                background: rgba(50, 50, 50, 230); /* Make selected tab's bg match/blend with pane's border or bg */
                color: white;
                border: 1px solid rgba(80, 80, 80, 200);
                border-bottom: 1px solid rgba(50, 50, 50, 230); /* Blend with pane */
            }
            QTabBar::tab:!selected:hover {
                background: rgba(60, 60, 60, 220);
                color: white;
            }

            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(65, 65, 65, 220), stop:1 rgba(50, 50, 50, 220));
                border: 1px solid rgba(80, 80, 80, 200);
                border-radius: 5px;
                color: #DDDDDD;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(75, 75, 75, 230), stop:1 rgba(60, 60, 60, 230));
                border: 1px solid rgba(100, 100, 100, 230);
            }
            QPushButton:pressed {
                background-color: rgba(40, 40, 40, 230);
            }
            /* Specific button styling if needed, e.g. for Send or Start Tuning */
            QPushButton#SendButton, QPushButton#StartTuningButton {
                 font-weight: bold;
                 padding: 8px 15px; /* Make them a bit larger */
            }


            QLineEdit, QTextEdit, QPlainTextEdit { /* General Text Inputs, not chat/log displays */
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid rgba(70, 70, 70, 150);
                border-radius: 4px;
                color: #DDDDDD;
                padding: 5px;
            }
            QSpinBox { /* Often similar to QLineEdit */
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid rgba(70, 70, 70, 150);
                border-radius: 4px;
                color: #DDDDDD;
                padding: 3px; /* Spinboxes might need less padding */
            }
            QSpinBox::up-button, QSpinBox::down-button {
                 /* Basic styling for spinbox arrows if default is ugly */
                 subcontrol-origin: border;
                 background-color: rgba(50,50,50,200);
                 border-radius: 2px;
            }


            /* Specific styling for Chat Display and Verbose Display using Object Names */
            QTextBrowser#ChatDisplayArea, QTextBrowser#VerboseDisplayBrowser, QTextBrowser#FineTuneLogBrowser {
                background-color: rgba(35, 35, 35, 230);
                color: #E0E0E0;
                border-radius: 6px;
                border: 1px solid rgba(60, 60, 60, 180);
                padding: 5px;
            }
             /* For the prompt input area if it's a QTextEdit and needs specific styling */
            QTextEdit#PromptInputArea {
                background-color: rgba(40, 40, 40, 210); /* Slightly different from other QLineEdits */
                color: #E8E8E8;
                border-radius: 6px;
                border: 1px solid rgba(65, 65, 65, 180);
                padding: 8px;
            }


            QListWidget {
                background-color: rgba(40, 40, 40, 210);
                border-radius: 6px;
                border: 1px solid rgba(60, 60, 60, 180);
                padding: 3px; /* Padding for the widget itself */
            }
            QListWidget::item {
                color: #COCOCO; /* Light gray for item text */
                padding: 5px 3px; /* Padding for each item */
                border-radius: 3px; /* Rounded corners for items themselves */
            }
            QListWidget::item:selected {
                background-color: rgba(70, 90, 120, 200); /* A distinct selection color */
                color: white;
                /* border: 1px solid rgba(100, 120, 150, 220); */ /* Optional border for selected item */
            }
            QListWidget::item:hover {
                background-color: rgba(55, 55, 65, 200); /* Subtle hover */
            }


            QComboBox {
                background-color: rgba(45, 45, 45, 220);
                border: 1px solid rgba(70, 70, 70, 150);
                border-radius: 4px;
                padding: 5px;
                color: #DDDDDD;
                min-width: 100px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: rgba(80, 80, 80, 180);
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            QComboBox QAbstractItemView { /* Dropdown list */
                background-color: #2E2E2E; /* Dark background for dropdown */
                color: #DDDDDD;
                border: 1px solid rgba(80, 80, 80, 200);
                selection-background-color: rgba(70, 90, 120, 200); /* Consistent selection color */
                padding: 3px;
            }

            QLabel {
                color: #D0D0D0; /* Slightly dimmer default for labels */
                background-color: transparent; /* Ensure labels don't have their own opaque background unless intended */
                border: none; /* No border for labels by default */
                padding: 2px;
            }
            /* For labels used as titles/headings */
            QLabel#SectionTitleLabel {
                font-weight: bold;
                color: #EFEFEF;
                padding-top: 5px;
                padding-bottom: 3px;
            }


            QScrollBar:vertical {
                border: none;
                background: rgba(30,30,30,180); /* Slightly transparent scrollbar track */
                width: 12px; /* Wider for easier clicking */
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(80,80,80,200);
                min-height: 25px; /* Taller handle */
                border-radius: 6px; /* More rounded */
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(100,100,100,220);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            /* Horizontal Scrollbar (similar styling) */
            QScrollBar:horizontal {
                border: none;
                background: rgba(30,30,30,180);
                height: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(80,80,80,200);
                min-width: 25px;
                border-radius: 6px;
            }
             QScrollBar::handle:horizontal:hover {
                background: rgba(100,100,100,220);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }

            QSplitter::handle {
                background-color: rgba(70, 70, 70, 50); /* More transparent handle */
                border: 1px solid rgba(60, 60, 60, 70);
            }
            QSplitter::handle:hover {
                background-color: rgba(90, 90, 90, 70);
            }
            QSplitter::handle:horizontal { width: 3px; }
            QSplitter::handle:vertical { height: 3px; }
        """)

        self._create_ui_components()
        self._connect_signals()


    def _create_ui_components(self):
        # Main splitter to divide left, center, and right panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # --- Left Panel (QTabWidget) ---
        self.left_tab_widget = QTabWidget()
        self.model_selection_widget = ModelSelectionWidget(self) # Existing widget

        # Placeholder for ConversationHistoryWidget - uncomment when file exists
        self.conversation_history_widget = ConversationHistoryWidget(self) # NOW UNCOMMENTED
        self.left_tab_widget.addTab(self.conversation_history_widget, "History")
        # For now, adding a QLabel placeholder for History tab
        # self.conversation_history_widget_placeholder = QLabel("Placeholder for Conversation History") # Commented out
        # self.left_tab_widget.addTab(self.conversation_history_widget_placeholder, "History") # Commented out

        self.left_tab_widget.addTab(self.model_selection_widget, "Models") # ModelSelection is now a tab too
        self.left_tab_widget.addTab(QLabel("Placeholder for Chat Settings"), "Chat Settings")

        # Instantiate and add FineTuningHubWidget
        self.fine_tuning_hub_widget = FineTuningHubWidget(self)
        self.left_tab_widget.addTab(self.fine_tuning_hub_widget, "Fine-Tuning")

        # --- Center Panel (ChatWindowWidget) ---
        self.chat_window_widget = ChatWindowWidget(self) # Existing widget
        # Pass verbose display reference to chat window
        if hasattr(self, 'verbose_display_widget'): # Check if actual widget, not placeholder
             self.chat_window_widget.set_verbose_display(self.verbose_display_widget)

        # --- Right Panel (QTabWidget) ---
        self.right_tab_widget = QTabWidget()

        # Placeholder for VerboseDisplayWidget - uncomment when file exists
        self.verbose_display_widget = VerboseDisplayWidget(self) # NOW UNCOMMENTED
        self.right_tab_widget.addTab(self.verbose_display_widget, "Verbose Output")
        # For now, adding a QLabel placeholder
        # self.verbose_display_widget_placeholder = QLabel("Placeholder for Verbose Output") # Commented out
        # self.right_tab_widget.addTab(self.verbose_display_widget_placeholder, "Verbose Output") # Commented out

        self.right_tab_widget.addTab(QLabel("Placeholder for Internals"), "Internals")

        # Add panels to the splitter
        self.main_splitter.addWidget(self.left_tab_widget)
        self.main_splitter.addWidget(self.chat_window_widget)
        self.main_splitter.addWidget(self.right_tab_widget)

        # Set initial sizes for splitter
        total_width = self.geometry().width() # Use current geometry
        self.main_splitter.setSizes([int(total_width * 0.20), int(total_width * 0.55), int(total_width * 0.25)])

        # Add the main_splitter to the main_layout of the central widget
        self.main_layout.addWidget(self.main_splitter)

    def _connect_signals(self):
        # Connect model selection change to chat window (as before)
        self.model_selection_widget.model_combo.currentTextChanged.connect(
            self.chat_window_widget.update_selected_model_display
        )

        # Connect history "Load Selected" - This will be fully active when ConversationHistoryWidget is done
        if hasattr(self, 'conversation_history_widget'): # Check if placeholder is replaced
            self.conversation_history_widget.load_button.clicked.connect(
                self._on_load_conversation_selected
            )
        else:
            print("ConversationHistoryWidget not yet initialized for signal connection.")

        # Placeholder for connecting ChatWindowWidget signals to VerboseDisplayWidget
        # self.chat_window_widget.new_response_generated.connect(self.verbose_display_widget.set_text)
        # This would require ChatWindowWidget to emit a signal with the full response text.

        # Connect chat window's new message signal (to be created) to verbose display
        # self.chat_window_widget.new_message_for_verbose.connect(self.verbose_display_widget.append_text)
        pass


    def _on_load_conversation_selected(self):
        # This method will be fully functional once ConversationHistoryWidget is implemented
        if not hasattr(self, 'conversation_history_widget') or not self.verbose_display_widget:
            print("History or Verbose widget not available for loading conversation.")
            return

        selected_item = self.conversation_history_widget.history_list.currentItem() # history_list is defined in ConversationHistoryWidget
        if not selected_item:
            print("No conversation selected from history.")
            # QMessageBox.information(self, "Load Error", "No conversation selected.")
            return

        filepath = selected_item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            print(f"Error: No filepath for selected item: {selected_item.text()}")
            # QMessageBox.warning(self, "Load Error", "No filepath associated with the selected conversation.")
            return

        print(f"Attempting to load conversation from: {filepath}")
        conversation_data = load_conversation(filepath)

        if conversation_data:
            self.chat_window_widget.load_conversation_from_data(conversation_data)
            import json # Temporary import for pretty printing
            self.verbose_display_widget.set_text(
                f"Loaded conversation: {conversation_data.get('conversation_id')}\n\n"
                f"{json.dumps(conversation_data, indent=2)}"
            )
            # Ensure the center panel (chat window) is visible, though it's not in a tab itself.
            # If the left panel had multiple tabs and history was one, you might want to switch
            # the left panel's current tab if needed, e.g., to a "chat details" tab if you add one.
            # self.left_tab_widget.setCurrentWidget(self.model_selection_widget) # Example if needed
            print(f"Conversation '{conversation_data.get('title', conversation_data.get('conversation_id'))}' loaded.")
        else:
            self.verbose_display_widget.set_text(f"Failed to load conversation from: {filepath}")
            print(f"Failed to load conversation from: {filepath}")
            # QMessageBox.critical(self, "Load Error", f"Failed to load conversation from:\n{filepath}")


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
