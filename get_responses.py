import os
from dotenv import load_dotenv
# from openai import AzureopenAI
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import google.generativeai as genai
import re

import openai

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
deployment_id = os.getenv('MODEL')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def chatbot_response(messages):
    response = openai.chat.completions.create(
        model=deployment_id,
        messages=messages,
        temperature=0,
        max_tokens=500,
        top_p=1
    )
    
    return response


# client = AzureopenAI(api_key=api_key,
#                     api_version=api_version,
#                     azure_endpoint=api_base)

# embedding = AzureopenAIEmbeddings(model="text-embedding-3-large",
#                                     api_key=api_key,
#                                     api_version=api_version,
#                                     azure_endpoint=api_base)

embedding = OpenAIEmbeddings(model="text-embedding-3-large")

def contextualize_question(chat_history:dict):
    contextualize_q_system_prompt = f"Given a chat history and the latest user question \
        which might reference context in the chat history, formulate standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."

    messages=[{"role": "system", 
               "content": f"""{contextualize_q_system_prompt}\n
               ## Chat history:\n{chat_history[:-1]}\n\n
               ## Latest user question: {chat_history[-1]["content"]}""",
            }
            ]
    
    response = openai.chat.completions.create(
        model=deployment_id,
        messages=messages
        )
    
    return response.choices[0].message.content

def get_rag_response(chat_history:dict, model, temperature):
    if len(chat_history) > 2:
        user_question = contextualize_question(chat_history)
    else:
        user_question = chat_history[-1]["content"]

    retriever = Chroma(
        collection_name="document_chunks",
        persist_directory="./chroma_vectorstore",
        embedding_function=embedding
                            ).as_retriever(search_kwargs={'k': 4})
    
    context = retriever.invoke(user_question)

    prompt_rag = f"""You are an assistant for question-answering tasks abour LangGraph.
    Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, say that you don't know.
    \n\n
    {context}
    \n\n
    Question:
    # Remember: only use the context to answer the question, if the question has no relation with the context just say that you can't answer base on the context
    Useful response:
    """
    
    messages=[
            {
            "role": "user",
            "content": prompt_rag,
            }
        ]
    
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature = temperature
        )
    
    return response

def get_response(chat_history:dict, model, temperature):
    if bool(re.match(r'^o\d', model)):
        messages=chat_history
        
        response = openai.chat.completions.create(
            model=model,
            messages=messages
            )
        return response.choices[0].message.content
    
    elif model.lower().startswith("gpt"):
        messages=chat_history

        response= openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature = temperature
        )
        return response.choices[0].message.content
    
    elif model.lower().startswith("gemini"):
        model = genai.GenerativeModel(model, generation_config=genai.GenerationConfig(temperature=temperature))

        gemini_history = []
        for message in chat_history[:-1]:
            role = message['role']
            content = message['content']

            # Gemini uses 'model' instead of 'assistant'
            if role == 'assistant':
                role = 'model'

            gemini_history.append({'role': role, 'parts': [content]})

        # Start the chat session
        chat = model.start_chat(history=gemini_history)

        # Continue the conversation (optional)
        user_input = chat_history[-1]['content']
        response = chat.send_message(user_input)
        return response.text

def create_session_name(question,answer, session_name_list):
    messages=[
        {
            "role": "system",
            "content": f"""in no more than 5 words define the theme of the chat interaction different to the ones in the list [{session_name_list}]
            and in the same language of the question.
            Question: {question}
            Assistant answer: {answer}.
            Theme:"""
        }
    ]
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=7,
        temperature=0
        )
    
    return response.choices[0].message.content
