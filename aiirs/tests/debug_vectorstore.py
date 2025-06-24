from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings
from pathlib import Path
import json

# Load vector store
vectorstore_dir = Path('aiiris_backend/vectorstore')
if vectorstore_dir.exists():
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
    vectorstore = FAISS.load_local(str(vectorstore_dir), embeddings, allow_dangerous_deserialization=True)
    
    print(f'Total documents in vector store: {len(vectorstore.docstore._dict)}')
    print('\nFirst 5 documents metadata:')
    count = 0
    for doc_id, document in vectorstore.docstore._dict.items():
        if count < 5:
            print(f'Doc ID: {doc_id}')
            print(f'Metadata: {document.metadata}')
            print(f'Content preview: {document.page_content[:100]}...')
            print('---')
            count += 1
    
    # Check what filenames exist in metadata
    filenames = set()
    for doc_id, document in vectorstore.docstore._dict.items():
        filename = document.metadata.get('file_name')
        if filename:
            filenames.add(filename)
    
    print(f'\nFilenames found in vector store: {filenames}')
else:
    print('Vector store not found') 