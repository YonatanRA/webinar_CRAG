from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.memory import ConversationBufferWindowMemory
import os
from operator import itemgetter
from dotenv import load_dotenv
load_dotenv(override=True)

from tools import ensemble_retriever, logger
from .prompt import system_prompt, question_prompt

# api key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


class Chat:

    def __init__(self, collection: str='design') -> None:
        logger.info('Init chat...')
        self.retriever = ensemble_retriever(collection)
        self.memory = ConversationBufferWindowMemory(k=4, return_messages=True)

    
    def get_context(self, prompt: str) -> list:
        logger.info('Getting context...')
        context = self.retriever.invoke(prompt)
        return context
    
    
    def chain_to_response(self) -> object:

        output_model = ChatOpenAI(model='gpt-4.1', streaming=True, max_retries=1, max_tokens=32768)

        final_prompt = ChatPromptTemplate.from_messages([('system', system_prompt),
                                                         
                                                         MessagesPlaceholder(variable_name='history'),
                                                         
                                                         ('human', question_prompt)])


        chain = (RunnablePassthrough.assign(history=RunnableLambda(self.memory.load_memory_variables) 
                                            | itemgetter('history'))) | final_prompt  | output_model | StrOutputParser()

        return chain
    
    
    def main(self, prompt: str):

        context = self.get_context(prompt)

        chain = self.chain_to_response()

        response = ''
        logger.info('Generating response...')
        for chunk in chain.stream({'context': context,
                                   'prompt': prompt}):
                    
                yield(chunk)

                response += chunk
                
                self.memory.save_context({'question': prompt}, 
                                         {'response': response})





    



