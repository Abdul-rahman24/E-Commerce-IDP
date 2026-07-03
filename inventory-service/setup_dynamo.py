import boto3

def create_inventory_table():
    print("Connecting to AWS via company profile...")
    # 1. Use the company session
    session = boto3.Session(
        profile_name="idp-sbx-trn-lab-01",
        region_name="ap-southeast-1"
    )
    
    dynamodb = session.client('dynamodb')
    
    # 2. Add the company suffix to the table name
    table_name = 'inventory_abd'
    
    print(f"Creating '{table_name}' table with required tags...")
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'productId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'productId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
        TableClass="STANDARD",
        DeletionProtectionEnabled=False,
        # 3. Add the mandatory company tags
        Tags=[
            {
                "Key": "ApplicationService",
                "Value": "" # Fill in your actual company value
            },
            {
                "Key": "CostCentre",
                "Value": "" # Fill in your actual company value
            }
        ]
    )
    print(f"Table created successfully!")
    print(f"ARN: {response['TableDescription']['TableArn']}")

if __name__ == "__main__":
    create_inventory_table()