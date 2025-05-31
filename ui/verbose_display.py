from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PyQt6.QtGui import QFont

class VerboseDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Use full space

        self.text_browser = QTextBrowser(self)
        self.text_browser.setObjectName("VerboseDisplayBrowser") # Object name for QSS
        self.text_browser.setReadOnly(True)

        # Monospace font for code/verbose output
        font = QFont("Monospace")
        # Alternative common monospaced fonts: "Courier New", "Consolas", "DejaVu Sans Mono"
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10) # Adjust size as needed
        self.text_browser.setFont(font)

        # Styling for dark theme (can also be controlled by global stylesheet)
        # self.text_browser.setStyleSheet("""
        #     QTextBrowser {
        #         background-color: #202020; /* Even darker for this display */
        #         color: #D0D0D0;
        #         border: 1px solid #303030;
        #         border-radius: 4px;
        #         padding: 5px;
        #     }
        # """)
        # The global stylesheet in main.py should cover most of this if specific selectors are used.

        layout.addWidget(self.text_browser)
        self.setLayout(layout)

    def append_text(self, text_chunk):
        """Appends a chunk of text to the display."""
        self.text_browser.append(text_chunk)
        # self.text_browser.verticalScrollBar().setValue(self.text_browser.verticalScrollBar().maximum()) # Auto-scroll

    def set_text(self, full_text):
        """Sets the entire content of the display."""
        self.text_browser.setPlainText(full_text) # Use setPlainText for simple text, or setHtml for HTML
        # self.text_browser.verticalScrollBar().setValue(self.text_browser.verticalScrollBar().maximum()) # Auto-scroll

    def clear_display(self):
        """Clears the display."""
        self.text_browser.clear()

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Apply a basic dark theme for standalone testing
    app.setStyleSheet("""
        QWidget { background-color: #2E2E2E; color: #E0E0E0; }
    """)

    widget = VerboseDisplayWidget()
    widget.setWindowTitle("Verbose Display Test")
    widget.setGeometry(100, 100, 600, 400)

    widget.set_text("This is the initial full text.\nIt uses a monospace font.\n\n")
    widget.append_text("This is an appended line.\n")
    widget.append_text("Another appended line with a number: 12345 and symbols: !@#$%^&*()_+")

    # Example of how it might look with code-like content
    widget.append_text("\n\n--- Example Code Block ---\n")
    widget.append_text("{\n  \"key\": \"value\",\n  \"number\": 42\n}")

    widget.show()
    sys.exit(app.exec())
