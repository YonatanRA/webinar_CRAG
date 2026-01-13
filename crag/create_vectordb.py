"""
Script for creating vector database from PDF documents.
Extracted from notebooks/CRAG.ipynb
"""

from typing import List
import os
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain.retrievers import BM25Retriever

from tqdm import tqdm
import pickle

# Load environment variables
load_dotenv()

# API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


class VectorDB:
    """
    Class for creating and managing vector databases with contextualized chunks.
    """

    def __init__(self, collection_name: str):
        """
        Initialize the VectorDB with collection name and required components.
        
        Args:
            collection_name: str, name of the collection in the database
        """
        self.collection_name = collection_name
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )
        
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model='gpt-4o', temperature=0)
    
    def process_document(self, file_paths: List[str]) -> List[Document]:
        """
        Process each document by dividing it into chunks and generating context for each one.
        
        Args:
            file_paths: list of strings, paths to PDF or TXT files
        
        Returns:
            list of contextualized chunks
        """
        contextualized_chunks = []
        
        for file_path in file_paths:
            # Process PDF
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                pages = loader.load()

                for i in tqdm(range(0, len(pages)-2, 1), leave=False, desc='Chunking PDF file'):
                    document = pages[i].page_content + pages[i+1].page_content + pages[i+2].page_content
                    chunks = self.text_splitter.create_documents([pages[i+1].page_content])
                    chunk_with_context = self._generate_contextualized_chunks(document, chunks, file_path)
                    contextualized_chunks += chunk_with_context

            # Process TXT
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    document = file.read()
                    chunks = self.text_splitter.create_documents([document])
                    chunk_with_context = self._generate_contextualized_chunks(document, chunks, file_path)
                    contextualized_chunks += chunk_with_context
                
        return contextualized_chunks
    
    def _generate_contextualized_chunks(self, document: str, chunks: List[Document], file_path: str) -> List[Document]:
        """
        Generate contextualized versions of the given chunks.
        
        Args:
            document: str, complete document to retrieve context from
            chunks: list of chunks without context
            file_path: str, path to the original file
        
        Returns:
            list of contextualized chunks
        """
        contextualized_chunks = []
        
        for chunk in tqdm(chunks, leave=False, desc='Generating chunk context'):
            # Create context
            context = self._generate_context(document, chunk.page_content)
            
            contextualized_content = f'{context}\n\n{chunk.page_content}'
            
            # Translate chunk to Spanish
            contextualized_content = self._translate_chunks(contextualized_content)
            
            # Add source
            source = file_path.split('/')[-1].split('.')[0].replace('_', ' ').title()
            contextualized_content = f'<documento> FUENTE: {source}. {contextualized_content}<documento>'

            contextualized_chunks.append(
                Document(page_content=contextualized_content, metadata=chunk.metadata)
            )
        
        return contextualized_chunks
    
    def _generate_context(self, document: str, chunk: str) -> str:
        """
        Generate context for a specific chunk using an LLM.
        
        Args:
            document: str, complete document to extract context from
            chunk: str, chunk without context
        
        Returns:
            str, context for the chunk
        """
        system_prompt = '''You are an AI assistant specializing in design systems. 
                           Your task is to provide brief, relevant context for a chunk of text 
                           from the document provided.
                           Here is the document:
                           <document>
                           {document}
                           </document>

                           Here is the chunk we want to situate within the whole document::
                           <chunk>
                           {chunk}
                           </chunk>

                           Provide a concise context (2-3 sentences) for this chunk, considering the 
                           following guidelines:
                           
                           1. Do not use phrases like "This chunk discusses", "The chunk focuses"
                              ,"This section provides", or any other reference to summaring. 
                              Avoid any reference to summaring. Instead, directly state the context.
                              Just give the context.
                              Do not use phrases like "This chunk discusses" or "This section provides". 
                              Instead, directly state the context.

                           
                           2. Identify the main topic or metric discussed (e.g., archetypes, dynamics, 
                              hierarchy, system).
                           
                           3. Mention any relevant time periods or comparisons.
                           
                           4. If applicable, note how this information relates to design, strategy, 
                              or market position.
                           
                           5. Include any key figures or percentages that provide important context.
                           

                           Please give a short succinct context to situate this chunk within the overall 
                           document for the purposes of improving search retrieval of the chunk. 
                           Answer only with the succinct context and nothing else.

                           Context:
                           '''
        
        prompt = ChatPromptTemplate.from_template(system_prompt)
        messages = prompt.format_messages(document=document, chunk=chunk)
        response = self.llm.invoke(messages).content
        
        return response
    
    def _translate_chunks(self, chunk: str) -> str:
        """
        Translate all chunks to Spanish.
        
        Args:
            chunk: str, chunk without translation
        
        Returns:
            str, chunk in Spanish
        """
        system_prompt = '''You are a good translator to spanish.
                           Given the next chunk translate to spanish:
                           
                           <chunk>
                           {chunk}
                           </chunk>
                           
                           Just give the traslation, do not comment anything.
                           If the chunk is already in spanish, repeat the chunk.
                           '''
        
        prompt = ChatPromptTemplate.from_template(system_prompt)
        messages = prompt.format_messages(chunk=chunk)
        response = self.llm.invoke(messages)
        
        return response.content
    
    def create_vectorstore(self, chunks: List[Document]) -> None:
        """
        Create a Chroma vector database to store the chunks.
        
        Args:
            chunks: list of chunks to save
        
        Returns:
            None
        """
        vectordb = Chroma.from_documents(
            chunks,
            self.embeddings,
            persist_directory='data/chroma_db',
            collection_name=self.collection_name
        )
    
    def create_bm25_retriever(self, chunks: List[Document]) -> None:
        """
        Create a BM25 retriever for the given chunks.
        
        Args:
            chunks: list of chunks to save
        
        Returns:
            None
        """
        bm25_retriever = BM25Retriever.from_documents(chunks)
        
        # Save BM25 object
        os.makedirs('data', exist_ok=True)
        with open(f'data/{self.collection_name}_bm25', 'wb') as bm25_file:
            pickle.dump(bm25_retriever, bm25_file)
    
    def store_to_db(self, file_paths: List[str]) -> None:
        """
        Complete process of saving to database from document.
        
        Args:
            file_paths: list of strings, paths to files to save in Chroma and BM25
        
        Returns:
            None
        """
        chunks = self.process_document(file_paths)
        self.create_vectorstore(chunks)
        self.create_bm25_retriever(chunks)


if __name__ == '__main__':
    # Example usage
    vectordb = VectorDB('design')
    vectordb.store_to_db(['data/thinking_systems_from_donella_meadows.pdf'])

