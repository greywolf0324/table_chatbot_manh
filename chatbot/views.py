from django.shortcuts import render,redirect
from django.http import JsonResponse

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat

from django.utils import timezone

import boto3
import json

TABLE_CHATBOT_SAGEMAKER_ENDPOINT = "huggingface-pytorch-inference-2024-04-21-19-08-27-137"

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
    response = "I'm responsing"


    client = boto3.client("sagemaker-runtime")

    payload = {
        "inputs": {
        "query": message,
        "table": {
            "inventory": ["Omni", "Electrical appliances", "Foods"],
            "quantity": ["11", "4512", "3934"],
            "status": ["approved", "reported", "reported"]
        }
            },
    }

    response = client.invoke_endpoint(
        EndpointName = TABLE_CHATBOT_SAGEMAKER_ENDPOINT,
        Body = json.dumps(payload),
        ContentType = "application/json"
    )
    answer = json.loads(response['Body'].read())['answer']
    print(answer)
    # answer = response.choices[0].message.content.strip()
    answer = response
    return answer

# Create your views here.

def chatbot(request):
    # chats = Chat.objects.filter(user=request.user)
    chats = ""

    if request.method == 'POST':
        message = request.POST.get('message')
        response = ask_table(message)

        chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now)
        chat.save()
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