import boto3
import secrets

AWS_REGION='<REPLACE-WITH-YOUR-AWS-REGION>'
QBUSINESS_APPLICATION_ID='<REPLACE-WITH-YOUR-AMAZON-Q-BUSINESS-APPLICATION-ID>'
queries = [ 
    "REPLACE-WITH-QUERY1",
    "REPLACE-WITH-QUERY2"
]
 
aq_client = boto3.client(
    'qbusiness', 
    region_name=AWS_REGION
)

def make_query(query):
    resp = aq_client.chat_sync(
        applicationId = QBUSINESS_APPLICATION_ID,
        userMessage = query,
        clientToken = str(secrets.SystemRandom().randint(0,10000))
    )
    print(f"User query: {query}")
    print(f"Amazon Q response: {resp['systemMessage']}")
    print("---------")

for q in queries:
    make_query(q)
