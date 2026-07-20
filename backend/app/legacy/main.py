from fastapi import FastAPI

app = FastAPI(
    title="AMF API",
    description="AI-Based Furniture Material & Cost Estimator",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "Welcome to the AMF Backend API!",
        "status": "Running Successfully"
    }