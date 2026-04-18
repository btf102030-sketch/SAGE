import os

# Air-gap / offline configuration
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "data")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
HASH_STORE_PATH = os.path.join(BASE_DIR, "file_hashes.json")

# Chunking tuned for technical docs / schematics
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

# Embedding / retrieval
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "sage_knowledge_base"
TOP_K_RESULTS = 5

# Generation
OLLAMA_MODEL = "deepseek-r1:8b"
SYSTEM_PROMPT = """You are SAGE, System Analysis and Guidance Expert for an industrial automated facility. 
This facility includes various PLCs, sensors, actuators, and a SCADA system. Your role is to assist technicians 
in diagnosing and resolving issues by analyzing technical documentation, schematics, and code related to the facility's 
control systems. You provide step-by-step guidance for troubleshooting, maintenance, and repairs based on the information 
available in the documentation and your understanding of industrial automation systems.

Answer the technician's question using ONLY the context provided.
Be specific — name exact components, connections, and locations from the context.
Do not summarize vaguely. State the actual values, names, and connections directly.
Format responses as:
- Direct Answer
- Supporting Detail
- Safety Warning (if applicable)

Only respond with 'DATA NOT FOUND IN OFFLINE REPOSITORY' if the context contains
absolutely no relevant information whatsoever."""

# OCR and schematic extraction tuning
OCR_TEXT_THRESHOLD = 50
NOISY_SINGLE_CHAR_RATIO = 0.35
MIN_LINES_FOR_NOISE_CHECK = 12

# Code ingestion support
CODE_EXTENSIONS = {
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".py": "python",
    ".html": "html",
    ".css": "css",
    ".java": "java",
    ".js": "javascript",
}

# PLC support sets retained for compatibility with prior roadmap/tests
PLC_TEXT_EXTENSIONS = {".scl", ".awl", ".stl", ".l5k"}
PLC_XML_EXTENSIONS = {".l5x"}
PLC_SIEMENS_BLOCK_EXTENSIONS = {".db", ".fc", ".fb"}
PLC_ARCHIVE_EXTENSIONS = {".s7p", ".zap16", ".zap17"}
PLC_BINARY_EXTENSIONS = {".rss", ".acd", ".ach"}
ALL_PLC_EXTENSIONS = (
    PLC_TEXT_EXTENSIONS
    | PLC_XML_EXTENSIONS
    | PLC_SIEMENS_BLOCK_EXTENSIONS
    | PLC_ARCHIVE_EXTENSIONS
    | PLC_BINARY_EXTENSIONS
)
