# Chroma DB Connection Script

This repository contains a Python script (`chroma_connect.py`) that demonstrates how to connect to a Chroma vector database.

## `chroma_connect.py`

This script initializes a connection to a Chroma DB instance.

### Features:
- Shows how to import the `chromadb` library.
- Initializes a `PersistentClient`, which stores data locally in a `./chroma_db` directory.
  - Comments in the script also show how to initialize an `InMemoryClient` or an `HttpClient` (for connecting to a remote Chroma DB server).
- Prints the Chroma DB client version.
- Includes commented-out example code for:
    - Creating or getting a collection.
    - Adding documents to a collection (with sample documents, metadatas, and IDs).
    - Querying a collection with sample queries.
    - Listing all collections.
    - Deleting a collection.

### Prerequisites

Before running the script, you need to install the `chromadb` Python library:

```bash
pip install chromadb
```

You might also need other dependencies depending on the embedding models you choose to use with ChromaDB (e.g., `sentence-transformers`, `openai`, etc.), though the basic script and default embedding model should work with just `chromadb`.

### Running the Script

1.  **Ensure `chromadb` is installed:**
    ```bash
    pip install chromadb
    ```
2.  **Execute the Python script:**
    ```bash
    python chroma_connect.py
    ```

Upon successful execution, the script will print:
- A confirmation that the Chroma DB client has been initialized.
- The version of the `chromadb` library being used.
- The path where persistent data will be stored (`./chroma_db`).

### Customization

-   **Client Type**: Modify the `client` variable initialization in `chroma_connect.py` to switch between `PersistentClient`, `InMemoryClient`, or `HttpClient` based on your needs.
-   **Example Usage**: Uncomment and modify the example code sections at the end of the script to experiment with creating collections, adding data, and performing queries.
-   **Embedding Models**: For advanced usage, Chroma DB allows you to specify different embedding models. Refer to the official Chroma DB documentation for more details on how to integrate various embedding functions.
