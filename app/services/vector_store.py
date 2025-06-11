import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
import os
import uuid
from app.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        """Initialize ChromaDB client with persistent storage"""
        # Create persist directory if it doesn't exist
        os.makedirs(settings.chroma_persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Cache for collections
        self._collections = {}
    
    def get_collection_name(self, tenant_id: str, collection_type: str) -> str:
        """Generate collection name for tenant and type"""
        return f"tenant_{tenant_id}_{collection_type}"
    
    def get_collection(self, tenant_id: str, collection_type: str):
        """Get or create collection for tenant and type"""
        collection_name = self.get_collection_name(tenant_id, collection_type)
        
        if collection_name not in self._collections:
            try:
                # Try to get existing collection
                collection = self.client.get_collection(name=collection_name)
            except ValueError:
                # Create new collection if it doesn't exist
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            
            self._collections[collection_name] = collection
        
        return self._collections[collection_name]
    
    async def add_documents(
        self,
        tenant_id: str,
        collection_type: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """Add documents to tenant's collection"""
        try:
            collection = self.get_collection(tenant_id, collection_type)
            
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to {tenant_id}:{collection_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return False
    
    async def update_documents(
        self,
        tenant_id: str,
        collection_type: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """Update documents in tenant's collection"""
        try:
            collection = self.get_collection(tenant_id, collection_type)
            
            collection.update(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Updated {len(documents)} documents in {tenant_id}:{collection_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating documents in vector store: {e}")
            return False
    
    async def delete_documents(
        self,
        tenant_id: str,
        collection_type: str,
        ids: List[str]
    ) -> bool:
        """Delete documents from tenant's collection"""
        try:
            collection = self.get_collection(tenant_id, collection_type)
            
            collection.delete(ids=ids)
            
            logger.info(f"Deleted {len(ids)} documents from {tenant_id}:{collection_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting documents from vector store: {e}")
            return False
    
    async def search_documents(
        self,
        tenant_id: str,
        collection_type: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search documents in tenant's collection"""
        try:
            collection = self.get_collection(tenant_id, collection_type)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            return {
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "ids": results["ids"][0] if results["ids"] else []
            }
            
        except Exception as e:
            logger.error(f"Error searching documents in vector store: {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}
    
    async def get_collection_count(self, tenant_id: str, collection_type: str) -> int:
        """Get document count in tenant's collection"""
        try:
            collection = self.get_collection(tenant_id, collection_type)
            return collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0
    
    async def delete_tenant_collections(self, tenant_id: str) -> bool:
        """Delete all collections for a tenant"""
        try:
            # Get all collections for this tenant
            collections = self.client.list_collections()
            tenant_prefix = f"tenant_{tenant_id}_"
            
            for collection in collections:
                if collection.name.startswith(tenant_prefix):
                    self.client.delete_collection(name=collection.name)
                    # Remove from cache
                    if collection.name in self._collections:
                        del self._collections[collection.name]
            
            logger.info(f"Deleted all collections for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting tenant collections: {e}")
            return False
    
    # Knowledge Item Helper Methods
    async def add_knowledge_item(
        self,
        knowledge_id: str,
        title: str,
        content: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add knowledge item to vector store"""
        try:
            from app.services.openai_service import openai_service
            
            # Create embedding
            content_for_embedding = f"{title}\n{content}"
            embedding = await openai_service.create_embedding(content_for_embedding)
            
            # Generate vector ID
            vector_id = f"knowledge_{tenant_id}_{str(uuid.uuid4())}"
            
            # Prepare metadata
            item_metadata = {
                "knowledge_id": knowledge_id,
                "title": title,
                "type": "knowledge",
                **(metadata or {})
            }
            
            # Add to vector store
            success = await self.add_documents(
                tenant_id=tenant_id,
                collection_type="knowledge",
                documents=[content],
                embeddings=[embedding],
                metadatas=[item_metadata],
                ids=[vector_id]
            )
            
            if success:
                return vector_id
            else:
                raise Exception("Failed to add to vector store")
            
        except Exception as e:
            logger.error(f"Error adding knowledge item to vector store: {e}")
            raise
    
    async def update_knowledge_item(
        self,
        vector_id: str,
        title: str,
        content: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update knowledge item in vector store"""
        try:
            from app.services.openai_service import openai_service
            
            # Create new embedding
            content_for_embedding = f"{title}\n{content}"
            embedding = await openai_service.create_embedding(content_for_embedding)
            
            # Prepare metadata
            item_metadata = {
                "title": title,
                "type": "knowledge",
                **(metadata or {})
            }
            
            # Update in vector store
            return await self.update_documents(
                tenant_id=tenant_id,
                collection_type="knowledge",
                documents=[content],
                embeddings=[embedding],
                metadatas=[item_metadata],
                ids=[vector_id]
            )
            
        except Exception as e:
            logger.error(f"Error updating knowledge item in vector store: {e}")
            return False
    
    async def delete_knowledge_item(self, vector_id: str, tenant_id: str) -> bool:
        """Delete knowledge item from vector store"""
        try:
            return await self.delete_documents(
                tenant_id=tenant_id,
                collection_type="knowledge",
                ids=[vector_id]
            )
        except Exception as e:
            logger.error(f"Error deleting knowledge item from vector store: {e}")
            return False
    
    async def search_knowledge(
        self,
        query: str,
        tenant_id: str,
        limit: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search knowledge items using vector similarity"""
        try:
            from app.services.openai_service import openai_service
            
            # Create embedding for query
            query_embedding = await openai_service.create_embedding(query)
            
            # Search in vector store
            results = await self.search_documents(
                tenant_id=tenant_id,
                collection_type="knowledge",
                query_embedding=query_embedding,
                n_results=limit
            )
            
            # Convert to search results format
            search_results = []
            for i in range(len(results["ids"])):
                # Convert distance to similarity score
                similarity_score = 1 - results["distances"][i]
                
                # Filter by minimum score
                if similarity_score >= min_score:
                    metadata = results["metadatas"][i] if i < len(results["metadatas"]) else {}
                    search_results.append({
                        "id": metadata.get("knowledge_id", results["ids"][i]),
                        "vector_id": results["ids"][i],
                        "content": results["documents"][i],
                        "score": similarity_score,
                        "metadata": metadata
                    })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector store"""
        try:
            # Test basic connectivity
            collections = self.client.list_collections()
            
            # Count total vectors across all collections
            total_vectors = 0
            collection_details = []
            
            for collection in collections:
                try:
                    count = collection.count()
                    total_vectors += count
                    collection_details.append({
                        "name": collection.name,
                        "count": count
                    })
                except Exception as e:
                    logger.warning(f"Error getting count for collection {collection.name}: {e}")
            
            # Calculate estimated index size (rough estimate)
            index_size = total_vectors * 1536 * 4  # Assuming 1536-dim embeddings, 4 bytes per float
            
            return {
                "healthy": True,
                "collections": len(collections),
                "total_vectors": total_vectors,
                "collection_details": collection_details,
                "index_size": index_size,
                "persist_directory": settings.chroma_persist_directory,
                "status": "operational"
            }
            
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "collections": 0,
                "total_vectors": 0,
                "status": "error"
            }


# Global vector store instance
vector_store = VectorStore() 