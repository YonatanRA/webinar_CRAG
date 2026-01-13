"""
Script for retrieving documents from vector database.
Extracted from notebooks/CRAG.ipynb
"""

from langchain.retrievers import ContextualCompressionRetriever, BM25Retriever, EnsembleRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_transformers.embeddings_redundant_filter import EmbeddingsRedundantFilter
from langchain.retrievers.document_compressors import FlashrankRerank, DocumentCompressorPipeline
import pickle
import os


def ensemble_retriever(collection_name: str) -> ContextualCompressionRetriever:
    """
    Retrieval from ChromaDB and BM25 with compression and reranking.
    
    Args:
        collection_name: str, collection to be used
    
    Returns:
        ContextualCompressionRetriever, ChromaDB+BM25+ReRanker
    """
    embeddings = OpenAIEmbeddings()
    
    # Load ChromaDB
    retriever_chroma = Chroma(
        persist_directory='data/chroma_db',
        collection_name=collection_name,
        embedding_function=embeddings
    )
    
    retriever_chroma = retriever_chroma.as_retriever(
        search_type='mmr',
        search_kwargs={'k': 20, 'lambda_mult': 0.5}
    )
    
    # Load BM25
    bm25_path = f'data/{collection_name}_bm25'
    if not os.path.exists(bm25_path):
        raise FileNotFoundError(f"BM25 retriever not found at {bm25_path}. Please run create_vectordb.py first.")
    
    with open(bm25_path, 'rb') as bm25_file:
        bm25_retriever = pickle.load(bm25_file)
    
    bm25_retriever.k = 10
    
    # Create ensemble retriever
    ensemble = EnsembleRetriever(
        retrievers=[retriever_chroma, bm25_retriever],
        weights=[0.5, 0.5]
    )
    
    # Create compression pipeline
    redundant_filter = EmbeddingsRedundantFilter(embeddings=embeddings)
    reranker = FlashrankRerank()
    
    pipeline_compressor = DocumentCompressorPipeline(
        transformers=[redundant_filter, reranker]
    )
    
    compression_pipeline = ContextualCompressionRetriever(
        base_compressor=pipeline_compressor,
        base_retriever=ensemble
    )
    
    return compression_pipeline


if __name__ == '__main__':
    # Example usage
    retriever = ensemble_retriever('design')
    
    # Test query
    query = '¿qué es un sistema complejo?'
    print(f"Query: {query}\n")
    
    response = retriever.invoke(query)
    print(f"Retrieved {len(response)} documents:\n")
    
    for i, doc in enumerate(response, 1):
        print(f"Document {i}:")
        print(doc.page_content[:200] + "...\n")
