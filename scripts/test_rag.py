#!/usr/bin/env python3
"""
Test script for RAG functionality in the pricing API.
"""

import requests
import json
from typing import Dict, Any


def test_rag_search():
    """Test the RAG search endpoint."""
    print("Testing RAG Search...")
    
    # Test queries
    test_queries = [
        "cheapest models for text generation",
        "models that support image processing",
        "fast models for coding",
        "models under $0.01 per token",
        "multimodal models"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        
        response = requests.post(
            "http://127.0.0.1:8000/rag/search",
            json={
                "query": query,
                "max_results": 3
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', {}).get('results', [])
            
            for i, result in enumerate(results[:2]):  # Show top 2 results
                print(f"  {i+1}. {result['model_name']} ({result['metadata']['provider']})")
                print(f"     {result['content'][:100]}...")
        else:
            print(f"  Error: {response.status_code} - {response.text}")


def test_rag_recommendations():
    """Test the RAG recommendations endpoint."""
    print("\nTesting RAG Recommendations...")
    
    # Test use cases
    test_cases = [
        ("coding", 50, 10000),
        ("document analysis", 100, 50000),
        ("image processing", 25, 5000),
        ("chatbot", 75, 20000)
    ]
    
    for use_case, budget, tokens in test_cases:
        print(f"\nUse case: {use_case} (Budget: ${budget}, Tokens: {tokens:,})")
        
        response = requests.post(
            f"http://127.0.0.1:8000/rag/recommendations",
            params={
                "use_case": use_case,
                "budget": budget,
                "max_tokens": tokens
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('data', {}).get('recommendations', [])
            
            for i, rec in enumerate(recommendations[:3]):  # Show top 3
                cost_str = f"${rec['estimated_cost']:.4f}" if rec['estimated_cost'] else "N/A"
                print(f"  {i+1}. {rec['model_name']} ({rec['provider']}) - {cost_str}")
                print(f"     {rec['reasoning'][:80]}...")
        else:
            print(f"  Error: {response.status_code} - {response.text}")


def test_index_endpoint():
    """Test the indexing endpoint."""
    print("\nTesting Index Endpoint...")
    
    response = requests.post("http://127.0.0.1:8000/rag/index")
    
    if response.status_code == 200:
        print("  Models indexed successfully!")
    else:
        print(f"  Error: {response.status_code} - {response.text}")


def main():
    """Run all RAG tests."""
    print("RAG Integration Test Suite")
    print("=" * 40)
    
    try:
        # Test indexing first
        test_index_endpoint()
        
        # Test search functionality
        test_rag_search()
        
        # Test recommendations
        test_rag_recommendations()
        
        print("\n" + "=" * 40)
        print("RAG tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"Error during testing: {e}")


if __name__ == "__main__":
    main() 