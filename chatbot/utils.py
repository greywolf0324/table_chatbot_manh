import requests
from typing import List
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

SITE_URL = "https://ptnrd.omni.manh.com/inventory"
TOKEN_URL = "https://ptnrd-auth.omni.manh.com/oauth/token"

TABLES = {
    "itemavailability": ["item", "quantity"],
    "orderline_summary": ["order", "orderline", "items", "order_status"],
    "ordersearch": ["order", "order_information", "order_status"]
}
API_URLS = [
    '/api/availability/beta/availabilitydetailbyview',
    '{{url}}/omnifacade/api/customerservice/order/orderLine?page=0&size=10&sort=CreatedTimestamp%2Bdesc&query=O',
    '{{url}}/omnifacade/api/customerservice/order/search/advanced'
]

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
            "%s"
        ]
        }
        ''',
]
class SQL_chatbot:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained("juierror/text-to-sql-with-table-schema")
        self.model = AutoModelForSeq2SeqLM.from_pretrained("juierror/text-to-sql-with-table-schema")
        self.username = "sme@veridian.info"
        self.password = "Veridian3!"
        self.client_id = "omnicomponent.1.0.0"
        self.client_secret = "b4s8rgTyg55XYNun"

    def message_preprocessor(self, default_message):


        return default_message
    
    def table_detector(self, message):
        detected_table = TABLES["itemavailability"]

        return detected_table
    
    def url_detector(self, message):
        detected_url = API_URLS[0]

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
    
    def request_body_generator(self, query):
        def info_getter(basic_info):

            return 'item001'
        
        info = info_getter(query)
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
    
    def response_modifier(self, API_response):

        return API_response
    
    def chatbot(self, message):
        processed_message = self.message_preprocessor(message)
        table = self.table_detector(processed_message)
        api_url = self.url_detector(processed_message)
        query = self.query_generator(question=processed_message, table=table)
        print("query: ", query)
        api_request_body = self.request_body_generator(query)
        api_response = self.API_requester(api_url=api_url, body=api_request_body)
        print("api_response: ", api_response)
        answer = self.response_modifier(api_response)

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
