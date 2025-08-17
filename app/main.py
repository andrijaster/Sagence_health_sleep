"""
Main entry point for Sleep Consultation AI API
Run with: python -m app.main or uvicorn app.main:app
"""

from app.api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)