"""Run the FastAPI server for the Multi-Agent Document Translator."""

import uvicorn
from config import settings

if __name__ == "__main__":
    print("🚀 Starting Multi-Agent Document Translator API")
    print(f"📡 Server will run on http://{settings.api_host}:{settings.api_port}")
    print("📖 API documentation available at http://localhost:8000/docs")
    print("🔄 Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )

