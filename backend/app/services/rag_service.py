import logging
import os
from typing import List, Optional, Sequence
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

    async def ingest_file(self, file_path: str, document_id: str) -> int:
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
            for idx, chunk in enumerate(chunks):
                if chunk.metadata is None:
                    chunk.metadata = {}
                chunk.metadata.update(
                    {
                        "document_id": document_id,
                        "source": file_path,
                        "chunk_index": idx,
                    }
                )

            if not chunks:
                logger.warning("No text chunks found in document")
                return 0

            # Add to vector store
            ids = [self._build_chunk_id(document_id, idx) for idx in range(len(chunks))]

            if self.vector_store is None:
                logger.info("Creating new vector store from documents")
                self.vector_store = FAISS.from_documents(
                    chunks, self.embeddings, ids=ids
                )
            else:
                logger.info("Adding documents to existing vector store")
                self.vector_store.add_documents(chunks, ids=ids)

            # Save vector store
            self._save_vector_store()

            logger.info(f"Ingested {len(chunks)} chunks from {file_path}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            raise

    def retrieve(
        self, query: str, k: int = 3, document_ids: Optional[Sequence[str]] = None
    ) -> List[Document]:
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
            docs = self.vector_store.similarity_search(query, k=max(k * 2, k))
            selected_ids = set(document_ids) if document_ids else None
            if selected_ids:
                filtered = [
                    doc
                    for doc in docs
                    if doc.metadata.get("document_id") in selected_ids
                ]
                return filtered[:k]
            return docs[:k]
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    def _save_vector_store(self):
        """Save vector store to disk"""
        if self.vector_store:
            os.makedirs(self.vector_db_path, exist_ok=True)
            self.vector_store.save_local(self.vector_db_path)
            logger.info(f"Saved vector store to {self.vector_db_path}")

    def _build_chunk_id(self, document_id: str, chunk_idx: int) -> str:
        return f"{document_id}_{chunk_idx}"

    def remove_document(self, document_id: str) -> int:
        """Remove all chunks for a document from the vector store."""
        if not self.vector_store:
            return 0

        docstore = getattr(self.vector_store, "docstore", None)
        if not docstore or not hasattr(docstore, "_dict"):
            logger.warning("Vector store docstore not available for deletion")
            return 0

        ids_to_remove = [
            doc_id
            for doc_id, doc in docstore._dict.items()
            if doc.metadata.get("document_id") == document_id
        ]

        if not ids_to_remove:
            return 0

        self.vector_store.delete(ids_to_remove)
        self._save_vector_store()
        logger.info(f"Removed {len(ids_to_remove)} chunks for document {document_id}")
        return len(ids_to_remove)


# Create singleton instance
rag_service = RagService()
