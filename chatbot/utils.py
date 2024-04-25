import requests

SITE_URL = "https://ptnrd.omni.manh.com/inventory"
TOKEN_URL = "https://ptnrd-auth.omni.manh.com/oauth/token"

class Requester:
    def __init__(self) -> None:
        self.username = "sme@veridian.info"
        self.password = "Veridian3!"
        self.client_id = "omnicomponent.1.0.0"
        self.client_secret = "b4s8rgTyg55XYNun"

    def requester(self, api_url, body, username:str = None, password:str = None, client_id:str = None, client_secret:str = None):
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
                return f"There are {kwargs['response']} {kwargs['itemID']} now."
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
        
        response = self.requester(api_url=api_url, body=body)

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
