
import chromadb
from chromadb.config import Settings

print("Testing ChromaDB initialization...")
try:
    # Try without settings
    client = chromadb.PersistentClient(path="./data/chroma_db_test")
    print("PersistentClient without settings works!")
    print(f"Client: {client}")
    
    # Try with settings
    settings = Settings(
        anonymized_telemetry=False,
        allow_reset=True,
    )
    client2 = chromadb.PersistentClient(path="./data/chroma_db_test2", settings=settings)
    print("PersistentClient with settings works!")
    print(f"Client2: {client2}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
