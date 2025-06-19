import streamlit as st
import os
import zipfile
import tempfile
import pandas as pd
import json
from io import BytesIO, StringIO
import time
from main import process_file  # Your custom processor

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
                                row = {"filename": os.path.basename(fpath)}
                                row.update(json_result)
                                st.session_state.results.append(row)
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
                    st.rerun()  # Refresh to show results section
                else:
                    st.warning("No valid files found to process.")
        else:
            st.warning("Please upload at least one file before pressing 'Process Files'.")

# Show results and editing interface after processing is complete
if st.session_state.processing_complete and st.session_state.results:
    st.success("✅ All files processed successfully!")
    
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
            st.rerun()
