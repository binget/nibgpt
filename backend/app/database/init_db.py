from app.database.session import Base, engine
from app.models import User
from app import models

def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialize_database()
    print("NIBGPT database tables created successfully.")
