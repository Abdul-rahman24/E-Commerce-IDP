import boto3
import time

def setup_cart_table():
    print("Connecting to AWS via company profile...")
    # 1. Use the company session
    session = boto3.Session(
        profile_name="idp-sbx-trn-lab-01",
        region_name="ap-southeast-1"
    )
    
    dynamodb_client = session.client('dynamodb')
    
    # 2. Add the company suffix to the table name
    table_name = 'cart_abd' 
    
    try:
        print(f"Creating '{table_name}' table with required tags...")
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'userId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'userId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
            TableClass="STANDARD",
            DeletionProtectionEnabled=False,
            # 3. Add the mandatory company tags
            Tags=[
                {
                    "Key": "ApplicationService",
                    "Value": "CartService" 
                },
                {
                    "Key": "CostCentre",
                    "Value": "YourCostCentreID" 
                }
            ]
        )
        print("Waiting for table to be active...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print("Enabling Time-To-Live (TTL) on 'expiresAt' attribute...")
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'expiresAt'
            }
        )
        print("Cart table and TTL successfully configured!")
        
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == "__main__":
    setup_cart_table()