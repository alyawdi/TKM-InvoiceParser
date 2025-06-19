import os
import argparse
from utils import *

def process_file(file_path):
    _, file_extension = os.path.splitext(file_path)  # Fixed: removed the asterisk
    file_extension = file_extension.lower()
    response = None
    
    if file_extension in [".jpg", ".jpeg", ".png"]:
        with open(file_path, "rb") as image_file:
            image_data = image_file.read()
        response = gemini_img_ocr(image_data, file_extension)
    elif file_extension == ".pdf":
        with open(file_path, "rb") as pdf_file:
            pdf_data = pdf_file.read()
        response = gemini_pdf_ocr(pdf_data)
    else:
        # print("Unsupported file type:", file_extension)
        return None
    
    cleaned_response = clean_text(response)
    return cleaned_response if cleaned_response is not None else None

if __name__ == "__main__":  # Fixed: proper double underscores
    parser = argparse.ArgumentParser(
        description="Process a file (PDF or image) using OCR."
    )
    parser.add_argument("file_path", type=str, help="Path to the file to process")
    args = parser.parse_args()
    response = process_file(args.file_path)
    print(response)