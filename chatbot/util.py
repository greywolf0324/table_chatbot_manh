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
                return quantity > 0
            case "itemcount":
                return quantity
            case "itemorderplace":
                return quantity > kwargs['qty']