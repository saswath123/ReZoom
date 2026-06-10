import fitz  # PyMuPDF
from docx import Document
import os
import re

def extract_text_from_pdf(file_path):
    """Extract text from PDF with better error handling"""
    try:
        text = ""
        pdf = fitz.open(file_path)
        
        for page_num, page in enumerate(pdf):
            page_text = page.get_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
        
        pdf.close()
        
        if not text or len(text.strip()) < 20:
            raise Exception("PDF contains insufficient text")
        
        # Clean the text
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove excessive newlines
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII chars
        
        return text.strip()
        
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")

def extract_text_from_docx(file_path):
    """Extract text from DOCX with better error handling"""
    try:
        text = ""
        doc = Document(file_path)
        
        # Extract from paragraphs
        for para in doc.paragraphs:
            if para.text and para.text.strip():
                text += para.text.strip() + "\n"
        
        # Extract from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text and cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    text += " | ".join(row_text) + "\n"
        
        if not text or len(text.strip()) < 20:
            raise Exception("DOCX contains insufficient text")
        
        # Clean the text
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        
        return text.strip()
        
    except Exception as e:
        raise Exception(f"DOCX extraction failed: {str(e)}")

def extract_resume_text(file_path):
    """Main extraction handler with validation"""
    try:
        if not os.path.exists(file_path):
            raise Exception("File not found")
        
        if not os.path.getsize(file_path) > 0:
            raise Exception("File is empty")
        
        if file_path.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            raise Exception("Unsupported file format. Use PDF or DOCX")
        
        if not text or len(text) < 50:
            raise Exception("Could not extract sufficient text from resume")
        
        print(f"Successfully extracted {len(text)} characters of text")  # Debug
        return text
        
    except Exception as e:
        print(f"Extraction error: {str(e)}")  # Debug
        raise
