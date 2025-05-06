"""
vector_db_connect.py
A simple example to connect to a Milvus vector database using PyMilvus.
"""
from pymilvus import connections

# Update these variables with your Milvus server details
MILVUS_HOST = "localhost"  # or your Milvus server IP/domain
MILVUS_PORT = "19530"      # default Milvus port

if __name__ == "__main__":
    try:
        print(f"Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT} ...")
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
        print("Successfully connected to Milvus!")
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
