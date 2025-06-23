"""Simple usage example for the Multi-Agent Document Translator."""

import asyncio
from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))

from multi_agent_document_translator import orchestrator


async def main():
    """Simple example of using the multi-agent document translator."""
    
    print("🌐 Multi-Agent Document Translator - Simple Example")
    print("=" * 50)
    
    # Example document path (you'll need to provide your own)
    document_path = "sample_document.pdf"  # Replace with your document
    target_language = "es"  # Spanish
    source_language = "auto"  # Auto-detect
    
    # Check if document exists
    if not Path(document_path).exists():
        print(f"❌ Document not found: {document_path}")
        print("Please provide a valid document path in the script.")
        return
    
    try:
        # Initialize the system
        print("🚀 Initializing multi-agent system...")
        await orchestrator.initialize()
        
        # Get supported languages
        languages = await orchestrator.get_supported_languages()
        print(f"📋 Supported languages: {list(languages.keys())}")
        
        # Translate the document
        print(f"🔄 Translating document: {document_path}")
        print(f"🌐 Target language: {languages.get(target_language, target_language)}")
        
        result = await orchestrator.translate_document(
            document_path=document_path,
            target_language=target_language,
            source_language=source_language,
            output_path=f"translated_document_{target_language}.pdf"
        )
        
        if result['success']:
            print("✅ Translation completed successfully!")
            print(f"⏱️  Processing time: {result['processing_time']:.1f} seconds")
            print(f"📄 Pages translated: {result['page_count']}")
            
            # Quality assessment
            quality = result['validation']['quality_assessment']
            print(f"🎯 Quality grade: {quality['grade']}")
            print(f"📊 Overall score: {quality.get('overall_score', 0):.2f}")
            
            # Output files
            if result['output_files']:
                print("📁 Output files:")
                for file_path in result['output_files']:
                    if os.path.exists(file_path):
                        print(f"   • {file_path}")
            
            # Recommendations
            recommendations = result['validation'].get('recommendations', [])
            if recommendations:
                print("💡 Recommendations:")
                for rec in recommendations:
                    print(f"   • {rec}")
        
        else:
            print(f"❌ Translation failed: {result['error']}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    finally:
        # Cleanup
        print("🔄 Shutting down system...")
        await orchestrator.shutdown()
        print("✅ Done!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())

