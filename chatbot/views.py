from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import auth
from django.contrib.auth.models import User
# from .models import Chat

import re
import json
import boto3
from langchain.llms.sagemaker_endpoint import SagemakerEndpoint
from langchain.llms.sagemaker_endpoint import LLMContentHandler
from langchain_core.prompts import PromptTemplate
from langchain.utilities.sql_database import SQLDatabase
from langchain.chains.sql_database.query import create_sql_query_chain
from typing import Dict
from sqlalchemy import create_engine, URL
from chatbot.utils import SQL_chatbot, Requester


bot = SQL_chatbot()

# TABLE_CHATBOT_SAGEMAKER_ENDPOINT = "huggingface-pytorch-tgi-inference-2024-04-24-14-30-53-911"
# ACCESSID = "AKIA4MTWMI6O4STOBVEC"
# ACCESSKEY = "mKXvPNo7kj4ICnwrotsLNxe2MH7AWgSqc7REBiD9"



class ContentHandler(LLMContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
            input_str = json.dumps({"inputs": prompt, **model_kwargs})
            print("input: ", input_str)
            return input_str.encode("utf-8")

        def transform_output(self, output: bytes) -> str:
            response_json = json.loads(output.read().decode("utf-8"))
            print("output: ", response_json)
            return response_json[0]['generated_text']
        
# def ask_table_llm(message):
#     content_handler = ContentHandler()

#     endpoint = "huggingface-pytorch-tgi-inference-2024-04-24-17-04-11-398"
#     aws_access_key_id = "AKIA4MTWMI6O4STOBVEC"
#     aws_secret_access_key = "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"

#     llm = SagemakerEndpoint(
#             endpoint_name=endpoint,
#             region_name="us-east-2",
#             model_kwargs={
#                 "temperature": 0,
#                 "maxTokens": 4096,
#                 "numResults": 3
#             },
#             content_handler=content_handler,
#             client=boto3.client(
#                 "runtime.sagemaker",
#                 aws_access_key_id = aws_access_key_id,
#                 aws_secret_access_key = aws_secret_access_key,
#                 region_name = "us-east-2"
#             )
#         )

#     db_url = URL.create(
#         "postgresql",
#         username="postgres",
#         password="philgrey",
#         host="localhost",
#         port=5432,
#         database="tablecbdbs"
#     )

#     db = SQLDatabase.from_uri(database_uri=db_url)
#     template = '''You are a PostgreSQL expert. Given an input question, create a syntactically correct PostgreSQL query to run. Never create DELETE, DROP, UPDATE query. Only perform SELECT operation.
#     Create only {top_k} SQL Query.
#     Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in double quotes (") to denote them as delimited identifiers.
#     Create query depending on table structure whether input value is not in table.
#     If question don't have number of item, order or orderline, don't create SQL Query and write its title to 'suggestion'. For example, question is 'I want to know if Item has inventory' and it doesn't have item number. in this case, never create query and make suggestion 'item'.
#     Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
#     Pay attention to use CURRENT_DATE function to get the current date, if the question involves "today".
    
#     Use the following format:
    
#     Question: Question here
#     SQLQuery: SQL Query to run
#     suggestion: 'suggest'
    
#     Only use the following tables:
#     {table_info}
    
#     Question: {input}'''
#     prompt = PromptTemplate.from_template(template)
#     chain = create_sql_query_chain(llm, db=db, prompt=prompt, k=1)
#     print("****")
#     answer  = chain.invoke({"question": message})
#     print("****")
#     return answer

# def chatbot_llm(request):
#     # chats = Chat.objects.filter(user=request.user)
#     chats = ""
#     default_response = "Can you let me know item ID?"
    
#     if request.method == 'POST':
#         message = request.POST.get('message')

#         temp = re.findall("\d+", message)
#         if 'rder' in message and 'item' not in message.lower():
#                 response = ask_table_llm(message)
#                 response = response.split("SQLQuery: ")[2].split("Ask: ")[0]
#         else:
#             response = ask_table_llm(message)
#             response = response.split("SQLQuery: ")[2].split("Ask: ")[0]

#         print("answer: ", response)
#         if response != default_response:
#             # Default Credential:
#                 # username: "sme@veridian.info"
#                 # password: "Veridian3!"
#                 # client_id: "omnicomponent.1.0.0"
#                 # client_secret: "b4s8rgTyg55XYNun"
            
#             message = message.lower()
#             if 'item' in message and 'inventory' in message:
#                 query_type = "itemavailable"
#             elif 'item' in message and 'quantity' in message:
#                 query_type = "itemcount"
#             elif 'item' in message and 'place' in message:
#                 query_type = "itemorderplace"
            
#             requester = Requester()
#             detected_args = requester.sql_query_parser(response)
#             print("query_type: ", query_type)
#             print("detected args: ", detected_args)
#             response = requester.itemavailability(querytype=query_type, **detected_args)

#         return JsonResponse({'message': message, 'response': response})
#     return render(request, 'chatbot.html', {'chats': chats})



def chatbot(request):
    print(request, type(request), "---")
    chats = ""
    if request.method == 'POST':
        message = request.POST.get('message')
        answer = bot.chatbot(message)

        return JsonResponse({'message': message, 'response': answer})

    return render(request, 'chatbot.html', {'chats': chats})

def login(request):
    if request.method=='POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})
    else:
        return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1==password2:
            try:
                user = User.objects.create_user(username, email, password1)
                user.save()
                auth.login(request, user)
                return redirect('chatbot')
            except:
                error_message = 'Error creating account'
            return render(request, 'register.html', {'error_message': error_message})
        else:
            error_message = "Password don't match" 
            return render(request, 'register.html', {'error_message': error_message})
    return render(request, 'register.html')

def logout(request):
    auth.logout(request)
    return redirect('login')