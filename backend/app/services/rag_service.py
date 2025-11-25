import logging
import os
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from config import settings

logger = logging.getLogger(__name__)


class RagService:
    """Service for RAG (Retrieval Augmented Generation) operations"""

    def __init__(self):
        self.vector_db_path = settings.absolute_vector_db_path
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model
        )
        self.vector_store: Optional[FAISS] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Initialize or load vector store"""
        try:
            if os.path.exists(self.vector_db_path) and os.path.exists(
                os.path.join(self.vector_db_path, "index.faiss")
            ):
                logger.info(f"Loading existing vector store from {self.vector_db_path}")
                self.vector_store = FAISS.load_local(
                    self.vector_db_path, self.embeddings
                )
            else:
                logger.info("Initializing new vector store")
                # Create empty vector store
                self.vector_store = None
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            self.vector_store = None

    async def ingest_file(self, file_path: str) -> int:
        """
        Ingest a file into the vector store

        Args:
            file_path: Path to the file to ingest

        Returns:
            Number of chunks added
        """
        try:
            # Load document
            if file_path.lower().endswith(".pdf"):
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif file_path.lower().endswith(".txt"):
                from langchain_community.document_loaders import TextLoader
                loader = TextLoader(file_path)
                documents = loader.load()
            else:
                raise ValueError("Unsupported file format. Only PDF and TXT are supported.")

            # Split text
            chunks = self.text_splitter.split_documents(documents)

            if not chunks:
                logger.warning("No text chunks found in document")
                return 0

            # Add to vector store
            if self.vector_store is None:
                logger.info("Creating new vector store from documents")
                
                # Manually embed to ensure numpy array
                texts = [d.page_content for d in chunks]
                metadatas = [d.metadata for d in chunks]
                embeddings_list = self.embeddings.embed_documents(texts)
                
                import numpy as np
                import faiss
                from langchain_community.docstore.in_memory import InMemoryDocstore
                
                # Convert to numpy
                embeddings = np.array(embeddings_list, dtype=np.float32)
                
                # Create index
                dimension = embeddings.shape[1]
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings)
                
                # Create docstore
                docstore = InMemoryDocstore()
                index_to_docstore_id = {}
                for i, (text, meta) in enumerate(zip(texts, metadatas)):
                    doc = Document(page_content=text, metadata=meta)
                    docstore.add({str(i): doc})
                    index_to_docstore_id[i] = str(i)
                    
                # Create FAISS store
                self.vector_store = FAISS(
                    embedding_function=self.embeddings,
                    index=index,
                    docstore=docstore,
                    index_to_docstore_id=index_to_docstore_id
                )
            else:
                logger.info("Adding documents to existing vector store")
                self.vector_store.add_documents(chunks)

            # Save vector store
            self._save_vector_store()

            logger.info(f"Ingested {len(chunks)} chunks from {file_path}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            raise

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """
        Retrieve relevant documents for a query

        Args:
            query: Search query
            k: Number of documents to retrieve

        Returns:
            List of relevant documents
        """
        if not self.vector_store:
            logger.warning("Vector store not initialized")
            return []

        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return docs
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    def _save_vector_store(self):
        """Save vector store to disk"""
        if self.vector_store:
            os.makedirs(self.vector_db_path, exist_ok=True)
            self.vector_store.save_local(self.vector_db_path)
            logger.info(f"Saved vector store to {self.vector_db_path}")


# Create singleton instance
rag_service = RagService()
