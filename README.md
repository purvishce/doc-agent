# 🧠 Agentic AI Document Processor

**An intelligent, multi-tool AI agent that automatically processes documents using LLMs, TTS, and image generation, all orchestrated through a SQLite database and a Gradio web interface.**

---
## 🔹 Gradio UI Screenshot

![Agentic AI Gradio UI](https://github.com/purvishce/doc-agent/blob/main/gradiooutput.png)

---
## 🔹 Key Features

* Automated workflow planning: text extraction, summarization, TTS, image generation
* Multi-modal AI processing: summary → audio → image
* Persistent SQLite storage
* Interactive Gradio web interface
* Modular, extensible design

---

## 🔹 Folder Structure

```
doc-agent/
│
├─ src/
│   ├─ main.py             # Entry point for tests & manual runs
│   ├─ ui.py               # Gradio UI for interactive usage
│   ├─ database.py         # SQLite DB operations
│   ├─ agent_planner.py    # Core AI agent logic & workflow
│   ├─ tts_service.py      # Optional TTS service helper
│   └─ models/             # Optional Python models for structured data
│
├─ data/
│   ├─ doc_agent.db         # SQLite database
│   └─ uploads/             # Uploaded documents
│
├─ output/
│   ├─ audio/              # Generated MP3 files
│   └─ images/             # Generated images
│
├─ database_migration.py    # Helper script to add DB columns
├─ .env                     # OpenAI API key configuration
└─ README.md
```

---

## 🔹 Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/doc-agent.git
cd doc-agent
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your OpenAI API key in `.env`:

```
OPENAI_API_KEY=sk-xxxxxx
```

---

## 🔹 Usage

### Run Agentic Workflow in Python:

```python
from agent_planner import AgentPlanner

planner = AgentPlanner()
doc_id = 1  # your document ID
planner.run_workflow(doc_id)
```

### Run Gradio Web Interface:

```bash
python src/main.py
```

* Upload documents
* View AI-generated summary, TTS audio, and images
* Workflow is fully automated

---

## 🔹 Database & Storage

* SQLite stores all document info: metadata, extracted text, summary, TTS path, image path, status
* `output/audio` → TTS files
* `output/images` → generated images

---

## 🔹 License

MIT License — feel free to use and extend!
