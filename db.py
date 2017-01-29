from __future__ import print_function # Python 2/3 compatibility
import boto3
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

## Must have already created DynamoDB table called "User" for this to work
## It should have a single primary key, "UserId"

table = boto3.resource('dynamodb').Table('User')

def get_user(session):
    """ Fetch user info from DynamoDB """
    try:
        response = table.get_item(
            Key={'userId': session['user']['userId']}
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False
    
    try:
        return response['Item']
    except KeyError:
        return False

def save_session(session,intent):
    """ Save User info to DynamoDB """
    try:
        response = table.put_item(
            Item={
                'userId': session['user']['userId'],
                'sessionId': session['sessionId'],
                'intent': intent,
                'session': json.dumps(session['attributes'])
            }
        )
        print("PutItem succeeded:")
        print(json.dumps(response))
    
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False

## Test commands           
#print(get_user("Victoria"))

#save_session(sessionId="ABC",userId="Victoria",session={},lastResponse="Hello2")
