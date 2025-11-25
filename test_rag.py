#!/usr/bin/env python3
"""
Test script for SolverAI RAG System
"""

import requests
import json
import time
import os
from fpdf import FPDF

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")

def create_dummy_pdf(filename="test_doc.pdf"):
    """Create a dummy PDF for testing"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    text = """
    SolverAI Secret Knowledge:
    
    1. The secret code is "BLUEBERRY".
    2. The project was founded in 2024 by the DeepMind team.
    3. The ultimate goal is to create a fully autonomous coding agent.
    """
    
    pdf.multi_cell(0, 10, text)
    pdf.output(filename)
    return filename

def test_upload(filename):
    """Test document upload"""
    print_section("1. Testing Document Upload")
    
    url = f"{BASE_URL}/upload"
    files = {'file': open(filename, 'rb')}
    
    try:
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            print("Upload successful!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_rag_chat():
    """Test chat with RAG context"""
    print_section("2. Testing RAG Chat")
    
    # Ask a question that requires the document context
    payload = {
        "message": "What is the secret code mentioned in the document?",
        "stream": False
    }
    
    print(f"Question: {payload['message']}")
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data['response']}")
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    # Create dummy PDF
    pdf_file = create_dummy_pdf()
    
    # Run tests
    if test_upload(pdf_file):
        # Wait a bit for indexing (though it's synchronous in our implementation)
        time.sleep(1)
        test_rag_chat()
    
    # Cleanup
    if os.path.exists(pdf_file):
        os.remove(pdf_file)

if __name__ == "__main__":
    main()
