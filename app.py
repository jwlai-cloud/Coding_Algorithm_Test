import gradio as gr
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
from transformers import pipeline
import requests
import os
from typing import Dict, List, Tuple, Optional
import tempfile

# Initialize the vision-language model for translation
# Using Hugging Face's BLIP-2 or similar model for image-to-text + translation
def initialize_models():
    """Initialize the models needed for document translation"""
    try:
        # For image captioning/OCR, we'll use a vision model
        # In production, you might want to use better OCR models
        image_to_text = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
        return image_to_text
    except Exception as e:
        print(f"Error initializing models: {e}")
        return None

# Global model initialization
vision_model = initialize_models()

def pdf_to_images(pdf_file) -> List[Image.Image]:
    """
    Convert PDF pages to images
    
    Args:
        pdf_file: Uploaded PDF file
        
    Returns:
        List[Image.Image]: List of PIL Images, one per page
    """
    if pdf_file is None:
        return []
    
    try:
        # Open the PDF
        pdf_document = fitz.open(pdf_file.name)
        images = []
        
        for page_num in range(len(pdf_document)):
            # Get the page
            page = pdf_document.load_page(page_num)
            
            # Convert page to image (300 DPI for good quality)
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~300 DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        pdf_document.close()
        return images
        
    except Exception as e:
        raise Exception(f"Error converting PDF to images: {str(e)}")

def extract_text_from_image(image: Image.Image) -> str:
    """
    Extract text from image using OCR/Vision model
    
    Args:
        image: PIL Image
        
    Returns:
        str: Extracted text
    """
    try:
        if vision_model is None:
            return "Vision model not available. Please check model initialization."
        
        # Use the vision model to extract text
        result = vision_model(image)
        
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('generated_text', '')
        return str(result)
        
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate text using Hugging Face translation models
    
    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        str: Translated text
    """
    try:
        # Create translation pipeline
        # For production, you might want to use specific translation models
        model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
        
        try:
            translator = pipeline("translation", model=model_name)
            result = translator(text)
            return result[0]['translation_text']
        except:
            # Fallback to a general multilingual model
            translator = pipeline("translation", model="facebook/mbart-large-50-many-to-many-mmt")
            result = translator(text, src_lang=source_lang, tgt_lang=target_lang)
            return result[0]['translation_text']
            
    except Exception as e:
        return f"Translation error: {str(e)}. Original text: {text}"

def document_translator(
    pdf_file, 
    source_language: str, 
    target_language: str
) -> Dict:
    """
    Main function to translate PDF documents
    
    Args:
        pdf_file: Uploaded PDF file
        source_language (str): Source language code (e.g., 'en', 'es', 'fr')
        target_language (str): Target language code (e.g., 'en', 'es', 'fr')
        
    Returns:
        dict: Translation results with original and translated text per page
    """
    
    if pdf_file is None:
        return {"error": "No PDF file uploaded"}
    
    if not source_language or not target_language:
        return {"error": "Please specify both source and target languages"}
    
    try:
        # Convert PDF to images
        images = pdf_to_images(pdf_file)
        
        if not images:
            return {"error": "Could not extract images from PDF"}
        
        results = {
            "total_pages": len(images),
            "source_language": source_language,
            "target_language": target_language,
            "pages": []
        }
        
        # Process each page
        for i, image in enumerate(images):
            page_result = {
                "page_number": i + 1,
                "original_text": "",
                "translated_text": "",
                "status": "processing"
            }
            
            try:
                # Extract text from image
                original_text = extract_text_from_image(image)
                page_result["original_text"] = original_text
                
                if original_text and original_text.strip():
                    # Translate the text
                    translated_text = translate_text(original_text, source_language, target_language)
                    page_result["translated_text"] = translated_text
                    page_result["status"] = "completed"
                else:
                    page_result["status"] = "no_text_found"
                    
            except Exception as e:
                page_result["status"] = f"error: {str(e)}"
            
            results["pages"].append(page_result)
        
        return results
        
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}

# Language options for the interface
LANGUAGE_OPTIONS = [
    ("English", "en"),
    ("Spanish", "es"), 
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Russian", "ru"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Arabic", "ar"),
    ("Hindi", "hi")
]

# Create the Gradio interface
demo = gr.Interface(
    fn=document_translator,
    inputs=[
        gr.File(
            label="Upload PDF Document",
            file_types=[".pdf"],
            type="filepath"
        ),
        gr.Dropdown(
            choices=LANGUAGE_OPTIONS,
            label="Source Language (language of the document)",
            value="en"
        ),
        gr.Dropdown(
            choices=LANGUAGE_OPTIONS,
            label="Target Language (translate to)",
            value="es"
        )
    ],
    outputs=gr.JSON(label="Translation Results"),
    title="📄 PDF Document Translator MCP Server",
    description="""
    Upload a PDF document and translate it to another language using AI vision models.
    
    **How it works:**
    1. Upload your PDF document
    2. Select the source language (language of your document)  
    3. Select the target language (language to translate to)
    4. The system will convert PDF pages to images and use AI to extract and translate text
    
    **MCP Server:** This app also functions as an MCP server that can be used by AI assistants and other applications.
    
    **Supported Languages:** English, Spanish, French, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Arabic, Hindi
    """,
    examples=[
        [None, "en", "es"],  # English to Spanish
        [None, "fr", "en"],  # French to English  
        [None, "de", "it"],  # German to Italian
    ],
    theme=gr.themes.Soft(),
    allow_flagging="never"
)

if __name__ == "__main__":
    # Launch with MCP server enabled
    demo.launch(
        mcp_server=True,
        share=False,
        server_name="0.0.0.0",
        server_port=7860
    )

