# To use this script, you need to install the chromadb library.
# You can install it using pip:
# pip install chromadb
import chromadb

# Initialize the Chroma DB client
# This will create a persistent client that stores data in a directory named 'chroma_db' in the same directory as the script.
# If the directory doesn't exist, it will be created.
client = chromadb.PersistentClient(path="./chroma_db")

# You can also use an in-memory client (data is lost when the script ends):
# client = chromadb.Client()

# Or, if you are running Chroma DB as a server:
# client = chromadb.HttpClient(url="http://localhost:8000")

print("Chroma DB client initialized.")
print(f"Client version: {chromadb.__version__}")
print("Persistent data will be stored in: ./chroma_db")

#tell me Bally

# To use Chroma DB, you typically work with collections.
# A collection is a group of embeddings.

# --- Creating or Getting a Collection ---
# If the collection already exists, this will load it. Otherwise, it will be created.
# collection_name = "my_sample_collection"
# print(f"\nAttempting to create or get collection: {collection_name}")
# try:
#     collection = client.get_or_create_collection(name=collection_name)
#     print(f"Successfully got/created collection: {collection_name}")
#     print(f"Number of items in collection: {collection.count()}")

#     # --- Adding Documents to a Collection ---
#     # Chroma DB will automatically use a default embedding model if you don't specify one.
#     # For more control, you can specify your own embedding function.
#     # See Chroma DB documentation for details on embedding functions.
#     if collection.count() == 0:
#         print("\nAdding documents to the collection (this may take a moment for the first run as model might be downloaded)...")
#         collection.add(
#             documents=[
#                 "This is document1 about apples",
#                 "This is document2 about bananas",
#                 "This is document3 about oranges"
#             ],
#             metadatas=[
#                 {"source": "doc_source_1"},
#                 {"source": "doc_source_2"},
#                 {"source": "doc_source_3"}
#             ],
#             ids=["id1", "id2", "id3"] # IDs must be unique
#         )
#         print(f"Added 3 documents. New collection count: {collection.count()}")
#     else:
#         print("\nDocuments already exist in the collection.")

#     # --- Querying a Collection ---
#     query_texts = ["What fruits are mentioned?"]
#     print(f"\nQuerying the collection with: {query_texts}")
#     results = collection.query(
#         query_texts=query_texts,
#         n_results=2 # Get the top 2 most similar results
#     )
#     print("Query results:")
#     for i, (docs, dists, metas) in enumerate(zip(results.get('documents', []), results.get('distances', []), results.get('metadatas', []))):
#         print(f"  Query: {query_texts[i]}")
#         if docs:
#             for doc, dist, meta in zip(docs, dists, metas):
#                 print(f"    Document: {doc}, Distance: {dist:.4f}, Metadata: {meta}")
#         else:
#             print("    No documents found for this query.")

# except Exception as e:
#     print(f"An error occurred: {e}")
#     print("Please ensure ChromaDB is running or accessible if using HttpClient.")
#     print("If using PersistentClient, check directory permissions and available space.")

# --- List all collections ---
# print("\n--- All Collections ---")
# collections = client.list_collections()
# if collections:
#     for coll in collections:
#         print(f"Collection: {coll.name}, ID: {coll.id}, Count: {coll.count()}")
# else:
#     print("No collections found.")

# --- Deleting a Collection ---
# To delete a collection (use with caution!):
# print(f"\nAttempting to delete collection: {collection_name}")
# try:
#    client.delete_collection(name=collection_name)
#    print(f"Successfully deleted collection: {collection_name}")
# except Exception as e:
#    print(f"Error deleting collection {collection_name}: {e}")
