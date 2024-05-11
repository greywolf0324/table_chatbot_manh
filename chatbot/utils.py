import requests
from typing import List
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transformers import pipeline
import json
import boto3
from typing import Dict
from chatbot.config import(
    message_preprocessor_prompt,
    no_order_prompt,
    no_item_prompt,
    response_modifier_prompt,
    answer_modifier_prompt,
    no_item_answer,
    no_order_answer,
    endpoint,
    aws_access_key_id,
    aws_secret_access_key,
    TOKEN_URL,
    TABLES,
    USERNAME,
    PASSWORD,
    CLIENT_ID,
    CLIENT_SECRET,
    BASICURL_ITEMTYPE,
    BASICURL_ORDERLINE,
    BASICURL_MAOORDER,
)

API_classifier = pipeline("sentiment-analysis", model="philgrey/my_awesome_model")
Question_classifier = pipeline("sentiment-analysis", model="philgrey/question_classifier")

runtime = boto3.client("sagemaker-runtime", region_name = "us-east-2", aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key)

class SQL_chatbot:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained("juierror/text-to-sql-with-table-schema")
        self.model = AutoModelForSeq2SeqLM.from_pretrained("juierror/text-to-sql-with-table-schema")
        self.username = USERNAME
        self.password = PASSWORD
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.message_saver = []

    def llmanswer_getter(self, input):
        payload = {
            "inputs": input,
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
        response = json.loads(response["Body"].read().decode("utf-8"))[0]['generated_text']
        print(response)
        i = 0
        processed_message = response.split("Output:")[2].split("\n")[0]
        print(processed_message, "--")
        length = len(processed_message)
        while not length:
            i += 1
            processed_message = response.split("Output:")[2].split("\n")[i]
            print(processed_message, "--")
            length = len(processed_message)
        
        return processed_message
    
    def question_classifier(self, message):
        match Question_classifier(message)[0]["label"]:
            case 'POSITIVE': return True
            case 'NEGATIVE': return False

    def message_preprocessor(self, message):
        # LLM: "HuggingFaceH4/zephyr-7b-beta"
        if len(message) == 1:
            return message
        else:
            processed_message = self.llmanswer_getter(message_preprocessor_prompt + message + "\nOutput:\n")

            return processed_message
    
    def IDdetector(self, question):
        ID = API_classifier(question)[0]['label']
        if ID == "maoorder" and "orderline" in "".join(question).lower():
            ID == "orderline"

        return ID
    
    def info_getter(self, query, ID):
        return query.split("=")[1].replace(" ", "").replace(";", "")
    
    def url_detector(self, query, ID):
        info = self.info_getter(query, ID)

        match ID:
            case "itemtype":
                detected_url = BASICURL_ITEMTYPE
            case "orderline":
                detected_url = BASICURL_ORDERLINE + info + "%27"
            case "maoorder":
                detected_url = BASICURL_MAOORDER
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

        if len(API_response['data']) == 0:
            if ID == "maoorder" or ID == "orderline":
                prompt = no_order_prompt
            elif ID == "itemtype":
                prompt = no_item_prompt
            processed_message = self.llmanswer_getter(prompt)
        else:
            data = API_response['data'][0]
            if ID == "maoorder":
                if content == "order_status":
                    self.response_data = dict((k, data[k]) for k in ('CreatedTimestamp', 'FulfillmentStatus', 'OrderTotal') if k in data)

            processed_message = self.llmanswer_getter(response_modifier_prompt + str(self.response_data) + "\nOutput:\n",)
            
        return processed_message
    
    def chatbot(self, message):
        To_nextstep = self.question_classifier(message)
        if To_nextstep:
            self.message_saver.append(message)

            processed_message   = self.message_preprocessor(" ".join(self.message_saver))
            ID                  = self.IDdetector(processed_message)
            table               = TABLES[ID]
            query               = self.query_generator(question=processed_message, table=table)
            api_url             = self.url_detector(query, ID)
            api_request_body    = self.request_body_generator(query, ID)
            api_response        = self.API_requester(api_url=api_url, body=api_request_body, ID = ID)
            answer              = self.response_modifier(api_response, ID, query)

            self.message_saver = []
        else:
            self.message_saver.append(message)

            ID = self.IDdetector("".join(self.message_saver))
            match ID:
                case "itemtype":
                    answer = no_item_answer
                case "orderline":
                    answer = no_order_answer
                case "maoorder":
                    answer = no_order_answer

            answer = self.llmanswer_getter(answer_modifier_prompt + str(answer) + "\nOutput:\n")
        
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
