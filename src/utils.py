def chunk_text(text, max_length=4000):
    """
    Chunks a given text into a list of strings, where each string is no longer than max_length characters.

    The method splits the text into paragraphs and then iterates over them, adding each paragraph to the current chunk.
    If the length of the current chunk plus the length of the current paragraph exceeds max_length, it appends the current
    chunk to the list of chunks and starts a new chunk with the current paragraph.

    The method returns a list of strings, where each string is a chunk of the original text, no longer than max_length characters.

    Parameters
    ----------
    text : str
        The text to be chunked
    max_length : int
        The maximum length of each chunk, in characters. Default is 4000 characters

    Returns
    -------
    list
        A list of strings, where each string is a chunk of the original text, no longer than max_length characters.
    """
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) <= max_length:
            current_chunk += paragraph + "\n\n"
        else:
            chunks.append(current_chunk)
            current_chunk = paragraph + "\n\n"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def parse_qa_response(response_text):
    """
    Parse the response from Gemini's generate_content API and extract the questions and answers.

    The response is expected to be in the following format:
    Question 1:
    Answer 1:
    Question 2:
    Answer 2:
    ...

    The function will split the response into lines and iterate over them,
    identifying the questions and answers based on the presence of "Question" or "Answer" keywords
    in the line.

    The function will return a list of dictionaries, each containing a question and its answer.
    """
    lines = response_text.split('\n')
    qa_pairs = []
    current_question = None
    current_answer = ""
    expecting_question = False  # Flag to track if the next line contains the question
    expecting_answer = False  # Flag to track if the next line contains the answer

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith(("Domanda", "Question", "Frage", "Pregunta", "Réponse")):
            # Save the previous question/answer pair
            if current_question:
                qa_pairs.append({"question": current_question, "answer": current_answer.strip()})

            # Check if the question is on the same line after ":"
            parts = line.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                current_question = parts[1].strip()  # Question on the same line
                expecting_question = False  # No need to wait for the next line
            else:
                expecting_question = True  # The next line will contain the question
                current_question = None

            current_answer = ""
            continue

        if expecting_question:
            # If we were expecting a question, the current line is the question
            current_question = line
            expecting_question = False
            continue

        if line.startswith(("Risposta", "Answer", "Antwort", "Respuesta", "Réponse")):
            # Save the previous question/answer pair if it exists
            if current_question and current_answer:
                qa_pairs.append({"question": current_question, "answer": current_answer.strip()})
                current_answer = ""

            # Check if the answer is on the same line after ":"
            parts = line.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                current_answer = parts[1].strip()  # Answer on the same line
                expecting_answer = False  # No need to wait for the next line
            else:
                expecting_answer = True  # The next line will contain the answer
                current_answer = ""

            continue

        if expecting_answer:
            # If we were expecting an answer, the current line is the answer
            current_answer = line
            expecting_answer = False
            continue

        # If it's not a new question or answer, append to the current answer
        if current_answer:
            current_answer += " " + line
        elif current_question:  # If we are in a question but haven't started the answer yet
            current_answer = line

    # Save the last question/answer pair
    if current_question:
        qa_pairs.append({"question": current_question, "answer": current_answer.strip()})

    return qa_pairs