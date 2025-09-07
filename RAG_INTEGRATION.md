# RAG Integration for LLM Pricing API

This document describes the RAG (Retrieval-Augmented Generation) integration that enables natural language queries and intelligent model recommendations.

## Features

### 1. Natural Language Model Search
Search for models using natural language queries instead of knowing exact model names.

**Endpoint**: `POST /rag/search`

**Example Queries**:
- "cheapest models for text generation"
- "models that support image processing"
- "fast models for coding"
- "models under $0.01 per token"
- "multimodal models"

### 2. Intelligent Model Recommendations
Get personalized model recommendations based on use case and constraints.

**Endpoint**: `POST /rag/recommendations`

**Parameters**:
- `use_case`: Description of your use case (e.g., "coding", "document analysis")
- `budget`: Maximum budget in dollars (optional)
- `max_tokens`: Estimated token usage (optional)

### 3. Automatic Model Indexing
Models are automatically indexed in a vector database for semantic search.

**Endpoint**: `POST /rag/index`

## How It Works

### 1. Document Creation
Each model is converted into a rich document containing:
- Model description and capabilities
- Pricing information
- Use case suggestions
- Performance characteristics

### 2. Vector Embeddings
- Uses `sentence-transformers` with the `all-MiniLM-L6-v2` model
- Converts model descriptions and user queries to embeddings
- Stores embeddings in ChromaDB vector database

### 3. Semantic Search
- User queries are converted to embeddings
- Similarity search finds relevant models
- Results are ranked by relevance

### 4. Smart Recommendations
- Analyzes use case requirements
- Considers budget constraints
- Calculates cost estimates
- Provides reasoning for recommendations

## API Endpoints

### Search Models
```bash
curl -X POST "http://localhost:8000/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cheapest models for coding",
    "max_results": 5
  }'
```

### Get Recommendations
```bash
curl -X POST "http://localhost:8000/rag/recommendations?use_case=coding&budget=50&max_tokens=10000"
```

### Index Models
```bash
curl -X POST "http://localhost:8000/rag/index"
```

## Example Responses

### Search Response
```json
{
  "status": "success",
  "data": {
    "query": "cheapest models for coding",
    "results": [
      {
        "model_name": "claude-3-haiku",
        "content": "Claude 3 Haiku is a text model from Anthropic...",
        "metadata": {
          "provider": "Anthropic",
          "input_price_per_token": 0.00025,
          "output_price_per_token": 0.00125
        },
        "distance": 0.123
      }
    ],
    "total_results": 1
  }
}
```

### Recommendations Response
```json
{
  "status": "success",
  "data": {
    "use_case": "coding",
    "budget": 50,
    "max_tokens": 10000,
    "recommendations": [
      {
        "model_name": "claude-3-haiku",
        "provider": "Anthropic",
        "modalities": ["text"],
        "context_window": 200000,
        "input_price": 0.00025,
        "output_price": 0.00125,
        "estimated_cost": 8.75,
        "reasoning": "Very cost-effective for input processing...",
        "budget_friendly": true
      }
    ],
    "cost_analysis": {
      "min_cost": 8.75,
      "max_cost": 15.50,
      "avg_cost": 12.13,
      "budget_viable": true
    },
    "provider_breakdown": {
      "Anthropic": 2,
      "OpenAI": 1
    }
  }
}
```

## Benefits

1. **Natural Language Access**: No need to know exact model names
2. **Intelligent Recommendations**: Context-aware suggestions
3. **Cost Optimization**: Budget-aware model selection
4. **Use Case Matching**: Find models for specific tasks
5. **Dynamic Updates**: Incorporates real-time pricing changes

## Testing

Run the test script to verify RAG functionality:

```bash
python scripts/test_rag.py
```

## Dependencies

- `sentence-transformers`: For text embeddings
- `chromadb`: Vector database
- `numpy`: Numerical operations

## Configuration

The RAG service uses default settings:
- Embedding model: `all-MiniLM-L6-v2`
- Vector database: ChromaDB (persistent)
- Storage location: `./chroma_db`

## Future Enhancements

1. **Advanced Filtering**: Support for more complex filters
2. **Cost Optimization**: More sophisticated cost analysis
3. **Performance Metrics**: Include speed and quality metrics
4. **User Feedback**: Learn from user preferences
5. **Real-time Updates**: Automatic re-indexing on price changes 