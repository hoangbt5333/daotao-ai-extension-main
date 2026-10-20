import pdfplumber
import docx
import os

def extract_text_from_file(file_path):
    """Extract text from file based on file extension"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif file_ext == ".docx":
        return extract_text_from_docx(file_path)
    elif file_ext == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read() 