import time
import openai


def generate_questions_and_answers(text):
    # Initialize an empty list to store question-answer pairs
    qa_pairs = []

    # Split the generated questions by newline character
    questions = generate_questions(text).split('\n')

    # Iterate through the generated questions
    for question in questions:
        if question.strip():
            # Create a prompt that includes both the question and the text
            prompt = f"Question: {question}\nText: {text}\nAnswer:"

            # Generate an answer for the question
            answer = generate_answer(prompt)

            # Add the question-answer pair to the list
            qa_pairs.append((question.strip(), answer.strip()))

    return qa_pairs


def generate_questions(text):
    # Define the prompt for generating questions
    prompt = f"Create questions from the following text, each question in a separate line: '{text}'"

    # Generate questions using GPT-3
    response = None
    while not response:
        try:
            response = openai.Completion.create(
                prompt=prompt,
                model='text-davinci-003',
                max_tokens=3000,
            )
        except openai.error.RateLimitError:
            print("Rate limit exceeded. Waiting for 60 seconds...")
            time.sleep(60)  # Wait for 60 seconds before making the next request

    # Extract and format the generated questions
    questions = response.choices[0].text.strip()
    return questions


def generate_answer(prompt):
    # Generate an answer for the question using GPT-3
    response = None
    while not response:
        try:
            response = openai.Completion.create(
                prompt=prompt,
                model='text-davinci-003',
                max_tokens=3000,
                stop='\n',  # Stop at newline character to separate answers
            )
        except openai.error.RateLimitError:
            print("Rate limit exceeded. Waiting for 60 seconds...")
            time.sleep(60)  # Wait for 60 seconds before making the next request

    # Extract and format the generated answer
    answer = response.choices[0].text.strip()

    return answer
