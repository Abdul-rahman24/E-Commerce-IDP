import boto3

def setup_order_table():
    print("Connecting to AWS via company profile...")
    # 1. Use the company session
    session = boto3.Session(
        profile_name="idp-sbx-trn-lab-01",
        region_name="ap-southeast-1"
    )
    
    dynamodb_client = session.client('dynamodb')
    
    # 2. Add the company suffix to the table name
    table_name = 'orders_abd'
    
    try:
        print(f"Creating '{table_name}' table with GSI and required tags...")
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'orderId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'orderId', 'AttributeType': 'S'},
                {'AttributeName': 'userId', 'AttributeType': 'S'}
            ],
            # Keeping your Global Secondary Index intact
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserIdIndex',
                    'KeySchema': [{'AttributeName': 'userId', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
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
        print("Waiting for table to be active...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print("Order table successfully configured!")
        
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == "__main__":
    setup_order_table()