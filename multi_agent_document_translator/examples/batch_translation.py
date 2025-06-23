"""Batch translation example for multiple documents."""

import asyncio
from pathlib import Path
import sys
import os
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))

from multi_agent_document_translator import orchestrator


async def translate_batch(documents: List[str], target_language: str, 
                         source_language: str = "auto") -> List[Dict[str, Any]]:
    """Translate multiple documents in batch."""
    
    results = []
    
    print(f"🚀 Starting batch translation of {len(documents)} documents")
    print(f"🌐 Target language: {target_language}")
    print("=" * 60)
    
    # Initialize system once
    await orchestrator.initialize()
    
    for i, doc_path in enumerate(documents, 1):
        print(f"\n📄 Processing document {i}/{len(documents)}: {Path(doc_path).name}")
        
        if not Path(doc_path).exists():
            print(f"❌ Document not found: {doc_path}")
            results.append({
                'document': doc_path,
                'success': False,
                'error': 'File not found'
            })
            continue
        
        try:
            # Create output path
            doc_name = Path(doc_path).stem
            output_path = f"batch_output/translated_{doc_name}_{target_language}.pdf"
            
            # Ensure output directory exists
            Path("batch_output").mkdir(exist_ok=True)
            
            # Translate document
            result = await orchestrator.translate_document(
                document_path=doc_path,
                target_language=target_language,
                source_language=source_language,
                output_path=output_path
            )
            
            if result['success']:
                print(f"✅ Completed in {result['processing_time']:.1f}s")
                quality = result['validation']['quality_assessment']
                print(f"🎯 Quality: {quality['grade']} ({quality.get('overall_score', 0):.2f})")
                
                results.append({
                    'document': doc_path,
                    'success': True,
                    'processing_time': result['processing_time'],
                    'page_count': result['page_count'],
                    'quality_grade': quality['grade'],
                    'quality_score': quality.get('overall_score', 0),
                    'output_files': result['output_files']
                })
            else:
                print(f"❌ Failed: {result['error']}")
                results.append({
                    'document': doc_path,
                    'success': False,
                    'error': result['error']
                })
        
        except Exception as e:
            print(f"❌ Error processing {doc_path}: {str(e)}")
            results.append({
                'document': doc_path,
                'success': False,
                'error': str(e)
            })
    
    return results


async def main():
    """Batch translation example."""
    
    print("🌐 Multi-Agent Document Translator - Batch Processing Example")
    print("=" * 60)
    
    # Example documents (replace with your actual documents)
    documents = [
        "document1.pdf",
        "document2.pdf", 
        "document3.docx"
    ]
    
    # Check which documents exist
    existing_docs = [doc for doc in documents if Path(doc).exists()]
    
    if not existing_docs:
        print("❌ No documents found. Please add some documents to translate.")
        print("Expected documents:")
        for doc in documents:
            print(f"   • {doc}")
        return
    
    print(f"📋 Found {len(existing_docs)} documents to translate:")
    for doc in existing_docs:
        print(f"   • {doc}")
    
    # Translation settings
    target_language = "es"  # Spanish
    source_language = "auto"
    
    try:
        # Perform batch translation
        results = await translate_batch(existing_docs, target_language, source_language)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 BATCH TRANSLATION SUMMARY")
        print("=" * 60)
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        
        if successful:
            total_time = sum(r['processing_time'] for r in successful)
            total_pages = sum(r['page_count'] for r in successful)
            avg_quality = sum(r['quality_score'] for r in successful) / len(successful)
            
            print(f"⏱️  Total processing time: {total_time:.1f} seconds")
            print(f"📄 Total pages translated: {total_pages}")
            print(f"🎯 Average quality score: {avg_quality:.2f}")
            
            print("\n📁 Output files:")
            for result in successful:
                doc_name = Path(result['document']).name
                print(f"   • {doc_name} → {result['quality_grade']}")
                for output_file in result.get('output_files', []):
                    if os.path.exists(output_file):
                        print(f"     📄 {output_file}")
        
        if failed:
            print("\n❌ Failed documents:")
            for result in failed:
                doc_name = Path(result['document']).name
                print(f"   • {doc_name}: {result['error']}")
    
    except Exception as e:
        print(f"❌ Batch processing error: {str(e)}")
    
    finally:
        # Cleanup
        print("\n🔄 Shutting down system...")
        await orchestrator.shutdown()
        print("✅ Batch processing complete!")


if __name__ == "__main__":
    # Run the batch translation example
    asyncio.run(main())

