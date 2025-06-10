"""
Sample usage examples for the PDF Document Translator MCP Server
"""

import requests
import json

# Example 1: Using the MCP server programmatically
def test_mcp_server():
    """Test the MCP server functionality"""
    
    # MCP server endpoint (adjust URL as needed)
    mcp_endpoint = "http://localhost:7860/gradio_api/mcp/sse"
    
    # Example MCP request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "document_translator",
            "arguments": {
                "pdf_file": "path/to/your/document.pdf",
                "source_language": "en",
                "target_language": "es"
            }
        }
    }
    
    print("MCP Request Example:")
    print(json.dumps(mcp_request, indent=2))

# Example 2: Claude Desktop configuration
def claude_desktop_config():
    """Example Claude Desktop configuration"""
    
    config = {
        "mcpServers": {
            "pdf-translator": {
                "command": "npx",
                "args": [
                    "mcp-remote",
                    "https://your-username-pdf-translator.hf.space/gradio_api/mcp/sse"
                ]
            }
        }
    }
    
    print("Claude Desktop Configuration:")
    print(json.dumps(config, indent=2))

# Example 3: Language codes reference
def language_codes():
    """Reference for supported language codes"""
    
    languages = {
        "en": "English",
        "es": "Spanish", 
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "ar": "Arabic",
        "hi": "Hindi"
    }
    
    print("Supported Language Codes:")
    for code, name in languages.items():
        print(f"  {code}: {name}")

# Example 4: Expected response format
def response_format():
    """Example of expected response format"""
    
    example_response = {
        "total_pages": 2,
        "source_language": "en",
        "target_language": "es",
        "pages": [
            {
                "page_number": 1,
                "original_text": "Hello, this is a sample document.",
                "translated_text": "Hola, este es un documento de muestra.",
                "status": "completed"
            },
            {
                "page_number": 2,
                "original_text": "This is the second page.",
                "translated_text": "Esta es la segunda página.",
                "status": "completed"
            }
        ]
    }
    
    print("Expected Response Format:")
    print(json.dumps(example_response, indent=2))

if __name__ == "__main__":
    print("=== PDF Document Translator MCP Server Examples ===\n")
    
    test_mcp_server()
    print("\n" + "="*50 + "\n")
    
    claude_desktop_config()
    print("\n" + "="*50 + "\n")
    
    language_codes()
    print("\n" + "="*50 + "\n")
    
    response_format()

