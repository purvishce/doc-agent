import gradio as gr
from agent_planner import AgentPlanner
from database import DatabaseManager

planner = AgentPlanner()
db = DatabaseManager()

def process_document(file):
    if not file:
        return "❌ Please upload a document.", None, None, None
    
    # Insert document into DB
    doc_id = db.insert_document(file.name)
   
    db.update_extracted_text(doc_id, "This is a test document for demo.")  # placeholder text

    # Run the agent workflow
    planner.run_workflow(doc_id)

    doc = db.get_document(doc_id)

    return (
        doc["summary"],
        doc.get("tts_path"),
        doc.get("image_path"),
        doc.get("status")
    )

