import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import os

class OCRService:
    def extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        print(f"🔍 Extracting text from {file_path}")

        if ext == ".pdf":
            return self._extract_from_pdf(file_path)
        elif ext in [".png", ".jpg", ".jpeg"]:
            return self._extract_from_image(file_path)
        else:
            print("⚠️ Unsupported file type")
            return ""

    def _extract_from_pdf(self, file_path):
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text("text")
        return text.strip()

    def _extract_from_image(self, file_path):
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
