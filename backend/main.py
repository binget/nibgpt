from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {
        "application": "NIBGPT",
        "status": "Running",
        "version": "1.0"
    }
