from django.shortcuts import render,redirect
from django.http import JsonResponse

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat

from django.utils import timezone

import boto3
import json
from langchain.llms.sagemaker_endpoint import SagemakerEndpoint
from langchain.llms.sagemaker_endpoint import LLMContentHandler
from langchain_core.prompts import PromptTemplate
from langchain.utilities.sql_database import SQLDatabase
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain.chains.conversation.base import ConversationChain
from typing import Dict
from sqlalchemy import create_engine, URL


TABLE_CHATBOT_SAGEMAKER_ENDPOINT = "huggingface-pytorch-inference-2024-04-21-19-08-27-137"
ACCESSID = "AKIA4MTWMI6O4STOBVEC"
ACCESSKEY = "mKXvPNo7kj4ICnwrotsLNxe2MH7AWgSqc7REBiD9"

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
        
def ask_table(message):
    # response = openai.ChatCompletion.create(
    #     model = "gpt-3.5-turbo-16k-0613",
    #     # prompt = message,
    #     # max_tokens=150,
    #     # n=1,
    #     # stop=None,
    #     # temperature=0.7,
    #     messages=[
    #         {"role": "system", "content": "You are an helpful assistant."},
    #         {"role": "user", "content": message},
    #     ]
    # )
    # response = "I'm responsing"


    # client = boto3.client("sagemaker-runtime", 
    #                       region_name = "us-east-2",
    #                       aws_access_key_id=ACCESSID,
    #                       aws_secret_access_key= ACCESSKEY)

    # payload = {
    #     "inputs": {
    #     "query": message,
    #     "table": {
    #         "Item": ["Omni", "Electrical appliances", "Foods"],
    #         "quantity": ["11", "4512", "3934"],
    #         # "status": ["approved", "reported", "reported"]
    #     }
    #         },
    # }

    # response = client.invoke_endpoint(
    #     EndpointName = TABLE_CHATBOT_SAGEMAKER_ENDPOINT,
    #     Body = json.dumps(payload),
    #     ContentType = "application/json"
    # )
    # answer = json.loads(response['Body'].read())['answer']
    # print(answer)
    # answer = response.choices[0].message.content.strip()
    # answer = response
    content_handler = ContentHandler()

    endpoint = "huggingface-pytorch-tgi-inference-2024-04-24-01-23-35-845"
    aws_access_key_id = "AKIA4MTWMI6O4STOBVEC"
    aws_secret_access_key = "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"

    llm = SagemakerEndpoint(
            endpoint_name=endpoint,
            region_name="us-east-2",
            model_kwargs={
                "temperature": 0,
                "maxTokens": 4096,
                "numResults": 3
            },
            content_handler=content_handler,
            client=boto3.client(
                "runtime.sagemaker",
                aws_access_key_id = aws_access_key_id,
                aws_secret_access_key = aws_secret_access_key,
                region_name = "us-east-2"
            )
        )

    db_url = URL.create(
        "postgresql",
        username="postgres",
        password="philgrey",
        host="localhost",
        port=5432,
        database="tablecbdbs"
    )

    db = SQLDatabase.from_uri(database_uri=db_url)
    template = '''You are a PostgreSQL expert. Given an input question, first create a syntactically correct PostgreSQL query to run, then look at the results of the query and return the answer to the input question.\nUnless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per PostgreSQL. You can order the results to return the most informative data in the database.\nNever query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in double quotes (") to denote them as delimited identifiers.\ncreate query depending on table structure whether input value is not in table\nif question is item order placement availability, make query using CAST.\nPay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.\nPay attention to use CURRENT_DATE function to get the current date, if the question involves "today".\n\nUse the following format:\n\nQuestion: Question here\nSQLQuery: SQL Query to run\nSQLResult: Result of the SQLQuery\nAnswer: Final answer here\n\nOnly use the following tables:\n{table_info}\n\nQuestion: {input}'''
    prompt = PromptTemplate.from_template(template)
    chain = create_sql_query_chain(llm, db=db, prompt=prompt)
    print("****")
    answer  = chain.invoke({"question": message})
    print("****")
    return answer

# Create your views here.

def chatbot(request):
    # chats = Chat.objects.filter(user=request.user)
    chats = ""
    
    if request.method == 'POST':
        message = request.POST.get('message')
        # response = chain.invoke({"question": "I want to know if Item ITEM001 has inventory"})
        response = ask_table(message)
        print("++++", type(response), "++++")
        # chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now)
        # chat.save()
        return JsonResponse({'message': message, 'response': response})
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