from __future__ import print_function # Python 2/3 compatibility
import boto3
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime

## Must have already created DynamoDB table called "User" for this to work
## It should have a single primary key, "UserId"

user_table = boto3.resource('dynamodb').Table('User')
request_table = boto3.resource('dynamodb').Table('Request')

def get_user(session):
    """ Fetch user info from DynamoDB """
    try:
        response = user_table.get_item(
            Key={'userId': session['user']['userId']}
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False
    
    try:
        return response['Item']
    except KeyError:
        return False

def save_session(session,request):
    """ Save session info to DynamoDB """
    try:
        
        response = request_table.put_item(
            Item={
                'userId': session.user.userId,
                'sessionId': session.sessionId,
                'requestId': request.requestId,
                'intent': request.intent.name if "intent" in request else {},
                'session': json.dumps(session['attributes']),
                'slots': json.dumps(request['intent']['slots']) if "intent" in request and "slots" in request['intent'] else {},
                'date': str(datetime.now())
            }
        )
        print("PutItem Request succeeded:")
        
        print(json.dumps(response))
    
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False

def save_last_train(session,request):
    """ Save User info to DynamoDB """
    try:
        response = user_table.put_item(
            Item={
                'userId': session.user.userId,
                'sessionId': session.sessionId,
                'requestId': request.requestId,
                'intent': request.intent.name if "intent" in request else {},
                'session': json.dumps(session['attributes']),
                'slots': json.dumps(request['intent']['slots']) if "intent" in request and "slots" in request['intent'] else {},
                'date': str(datetime.now())
            }
        )
        print("PutItem Last User Train succeeded:")
        
        print(json.dumps(response))
    
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False

## Test commands           
#print(get_user("Victoria"))

#save_session(sessionId="ABC",userId="Victoria",session={},lastResponse="Hello2")
