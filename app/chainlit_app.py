"""
Chainlit application for CRAG chatbot.
Extracted from notebooks/CRAG.ipynb and integrated with existing chatbot structure.
"""

import chainlit as cl
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.memory import ConversationBufferWindowMemory
from operator import itemgetter

import sys
from pathlib import Path

# Add parent directory to path to import crag module
sys.path.append(str(Path(__file__).parent.parent))
from crag.retrieve_db import ensemble_retriever

# Load environment variables
load_dotenv()

# API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# System prompt for the chatbot
SYSTEM_PROMPT = '''
Tu funcion es responder preguntas al respecto de archivos pdfs que se van proporcionar.
Devuelve siempre una respuesta amplia y bien explicada.
No uses nunca frases como "Basándonos en el contexto proporcionado...", utiliza un estilo conversacional.
'''

QUESTION_PROMPT = '''
Dada el siguiente contexto, responde la pregunta:
    
contexto: {context}, 
                    
pregunta: {prompt}.
      
'''


class Chat:
    """
    Chat class for handling conversations with RAG retrieval.
    """

    def __init__(self, collection: str = 'design') -> None:
        """
        Initialize the chat with retriever and memory.
        
        Args:
            collection: str, name of the collection to use
        """
        self.retriever = ensemble_retriever(collection)
        self.memory = ConversationBufferWindowMemory(k=4, return_messages=True)
    
    def get_context(self, prompt: str) -> list:
        """
        Get relevant context for the prompt using the retriever.
        
        Args:
            prompt: str, user's question
        
        Returns:
            list of relevant documents
        """
        context = self.retriever.invoke(prompt)
        return context
    
    def chain_to_response(self) -> object:
        """
        Create the chain for generating responses.
        
        Returns:
            LangChain chain object
        """
        output_model = ChatOpenAI(
            model='gpt-4o',
            streaming=True,
            max_retries=1,
            max_tokens=32768
        )

        final_prompt = ChatPromptTemplate.from_messages([
            ('system', SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name='history'),
            ('human', QUESTION_PROMPT)
        ])

        chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(self.memory.load_memory_variables) | itemgetter('history')
            )
            | final_prompt
            | output_model
            | StrOutputParser()
        )

        return chain
    
    def main(self, prompt: str):
        """
        Main method to process a prompt and generate a streaming response.
        
        Args:
            prompt: str, user's question
        
        Yields:
            str, chunks of the response
        """
        context = self.get_context(prompt)
        chain = self.chain_to_response()

        response = ''
        for chunk in chain.stream({
            'context': context,
            'prompt': prompt
        }):
            yield chunk
            response += chunk
            
            self.memory.save_context(
                {'question': prompt},
                {'response': response}
            )


# Initialize chatbot
chatbot = Chat()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handle incoming messages from the user.
    
    Args:
        message: cl.Message, the user's message
    """
    msg = cl.Message(content='')
    response = ''

    async with cl.Step(type='run'):
        for chunk in chatbot.main(prompt=message.content):
            await msg.stream_token(chunk)
            response += chunk

        await msg.send()


@cl.on_chat_start
async def on_chat_start():
    """
    Initialize the chat session.
    """
    await cl.Message(
        content="¡Hola! Soy un asistente especializado en responder preguntas sobre documentos PDF. ¿En qué puedo ayudarte?"
    ).send()

