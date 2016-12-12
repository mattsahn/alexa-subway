import logging
import requests
import json
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session

## URL of MTA realtime subway API. I am hosting on Lambda
mta_api_url = "https://pbdexmgg8g.execute-api.us-east-1.amazonaws.com/dev"

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)


@ask.launch

def welome():

    welcome_msg = "welcome to Subway Status! You can ask What lines are available?"

    return question(welcome_msg)


@ask.intent("AvailableLinesIntent")
## This intent is to get the next arrival times for a given subway line

def available_lines():

    print("Intent: AvailableLinesIntent")
    
    MTARequest = requests.get(mta_api_url + "/routes")
    
    data = json.loads(MTARequest.text)
    
    print("json loaded")
    
    lines = ""
    for line in data['data']:
        print(line)  
        lines += line + ", "
        
    return statement("The available lines are " + lines) 
    
@ask.intent("NextSubwayIntent")
## This intent is to get the next arrival times for a given subway line

def next_subway():

    # hardcode a station ID, route, and line for now
    station_id = "309"
    route = "6"
    direction = "N"
    
    print("Intent: NextSubwayIntent")
    
    MTARequest = requests.get(mta_api_url + "/by-id/" + station_id)
    
    data = json.loads(MTARequest.text)
    
    print("json loaded")
    
    times = ""
    
    for train in data['data'][0][direction]:
        if (train['route']==route):
            times += train['time'] + ", "
        
    return statement("The next Northbound " + route + " train arrival times at Union Square are " + times) 


@ask.intent("AMAZON.StopIntent")

def stop():
    print ("Intent: AMAZON.StopIntent")
    return statement("Goodbye.")

if __name__ == '__main__':

    app.run(debug=True)
