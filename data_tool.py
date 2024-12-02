import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QListWidget, QLineEdit, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtCore import Qt


class ChatDatasetTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Dataset Creator")
        self.resize(800, 600)

        # Role toggle: starts with "user"
        self.current_role = "user"
        self.chat_data = []

        # Main layout
        main_layout = QHBoxLayout()

        # Left: Message list
        self.message_list = QListWidget()
        self.message_list.setFixedWidth(200)
        self.message_list.setFocusPolicy(Qt.StrongFocus)
        self.message_list.keyPressEvent = self.handle_keypress  # Override key press
        main_layout.addWidget(self.message_list)

        # Right: Chat and Input
        right_layout = QVBoxLayout()

        # Chat history display
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        right_layout.addWidget(self.chat_history)

        # Input layout
        input_layout = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.returnPressed.connect(self.handle_send)  # Enter key triggers send
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send)  # Send button triggers send
        input_layout.addWidget(self.send_button)

        right_layout.addLayout(input_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        # Load existing data and update the UI
        self.data_dir = "train/messages/"
        self.finetuning_file = "train/finetuning.jsonl"
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.finetuning_file), exist_ok=True)

        self.load_existing_data()
        self.update_message_list()

    def closeEvent(self, event):
        """Merge all conversation files when the application closes."""
        self.merge_conversations()
        event.accept()  # Proceed with the close event

    def load_existing_data(self):
        self.chat_data = []
        for file in sorted(os.listdir(self.data_dir)):
            if file.endswith(".jsonl"):
                with open(os.path.join(self.data_dir, file), 'r', encoding='utf-8') as f:
                    self.chat_data.extend(json.loads(line) for line in f)
        self.update_message_list()

    def update_message_list(self):
        self.message_list.clear()
        for idx, entry in enumerate(self.chat_data):
            item = QListWidgetItem(f"Conversation {idx + 1}")
            item.setData(Qt.UserRole, idx)  # Store the index
            self.message_list.addItem(item)
        self.message_list.currentRowChanged.connect(self.display_messages)

    def display_messages(self, index):
        if index < 0 or index >= len(self.chat_data):
            return
        messages = self.chat_data[index]["messages"]
        self.chat_history.clear()
        for msg in messages:
            self.append_message(msg["role"], msg["content"])

    def append_message(self, role, content):
        color = QColor(255, 228, 228) if role == "user" else QColor(228, 241, 255)

        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_history.setTextCursor(cursor)

        self.chat_history.setTextBackgroundColor(color)
        self.chat_history.insertPlainText(f"{role.capitalize()}: {content}\n")
        self.chat_history.setTextBackgroundColor(QColor(255, 255, 255))

    def handle_send(self):
        text = self.input_field.text().strip()
        if not text or text.lower() == "stop":
            self.start_new_conversation()
            return

        self.add_message(self.current_role, text)

        # Toggle role for next input
        self.current_role = "assistant" if self.current_role == "user" else "user"
        self.input_field.clear()

    def start_new_conversation(self):
        self.current_role = "user"
        self.chat_data.append({"messages": []})
        self.save_current_conversation()
        self.input_field.clear()
        self.chat_history.clear()
        self.update_message_list()

    def add_message(self, role, content):
        if not self.chat_data or "messages" not in self.chat_data[-1]:
            self.chat_data.append({"messages": []})

        self.chat_data[-1]["messages"].append({"role": role, "content": content})
        self.save_current_conversation()
        self.update_message_list()
        self.display_messages(len(self.chat_data) - 1)

    def save_current_conversation(self):
        if not self.chat_data:
            return

        filename = os.path.join(self.data_dir, f"conversation_{len(self.chat_data)}.jsonl")
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(self.chat_data[-1], file, ensure_ascii=False)
            file.write('\n')

    def merge_conversations(self):
        with open(self.finetuning_file, 'w', encoding='utf-8') as outfile:
            for file in sorted(os.listdir(self.data_dir)):
                if file.endswith(".jsonl"):
                    with open(os.path.join(self.data_dir, file), 'r', encoding='utf-8') as infile:
                        for line in infile:
                            outfile.write(line)

    def handle_keypress(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_selected_conversation()
        else:
            super(QListWidget, self.message_list).keyPressEvent(event)

    def delete_selected_conversation(self):
        current_item = self.message_list.currentItem()
        if not current_item:
            return

        conversation_index = current_item.data(Qt.UserRole)
        confirmation = QMessageBox.question(
            self, "Delete Conversation", "Are you sure you want to delete this conversation?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            # Remove conversation file
            filename = os.path.join(self.data_dir, f"conversation_{conversation_index + 1}.jsonl")
            if os.path.exists(filename):
                os.remove(filename)

            # Remove from data and UI
            del self.chat_data[conversation_index]
            self.update_message_list()
            self.chat_history.clear()

            # Renumber the remaining conversation files
            self.renumber_files()

    def renumber_files(self):
        """Renumber conversation files to maintain consistent numbering."""
        for idx, entry in enumerate(self.chat_data):
            filename = os.path.join(self.data_dir, f"conversation_{idx + 1}.jsonl")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(entry, file, ensure_ascii=False)
                file.write('\n')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatDatasetTool()
    window.show()
    sys.exit(app.exec_())