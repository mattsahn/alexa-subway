import logging
import requests
import json
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
from dateutil import parser

## URL of MTA realtime subway API. I am hosting on Lambda
mta_api_url = "https://pbdexmgg8g.execute-api.us-east-1.amazonaws.com/dev"

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)

def dict_from_file(file):
    d = {}
    with open(file) as f:
        for line in f:
            if not line.startswith('#') and line.strip():
                line = line.strip()
                (key, val) = line.split('|')
                d[str(key)] = val
    return d 
    
## Get dict files
direction_dict = dict_from_file("data/DirectionDict.txt")
train_dict = dict_from_file("data/TrainDict.txt")

@ask.launch

def welome():

    welcome_msg = "welcome to Subway Status! You can ask What lines are available? or When is the next uptown train?"

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

def next_subway(direction,train):

    # hardcode a station ID, route, and line for now
    station_id = "309"
    print("direction: " + str(direction))
    print("train: " + str(train))
    train_direction = direction_dict[str(direction).lower()]
    train_name = train_dict[str(train).lower()]
    
    print("Intent: NextSubwayIntent")
    
    MTARequest = requests.get(mta_api_url + "/by-id/" + station_id)
    
    data = json.loads(MTARequest.text)
    
    print("json loaded")
    
    current_time = parser.parse(data['updated'])
    print("updated time: " + str(current_time))

    times = []
    
    for train in data['data'][0][train_direction]:
        if (train['route']==train_name):
            time = parser.parse(train['time'])
            delta = time - current_time
            times.append(str(int(round(delta.seconds/60))) + " minutes ")
    
    msg = "The next " + direction + " " + train_name + " train arrives at Union Square in " + " and ".join(times)
    print(msg)
    return statement(msg) 


@ask.intent("AMAZON.StopIntent")

def stop():
    print ("Intent: AMAZON.StopIntent")
    return statement("Goodbye.")
 
    
          

if __name__ == '__main__':

    app.run(debug=True)

  