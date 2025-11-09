import sqlite3
from pathlib import Path
import json

class Database:
    """Database handler for document management and audit logging."""
    
    def __init__(self):
        """Initialize the Database connection and create tables if they don't exist.
        
        Sets up the SQLite database at 'data/database.db' and initializes
        the documents and audit tables.
        """
        self.db_path = Path(__file__).resolve().parent.parent / "data" / "database.db"
         # Ensure the data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self):
        """Create and return a connection to the SQLite database.
        
        Returns:
            sqlite3.Connection: Database connection object.
        """
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Initialize the database schema by creating tables if they don't exist.
        
        Creates two tables:
        - documents: Stores document metadata, extracted text, summaries, and file paths
        - audit: Stores audit log entries for document actions
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'uploaded',
                extracted_text TEXT,
                summary TEXT,
                metadata_json TEXT,
                tts_path TEXT,
                image_path TEXT,
                version INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            action TEXT,
            actor TEXT,
            note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        conn.close()

    def insert_document(self, filename, extracted_text=None):
        """Insert a new document into the database.
        
        Args:
            filename: Name of the document file.
            extracted_text: Optional extracted text content from the document.
            
        Returns:
            int: The ID of the newly inserted document.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (filename, extracted_text) VALUES (?, ?)""", (filename, extracted_text))
        conn.commit()
        document_id = cursor.lastrowid
        conn.close()
        self.log_audit(document_id, "insert", "system", f"Document {filename} uploaded")
        return document_id

    def get_document(self, document_id):
        """Retrieve a document by its ID.
        
        Args:
            document_id: The ID of the document to retrieve.
            
        Returns:
            dict: Dictionary containing document data with keys: id, filename,
                  uploaded_at, status, extracted_text, summary, metadata_json,
                  tts_path, image_path, version. Returns None if document not found.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM documents WHERE id = ?""", (document_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None 
        
        return {
            "id": row[0],
            "filename": row[1],
            "uploaded_at": row[2],
            "status": row[3],
            "extracted_text": row[4],
            "summary": row[5],
            "metadata_json": row[6],
            "tts_path": row[7],
            "image_path":row[8],
            "version":row[9]
        }
    
    def update_extracted_text(self, document_id, extracted_text):
        """Update the extracted text field for a document.
        
        Args:
            document_id: The ID of the document to update.
            extracted_text: The extracted text content to store.
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents SET extracted_text = ? WHERE id = ?
        """, (extracted_text, document_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            self.log_audit(document_id, "update", "system", "Extracted text updated")
        return success
    
    def update_summary(self, document_id, summary):
        """Update the summary field for a document.
        
        Args:
            document_id: The ID of the document to update.
            summary: The summary text to store.
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents SET summary = ? WHERE id = ?
        """, (summary, document_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            self.log_audit(document_id, "update", "system", "Summary updated")
        return success
    
    def update_tts_path(self, doc_id: int, tts_path: str):
        """Update the text-to-speech audio file path for a document.
        
        Args:
            doc_id: The ID of the document to update.
            tts_path: Path to the generated audio file.
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents SET tts_path = ? WHERE id = ?
        """, (tts_path, doc_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            self.log_audit(doc_id, "update", "system", f"TTS path updated: {tts_path}")
        return success
    
    def update_image_path(self, doc_id: int, image_path: str):
        """Update the generated image file path for a document.
        
        Args:
            doc_id: The ID of the document to update.
            image_path: Path to the generated image file.
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents SET image_path = ? WHERE id = ?
        """, (image_path, doc_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            self.log_audit(doc_id, "update", "system", f"Image path updated: {image_path}")            
        return success
    
    def update_status(self, doc_id: int, status: str):
        """Update the processing status for a document.
        
        Args:
            doc_id: The ID of the document to update.
            status: The new status (e.g., 'uploaded', 'text_extracted', 
                   'summarized', 'tts_done', 'image_generated', 'complete').
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents SET status = ? WHERE id = ?
        """, (status, doc_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            self.log_audit(doc_id, "update", "system", f"Status updated to: {status}")
        return success

    def log_audit(self, document_id, action, actor, note):
        """Log an audit entry for a document action.
        
        Records actions performed on documents for tracking and auditing purposes.
        
        Args:
            document_id: The ID of the document the action was performed on.
            action: The action type (e.g., 'insert', 'update', 'delete').
            actor: Who or what performed the action (e.g., 'system', 'user').
            note: Additional notes or description of the action.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit (document_id, action, actor, note) VALUES (?, ?, ?, ?)
        """, (document_id, action, actor, note))
        conn.commit()
        conn.close()
    