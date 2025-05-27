import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog, QComboBox,
                             QTextEdit, QMessageBox, QProgressBar)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from dotenv import load_dotenv

from gemini_processor import GeminiProcessor


class PDFQAGenerator(QMainWindow):
    def __init__(self):
        """
        Initializes the main window of the PDF Q&A Generator application.

        This constructor initializes the main window's title, sets its minimum
        size to 800x600, and calls the `init_ui` method to set up the user
        interface.
        """
        super().__init__()
        self.setWindowTitle("PDF Q&A Generator with Gemini")
        self.setMinimumSize(800, 600)
        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface of the main window.

        This method sets up the main layout of the window by creating a vertical
        layout (QVBoxLayout) and adding various widgets to it. The widgets
        include labels, text edits, buttons, and a progress bar. The method also
        initializes the QA pairs list as an empty list.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Show API Key info
        api_layout = QHBoxLayout()
        api_status_label = QLabel("Gemini API Status:")
        api_status = "✅ API key found" if os.getenv("API_KEY") else "❌ API key missing in .env file"
        self.api_status_label = QLabel(api_status)
        api_layout.addWidget(api_status_label)
        api_layout.addWidget(self.api_status_label)
        main_layout.addLayout(api_layout)

        # Input file selection section
        input_layout = QHBoxLayout()
        input_label = QLabel("Input PDF file:")
        self.input_path = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_input_file)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(browse_button)
        main_layout.addLayout(input_layout)

        # Output file section
        output_layout = QHBoxLayout()
        output_label = QLabel("Output PDF file:")
        self.output_path = QLineEdit("questions_answers.pdf")
        browse_output_button = QPushButton("Browse")
        browse_output_button.clicked.connect(self.browse_output_file)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_output_button)
        main_layout.addLayout(output_layout)

        # Language selection
        language_layout = QHBoxLayout()
        language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Italian", "Français", "Español", "Deutsch"])
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        main_layout.addLayout(language_layout)

        # Preview area for results
        preview_label = QLabel("Results Preview:")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        main_layout.addWidget(preview_label)
        main_layout.addWidget(self.preview_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate PDF Q&A")
        self.generate_button.clicked.connect(self.generate_qa_pdf)
        button_layout.addWidget(self.generate_button)
        main_layout.addLayout(button_layout)

        # Initialize the list to store Q&A pairs
        self.qa_pairs = []

    def browse_input_file(self):
        """
        Prompts the user to select an input PDF file via a file dialog.
        Sets the input path and updates the output path to the same directory as the input by default.

        :return: None
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input PDF", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.input_path.setText(file_path)
            # Set the output file in the same directory as the input by default
            input_dir = os.path.dirname(file_path)
            default_output = os.path.join(input_dir, "questions_answers.pdf")
            self.output_path.setText(default_output)

    def browse_output_file(self):
        """
        Prompts the user to select an output PDF file via a file dialog.
        Determines the initial directory to be the same as the input file's directory if available.
        Sets the output path to the selected file path.

        :return: None
        """
        input_path = self.input_path.text()
        initial_dir = os.path.dirname(input_path) if input_path else ""

        # Get the current file name to use as default
        current_name = os.path.basename(self.output_path.text()) if self.output_path.text() else "questions_answers.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF as", os.path.join(initial_dir, current_name), "PDF Files (*.pdf)"
        )
        if file_path:
            # Ensure it has the .pdf extension
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            self.output_path.setText(file_path)

    def generate_qa_pdf(self):
        """
        Trigger the generation of the PDF Q&A file.

        This method is connected to the Generate PDF Q&A button in the main window.
        It checks if the input PDF path is valid and if the Gemini API key is available.
        If these checks pass, it starts the processing of the PDF in a separate thread
        using GeminiProcessor and updates the progress bar and preview area as necessary.

        :return: None
        """
        input_path = self.input_path.text()

        if not input_path:
            QMessageBox.warning(self, "Attention", "Select an input PDF file.")
            return

        if not os.getenv("API_KEY"):
            QMessageBox.warning(self, "Attention",
                                "Gemini API Key not found in the .env file. Add API_KEY=your_key in the .env file.")
            return

        # Disable the button during processing
        self.generate_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.preview_text.clear()

        # Start the process in a separate thread
        self.worker = GeminiProcessor(
            input_path,
            self.language_combo.currentText()
        )

        self.worker.progress_update.connect(self.update_progress)
        self.worker.processing_complete.connect(self.create_output_pdf)
        self.worker.error_occurred.connect(self.show_error)

        self.worker.start()

    def update_progress(self, value):
        """
        Updates the progress bar with the given value.

        This slot is connected to the `progress_update` signal of the GeminiProcessor
        and is called whenever the processor updates its progress.

        :param int value: A value between 0 and 100 to update the progress bar.
        """
        self.progress_bar.setValue(value)
        self.progress_bar.setValue(value)

    def show_error(self, error_message):
        """
        Displays an error message box with the given error message.
        Re-enables the "Generate" button.

        :param str error_message: The error message to be displayed.
        """
        QMessageBox.critical(self, "Error", error_message)
        self.generate_button.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)
        self.generate_button.setEnabled(True)

    def create_output_pdf(self, qa_pairs):
        """
        Creates a PDF document with the given QA pairs and saves it to the output path.

        If the QA pairs list is empty, shows a warning message box and re-enables the "Generate" button.

        Otherwise, creates a SimpleDocTemplate PDF document with the given QA pairs formatted as title, question and answer.
        The title is centered and in a larger font size, the questions are in a smaller font size, left-indented and bold, and the answers are plain text with a smaller font size.
        The document is saved to the output path and a success message box is shown.

        If an error occurs while creating the PDF, shows an error message box with the error message and re-enables the "Generate" button.

        :param list qa_pairs: A list of QA pairs to be written to the PDF document.
        """
        if not qa_pairs:
            QMessageBox.warning(self, "Attention", "No questions and answers generated.")
            self.generate_button.setEnabled(True)
            return

        try:
            output_path = self.output_path.text()
            if not output_path.lower().endswith('.pdf'):
                output_path += '.pdf'

            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Create the PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()

            # Customize styles
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.darkblue,
                spaceAfter=12
            )

            question_style = ParagraphStyle(
                'QuestionStyle',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.darkblue,
                spaceBefore=10,
                spaceAfter=6,
                alignment=4
            )

            answer_style = ParagraphStyle(
                'AnswerStyle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=12,
                leftIndent=20,
                alignment=4
            )

            # Build content
            content = []

            # Add title
            language_title = {
                "Italian": "Domande e Risposte",
                "English": "Questions and Answers",
                "Français": "Questions et Réponses",
                "Español": "Preguntas y Respuestas",
                "Deutsch": "Fragen und Antworten"
            }.get(self.language_combo.currentText(), "Domande e Risposte")

            content.append(Paragraph(language_title, title_style))
            content.append(Spacer(1, 12))

            # Preview in TextEdit
            self.preview_text.clear()

            # Add question/answer pairs
            for i, qa in enumerate(qa_pairs, 1):
                # Format question text
                question_text = f"{i}. {qa['question']}"
                content.append(Paragraph(question_text, question_style))

                # Format answer text
                answer_text = qa['answer']
                content.append(Paragraph(answer_text, answer_style))

                # Add to preview
                self.preview_text.append(question_text)
                self.preview_text.append(answer_text)
                self.preview_text.append("\n")

            # Generate the PDF
            doc.build(content)

            QMessageBox.information(
                self,
                "Operation completed",
                f"PDF file successfully generated: {output_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error creating the PDF: {str(e)}"
            )

        finally:
            self.generate_button.setEnabled(True)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(dotenv_path="../.env")
    app = QApplication(sys.argv)
    window = PDFQAGenerator()
    window.show()
    sys.exit(app.exec())