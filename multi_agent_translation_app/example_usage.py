"""Example usage of the Multi-Agent Document Translation App."""

import asyncio
import os
from pathlib import Path

from agents import OrchestratorAgent
from config.settings import settings
from utils import GCSHelper


async def example_translation():
    """Example of how to use the translation system."""
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent()
    gcs_helper = GCSHelper()
    
    print("🚀 Multi-Agent Document Translation Example")
    print("=" * 50)
    
    try:
        # Start orchestrator
        await orchestrator.start()
        print("✅ Orchestrator started")
        
        # Example translation request
        translation_request = {
            "document_path": "gs://your-bucket/sample-document.pdf",
            "target_language": "es",
            "source_language": "auto",
            "job_id": "example_job_001"
        }
        
        print(f"📄 Processing document: {translation_request['document_path']}")
        print(f"🌍 Target language: {translation_request['target_language']}")
        
        # Process translation
        result = await orchestrator.process(translation_request)
        
        if result.success:
            print("\n✅ Translation completed successfully!")
            print(f"📊 Job ID: {result.data['job_id']}")
            print(f"📈 Status: {result.data['status']}")
            print(f"📑 Pages processed: {result.data['pages_processed']}")
            print(f"🔄 Pages translated: {result.data['pages_translated']}")
            print(f"⭐ Overall quality score: {result.data['overall_quality_score']:.3f}")
            
            if result.data.get('output_document'):
                print(f"📁 Output document: {result.data['output_document']}")
                
            # Display individual quality scores
            if result.data.get('individual_quality_scores'):
                print("\n📊 Individual page quality scores:")
                for i, score in enumerate(result.data['individual_quality_scores'], 1):
                    print(f"   Page {i}: {score:.3f}")
                    
        else:
            print(f"\n❌ Translation failed: {result.error}")
            
    except Exception as e:
        print(f"\n💥 Error occurred: {str(e)}")
        
    finally:
        await orchestrator.stop()
        print("\n🛑 Orchestrator stopped")


async def example_with_local_file():
    """Example using a local file."""
    
    print("\n" + "=" * 50)
    print("📁 Local File Translation Example")
    print("=" * 50)
    
    # Check if example file exists
    example_file = Path("example_document.pdf")
    
    if not example_file.exists():
        print("⚠️  Example file 'example_document.pdf' not found")
        print("   Please place a PDF file named 'example_document.pdf' in the current directory")
        return
        
    try:
        # Upload file to GCS first
        gcs_helper = GCSHelper()
        
        print(f"📤 Uploading {example_file.name} to GCS...")
        gcs_path = f"{settings.GCS_INPUT_FOLDER}/{example_file.name}"
        document_uri = gcs_helper.upload_file(str(example_file), gcs_path)
        print(f"✅ Uploaded to: {document_uri}")
        
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        await orchestrator.start()
        
        # Process translation
        translation_request = {
            "document_path": document_uri,
            "target_language": "fr",  # Translate to French
            "source_language": "auto",
            "job_id": f"local_file_{int(asyncio.get_event_loop().time())}"
        }
        
        print(f"🔄 Starting translation to French...")
        result = await orchestrator.process(translation_request)
        
        if result.success:
            print("✅ Local file translation completed!")
            print(f"📊 Quality score: {result.data['overall_quality_score']:.3f}")
        else:
            print(f"❌ Translation failed: {result.error}")
            
        await orchestrator.stop()
        
    except Exception as e:
        print(f"💥 Error with local file: {str(e)}")


def print_system_info():
    """Print system configuration information."""
    
    print("\n" + "=" * 50)
    print("⚙️  System Configuration")
    print("=" * 50)
    
    print(f"🌐 Google Cloud Project: {settings.GOOGLE_CLOUD_PROJECT or 'Not configured'}")
    print(f"🪣 GCS Bucket: {settings.GCS_BUCKET_NAME}")
    print(f"🖼️  Image DPI: {settings.IMAGE_DPI}")
    print(f"🔄 Max Retries: {settings.MAX_RETRIES}")
    print(f"⭐ Min Quality Score: {settings.MIN_QUALITY_SCORE}")
    print(f"🗣️  Supported Languages: {', '.join(settings.SUPPORTED_LANGUAGES)}")
    
    # Check if credentials are configured
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("✅ Google Cloud credentials configured")
    else:
        print("⚠️  Google Cloud credentials not found")
        print("   Set GOOGLE_APPLICATION_CREDENTIALS environment variable")


async def main():
    """Main example function."""
    
    print_system_info()
    
    # Check if Google Cloud is configured
    if not settings.GOOGLE_CLOUD_PROJECT:
        print("\n❌ Google Cloud Project not configured")
        print("   Please set GOOGLE_CLOUD_PROJECT environment variable")
        return
        
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("\n❌ Google Cloud credentials not configured")
        print("   Please set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        return
    
    # Run examples
    print("\n🎯 Choose an example to run:")
    print("1. Basic translation example (requires GCS document)")
    print("2. Local file translation example")
    print("3. Both examples")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        await example_translation()
    elif choice == "2":
        await example_with_local_file()
    elif choice == "3":
        await example_translation()
        await example_with_local_file()
    else:
        print("Invalid choice. Running basic example...")
        await example_translation()
    
    print("\n🎉 Example completed!")


if __name__ == "__main__":
    asyncio.run(main())

