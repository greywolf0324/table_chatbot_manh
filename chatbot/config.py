

message_preprocessor_prompt = """Your role is to get one sentence by summarizing two or more sentences while preserving all the information contained in the inputs.
You have to remove unnecessary information as much as possible.
for example, if input is "I want to know get the status of an Order using the Advanced Summary Search", you can summarize it as "I want to know get the status of an Order" by removing "Advanced Summary Search".

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

response_modifier_prompt = """Your role is to generate output that explains input user will give you.
here are some requirements:
 - when you explain about the item ID or order ID, don't explain it with implicit form like 'x'. specify it like 'this order' or 'this item'.

use following format:

input:
User's input
Output:
your answer

input:
"""
answer_modifier_prompt = """Your role is to generate US Native english from following basic data. All grammar has to be perfect. 
use the following format:

inputs:
you haven't specify item ID
Output:
You haven't specified the item ID.

inputs:
"""
no_item_answer = "you didn't specify item ID"
no_order_answer = "you didn't specify order ID"

endpoint = "huggingface-pytorch-tgi-inference-2024-05-21-14-32-15-251"
aws_access_key_id = "AKIA4MTWMI6O4STOBVEC"
aws_secret_access_key = "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"

TOKEN_URL = "https://ptnrd-auth.omni.manh.com/oauth/token"

TABLES = {
    "itemtype": ["item", "quantity"],
    "orderline": ["order", "orderline", "items", "order_status"],
    "maoorder": ["order", "order_information", "order_status"]
}
USERNAME = "sme@veridian.info"
PASSWORD = "Veridian3!"
CLIENT_ID = "omnicomponent.1.0.0"
CLIENT_SECRET = "b4s8rgTyg55XYNun"
BASICURL_ITEMTYPE = "https://ptnrd.omni.manh.com/inventory/api/availability/beta/availabilitydetailbyview"
BASICURL_ORDERLINE = "https://ptnrd.omni.manh.com/omnifacade/api/customerservice/order/orderLine?page=0&size=10&sort=CreatedTimestamp%2Bdesc&query=OrderId%3D%27"
BASICURL_MAOORDER = "https://ptnrd.omni.manh.com/omnifacade/api/customerservice/order/search/advanced"