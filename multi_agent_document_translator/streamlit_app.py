"""Streamlit web interface for the Multi-Agent Document Translator."""

import streamlit as st
import asyncio
from pathlib import Path
import tempfile
import os
from datetime import datetime
import json

from .orchestrator import orchestrator
from .config import settings


# Page configuration
st.set_page_config(
    page_title="Multi-Agent Document Translator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .agent-status {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .agent-running {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .agent-stopped {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .quality-excellent {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 0.25rem;
    }
    .quality-good {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 0.5rem;
        border-radius: 0.25rem;
    }
    .quality-poor {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


async def initialize_system():
    """Initialize the multi-agent system."""
    if 'system_initialized' not in st.session_state:
        with st.spinner("Initializing multi-agent system..."):
            try:
                await orchestrator.initialize()
                st.session_state.system_initialized = True
                st.success("✅ Multi-agent system initialized successfully!")
            except Exception as e:
                st.error(f"❌ Failed to initialize system: {str(e)}")
                st.session_state.system_initialized = False


def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">🌐 Multi-Agent Document Translator</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Initialize system
    if 'system_initialized' not in st.session_state:
        st.session_state.system_initialized = False
    
    if not st.session_state.system_initialized:
        if st.button("🚀 Initialize System"):
            asyncio.run(initialize_system())
        return
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 System Status")
        
        # Get system status
        try:
            status = asyncio.run(orchestrator.get_system_status())
            
            st.markdown(f"**Session ID:** `{status['session_id'][:8]}...`")
            st.markdown(f"**Status:** {'🟢 Running' if status['initialized'] else '🔴 Stopped'}")
            
            st.subheader("Agent Status")
            for agent_name, is_running in status['agents'].items():
                status_class = "agent-running" if is_running else "agent-stopped"
                status_icon = "🟢" if is_running else "🔴"
                st.markdown(
                    f'<div class="agent-status {status_class}">'
                    f'{status_icon} {agent_name.title()}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            
            st.subheader("Configuration")
            st.markdown(f"**Max File Size:** {status['max_file_size_mb']} MB")
            st.markdown(f"**Supported Formats:** {', '.join(status['supported_formats'])}")
            
        except Exception as e:
            st.error(f"Could not get system status: {str(e)}")
    
    # Main interface
    tab1, tab2, tab3 = st.tabs(["📄 Translate Document", "📊 Results", "ℹ️ About"])
    
    with tab1:
        translate_document_tab()
    
    with tab2:
        results_tab()
    
    with tab3:
        about_tab()


def translate_document_tab():
    """Document translation interface."""
    st.header("📄 Document Translation")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a document to translate",
        type=['pdf', 'docx', 'doc', 'txt'],
        help="Supported formats: PDF, DOCX, DOC, TXT"
    )
    
    if uploaded_file is not None:
        # Display file info
        file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📁 **File:** {uploaded_file.name} ({file_size:.1f} MB)")
        
        # Language selection
        col1, col2 = st.columns(2)
        
        with col1:
            supported_languages = asyncio.run(orchestrator.get_supported_languages())
            target_language = st.selectbox(
                "Target Language",
                options=list(supported_languages.keys()),
                format_func=lambda x: f"{supported_languages[x]} ({x})",
                help="Select the language to translate to"
            )
        
        with col2:
            source_language = st.selectbox(
                "Source Language",
                options=["auto"] + list(supported_languages.keys()),
                format_func=lambda x: "Auto-detect" if x == "auto" else f"{supported_languages[x]} ({x})",
                help="Select the source language (auto-detect recommended)"
            )
        
        # Translation options
        st.subheader("Translation Options")
        
        col3, col4 = st.columns(2)
        with col3:
            output_format = st.selectbox(
                "Output Format",
                options=["pdf", "images"],
                help="Choose output format"
            )
        
        with col4:
            save_intermediate = st.checkbox(
                "Save intermediate files",
                help="Keep intermediate images for debugging"
            )
        
        # Translate button
        if st.button("🚀 Start Translation", type="primary"):
            if file_size > settings.max_file_size_mb:
                st.error(f"❌ File size ({file_size:.1f} MB) exceeds maximum ({settings.max_file_size_mb} MB)")
                return
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_path = tmp_file.name
            
            # Create output path
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_filename = f"translated_{Path(uploaded_file.name).stem}_{target_language}.pdf"
            output_path = output_dir / output_filename
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Start translation
                status_text.text("🔄 Starting translation process...")
                progress_bar.progress(10)
                
                result = asyncio.run(orchestrator.translate_document(
                    document_path=temp_path,
                    target_language=target_language,
                    source_language=source_language,
                    output_path=str(output_path) if output_format == "pdf" else None
                ))
                
                progress_bar.progress(100)
                
                if result['success']:
                    # Store result in session state
                    if 'translation_results' not in st.session_state:
                        st.session_state.translation_results = []
                    
                    result['timestamp'] = datetime.now()
                    result['original_filename'] = uploaded_file.name
                    st.session_state.translation_results.append(result)
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    # Success message
                    quality = result['validation']['quality_assessment']
                    st.success(f"✅ Translation completed successfully in {result['processing_time']:.1f}s!")
                    
                    # Quality assessment
                    quality_class = get_quality_class(quality['grade'])
                    st.markdown(
                        f'<div class="{quality_class}">'
                        f'**Quality Assessment:** {quality["grade"]} '
                        f'({quality.get("overall_score", 0):.2f})'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Download buttons
                    if result.get('output_files'):
                        for output_file in result['output_files']:
                            if os.path.exists(output_file):
                                with open(output_file, 'rb') as f:
                                    st.download_button(
                                        label=f"📥 Download {Path(output_file).name}",
                                        data=f.read(),
                                        file_name=Path(output_file).name,
                                        mime="application/octet-stream"
                                    )
                    
                    # Show intermediate files if requested
                    if save_intermediate and result.get('translated_images'):
                        st.subheader("Translated Pages Preview")
                        for i, img_path in enumerate(result['translated_images'][:3]):  # Show first 3 pages
                            if os.path.exists(img_path):
                                st.image(img_path, caption=f"Page {i+1}", width=400)
                
                else:
                    status_text.empty()
                    progress_bar.empty()
                    st.error(f"❌ Translation failed: {result['error']}")
                
            except Exception as e:
                status_text.empty()
                progress_bar.empty()
                st.error(f"❌ Translation error: {str(e)}")
            
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass


def results_tab():
    """Translation results and history."""
    st.header("📊 Translation Results")
    
    if 'translation_results' not in st.session_state or not st.session_state.translation_results:
        st.info("No translation results yet. Translate a document to see results here.")
        return
    
    # Results summary
    results = st.session_state.translation_results
    st.metric("Total Translations", len(results))
    
    # Recent results
    st.subheader("Recent Translations")
    
    for i, result in enumerate(reversed(results[-10:])):  # Show last 10 results
        with st.expander(f"📄 {result['original_filename']} → {result['target_language']} ({result['timestamp'].strftime('%Y-%m-%d %H:%M')})"):
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Pages", result.get('page_count', 0))
                st.metric("Processing Time", f"{result.get('processing_time', 0):.1f}s")
            
            with col2:
                quality = result.get('validation', {}).get('quality_assessment', {})
                st.metric("Quality Grade", quality.get('grade', 'Unknown'))
                st.metric("Overall Score", f"{quality.get('overall_score', 0):.2f}")
            
            with col3:
                st.metric("File Size", f"{result.get('metadata', {}).get('file_size_mb', 0):.1f} MB")
                st.metric("Original Format", result.get('metadata', {}).get('original_format', 'Unknown'))
            
            # Validation details
            if 'validation' in result and 'overall_scores' in result['validation']:
                st.subheader("Quality Metrics")
                scores = result['validation']['overall_scores']
                
                for metric, data in scores.items():
                    if isinstance(data, dict) and 'average' in data:
                        st.progress(data['average'], text=f"{metric.replace('_', ' ').title()}: {data['average']:.2f}")
            
            # Recommendations
            if 'validation' in result and 'recommendations' in result['validation']:
                recommendations = result['validation']['recommendations']
                if recommendations:
                    st.subheader("Recommendations")
                    for rec in recommendations:
                        st.write(f"• {rec}")
            
            # Download files
            if result.get('output_files'):
                st.subheader("Download Files")
                for output_file in result['output_files']:
                    if os.path.exists(output_file):
                        with open(output_file, 'rb') as f:
                            st.download_button(
                                label=f"📥 {Path(output_file).name}",
                                data=f.read(),
                                file_name=Path(output_file).name,
                                mime="application/octet-stream",
                                key=f"download_{i}_{Path(output_file).name}"
                            )


def about_tab():
    """About and help information."""
    st.header("ℹ️ About Multi-Agent Document Translator")
    
    st.markdown("""
    ### 🎯 Purpose
    This application solves the common problem of layout destruction in document translation by using a sophisticated multi-agent architecture.
    
    ### 🏗️ Architecture
    
    **Agent 1: Document-to-Image Converter**
    - Converts PDF pages to high-quality images
    - Maintains original resolution and formatting
    - Handles various document formats
    
    **Agent 2: Multimodal Translation Agent**
    - Uses Google Gemini Vision API for image-based translation
    - Preserves layout, fonts, and visual elements
    - Translates text while maintaining spatial relationships
    
    **Agent 3: Quality Validation Agent**
    - Validates translation accuracy
    - Checks layout preservation
    - Provides quality metrics and feedback
    
    ### 🌟 Features
    - **Layout Preservation**: Maintains original document formatting
    - **Multi-format Support**: PDF, DOCX, and other document formats
    - **Quality Assurance**: Built-in validation and quality checks
    - **Scalable Architecture**: Agent-based system for easy extension
    - **Google AI Integration**: Leverages Gemini's multimodal capabilities
    
    ### 🚀 How to Use
    1. Upload your document in the "Translate Document" tab
    2. Select target and source languages
    3. Choose output format and options
    4. Click "Start Translation"
    5. Download your translated document
    6. Review results and quality metrics in the "Results" tab
    
    ### 📋 Supported Languages
    """)
    
    # Display supported languages
    try:
        languages = asyncio.run(orchestrator.get_supported_languages())
        cols = st.columns(3)
        lang_items = list(languages.items())
        
        for i, (code, name) in enumerate(lang_items):
            with cols[i % 3]:
                st.write(f"🌐 **{name}** ({code})")
    except:
        st.write("Could not load supported languages")
    
    st.markdown("""
    ### ⚙️ Technical Details
    - **Backend**: Python with FastAPI
    - **AI Models**: Google Gemini Vision API
    - **Document Processing**: PyPDF2, pdf2image, python-docx
    - **Image Processing**: OpenCV, Pillow
    - **Quality Assessment**: Structural similarity, histogram comparison
    - **Architecture**: Multi-agent system with A2A protocol
    
    ### 📞 Support
    For technical support or feature requests, please contact the development team.
    """)


def get_quality_class(grade: str) -> str:
    """Get CSS class for quality grade."""
    if grade in ['Excellent', 'Good']:
        return 'quality-excellent'
    elif grade in ['Satisfactory']:
        return 'quality-good'
    else:
        return 'quality-poor'


if __name__ == "__main__":
    main()

