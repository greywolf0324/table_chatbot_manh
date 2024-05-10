print(1)
import requests
print(2)
from typing import List
print(3)
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
print(4)
from transformers import pipeline
import json
import boto3
from typing import Dict

TOKEN_URL = "https://ptnrd-auth.omni.manh.com/oauth/token"

TABLES = {
    "itemtype": ["item", "quantity"],
    "orderline": ["order", "orderline", "items", "order_status"],
    "maoorder": ["order", "order_information", "order_status"]
}
print("classifier running...")
API_classifier = pipeline("sentiment-analysis", model="philgrey/my_awesome_model")
Question_classifier = pipeline("sentiment-analysis", model="philgrey/question_classifier")

message_preprocessor_prompt = """Your role is to get one sentence by summarizing two or more sentences while preserving all the information contained in the inputs.
use the following format:

inputs:
what is the status of my order?
My order is JWOrder124. Can you give me the status?
Output:
what is the status of order JWOrder124?

inputs:

"""
no_order_prompt = """You are professional virtual assistant that answers to User's question.
All question answering will be done following format.

input:
User's question
output:
your answer

input:
write simple response in American English stating that there is no order.
output:

"""

no_item_prompt = """You are professional virtual assistant that answers to User's question.
All question answering will be done following format.

input:
User's question
output:
your answer

input:
write simple response in American English stating that there is no item.
output:

"""

response_modifier_prompt = """Your role is to generate description that explains basic data user will give you.
basic data:

"""
answer_modifier_prompt = """Your role is to generate US Native english from following basic data. All grammar has to be perfect. 
use the following format:

inputs:
you haven't specify item ID
Output:
You haven't specified the item ID.

inputs:
"""
endpoint = "huggingface-pytorch-tgi-inference-2024-05-10-14-53-22-247"
aws_access_key_id = "AKIA4MTWMI6O4STOBVEC"
aws_secret_access_key = "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"

runtime = boto3.client("sagemaker-runtime", region_name = "us-east-2", aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key)

# API_URLS = [
#     '/api/availability/beta/availabilitydetailbyview',
#     '/omnifacade/api/customerservice/order/orderLine?page=0&size=10&sort=CreatedTimestamp%2Bdesc&query=O',
#     '{{url}}/omnifacade/api/customerservice/order/search/advanced'
# ]

REQUEST_BODIES = [
    '''{
        "AvailabilityRequestViews": [
            {
            "ConsiderCapacityFullLocations": true,
            "ConsiderOutageLocations": true,
            "IncludeStoreExclusions": true,
            "ViewName": "US_Network"
            }
        ],
        "Items": [
            "CSOITEM001"
        ]
        }
        ''',
]



class SQL_chatbot:
    def __init__(self) -> None:
        print("sql model running...")
        self.tokenizer = AutoTokenizer.from_pretrained("juierror/text-to-sql-with-table-schema")
        self.model = AutoModelForSeq2SeqLM.from_pretrained("juierror/text-to-sql-with-table-schema")
        print("authentication info reading...")
        self.username = "sme@veridian.info"
        self.password = "Veridian3!"
        self.client_id = "omnicomponent.1.0.0"
        self.client_secret = "b4s8rgTyg55XYNun"
        self.message_saver = []

    def question_classifier(self, message):
        match Question_classifier(message)[0]["label"]:
            case 'POSITIVE': return True
            case 'NEGATIVE': return False

    def message_preprocessor(self, message):
        # LLM: "HuggingFaceH4/zephyr-7b-beta"
        print("message: ", message)
        if len(message) == 1:
            return message
        else:
            payload = {
                "inputs": message_preprocessor_prompt + message + "\nOutput: ",
                "parameters": {
                    "do_sample": True,
                    "top_p": 0.7,
                    "top_k": 3,
                    "temperature": 0.3,
                    "max_new_tokens": 128,
                    "repetition_penalty":1.03
                }
            }
                    
                    
            
            response = runtime.invoke_endpoint(EndpointName = endpoint, ContentType = "application/json", Body = json.dumps(payload))
            res = json.loads(response["Body"].read().decode("utf-8"))[0]['generated_text']
            print(res)
            try:
                processed_message = res.split("Output:")[2].split("inputs")[0].replace("\n", "")
                # processed_message = res[12]
            except:
                processed_message = res.split("output:")[2].split("A:")[0].replace("\n", "")

            return processed_message
    
    def IDdetector(self, question):
        ID = API_classifier(question)[0]['label']
        if ID == "maoorder" and "orderline" in "".join(question).lower():
            ID == "orderline"

        return ID
    
    # def table_detector(self, message):
    #     detected_table = TABLES["itemtype"]

    #     return detected_table
    
    def info_getter(self, query, ID):
        res = query.split("=")[1].replace(" ", "").replace(";", "")
        # match ID:
        #     case "itemtype":
        #         res = query.split("=").replace(" ", "").replace(";", "")
        #     case "orderline":
        #         res = query.split("=").replace(" ", "").replace(";", "")
        #     case "maoorder":
        return res
    
    def url_detector(self, query, ID):
        info = self.info_getter(query, ID)

        match ID:
            case "itemtype":
                detected_url = "https://ptnrd.omni.manh.com/inventory/api/availability/beta/availabilitydetailbyview"
            case "orderline":
                detected_url = "https://ptnrd.omni.manh.com/omnifacade/api/customerservice/order/orderLine?page=0&size=10&sort=CreatedTimestamp%2Bdesc&query=OrderId%3D%27" + info + "%27"
            case "maoorder":
                detected_url = "https://ptnrd.omni.manh.com/omnifacade/api/customerservice/order/search/advanced"
        print("URL: ", detected_url)
        return detected_url
    
    def prepare_input(self, question: str, table: List[str]):
        table_prefix = "table:"
        question_prefix = "question:"
        join_table = ",".join(table)
        inputs = f"{question_prefix} {question} {table_prefix} {join_table}"
        input_ids = self.tokenizer(inputs, max_length=700, return_tensors="pt").input_ids

        return input_ids

    def query_generator(self, question: str, table: List[str]) -> str:
        input_data = self.prepare_input(question=question, table=table)
        input_data = input_data.to(self.model.device)
        outputs = self.model.generate(inputs=input_data, num_beams=10, top_k=10, max_length=700)
        print(outputs)
        result = self.tokenizer.decode(token_ids=outputs[0], skip_special_tokens=True)

        return result
    
    def request_body_generator(self, query, ID):        
        info = self.info_getter(query, ID)
        match ID:
            case "itemtype":
                detected_request = '''{
                                    "AvailabilityRequestViews": [
                                        {
                                        "ConsiderCapacityFullLocations": true,
                                        "ConsiderOutageLocations": true,
                                        "IncludeStoreExclusions": true,
                                        "ViewName": "US_Network"
                                        }
                                    ],
                                    "Items": [
                                        "%s"
                                    ]
                                    }
                                ''' % info
            case "orderline":
                detected_request = None
            case "maoorder":
                detected_request = """{
                                    "Query": "OrderId = '%s'",
                                    "Page": 0,
                                    "Size": 10
                                }
                            """ % info
        print("detected request: ", detected_request)
        return detected_request

    def API_requester(self, api_url, body, ID, username:str = None, password:str = None, client_id:str = None, client_secret:str = None):
        if username != None:
            self.username = username
        if password != None:
            self.password = password
        if client_id != None:
            self.client_id = client_id
        if client_secret != None:
            self.client_secret = client_secret

        print(api_url)
        response = requests.post(TOKEN_URL, data={
                                "grant_type": "password",
                                "username": self.username, "password": self.password},
                                auth=(self.client_id, self.client_secret))
        response.raise_for_status()
        token = response.json()["access_token"]
        match ID:
            case "itemtype":
                response = requests.post(
                    url=api_url,
                    data=body,
                    headers={"Content-Type": "application/json",
                            'Authorization': 'Bearer ' + token
                    }
                )
            case "orderline":
                response = requests.get(
                    url=api_url,
                    headers={"Content-Type": "application/json",
                            'Authorization': 'Bearer ' + token
                    }
                )
            case "maoorder":
                response = requests.post(
                    url=api_url,
                    data=body,
                    headers={"Content-Type": "application/json",
                            'Authorization': 'Bearer ' + token
                    }
                )

        return response.json()
    
    def response_modifier(self, API_response: Dict, ID, query: str):
        content = query.lower().split("select ")[1].split("from")[0].replace(" ", "")
        print("ID: ", ID, "--")
        print("content: ", content, "--")

        if len(API_response['data']) == 0:
            if ID == "maoorder" or ID == "orderline":
                prompt = no_order_prompt
            elif ID == "itemtype":
                prompt = no_item_prompt
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "do_sample": True,
                    "top_p": 0.7,
                    "top_k": 3,
                    "temperature": 0.3,
                    "max_new_tokens": 128,
                    "repetition_penalty":1.03
                }
            }
                    
            response = json.loads(runtime.invoke_endpoint(EndpointName = endpoint, ContentType = "application/json", Body = json.dumps(payload))["Body"].read().decode("utf-8"))

            print("final response: ", response)
            processed_message = response[0]['generated_text'].split("\n")[12]
        else:
            data = API_response['data'][0]
            print("data: ", data)
            if content == "order_status":
                print(1)
            if ID == "maoorder":
                print(1)
                if content == "order_status":
                    print(1)
                    response_data = dict((k, data[k]) for k in ('CreatedTimestamp', 'FulfillmentStatus', 'OrderTotal') if k in data)
            payload = {
                "inputs": response_modifier_prompt + str(response_data) + "\nresponse:\n",
                "parameters": {
                    "do_sample": True,
                    "top_p": 0.7,
                    "top_k": 50,
                    "temperature": 0.3,
                    "max_new_tokens": 512,
                    "repetition_penalty":1.03
                }
            }
                    
            response = json.loads(runtime.invoke_endpoint(EndpointName = endpoint, ContentType = "application/json", Body = json.dumps(payload))["Body"].read().decode("utf-8"))
            processed_message = response[0]['generated_text'].split('response:')[1].replace("\n", "")
            print("answer: ", processed_message)
        return processed_message
    
    def chatbot(self, message):
        print("message: ", message)
        To_nextstep = self.question_classifier(message)
        print("question type: ", To_nextstep)
        if To_nextstep:
            self.message_saver.append(message)
            print("saved message: ", self.message_saver)
            processed_message = self.message_preprocessor(" ".join(self.message_saver))
            print("processed_message: ", processed_message)
            ID = self.IDdetector(processed_message)
            print("ID: ", ID)
            table = TABLES[ID]
            query = self.query_generator(question=processed_message, table=table)
            print("query: ", query)
            api_url = self.url_detector(query, ID)
            api_request_body = self.request_body_generator(query, ID)
            api_response = self.API_requester(api_url=api_url, body=api_request_body, ID = ID)
            print("api_response: ", api_response)
            answer = self.response_modifier(api_response, ID, query)
            # answer = str(api_response['data'])

            self.message_saver = []
        else:
            self.message_saver.append(message)
            ID = self.IDdetector("".join(self.message_saver))
            print("ID: ", ID)
            match ID:
                case "itemtype":
                    answer = "you didn't specify item ID"
                case "orderline":
                    answer = "you didn't specify order ID"
                case "maoorder":
                    answer = "you didn't specify order ID"
            payload = {
                "inputs": answer_modifier_prompt + str(answer),
                "parameters": {
                    "do_sample": True,
                    "top_p": 0.7,
                    "top_k": 50,
                    "temperature": 0.3,
                    "max_new_tokens": 512,
                    "repetition_penalty":1.03
                }
            }
                    
            response = json.loads(runtime.invoke_endpoint(EndpointName = endpoint, ContentType = "application/json", Body = json.dumps(payload))["Body"].read().decode("utf-8"))
            # print(json.loads(response["Body"].read().decode("utf-8")))
            # res = json.loads(response["Body"].read().decode("utf-8"))
            print(type(response))
            print(response)
            answer = response[0]['generated_text'].split("\n")[11]
        print("\n--------------------------------------------------------------------------------------------------------------------------\n")
        return answer

# class Requester:
#     def __init__(self) -> None:
#         self.username = "sme@veridian.info"
#         self.password = "Veridian3!"
#         self.client_id = "omnicomponent.1.0.0"
#         self.client_secret = "b4s8rgTyg55XYNun"

#     def API_requester(self, api_url, body, username:str = None, password:str = None, client_id:str = None, client_secret:str = None):
#         if username != None:
#             self.username = username
#         if password != None:
#             self.password = password
#         if client_id != None:
#             self.client_id = client_id
#         if client_secret != None:
#             self.client_secret = client_secret

#         response = requests.post(TOKEN_URL, data={
#                                 "grant_type": "password",
#                                 "username": self.username, "password": self.password},
#                                 auth=(self.client_id, self.client_secret))
#         response.raise_for_status()
#         token = response.json()["access_token"]

#         response = requests.post(
#             url=SITE_URL + api_url,
#             data=body,
#             headers={"Content-Type": "application/json",
#                     'Authorization': 'Bearer ' + token
#             }
#         )

#         return response.json()
    
#     def sql_query_parser(self, sql_query: str):
#         detected_args = {}
#         sql_query = sql_query.lower()

#         detected_args.update({"itemID": sql_query.split("where")[1].split("'")[1]})
        
#         return detected_args
        
#     def response_modifier(self, **kwargs):
#         match kwargs["query_type"]:
#             case "itemavailable":
#                 if kwargs["response"]:
#                     return f"Yes, {kwargs['itemID']} is available."
#                 else:
#                     return f"No, {kwargs['itemID']} is not available."
#             case "itemcount":
#                 return f"There are {int(kwargs['response'])} {kwargs['itemID']} now."
#             case "itemorderplace":
#                 if kwargs["response"]:
#                     return f"Yes, you can place order."
#                 else:
#                     return f"No, you can't place order since there aren't sufficient items"
    
#     def itemavailability(self, querytype: str, **kwargs):
#         api_url = "/api/availability/beta/availabilitydetailbyview"
#         body = '''{
#         "AvailabilityRequestViews": [
#             {
#             "ConsiderCapacityFullLocations": true,
#             "ConsiderOutageLocations": true,
#             "IncludeStoreExclusions": true,
#             "ViewName": "US_Network"
#             }
#         ],
#         "Items": [
#             "%s"
#         ]
#         }
#         ''' % kwargs['itemID']
        
#         response = self.API_requester(api_url=api_url, body=body)

#         if response['data'] == None:
#             quantity = 0
#         else:
#             quantity = response['data'][0]['TotalQuantity']
        
        
#         match querytype:
#             case "itemavailable":
#                 response =  {"query_type": querytype, "response": quantity > 0, "itemID": kwargs['itemID']}
#             case "itemcount":
#                 response =  {"query_type": querytype, "response": quantity, "itemID": kwargs['itemID']}
#             case "itemorderplace":
#                 response =  {"query_type": querytype, "response": quantity > kwargs['qty'], "itemID": kwargs['itemID']}

#         response = self.response_modifier(**response)

#         return response
