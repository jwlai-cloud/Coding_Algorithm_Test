"""Run the Streamlit web interface for the Multi-Agent Document Translator."""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the Streamlit application."""
    
    print("🌐 Starting Multi-Agent Document Translator Web Interface")
    print("🔄 Press Ctrl+C to stop the application")
    
    # Get the path to the streamlit app
    app_path = Path(__file__).parent / "streamlit_app.py"
    
    try:
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(app_path),
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n🔄 Shutting down application...")
    except Exception as e:
        print(f"❌ Error running Streamlit: {str(e)}")

if __name__ == "__main__":
    main()

