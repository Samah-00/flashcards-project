from models import Folder


def get_folder_and_flashcards(folder_id, session):
    folder = session.query(Folder).get(folder_id)
    flashcards = folder.flashcards if folder else []
    return folder, flashcards


def fetch_flashcards_data(flashcards):
    return [{"id": card.id, "question": card.question, "answer": card.answer, "attempts": card.attempts}
            for card in flashcards]

