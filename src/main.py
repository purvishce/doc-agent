import gradio as gr
import os
import shutil
from agent_planner import AgentPlanner
from database import Database

planner = AgentPlanner()
db = Database()

# Ensure directories exist
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("output/audio", exist_ok=True)
os.makedirs("output/images", exist_ok=True)

def process_document(file_path):
    """Process uploaded document through the agentic workflow."""
    if file_path is None:
        return "", None, None, "No file uploaded"
    
    # Get filename from path
    filename = os.path.basename(file_path)
    
    # Copy file to our uploads directory (Gradio uses temp files)
    dest_path = os.path.join("data/uploads", filename)
    shutil.copy2(file_path, dest_path)
    
    # Extract text first using OCR service
    text = planner.ocr.extract_text(dest_path)
    
    # Insert document with extracted text
    doc_id = db.insert_document(filename, text)
    
    # Update status
    db.update_status(doc_id, "text_extracted")
    
    # Run full agentic workflow (consume generator)
    for _ in planner.run_agentic_workflow(doc_id):
        pass  # Consume generator but don't use streaming updates for now
    
    # Get final document data
    doc = db.get_document(doc_id)
    
    # Return outputs matching the output components
    summary = doc.get("summary", "")
    tts_path = doc.get("tts_path")
    image_path = doc.get("image_path")
    status = doc.get("status", "unknown")
    
    return summary, tts_path, image_path, status

with gr.Blocks(title="Agentic AI Dashboard") as demo:
    gr.Markdown("# 🤖 Agentic AI Dashboard")
    gr.Markdown("Upload document(s) → AI extracts text, summarizes, generates TTS & image.")

    with gr.Row():
        file_input = gr.File(label="Upload Document", file_types=[".pdf", ".png", ".jpg"], type="filepath")
    
    with gr.Row():
        run_btn = gr.Button("🚀 Process Document")

    gr.Markdown("Output: AI extracts text, summarizes, generates TTS & image.")
    with gr.Row():
        summary_output = gr.Textbox(label="Summary", interactive=False, lines=20)
        audio_output = gr.Audio(label="Speech Output", type="filepath")
        image_output = gr.Image(label="Generated Image")
        status_output = gr.Textbox(label="Status")

    run_btn.click(
        fn=process_document,
        inputs=[file_input],
        outputs=[summary_output, audio_output, image_output, status_output]
    )

if __name__ == "__main__":
    demo.launch()
