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

SITE_URL = "https://ptnrd.omni.manh.com/inventory"
TOKEN_URL = "https://ptnrd-auth.omni.manh.com/oauth/token"

TABLES = {
    "itemtype": ["item", "quantity"],
    "orderline": ["order", "orderline", "items", "order_status"],
    "maoorder": ["order", "order_information", "order_status"]
}
print("classifier running...")
API_classifier = pipeline("sentiment-analysis", model="philgrey/my_awesome_model")
Question_classifier = pipeline("sentiment-analysis", model="philgrey/question_classifier")

message_preprocessor_prompt = """Your role is to summarize two or more sentences to one sentence while preserving all the information contained in the sentences.
use the following format:

inputs:
what is the status of my order?
My order is JWOrder124. Can you give me the status?
Output:
what is the status of order JWOrder124?

inputs:

"""

endpoint = "huggingface-pytorch-tgi-inference-2024-05-05-13-24-25-210"
aws_access_key_id = "AKIA4MTWMI6O4STOBVEC"
aws_secret_access_key = "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"

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
        self.message_saver = ""

    def question_classifier(self, message):
        print(Question_classifier(message))
        match Question_classifier(message)[0]["label"]:
            case 'POSITIVE': return True
            case 'NEGATIVE': return False

    def message_preprocessor(self, message):
        # LLM: "microsoft/phi-2"
        payload = {
            "inputs": message_preprocessor_prompt + message,
            "parameters": {
                "do_sample": True,
                "top_p": 0.7,
                "top_k": 50,
                "temperature": 0.3,
                "max_new_tokens": 512,
                "repetition_penalty":1.03
            }
        }
                
                
        runtime = boto3.client("sagemaker-runtime", region_name = "us-east-2", aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key)
        response = runtime.invoke_endpoint(EndpointName = endpoint, ContentType = "application/json", Body = json.dumps(payload))
        processed_message = json.loads(response["Body"].read().decode("utf-8"))[0]['generated_text'].split("Output:")[2].split("inputs")[0].replace("\n", "")

        return processed_message
    
    def IDdetector(self, question):
        ID = API_classifier(question)[0]['label']
        if ID == "maoorder" and "orderline" in question:
            ID == "orderline"

        return ID
    
    # def table_detector(self, message):
    #     detected_table = TABLES["itemtype"]

    #     return detected_table
    
    def info_getter(self, query):

        return 'item001'
    
    def url_detector(self, query, ID):
        info = self.info_getter(query)
        match ID:
            case "itemtype":
                detected_url = "https://ptnrd.omni.manh.com/inventory/api/availability/beta/availabilitydetailbyview"
            case "orderline":
                detected_url = "https://ptnrd.omni.manh.com/omnifacade/api/customerservice/order/orderLine?page=0&size=10&sort=CreatedTimestamp%2Bdesc&query=OrderId%3D%27" + "%s%27" % info
            case "maoorder":
                detected_url = "https://ptnrd.omni.manh.com/omnifacade/api/customerservice/order/search/advanced"

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
        print("*********")
        outputs = self.model.generate(inputs=input_data, num_beams=10, top_k=10, max_length=700)
        result = self.tokenizer.decode(token_ids=outputs[0], skip_special_tokens=True)

        return result
    
    def request_body_generator(self, query):        
        info = self.info_getter(query)
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
                "ITEM001"
            ]
            }
        '''

        return detected_request

    def API_requester(self, api_url, body, username:str = None, password:str = None, client_id:str = None, client_secret:str = None):
        if username != None:
            self.username = username
        if password != None:
            self.password = password
        if client_id != None:
            self.client_id = client_id
        if client_secret != None:
            self.client_secret = client_secret
        print(SITE_URL)
        print(api_url)
        response = requests.post(TOKEN_URL, data={
                                "grant_type": "password",
                                "username": self.username, "password": self.password},
                                auth=(self.client_id, self.client_secret))
        response.raise_for_status()
        token = response.json()["access_token"]
        print(token)
        response = requests.post(
            url=api_url,
            data=body,
            headers={"Content-Type": "application/json",
                    'Authorization': 'Bearer ' + token
            }
        )

        return response.json()
    
    def response_modifier(self, API_response):

        return API_response
    
    def chatbot(self, message):
        is_message = self.question_classifier(message)
        if is_message:
            self.message_saver += message
            print(self.message_saver)
            processed_message = self.message_preprocessor(self.message_saver)
            ID = self.IDdetector(processed_message)
            print(ID, "--")
            table = TABLES[ID]
            query = self.query_generator(question=processed_message, table=table)
            api_url = self.url_detector(query, ID)
            print("query: ", query)
            api_request_body = self.request_body_generator(query)
            api_response = self.API_requester(api_url=api_url, body=api_request_body)
            print("api_response: ", api_response)
            answer = self.response_modifier(api_response)

            self.message_saver = ""
        else:
            self.message_saver += message

        return answer

class Requester:
    def __init__(self) -> None:
        self.username = "sme@veridian.info"
        self.password = "Veridian3!"
        self.client_id = "omnicomponent.1.0.0"
        self.client_secret = "b4s8rgTyg55XYNun"

    def API_requester(self, api_url, body, username:str = None, password:str = None, client_id:str = None, client_secret:str = None):
        if username != None:
            self.username = username
        if password != None:
            self.password = password
        if client_id != None:
            self.client_id = client_id
        if client_secret != None:
            self.client_secret = client_secret

        response = requests.post(TOKEN_URL, data={
                                "grant_type": "password",
                                "username": self.username, "password": self.password},
                                auth=(self.client_id, self.client_secret))
        response.raise_for_status()
        token = response.json()["access_token"]

        response = requests.post(
            url=SITE_URL + api_url,
            data=body,
            headers={"Content-Type": "application/json",
                    'Authorization': 'Bearer ' + token
            }
        )

        return response.json()
    
    def sql_query_parser(self, sql_query: str):
        detected_args = {}
        sql_query = sql_query.lower()

        detected_args.update({"itemID": sql_query.split("where")[1].split("'")[1]})
        
        return detected_args
        
    def response_modifier(self, **kwargs):
        match kwargs["query_type"]:
            case "itemavailable":
                if kwargs["response"]:
                    return f"Yes, {kwargs['itemID']} is available."
                else:
                    return f"No, {kwargs['itemID']} is not available."
            case "itemcount":
                return f"There are {int(kwargs['response'])} {kwargs['itemID']} now."
            case "itemorderplace":
                if kwargs["response"]:
                    return f"Yes, you can place order."
                else:
                    return f"No, you can't place order since there aren't sufficient items"
    
    def itemavailability(self, querytype: str, **kwargs):
        api_url = "/api/availability/beta/availabilitydetailbyview"
        body = '''{
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
        ''' % kwargs['itemID']
        
        response = self.API_requester(api_url=api_url, body=body)

        if response['data'] == None:
            quantity = 0
        else:
            quantity = response['data'][0]['TotalQuantity']
        
        
        match querytype:
            case "itemavailable":
                response =  {"query_type": querytype, "response": quantity > 0, "itemID": kwargs['itemID']}
            case "itemcount":
                response =  {"query_type": querytype, "response": quantity, "itemID": kwargs['itemID']}
            case "itemorderplace":
                response =  {"query_type": querytype, "response": quantity > kwargs['qty'], "itemID": kwargs['itemID']}

        response = self.response_modifier(**response)

        return response
