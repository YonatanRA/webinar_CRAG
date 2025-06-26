from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_transformers.embeddings_redundant_filter import EmbeddingsRedundantFilter
from langchain.retrievers.document_compressors import FlashrankRerank, DocumentCompressorPipeline
import pickle


def ensemble_retriever(collection_name: str) -> EnsembleRetriever:
    
    """
    Recuperación desde ChromaDB y BM25.
    
    Params:
    collection_name: str, coleccion a ser usada 

    Return:
    EnsembleRetriever, ChromaDB+BM25+ReRanker 
    """
    
    embeddings = OpenAIEmbeddings()
    
    # carga chromaDB
    retriver_chroma = Chroma(persist_directory='../data/chroma_db',
                             collection_name=collection_name, 
                             embedding_function=embeddings)
    
    retriver_chroma = retriver_chroma.as_retriever(search_type='mmr', search_kwargs={'k':20, 
                                                                                     'lambda_mult': 0.5})
    
    
    # carga BM25
    with open(f'../data/{collection_name}_bm25', 'rb') as bm25_file:
        bm25_retriever = pickle.load(bm25_file)
            
    
    bm25_retriever.k = 10
        
    ensemble_retriever = EnsembleRetriever(retrievers=[retriver_chroma, bm25_retriever],
                                           weights=[0.5, 0.5])

    redundant_filter = EmbeddingsRedundantFilter(embeddings=embeddings)

    reranker = FlashrankRerank()

    pipeline_compressor = DocumentCompressorPipeline(transformers=[redundant_filter, reranker])

    compression_pipeline = ContextualCompressionRetriever(base_compressor=pipeline_compressor,
                                                          base_retriever=ensemble_retriever)

    return compression_pipeline
