# 📄 PDF Document Translator MCP Server

A powerful MCP (Model Context Protocol) server built with Gradio that translates PDF documents using AI vision models. Upload a PDF, select source and target languages, and get AI-powered translations of your documents.

## 🚀 Features

- **PDF to Image Conversion**: Automatically converts PDF pages to high-quality images
- **AI Vision OCR**: Extracts text from document images using state-of-the-art vision models
- **Multi-language Translation**: Supports 12+ languages including English, Spanish, French, German, Chinese, Japanese, and more
- **MCP Server**: Functions as both a web interface and MCP server for AI assistants
- **Hugging Face Integration**: Uses Hugging Face transformers for translation
- **Easy Deployment**: Ready for Hugging Face Spaces deployment

## 🛠️ How It Works

1. **Upload PDF**: Users upload a PDF document through the web interface
2. **Convert to Images**: PDF pages are converted to high-resolution images (300 DPI)
3. **Text Extraction**: AI vision models extract text from each page image
4. **Translation**: Extracted text is translated using specialized translation models
5. **Results**: Returns structured JSON with original and translated text for each page

## 🌍 Supported Languages

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)
- Arabic (ar)
- Hindi (hi)

## 🔧 Technical Stack

- **Gradio**: Web interface and MCP server framework
- **PyMuPDF**: PDF processing and conversion
- **Transformers**: Hugging Face models for vision and translation
- **PIL/Pillow**: Image processing
- **PyTorch**: Deep learning backend

## 🚀 Quick Start

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Access the web interface at `http://localhost:7860`
5. MCP server endpoint: `http://localhost:7860/gradio_api/mcp/sse`

### Hugging Face Spaces Deployment

1. Create a new Gradio Space on Hugging Face
2. Upload `app.py` and `requirements.txt`
3. The space will automatically build and deploy
4. Your MCP server will be available at: `https://your-username-space-name.hf.space/gradio_api/mcp/sse`

## 🤖 MCP Integration

This server can be used by AI assistants and applications that support the MCP protocol:

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pdf-translator": {
      "command": "npx",
      "args": [
        "mcp-remote", 
        "https://your-username-space-name.hf.space/gradio_api/mcp/sse"
      ]
    }
  }
}
```

### Direct MCP Usage

The server exposes a `document_translator` tool that accepts:
- `pdf_file`: PDF file to translate
- `source_language`: Source language code
- `target_language`: Target language code

Returns structured JSON with translation results for each page.

## 📝 Example Usage

### Web Interface
1. Upload a PDF document
2. Select source language (e.g., "English")
3. Select target language (e.g., "Spanish")
4. Click submit to get translations

### MCP Tool Call
```json
{
  "tool": "document_translator",
  "arguments": {
    "pdf_file": "path/to/document.pdf",
    "source_language": "en",
    "target_language": "es"
  }
}
```

## 🔍 API Schema

The MCP server automatically generates a schema available at:
`http://localhost:7860/gradio_api/mcp/schema`

## 🛡️ Error Handling

The server includes comprehensive error handling for:
- Invalid PDF files
- Unsupported languages
- Model loading failures
- Network connectivity issues
- Image processing errors

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built following the [Hugging Face MCP Course](https://huggingface.co/learn/mcp-course)
- Uses Gradio's excellent MCP integration
- Powered by Hugging Face transformers and models

