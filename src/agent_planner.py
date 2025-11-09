from database import Database
from openai import OpenAI
import os
import base64
import time
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from ocr_service import OCRService

class AgentPlanner:
    """Agent planner that orchestrates document processing workflow using AI."""
    
    def __init__(self):
        """Initialize the AgentPlanner with OpenAI client and database connection.
        
        Raises:
            ValueError: If OPENAI_API_KEY environment variable is not set.
        """
        load_dotenv(override=True)
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please create a .env file with OPENAI_API_KEY=your-key or set it as an environment variable."
            )
        print(f"OpenAI API Key loaded (begins with {openai_api_key[:8]}...)")
        self.client = OpenAI(api_key=openai_api_key)
        self.db = Database()
        self.ocr = OCRService()
        self.tools = {

            "summarize": self.summarize_document,
            "tts":self.text_to_speech,
            "generate_image": self.generate_image_from_doc            
        }

    def plan_next_step_agentic(self, doc_id: int):
        """Use AI reasoning to decide the next step in the document processing workflow.
        
        Args:
            doc_id: The document ID to plan the next step for.
            
        Returns:
            str: The next action to perform (e.g., 'extract_text', 'summarize', 'tts', 
                 'generate_image', or 'complete').
        """
        doc = self.db.get_document(doc_id)
        if not doc:
            return None

        has_text = bool(doc.get('extracted_text'))
        has_summary = bool(doc.get('summary'))
        has_audio = bool(doc.get('tts_path'))
        has_image = bool(doc.get('image_path'))

        context = f"""Analyze the document processing status and return ONLY the action name.

                    Document Status:
                    - Text extracted: {has_text}
                    - Summary: {has_summary}
                    - Audio (TTS): {has_audio}
                    - Image: {has_image}

                    Required workflow: extract_text -> summarize -> tts -> generate_image

                    Return ONLY one word from this list:
                    - "extract_text" (if text is missing)
                    - "summarize" (if summary is missing)
                    - "tts" (if audio is missing)
                    - "generate_image" (if image is missing)
                    - "complete" (if all steps are done)

                    Return only the word, nothing else."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a workflow planner. Return ONLY the action name as a single word. Do not include any explanations or additional text."},
                {"role": "user", "content": context},
            ],
            temperature=0.1,  # Lower temperature for more deterministic output
        )

        raw_response = response.choices[0].message.content.strip().lower()
        
        # Extract action name from response (in case AI adds extra text)
        valid_actions = ["extract_text", "summarize", "tts", "generate_image", "complete"]
        next_action = None
        
        # Try to find a valid action in the response
        for action in valid_actions:
            if action in raw_response:
                next_action = action
                break
        
        # If no action found, try to parse common patterns
        if not next_action:
            if "summar" in raw_response:
                next_action = "summarize"
            elif "text" in raw_response and "extract" in raw_response:
                next_action = "extract_text"
            elif "tts" in raw_response or "speech" in raw_response or "audio" in raw_response:
                next_action = "tts"
            elif "image" in raw_response:
                next_action = "generate_image"
            elif "complete" in raw_response or "done" in raw_response or "finish" in raw_response:
                next_action = "complete"
            else:
                # Fallback: use rule-based logic if AI response is unclear
                print(f"⚠️ Could not parse AI response: {raw_response}. Using rule-based fallback.")
                return self.plan_next_step_rulebase(doc_id)
        
        print(f"🤖 AI planner decided next action: {next_action}")
        return next_action

    def plan_next_step_rulebase(self, doc_id: int):
        """Decide the next step using rule-based logic (non-AI approach).
        
        Checks the document state and returns the next required action based on
        a predefined sequence: extract_text -> summarize -> tts -> generate_image.
        
        Args:
            doc_id: The document ID to plan the next step for.
            
        Returns:
            str: The next action to perform, or None if document not found.
                 Possible values: 'extract_text', 'summarize', 'tts', 
                 'generate_image', 'complete'.
        """
        doc = self.db.get_document(doc_id)
        if not doc:
            print(" Document not found")
            return None

        print(f"Planning for document: {doc['filename']}")
        
        # Basic decision rules (we will improve later)
        if not doc["extracted_text"]:
            print(" Need to extract text!")
            return "extract_text"

        if not doc["summary"]:
            print(" Need to summarize!")
            return "summarize"

        if not doc.get("tts_path"):
            print(" Need to generate speech!")
            return "tts"

        if not doc.get("image_path"):
            print(" Need an image!")
            return "generate_image"

        print(" Document fully processed!")
        return "complete"

    def summarize_document(self, doc_id: int):
        """Generate a summary of the document using OpenAI's GPT model.
        
        Retrieves the extracted text from the document, sends it to OpenAI
        for summarization, and stores the result in the database.
        
        Args:
            doc_id: The document ID to summarize.
            
        Returns:
            str: The generated summary text, or None if summarization fails.
        """
        print(" Summarizing...")       
        doc = self.db.get_document(doc_id)
        text = doc["extracted_text"]

        print("🧠 Calling OpenAI to summarize...")

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": "Summarize the document in 3-4 bullet points."
            },{
                "role": "user",
                "content": text
            }]
        )

        summary = response.choices[0].message.content.strip()

        updated = self.db.update_summary(doc_id, summary)

        if updated:
            print(f"✅ Summary stored for doc {doc_id}")
        else:
            print("❌ Failed to update summary")

        return summary   
    
    def _extract_from_image(self, file_path):
        """Extract text from an image file using OCR (Tesseract).
        
        Args:
            file_path: Path to the image file (PNG, JPG, JPEG).
            
        Returns:
            str: The extracted text from the image.
        """
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
        
    def text_to_speech(self, doc_id: int):
        """Convert document summary to speech using OpenAI's TTS API.
        
        Retrieves the document summary and generates an audio file using
        OpenAI's text-to-speech model. Saves the audio file and updates
        the database with the file path.
        
        Args:
            doc_id: The document ID to generate speech for.
            
        Returns:
            str: Path to the generated audio file, or None if no summary exists.
        """
        print(" Generating TTS...")
        doc = self.db.get_document(doc_id)
        summary = doc["summary"]

        if not summary:
            print(" No summary to convert to speech!")
            return

        print(" Calling OpenAI TTS...")

        response = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=summary
        )
        audio_folder = "output/audio"
        os.makedirs(audio_folder, exist_ok=True)
        audio_path = os.path.join(audio_folder, f"doc_{doc_id}.mp3")
        with open(audio_path, "wb") as f:
            f.write(response.read())
        self.db.update_tts_path(doc_id, audio_path)
        print(f"✅ TTS saved: {audio_path}")
        return audio_path

    def generate_image_from_doc(self, doc_id: int):
        """Generate an image from the document summary using DALL·E.
        
        Uses the document summary as a prompt to generate an image using
        OpenAI's DALL·E model. Saves the image as a PNG file and updates
        the database with the file path.
        
        Args:
            doc_id: The document ID to generate an image for.
            
        Returns:
            str: Path to the generated image file, or None if no summary exists.
        """
        doc = self.db.get_document(doc_id)
        summary = doc["summary"]

        if not summary:
            print("❌ No summary available to generate image!")
            return

        print("🎨 Calling DALL·E to generate image...")

        response = self.client.images.generate(
            model="dall-e-3",
            prompt=f"Create a simple illustration representing: {summary}",
            size="1024x1024",
            response_format="b64_json"
        )

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        image_folder = "output/images"
        os.makedirs(image_folder, exist_ok=True)

        image_path = os.path.join(image_folder, f"doc_{doc_id}.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)

        self.db.update_image_path(doc_id, image_path)

        print(f"✅ Image generated and saved: {image_path}")
        return image_path
        
    def run_agentic_workflow(self, doc_id: int, max_steps=10):
        """Run the complete document processing workflow using AI planning.
        
        Executes a workflow that processes a document through multiple stages:
        text extraction, summarization, text-to-speech conversion, and image generation.
        Uses AI to decide the next step at each stage. Stops when complete or
        when maximum steps are reached.
        
        Args:
            doc_id: The document ID to process.
            max_steps: Maximum number of workflow steps to execute (default: 10).
        """
        print(f"🚀 Starting full workflow for doc {doc_id}")
     
        step = 0

        while step < max_steps:
            next_action = self.plan_next_step_agentic(doc_id)
            
            # If AI planner fails, try rule-based
            if next_action is None or next_action not in ["extract_text", "summarize", "tts", "generate_image", "complete"]:
                print(f"⚠️ AI planner returned invalid action: {next_action}. Using rule-based fallback...")
                next_action = self.plan_next_step_rulebase(doc_id)
                if next_action is None:
                    print("❌ Could not determine next action. Stopping workflow.")
                    break
            
            # Handle complete
            if next_action == "complete":
                print("✅ Workflow complete!")
                self.db.update_status(doc_id, "complete")
                yield {"status": "✅ Workflow complete!"}
                break

            # Execute the action
            if next_action == "extract_text":
                print("⚙️ Extracting text from document...")
                doc = self.db.get_document(doc_id)
                if doc:
                    file_path = os.path.join("data/uploads", doc["filename"])
                    if os.path.exists(file_path):
                        text = self.ocr.extract_text(file_path)
                        self.db.update_extracted_text(doc_id, text)
                        self.db.update_status(doc_id, "text_extracted")
                        yield {"status": "📄 Text extracted"}
                    else:
                        print(f"⚠️ File not found: {file_path}")
                        yield {"status": f"⚠️ File not found: {file_path}"}

            elif next_action == "summarize":
                print("🧠 Summarizing document...")
                try:
                    self.summarize_document(doc_id)
                    self.db.update_status(doc_id, "summarized")
                    yield {"status": "🧠 Summarized"}
                except Exception as e:
                    print(f"❌ Error summarizing: {e}")
                    yield {"status": f"❌ Error: {str(e)}"}

            elif next_action == "tts":
                print("🎤 Generating text-to-speech...")
                try:
                    self.text_to_speech(doc_id)
                    self.db.update_status(doc_id, "tts_done")
                    yield {"status": "🎤 TTS generated"}
                except Exception as e:
                    print(f"❌ Error generating TTS: {e}")
                    yield {"status": f"❌ Error: {str(e)}"}

            elif next_action == "generate_image":
                print("🎨 Generating image...")
                try:
                    self.generate_image_from_doc(doc_id)
                    self.db.update_status(doc_id, "image_generated")
                    yield {"status": "🎨 Image generated"}
                except Exception as e:
                    print(f"❌ Error generating image: {e}")
                    yield {"status": f"❌ Error: {str(e)}"}

            step += 1
            time.sleep(1)  # Small delay for readability

        print("🏁 Agent finished processing document.")