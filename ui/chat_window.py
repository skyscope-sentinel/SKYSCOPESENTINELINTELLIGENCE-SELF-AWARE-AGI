from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QMessageBox, QApplication
from PyQt6.QtGui import QTextCursor # Added QTextCursor
from PyQt6.QtCore import Qt, QTimer # QTimer might be used if processEvents causes issues.
from core.ollama_integration import generate_response # Updated generate_response supports streaming
from core.memory_manager import save_conversation
import uuid
from datetime import datetime

class ChatWindowWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_selected_model_for_chat = None
        self.current_conversation_id = None
        self.current_messages = []
        self.timestamp_start = None
        self.verbose_display = None
        self.current_assistant_message = "" # For accumulating streamed response
        self.ollama_integration_client = None # Placeholder if direct client access needed, but using functions for now.
        self._init_ui()

    def set_verbose_display(self, verbose_widget):
        """Sets the reference to the verbose display widget."""
        self.verbose_display = verbose_widget

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Styling placeholder:
        # self.setStyleSheet("""
        #     QWidget {
        #         background-color: #333333; /* Dark background for chat area */
        #         color: #e0e0e0;
        #     }
        #     QLabel {
        #         font-size: 12px;
        #         color: #c0c0c0;
        #         padding-bottom: 3px;
        #     }
        #     QTextEdit, QPlainTextEdit {
        #         background-color: #2b2b2b;
        #         color: #f0f0f0;
        #         border: 1px solid #444444;
        #         border-radius: 4px;
        #         padding: 8px; /* Increased padding */
        #         font-size: 14px; /* Slightly larger font */
        #     }
        #     QTextBrowser { /* If used for display */
        #         background-color: #2b2b2b;
        #         color: #f0f0f0;
        #         border: 1px solid #444444;
        #         border-radius: 4px;
        #         padding: 8px;
        #         font-size: 14px;
        #     }
        #     QPushButton {
        #         background-color: #007bff; /* Blue send button */
        #         color: white;
        #         border: none;
        #         border-radius: 4px;
        #         padding: 10px; /* Larger padding */
        #         font-size: 14px;
        #         margin-top: 5px;
        #     }
        #     QPushButton:hover {
        #         background-color: #0056b3;
        #     }
        #     QPushButton:pressed {
        #         background-color: #004085;
        #     }
        # """)

        # Selected model display (read-only)
        self.selected_model_label = QLabel("Current Model: Not Selected")
        self.selected_model_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.selected_model_label.setStyleSheet("padding: 5px; background-color: #2a2a2a; border-radius: 3px;")
        main_layout.addWidget(self.selected_model_label)

        # Chat display area (read-only)
        self.chat_display = QTextEdit() # Using QTextEdit to allow rich text if needed later
        self.chat_display.setObjectName("ChatDisplayArea") # Object name for QSS
        self.chat_display.setReadOnly(True)
        # For auto-scrolling:
        # self.scroll_area = QScrollArea()
        # self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setWidget(self.chat_display)
        # self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_layout.addWidget(self.chat_display, 5) # Give more stretch factor

        # Input area
        input_layout = QHBoxLayout()
        self.prompt_input = QTextEdit() # Using QTextEdit for multi-line input by default
        self.prompt_input.setObjectName("PromptInputArea") # Object name for QSS
        self.prompt_input.setFixedHeight(100) # Set a fixed height for the input box
        # self.prompt_input.setPlaceholderText("Enter your prompt here...") # Placeholder text
        input_layout.addWidget(self.prompt_input, 4)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("SendButton") # Object name for QSS
        # Add a button to start a new chat session (optional for this subtask, but good for usability)
        # self.new_chat_button = QPushButton("New Chat")
        # self.new_chat_button.clicked.connect(self._start_new_chat_session)
        # input_layout.addWidget(self.new_chat_button)

        self.send_button.clicked.connect(self._on_send_clicked)
        # self.send_button.setFixedHeight(self.prompt_input.sizeHint().height()) # Match height
        input_layout.addWidget(self.send_button, 1)

        main_layout.addLayout(input_layout, 1) # Less stretch factor for input section
        self.setLayout(main_layout)

    def update_selected_model_display(self, model_name):
        """Public method to be called when the model selection changes."""
        self.current_selected_model_for_chat = model_name
        if model_name:
            self.selected_model_label.setText(f"Current Model: {model_name}")
            print(f"ChatWindowWidget: Model updated to {model_name}") # For debugging
        else:
            self.selected_model_label.setText("Current Model: Not Selected")
            print("ChatWindowWidget: Model cleared or not selected") # For debugging


    def _on_send_clicked(self):
        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Input Error", "Prompt cannot be empty.")
            return

        selected_model = self.current_selected_model_for_chat
        if not selected_model or selected_model in ["No models found", "Error loading models"]:
            QMessageBox.warning(self, "Model Error", "Please select a valid Ollama model first.")
            return

        # --- Display user's prompt ---
        user_timestamp = datetime.now().strftime("%H:%M:%S")
        # Using HTML for better control over formatting and to allow appending later.
        # Storing the initial HTML for the assistant's message might be complex.
        # A simpler way for now is to append user message, then append assistant message label, then stream to it.
        self.chat_display.append(f"<span style='color: #777;'>[{user_timestamp}]</span> <b style='color: #A9D18E;'>You:</b><br>{prompt_text.replace(chr(10), '<br>')}<br>")
        self.prompt_input.clear()

        # --- Prepare for assistant's response (streaming) ---
        self.current_assistant_message = "" # Reset accumulator
        assistant_timestamp = datetime.now().strftime("%H:%M:%S")
        # Append the initial part of the assistant's message. Chunks will be added by _handle_streamed_chunk.
        # We need a way to identify this message block if we want to replace its content rather than just append.
        # For now, direct append in _handle_streamed_chunk will create new paragraphs.
        # A more robust way: use QTextCursor to move to end, insert new content.
        self.chat_display.append(f"<span style='color: #777;'>[{assistant_timestamp}]</span> <b style='color: #9BC2E6;'>{selected_model}:</b><br>")
        # Ensure cursor is at the end for insertPlainText to work as expected append
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)


        if self.verbose_display:
            self.verbose_display.clear_display() # Clear previous verbose output
            self.verbose_display.append_text(f"--- PROMPT SENT TO: {selected_model} ---\n{prompt_text}\n\n--- ASSISTANT RESPONSE (Streaming) ---\n")

        self.send_button.setEnabled(False)
        self.send_button.setText("Generating...")
        QApplication.processEvents() # Update UI before blocking call (if generate_response was blocking)

        try:
            # Call Ollama integration with streaming callback
            # generate_response now returns the full response after streaming is complete.
            full_response = generate_response(
                selected_model,
                prompt_text,
                stream_callback=self._handle_streamed_chunk
            )

            # Post-streaming actions:
            # _handle_streamed_chunk has updated self.current_assistant_message and UI.
            # The full_response is the same as self.current_assistant_message if no errors.
            # If there were errors during stream, full_response might contain error markers from ollama_integration.
            # We need to decide if we re-set the text area with full_response or trust _handle_streamed_chunk.
            # For now, assuming _handle_streamed_chunk did its job for the main chat_display.
            # If full_response contains error info not sent to stream, log it or display it.
            if "ERROR:" in full_response and self.current_assistant_message.find("ERROR:") == -1 :
                 # If error was in the returned string but not streamed, append it.
                 self.chat_display.append(f"<span style='color: #FF6347;'>{full_response.replace(self.current_assistant_message, '')}</span><br>")
                 if self.verbose_display:
                    self.verbose_display.append_text(f"\n--- FINAL RESPONSE (with error info) ---\n{full_response}\n")

            self.chat_display.append("<br>") # Add a separator for clarity before next prompt.
            self._save_current_conversation(prompt_text, self.current_assistant_message) # Save with accumulated message

        except Exception as e: # Should ideally be caught within generate_response or by its specific error returns
            error_message = f"Unhandled error during generation: {e}"
            print(error_message)
            self.chat_display.append(f"<span style='color: #FF6347;'>Error: {error_message}</span><br>")
            if self.verbose_display:
                self.verbose_display.append_text(f"\n--- UNHANDLED ERROR ---\n{error_message}\n")
            QMessageBox.critical(self, "Generation Error", error_message)
        finally:
            self.send_button.setEnabled(True)
            self.send_button.setText("Send")
            self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
            self.current_assistant_message = "" # Reset for next turn

    def _handle_streamed_chunk(self, chunk_content: str):
        """Handles a chunk of streamed content from Ollama."""
        self.current_assistant_message += chunk_content

        # Append the chunk to the QTextEdit. Using insertPlainText ensures it goes where the cursor is.
        # Since we moved cursor to end after assistant label, this effectively appends.
        # Replace newlines in chunk with <br> if needed for HTML, but insertPlainText handles plain text newlines.
        self.chat_display.insertPlainText(chunk_content.replace(chr(10), "\n")) # Ensure newlines are rendered.
        self.chat_display.ensureCursorVisible() # Keep the latest text visible

        if self.verbose_display:
            self.verbose_display.append_text(chunk_content)
            # self.verbose_display.ensureCursorVisible() # Not strictly needed for append_text if it auto-scrolls

        QApplication.processEvents() # Crucial for UI updates during stream

    def _save_current_conversation(self, user_prompt: str, assistant_response: str):
        """Helper method to save the current state of the conversation."""
        if not user_prompt and not assistant_response: # Avoid saving empty exchanges if any
            return

        user_message = {"role": "user", "content": user_prompt}
        assistant_message = {"role": "assistant", "content": assistant_response}

        # If it's a new chat (no ID yet), generate ID and start time
        if not self.current_conversation_id:
            self.current_conversation_id = str(uuid.uuid4())
            self.timestamp_start = datetime.now().isoformat()
            self.current_messages = [] # Ensure messages list is fresh for a new conversation
            print(f"New conversation started with ID: {self.current_conversation_id}")

        self.current_messages.append(user_message)
        self.current_messages.append(assistant_message)

        conversation_data = {
            "conversation_id": self.current_conversation_id,
            "model_name": self.current_selected_model_for_chat or "unknown_model",
            "timestamp_start": self.timestamp_start,
            "timestamp_last_exchange": datetime.now().isoformat(),
            "title": f"Chat with {self.current_selected_model_for_chat} at {self.timestamp_start.split('T')[0]}",
            "messages": self.current_messages, # Save all messages in this session
            "learned_summary": None,
            "tags": []
        }

        saved_path = save_conversation(conversation_data)
        if saved_path:
            print(f"Conversation progress saved to {saved_path}")
        else:
            print(f"Failed to save conversation for ID: {self.current_conversation_id}")


    def clear_chat(self):
        """Clears the chat display and resets internal conversation state."""
        self.chat_display.clear() # Clears the visual display
        self.current_messages = [] # Resets the internal message list
        self.current_conversation_id = None # Resets current conversation ID
        self.timestamp_start = None # Resets start timestamp
        self.current_assistant_message = "" # Reset accumulator for streamed response
        # Update any other UI elements if needed (e.g., title, status bar if you add one)
        self.selected_model_label.setText("Current Model: Not Selected") # Reset model display too
        print("Chat cleared, new session initiated.")


    def load_conversation_from_data(self, conversation_data):
        """
        Loads a conversation into the chat window from a dictionary.
        """
        self.clear_chat() # Start fresh

        self.current_conversation_id = conversation_data.get("conversation_id")
        self.timestamp_start = conversation_data.get("timestamp_start")
        # Ensure current_selected_model_for_chat is updated if possible,
        # or at least displayed.
        loaded_model_name = conversation_data.get("model_name", "Unknown Model")
        self.update_selected_model_display(loaded_model_name) # Update label

        self.chat_display.append(f"<i>Conversation loaded: {conversation_data.get('title', self.current_conversation_id)}</i>\n"
                                 f"<i>Model: {loaded_model_name}</i>\n---")

        for message in conversation_data.get("messages", []):
            role = message.get("role")
            content = message.get("content")
            # For loaded messages, we don't have original timestamps, so display without.
            # Or, if timestamps were saved in message dict, could use them.
            if role == "user":
                self.chat_display.append(f"<b style='color: #A9D18E;'>You:</b> {content}\n")
            elif role == "assistant":
                self.chat_display.append(f"<b style='color: #9BC2E6;'>{loaded_model_name}:</b> {content}\n")
            else: # Other roles like 'system'
                self.chat_display.append(f"<i style='color: #777;'>{role}: {content}</i>\n") # Use a neutral color for system
            self.current_messages.append(message) # Add to internal list for continued saving

        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
        print(f"Loaded conversation ID: {self.current_conversation_id}")


    def _start_new_chat_session(self): # Renamed clear_chat to this, more descriptive
        """Resets the chat for a new conversation."""
        # Optionally: ask user to save current one if it has messages
        self.clear_chat() # Use the new clear_chat method
        # Potentially update a title or status bar
        # Could also ask for a title for the new chat or generate one.

    def _save_current_conversation(self):
        if not self.current_messages: # No messages, nothing to save
            return

        # If it's a new chat (no ID yet), generate ID and start time
        if not self.current_conversation_id:
            self.current_conversation_id = str(uuid.uuid4())
            self.timestamp_start = datetime.now().isoformat()
            print(f"New conversation started with ID: {self.current_conversation_id}")


        conversation_data = {
            "conversation_id": self.current_conversation_id,
            "model_name": self.current_selected_model_for_chat or "unknown_model",
            "timestamp_start": self.timestamp_start,
            "timestamp_last_exchange": datetime.now().isoformat(),
            "title": f"Chat with {self.current_selected_model_for_chat} at {self.timestamp_start}", # Basic title
            "messages": self.current_messages,
            "learned_summary": None, # Placeholder
            "tags": [] # Placeholder
        }

        saved_path = save_conversation(conversation_data)
        if saved_path:
            print(f"Conversation progress saved to {saved_path}")
        else:
            print(f"Failed to save conversation for ID: {self.current_conversation_id}")
            # Optionally inform user via UI (e.g. status bar message)
            # self.statusBar().showMessage("Failed to save conversation.", 5000)


if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    # Mock generate_response for standalone testing
    original_generate_response = generate_response
    def mock_generate_response_func(model, prompt):
        # return f"Mocked response for '{prompt}' from model '{model}'."
        # return "" # Test empty response
        raise Exception("Test generation error") # Test error case

    # core.ollama_integration.generate_response = mock_generate_response_func # Uncomment to mock

    app = QApplication(sys.argv)
    widget = ChatWindowWidget()
    widget.update_selected_model_display("test_model:latest") # Simulate model selection
    widget.show()

    # core.ollama_integration.generate_response = original_generate_response # Restore

    sys.exit(app.exec())
