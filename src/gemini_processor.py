from PyQt6.QtCore import QThread, pyqtSignal
import time
import os
import fitz  # PyMuPDF
import google.generativeai as genai

from utils import chunk_text, parse_qa_response


class GeminiProcessor(QThread):
    progress_update = pyqtSignal(int)
    processing_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, pdf_path, language):
        """
        Initializes a GeminiProcessor object.

        Parameters
        ----------
        pdf_path : str
            Path to the PDF file to be processed
        language : str
            Language of the PDF file. Currently, the supported languages are English, French, German, Italian and Spanish.

        Attributes
        ----------
        pdf_path : str
            Path to the PDF file to be processed
        language : str
            Language of the PDF file
        api_key : str
            Gemini API key
        qa_pairs : list
            List of dictionaries containing questions and their corresponding answers
        """
        super().__init__()
        self.pdf_path = pdf_path
        self.language = language
        self.api_key = os.getenv("API_KEY")
        self.qa_pairs = []

    def run(self):
        """
        This method is automatically called when the thread is started.
        It's responsible for processing the PDF file and generating the questions and answers.

        The method is blocking and should not be called from the main thread.
        It communicates with the main thread using signals.

        :raises Exception: If an exception occurs during processing, it is caught and
            emitted as an error message using the error_occurred signal.
        """
        global response
        try:
            # Check if the API key is available
            if not self.api_key:
                self.error_occurred.emit(
                    "Gemini API key not found in .env file. Add API_KEY=your_key in the .env file.")
                return

            # Configure Gemini API
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(os.getenv("GEMINI_MODEL"))

            # Extract text from the PDF
            text_content = self.extract_text_from_pdf(self.pdf_path)
            if not text_content:
                self.error_occurred.emit("Unable to extract text from the PDF or the file is empty.")
                return

            # Split text into manageable chunks (based on token length)
            chunks = chunk_text(text_content, max_length=4000)

            language_prompt = {
                "Italiano": "in italiano",
                "English": "in English",
                "Français": "en français",
                "Español": "en español",
                "Deutsch": "auf Deutsch"
            }.get(self.language, "in italiano")

            # Process each text chunk
            for i, chunk in enumerate(chunks):
                prompt = f"""
                Analyze the following text and generate 2 possible questions that a professor might ask,
                along with their answers {language_prompt}.
                Format the questions and answers clearly (Question 1:, Answer 1:, etc).

                Text to analyze:
                {chunk}
                """

                retries = 3
                wait_time = 1
                for attempt in range(retries):
                    try:
                        response = model.generate_content(prompt)
                        break
                    except Exception as e:
                        if "429" in str(e):
                            print(f"Quota exceeded. Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            wait_time += 1
                        else:
                            raise e

                qa_text = response.text.replace('*', '')
                qa_section = parse_qa_response(qa_text)
                self.qa_pairs.extend(qa_section)

                progress = int((i + 1) / len(chunks) * 100)
                self.progress_update.emit(progress)

            self.processing_complete.emit(self.qa_pairs)

        except Exception as e:
            self.error_occurred.emit(f"Error during processing: {str(e)}")

    def extract_text_from_pdf(self, pdf_path):
        """
        Extracts text from a PDF file.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            str: The extracted text from the PDF file

        Raises:
            Exception: If there is an error extracting text from the PDF file
        """
        full_text = ""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                full_text += page.get_text()
            return full_text
        except Exception as e:
            self.error_occurred.emit(f"Error extracting text from PDF: {str(e)}")
            return ""
