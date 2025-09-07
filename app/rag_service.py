import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

from app.db.repository_provider_model import get_all_pricing_data
from app.models import Modality

logger = logging.getLogger(__name__)


@dataclass
class ModelDocument:
    """Represents a model document for RAG indexing."""
    content: str
    metadata: Dict[str, Any]
    model_name: str


class RAGService:
    """Service for RAG operations on model pricing data."""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Try to get existing collection, create if it doesn't exist
        try:
            self.collection = self.client.get_collection(name="model_pricing")
        except:
            self.collection = self.client.create_collection(
                name="model_pricing",
                metadata={"description": "Model pricing and capability information"}
            )
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def create_model_document(self, provider_model) -> ModelDocument:
        """Create a document representation of a model for RAG indexing."""
        
        # Create a comprehensive description
        modalities = [m.value for m in provider_model.modalities]
        modality_str = ", ".join(modalities) if modalities else "text"
        
        # Calculate pricing per token
        input_price_per_token = provider_model.input_cost_per_mtok / 1_000_000
        output_price_per_token = provider_model.output_cost_per_mtok / 1_000_000
        
        # Create rich content description
        content_parts = [
            f"{provider_model.api_model_name} is a {modality_str} model from {provider_model.provider.name}.",
            f"Input tokens cost ${input_price_per_token:.6f} per token.",
            f"Output tokens cost ${output_price_per_token:.6f} per token.",
            f"Context window: {provider_model.context_window:,} tokens."
        ]
        
        if provider_model.max_output_tokens:
            content_parts.append(f"Maximum output: {provider_model.max_output_tokens:,} tokens.")
        
        if provider_model.tokens_per_second:
            content_parts.append(f"Speed: {provider_model.tokens_per_second:.1f} tokens/second.")
        
        if provider_model.supports_tools:
            content_parts.append("Supports function calling and tools.")
        
        # Add use case suggestions based on model characteristics
        if "text" in modalities:
            content_parts.append("Suitable for text generation, analysis, and conversation.")
        if "image" in modalities:
            content_parts.append("Can process and analyze images.")
        if "audio" in modalities:
            content_parts.append("Supports audio processing and transcription.")
        
        # Cost efficiency hints
        if input_price_per_token < 0.001:
            content_parts.append("Very cost-effective for input processing.")
        if output_price_per_token < 0.01:
            content_parts.append("Affordable for text generation.")
        
        content = " ".join(content_parts)
        
        # Create metadata with only non-None values
        metadata = {
            "model_name": provider_model.api_model_name,
            "provider": provider_model.provider.name,
            "modalities": ", ".join(modalities) if modalities else "text",
            "input_price_per_token": input_price_per_token,
            "output_price_per_token": output_price_per_token,
            "context_window": provider_model.context_window,
            "supports_tools": provider_model.supports_tools,
            "is_active": provider_model.is_active
        }
        
        # Add optional fields only if they're not None
        if provider_model.max_output_tokens is not None:
            metadata["max_output_tokens"] = provider_model.max_output_tokens
        if provider_model.tokens_per_second is not None:
            metadata["tokens_per_second"] = provider_model.tokens_per_second
        
        return ModelDocument(
            content=content,
            metadata=metadata,
            model_name=provider_model.api_model_name
        )
    
    def index_models(self, db_session) -> None:
        """Index all active models in the vector database."""
        try:
            # Get all active models
            provider_models = get_all_pricing_data(db_session)
            
            if not provider_models:
                logger.warning("No models found to index")
                return
            
            # Clear existing collection - delete all documents
            try:
                self.collection.delete(where={"is_active": True})
            except:
                # If delete fails, try to recreate the collection
                try:
                    self.client.delete_collection(name="model_pricing")
                except:
                    pass
                self.collection = self.client.create_collection(
                    name="model_pricing",
                    metadata={"description": "Model pricing and capability information"}
                )
            
            # Create documents and embeddings
            documents = []
            metadatas = []
            ids = []
            
            for provider_model in provider_models:
                doc = self.create_model_document(provider_model)
                
                documents.append(doc.content)
                metadatas.append(doc.metadata)
                ids.append(doc.model_name)
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Indexed {len(documents)} models in vector database")
            
        except Exception as e:
            logger.error(f"Error indexing models: {e}")
            raise
    
    def search_models(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for models using semantic similarity."""
        try:
            # Perform semantic search without filters for now
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    'model_name': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return []
    
    def get_model_recommendations(self, use_case: str, budget: Optional[float] = None,
                                 max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Get model recommendations based on use case and constraints."""
        
        # Build search query based on use case
        search_query = f"models for {use_case}"
        
        # Apply filters if constraints provided
        filters = {"is_active": True}
        if budget:
            # Estimate cost for given tokens and filter by budget
            if max_tokens:
                estimated_cost = max_tokens * 0.01  # Rough estimate
                if estimated_cost > budget:
                    search_query += f" with low cost under ${budget}"
        
        # Search for relevant models
        results = self.search_models(search_query, n_results=10)
        
        # Analyze and rank results
        recommendations = {
            'use_case': use_case,
            'budget': budget,
            'max_tokens': max_tokens,
            'recommendations': [],
            'cost_analysis': {},
            'provider_breakdown': {}
        }
        
        if results:
            # Group by provider
            provider_models = {}
            for result in results:
                provider = result['metadata']['provider']
                if provider not in provider_models:
                    provider_models[provider] = []
                provider_models[provider].append(result)
            
            # Create recommendations
            for result in results[:5]:  # Top 5 recommendations
                metadata = result['metadata']
                
                # Calculate estimated cost if tokens provided
                estimated_cost = None
                if max_tokens:
                    input_cost = metadata['input_price_per_token'] * max_tokens * 0.3  # Assume 30% input
                    output_cost = metadata['output_price_per_token'] * max_tokens * 0.7  # Assume 70% output
                    estimated_cost = input_cost + output_cost
                
                recommendation = {
                    'model_name': result['model_name'],
                    'provider': metadata['provider'],
                    'modalities': metadata['modalities'].split(', ') if metadata['modalities'] else [],  # Convert back to list
                    'context_window': metadata['context_window'],
                    'input_price': metadata['input_price_per_token'],
                    'output_price': metadata['output_price_per_token'],
                    'estimated_cost': estimated_cost,
                    'reasoning': result['content'][:200] + "...",
                    'budget_friendly': estimated_cost and estimated_cost < (budget or float('inf'))
                }
                
                recommendations['recommendations'].append(recommendation)
            
            # Cost analysis
            if recommendations['recommendations']:
                costs = [r['estimated_cost'] for r in recommendations['recommendations'] if r['estimated_cost']]
                if costs:
                    recommendations['cost_analysis'] = {
                        'min_cost': min(costs),
                        'max_cost': max(costs),
                        'avg_cost': sum(costs) / len(costs),
                        'budget_viable': all(c <= (budget or float('inf')) for c in costs)
                    }
            
            # Provider breakdown
            recommendations['provider_breakdown'] = {
                provider: len(models) for provider, models in provider_models.items()
            }
        
        return recommendations


# Global RAG service instance
rag_service = RAGService() 