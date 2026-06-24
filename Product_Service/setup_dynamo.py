import boto3

def create_table():
    dynamodb = boto3.client('dynamodb') # Automatically uses your 'aws configure' credentials
    
    print("Creating 'Products' table in AWS...")
    response = dynamodb.create_table(
        TableName='Products',
        KeySchema=[{'AttributeName': 'productId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'productId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    print("Table created successfully!")

if __name__ == "__main__":
    create_table()