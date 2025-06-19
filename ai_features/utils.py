from prompts import prompt_2
import google.generativeai as genai
from pdf2image import convert_from_path

vision_model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")
genai.configure(api_key="AIzaSyCxHZzWgfpgT91e-ReTrqioroVenes4Ato")

# Global token tracking
class TokenTracker:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.file_count = 0
        self.file_details = []
    
    def add_usage(self, filename, input_tokens, output_tokens, total_tokens, file_size=0, file_type=""):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_tokens += total_tokens
        self.file_count += 1
        
        self.file_details.append({
            'filename': filename,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'file_size': file_size,
            'file_type': file_type
        })
    
    def get_summary(self):
        return {
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_tokens,
            'file_count': self.file_count,
            'avg_tokens_per_file': self.total_tokens / max(1, self.file_count),
            'details': self.file_details
        }
    
    def print_summary(self):
        print("\n" + "="*50)
        print("📊 TOTAL TOKEN USAGE SUMMARY")
        print("="*50)
        print(f"Files processed: {self.file_count}")
        print(f"Total input tokens: {self.total_input_tokens:,}")
        print(f"Total output tokens: {self.total_output_tokens:,}")
        print(f"Total tokens used: {self.total_tokens:,}")
        print(f"Average tokens per file: {self.total_tokens / max(1, self.file_count):.1f}")
        print("="*50)

# Global instance
token_tracker = TokenTracker()

def pdf_to_images(pdf_path, output_folder, dpi=300):
    images = convert_from_path(pdf_path, dpi=dpi)
    for i, image in enumerate(images):
        image_path = f"{output_folder}/page_{i+1}.png"
        image.save(image_path, "PNG")

def clean_text(response):
    # Check if response is None or empty
    if response is None:
        return None
    
    # Convert to string if it's not already
    if not isinstance(response, str):
        response = str(response)
    
    # Clean the text
    response = response.replace("`", "")
    response = response.replace("json", "")
    return response.strip()

def gemini_img_ocr(image_data, file_extension, filename="unknown"):
    try:
        mime_type = None
        if file_extension == ".jpg" or file_extension == ".jpeg":
            mime_type = "image/jpeg"
        elif file_extension == ".png":
            mime_type = "image/png"
        
        contents = [
            {"mime_type": mime_type, "data": image_data},
            {"text": prompt_2},
        ]
        
        response = vision_model.generate_content(contents)
        
        # Track token usage
        if response and hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count
            output_tokens = usage.candidates_token_count
            total_tokens = usage.total_token_count
            
            # Add to tracker
            token_tracker.add_usage(
                filename=filename,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                file_size=len(image_data),
                file_type="image"
            )
            
            print(f"📊 {filename} - IMAGE TOKEN USAGE:")
            print(f"   Input tokens: {input_tokens:,}")
            print(f"   Output tokens: {output_tokens:,}")
            print(f"   Total tokens: {total_tokens:,}")
            print(f"   Image size: {len(image_data):,} bytes")
            print("-" * 40)
        
        # Check if response and response.text exist
        if response and hasattr(response, 'text') and response.text:
            return response.text
        else:
            print(f"Warning: Empty or invalid response from Gemini for image: {filename}")
            return None
            
    except Exception as e:
        print(f"Error in gemini_img_ocr for {filename}: {e}")
        return None

def gemini_pdf_ocr(pdf_data, filename="unknown"):
    try:
        mime_type = "application/pdf"
        contents = [
            {"mime_type": mime_type, "data": pdf_data},
            {"text": prompt_2},
        ]
        
        response = vision_model.generate_content(contents)
        
        # Track token usage
        if response and hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count
            output_tokens = usage.candidates_token_count
            total_tokens = usage.total_token_count
            
            # Add to tracker
            token_tracker.add_usage(
                filename=filename,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                file_size=len(pdf_data),
                file_type="pdf"
            )
            
            print(f"📊 {filename} - PDF TOKEN USAGE:")
            print(f"   Input tokens: {input_tokens:,}")
            print(f"   Output tokens: {output_tokens:,}")
            print(f"   Total tokens: {total_tokens:,}")
            print(f"   PDF size: {len(pdf_data):,} bytes")
            print("-" * 40)
        
        # Check if response and response.text exist
        if response and hasattr(response, 'text') and response.text:
            return response.text
        else:
            print(f"Warning: Empty or invalid response from Gemini for PDF: {filename}")
            return None
            
    except Exception as e:
        print(f"Error in gemini_pdf_ocr for {filename}: {e}")
        return None

def get_token_usage_summary():
    """Get token usage summary for display in Streamlit"""
    return token_tracker.get_summary()

def reset_token_tracker():
    """Reset token tracking (useful when starting new batch)"""
    token_tracker.reset()

def print_token_summary():
    """Print token usage summary to console"""
    token_tracker.print_summary()