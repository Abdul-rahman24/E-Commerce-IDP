import boto3

session = boto3.Session(
    profile_name="idp-sbx-trn-lab-01",
    region_name="ap-southeast-1"
)

dynamodb = session.client("dynamodb")

response = dynamodb.create_table(
    TableName="products_sdk_test",
    KeySchema=[
        {
            "AttributeName": "productId",
            "KeyType": "HASH"
        }
    ],
    AttributeDefinitions=[
        {
            "AttributeName": "productId",
            "AttributeType": "S"
        }
    ],
    BillingMode="PAY_PER_REQUEST",
    TableClass="STANDARD",
    DeletionProtectionEnabled=False,
    Tags=[
        {
            "Key": "ApplicationService",
            "Value": ""
        },
        {
            "Key": "CostCentre",
            "Value": ""
        }
    ]
)

print(response["TableDescription"]["TableArn"])