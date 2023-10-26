from flask_login import UserMixin
from flask_sqlalchemy.model import Model
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# Define the database model
Base = declarative_base()


class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    folders = relationship('Folder', backref='user', lazy=True)

    def __init__(self, username, password):
        self.username = username
        self.set_password(password)  # Hash the password when initializing

    def set_password(self, password):
        # Hash the password using sha256
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        # Check if the provided password matches the hashed password
        return check_password_hash(self.password, password)

    def get_id(self):
        return str(self.id)


class Folder(Base, Model):
    __tablename__ = 'folders'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    color = Column(String(10))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    full_access = Column(Boolean, default=False)  # to determine if users can modify/delete a folder or not
    latest_score = Column(Integer, default=-1)
    flashcards = relationship('Flashcard', backref='folder', lazy=True)

    def __init__(self, name, color, user, full_access=False):
        self.name = name
        self.color = color
        self.user_id = user
        self.full_access = full_access


class Flashcard(Base, Model):
    __tablename__ = 'flashcards'

    id = Column(Integer, primary_key=True)
    question = Column(String(200), nullable=False)
    answer = Column(String(200), nullable=False)
    attempts = Column(Integer, default=0)  # to track the number of attempts
    folder_id = Column(Integer, ForeignKey('folders.id'), nullable=False)

    def __init__(self, folder_id, question, answer):
        self.question = question
        self.answer = answer
        self.folder_id = folder_id


# Create a database engine
engine = create_engine(f'sqlite:///mydb.db')
# Drop the existing tables if they exist
# Base.metadata.drop_all(engine)
# Create the database tables
Base.metadata.create_all(engine)
# Create a session
Session = sessionmaker(bind=engine)
session = Session()
