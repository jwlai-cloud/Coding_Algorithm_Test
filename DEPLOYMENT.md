# 🚀 Deployment Guide for PDF Document Translator MCP Server

This guide covers how to deploy your PDF Document Translator MCP Server to Hugging Face Spaces and other platforms.

## 📋 Prerequisites

- Hugging Face account
- Git installed locally
- Python 3.8+ for local testing

## 🤗 Hugging Face Spaces Deployment

### Method 1: Web Interface (Recommended for beginners)

1. **Create a New Space**
   - Go to [huggingface.co/spaces](https://huggingface.co/spaces)
   - Click "Create new Space"
   - Choose a name (e.g., `pdf-document-translator`)
   - Select "Gradio" as the SDK
   - Choose "Public" or "Private" visibility
   - Click "Create Space"

2. **Upload Files**
   - Upload `app.py` (main application file)
   - Upload `requirements.txt` (dependencies)
   - Upload `README.md` (documentation)
   - Upload `config.json` (space configuration)

3. **Wait for Build**
   - Hugging Face will automatically build your space
   - Check the "Logs" tab for build progress
   - Build typically takes 3-5 minutes

4. **Access Your Space**
   - Web interface: `https://huggingface.co/spaces/YOUR_USERNAME/pdf-document-translator`
   - MCP endpoint: `https://YOUR_USERNAME-pdf-document-translator.hf.space/gradio_api/mcp/sse`

### Method 2: Git Repository

1. **Clone Your Space Repository**
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/pdf-document-translator
   cd pdf-document-translator
   ```

2. **Add Your Files**
   ```bash
   cp /path/to/your/app.py .
   cp /path/to/your/requirements.txt .
   cp /path/to/your/README.md .
   cp /path/to/your/config.json .
   ```

3. **Commit and Push**
   ```bash
   git add .
   git commit -m "Initial deployment of PDF Document Translator MCP Server"
   git push
   ```

## 🔧 Configuration Files

### config.json (Space Configuration)
```json
{
  "title": "PDF Document Translator MCP Server",
  "emoji": "📄",
  "colorFrom": "blue",
  "colorTo": "green",
  "sdk": "gradio",
  "sdk_version": "4.44.0",
  "app_file": "app.py",
  "pinned": false,
  "license": "mit"
}
```

### requirements.txt (Dependencies)
```
gradio[mcp]>=4.0.0
PyMuPDF>=1.23.0
Pillow>=10.0.0
transformers>=4.35.0
torch>=2.0.0
requests>=2.31.0
accelerate>=0.24.0
sentencepiece>=0.1.99
protobuf>=4.24.0
```

## 🧪 Testing Your Deployment

### 1. Web Interface Test
- Visit your space URL
- Upload a sample PDF
- Select source and target languages
- Verify translation results

### 2. MCP Server Test
- Check schema endpoint: `https://your-space.hf.space/gradio_api/mcp/schema`
- Verify MCP endpoint: `https://your-space.hf.space/gradio_api/mcp/sse`

### 3. Integration Test
Configure in Claude Desktop:
```json
{
  "mcpServers": {
    "pdf-translator": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-username-pdf-document-translator.hf.space/gradio_api/mcp/sse"
      ]
    }
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Build Failures**
   - Check requirements.txt for version conflicts
   - Verify all dependencies are available on PyPI
   - Check logs tab for specific error messages

2. **Memory Issues**
   - Hugging Face Spaces have memory limits
   - Consider using smaller models
   - Optimize image processing parameters

3. **Model Loading Errors**
   - Some models may not be available
   - Add fallback models in your code
   - Check model compatibility with transformers version

4. **MCP Connection Issues**
   - Verify the MCP endpoint URL
   - Check that `mcp_server=True` is set in launch()
   - Test with curl or browser first

### Debug Commands

```bash
# Test locally before deployment
python app.py

# Check requirements
pip install -r requirements.txt

# Test MCP schema
curl https://your-space.hf.space/gradio_api/mcp/schema
```

## 🔒 Security Considerations

1. **File Upload Limits**
   - Set reasonable file size limits
   - Validate file types
   - Implement rate limiting if needed

2. **Model Security**
   - Use trusted model sources
   - Consider model caching strategies
   - Monitor resource usage

3. **API Keys**
   - Use Hugging Face Secrets for sensitive data
   - Never commit API keys to repository
   - Use environment variables

## 📊 Monitoring and Maintenance

### Performance Monitoring
- Monitor space usage in Hugging Face dashboard
- Check processing times for different document sizes
- Monitor memory and CPU usage

### Updates and Maintenance
- Regularly update dependencies
- Test with new model versions
- Monitor for security updates

### Scaling Considerations
- For high traffic, consider Hugging Face Pro
- Implement caching for frequently translated documents
- Consider batch processing for multiple documents

## 🌐 Alternative Deployment Options

### 1. Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 7860

CMD ["python", "app.py"]
```

### 2. Cloud Platforms
- **Google Cloud Run**: Serverless container deployment
- **AWS Lambda**: Serverless function deployment
- **Azure Container Instances**: Container deployment
- **Railway**: Simple deployment platform

### 3. Self-Hosted
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py

# Access at http://localhost:7860
```

## 📈 Performance Optimization

### Model Optimization
- Use quantized models for faster inference
- Implement model caching
- Consider GPU acceleration for large documents

### Image Processing
- Optimize PDF to image conversion settings
- Implement image compression
- Cache processed images

### Translation Optimization
- Batch translation requests
- Use specialized translation models
- Implement translation caching

## 🎯 Next Steps

After successful deployment:

1. **Share Your Space**
   - Add to Hugging Face community
   - Share on social media
   - Create demo videos

2. **Gather Feedback**
   - Monitor user interactions
   - Collect feedback through issues
   - Iterate based on usage patterns

3. **Extend Functionality**
   - Add more languages
   - Support more document formats
   - Implement advanced OCR features

4. **Community Contribution**
   - Open source your improvements
   - Contribute to MCP ecosystem
   - Help others with similar projects

## 📞 Support

If you encounter issues:
- Check Hugging Face Spaces documentation
- Visit the MCP course forums
- Create issues in the project repository
- Join the Gradio community Discord

Happy deploying! 🚀

