import streamlit as st
import os
import zipfile
import tempfile
import pandas as pd
import json
import time
from main import process_file  # Your custom processor
from utils import get_token_usage_summary, reset_token_tracker, print_token_summary

# Add imports at the top if not already present
from io import BytesIO, StringIO

def calculate_price(input_tokens, output_tokens, num_images):
    """
    Calculate total price for Gemini 2.0 Flash based on:
    - Fixed prompt: 3000 characters
    - Variable number of images
    - Fixed output: 1000 characters per image
    """
    # Gemini 2.0 Flash pricing
    INPUT_TEXT_PRICE = 0.0375 / 1_000_000  # $0.0375 per 1M characters
    INPUT_IMAGE_PRICE = 0.0001935  # $0.0001935 per image
    OUTPUT_TEXT_PRICE = 0.15 / 1_000_000  # $0.15 per 1M characters
    
    # Calculate costs
    input_text_cost = 3000 * INPUT_TEXT_PRICE  # Fixed 3000 characters
    input_image_cost = num_images * INPUT_IMAGE_PRICE
    output_text_cost = (1000 * num_images) * OUTPUT_TEXT_PRICE  # 1000 chars per image
    
    total_cost = input_text_cost + input_image_cost + output_text_cost
    
    return {
        'input_text_cost': input_text_cost,
        'input_image_cost': input_image_cost,
        'output_text_cost': output_text_cost,
        'total_cost': total_cost
    }

def get_price_summary():
    """Get pricing summary for all processed files"""
    token_summary = get_token_usage_summary()
    if token_summary['file_count'] == 0:
        return {'file_count': 0, 'total_cost': 0, 'details': []}
    
    total_cost = 0
    details = []
    
    for usage in token_summary['details']:
        # Each file is 1 image based on your use case
        num_images = 1
        
        price_calc = calculate_price(
            usage['input_tokens'], 
            usage['output_tokens'], 
            num_images
        )
        
        total_cost += price_calc['total_cost']
        
        details.append({
            'filename': usage['filename'],
            'file_type': usage.get('file_type', 'Unknown'),
            'num_images': num_images,
            'cost': price_calc['total_cost'],
            'file_size': usage.get('file_size', 'Unknown')
        })
    
    return {
        'file_count': token_summary['file_count'],
        'total_cost': total_cost,
        'details': details
    }

def flatten_json_result(json_result):
    """Flatten nested JSON structure for sender and recipient"""
    flattened = {}
    
    # Copy top-level fields
    top_level_fields = ['transaction_id', 'transaction_number', 'payment_method', 
                       'invoice_date', 'invoice_time', 'amount', 'currency', 
                       'additional_data', 'image_type']
    
    for field in top_level_fields:
        flattened[field] = json_result.get(field, "")
    
    # Flatten sender fields
    sender = json_result.get('sender', {})
    flattened['sender_name'] = sender.get('name', "")
    flattened['sender_cnpj_cpf'] = sender.get('cnpj/cpf', "")
    flattened['sender_institution'] = sender.get('institution', "")
    flattened['sender_institution_cnpj'] = sender.get('institution_cnpj', "")
    
    # Flatten recipient fields
    recipient = json_result.get('recipient', {})
    flattened['recipient_name'] = recipient.get('name', "")
    flattened['recipient_cnpj_cpf'] = recipient.get('cnpj/cpf', "")
    flattened['recipient_institution'] = recipient.get('institution', "")
    flattened['recipient_pix_key'] = recipient.get('pix_key', "")
    
    return flattened

st.set_page_config(page_title="File Processor", layout="centered")
st.title("📄 Upload Images, PDFs, or a Folder (ZIP)")

# Initialize session state to persist results
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'temp_files_path' not in st.session_state:
    st.session_state.temp_files_path = None

# Only show upload form if not already processed or user wants to start over
if not st.session_state.processing_complete:
    with st.form("upload_form"):
        uploaded_files = st.file_uploader(
            "Upload one or more images, PDFs, or a ZIP folder",
            type=["jpg", "jpeg", "png", "pdf", "zip"],
            accept_multiple_files=True
        )
        submit_button = st.form_submit_button("Process Files")

    if submit_button:
        if uploaded_files:
            # Reset session state for new processing
            st.session_state.results = []
            st.session_state.processing_complete = False
            reset_token_tracker()  # Reset token tracking
            
            with tempfile.TemporaryDirectory() as temp_dir:
                files_to_process = []

                for uploaded_file in uploaded_files:
                    file_path = os.path.join(temp_dir, uploaded_file.name)

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    if uploaded_file.name.endswith(".zip"):
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                        for root, _, files in os.walk(temp_dir):
                            for file in files:
                                if file.lower().endswith((".jpg", ".jpeg", ".png", ".pdf")):
                                    files_to_process.append(os.path.join(root, file))
                    else:
                        if uploaded_file.name.lower().endswith((".jpg", ".jpeg", ".png", ".pdf")):
                            files_to_process.append(file_path)
                        else:
                            st.warning(f"Unsupported file type: {uploaded_file.name}")

                if files_to_process:
                    total_files = len(files_to_process)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    completed_files_box = st.empty()
                    processed_files = 0
                    file_time_estimates = []
                    completed_filenames = []

                    status_text.info(f"⏳ Starting processing of {total_files} files...")

                    for idx, fpath in enumerate(files_to_process):
                        start_time = time.time()
                        result = process_file(fpath)
                        end_time = time.time()
                        duration = end_time - start_time
                        file_time_estimates.append(duration)

                        if result is None:
                            st.session_state.results.append({"filename": os.path.basename(fpath), "error": "Processing failed"})
                        else:
                            try:
                                json_result = json.loads(result) if isinstance(result, str) else result
                                
                                # Flatten the nested JSON structure
                                flattened_result = flatten_json_result(json_result)
                                flattened_result["filename"] = os.path.basename(fpath)
                                
                                st.session_state.results.append(flattened_result)
                            except Exception as e:
                                st.session_state.results.append({"filename": os.path.basename(fpath), "error": str(e)})

                        processed_files += 1
                        completed_filenames.append(f"`{os.path.basename(fpath)}` ✅")
                        progress_bar.progress(processed_files / total_files)

                        avg_time = sum(file_time_estimates) / len(file_time_estimates)
                        remaining_time = avg_time * (total_files - processed_files)

                        status_text.markdown(
                            f"**Processed:** {processed_files}/{total_files} | ⏳ Est. time left: `{remaining_time:.1f}` seconds"
                        )
                        completed_files_box.markdown("### ✅ Completed Files\n" + "\n".join(completed_filenames))
                        time.sleep(0.1)  # Optional: give Streamlit time to refresh UI

                    # Mark processing as complete
                    st.session_state.processing_complete = True
                    
                    # Print token summary to console
                    print_token_summary()
                    
                    st.rerun()  # Refresh to show results section
                else:
                    st.warning("No valid files found to process.")
        else:
            st.warning("Please upload at least one file before pressing 'Process Files'.")

# Show results and editing interface after processing is complete
if st.session_state.processing_complete and st.session_state.results:
    st.success("✅ All files processed successfully!")
    
    # Display pricing summary
    price_summary = get_price_summary()
    if price_summary['file_count'] > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Files Processed", f"{price_summary['file_count']}")
        with col2:
            st.metric("Total Cost", f"${price_summary['total_cost']:.6f}")
        
        # Expandable detailed pricing breakdown
        with st.expander("💰 Detailed Cost Breakdown by File"):
            price_df = pd.DataFrame(price_summary['details'])
            if not price_df.empty:
                # Format cost column to show more decimal places
                price_df['cost_formatted'] = price_df['cost'].apply(lambda x: f"${x:.6f}")
                st.dataframe(
                    price_df[['filename', 'file_type', 'num_images', 'cost_formatted', 'file_size']].rename(columns={
                        'filename': 'File Name',
                        'file_type': 'File Type', 
                        'num_images': 'Images',
                        'cost_formatted': 'Cost',
                        'file_size': 'File Size'
                    }),
                    use_container_width=True
                )
    
    # Convert results to DataFrame
    df = pd.DataFrame(st.session_state.results)
    
    # Create the editable data editor
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="editable_results"
    )
    
    # Download buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Download Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Results')
        excel_buffer.seek(0)
        
        st.download_button(
            label="📥 Download Excel",
            data=excel_buffer,
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        # Download CSV
        csv_buffer = StringIO()
        edited_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        st.download_button(
            label="📄 Download CSV",
            data=csv_buffer.getvalue(),
            file_name="results.csv",
            mime="text/csv"
        )
    
    with col3:
        # Process new files button
        if st.button("🔄 Process New Files"):
            st.session_state.results = []
            st.session_state.processing_complete = False
            reset_token_tracker()  # Reset token tracking
            st.rerun()