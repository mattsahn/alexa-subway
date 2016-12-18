import logging
import requests
import json
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
from dateutil import parser
from fuzzywuzzy import process, fuzz

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
station_dict = dict_from_file("data/StationDict.txt")

@ask.launch

def welome():

    welcome_msg = "welcome to Subway Status! You can ask What lines are available? " + \
    "or When is the next uptown 6 train at Union Square?"

    return question(welcome_msg)

@ask.intent("TestIntent")

def test_intent(station):
    print("heard: " + str(station))
    return(question("I heard: " + str(station)))
    
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
    
def next_subway(direction,train,station):
    print("Intent: NextSubwayIntent")

    # print what Alexa returned for each slot. Helps with debugging.
    print("direction: " + str(direction))
    print("train: " + str(train))
    print("station: " + str(station))
    
    # If Alexa returns 'None' for a slot value, we can't continue, so let user know what is missing.
    missing_msg = ""
    if (direction == 'None'):
        missing_msg += "I did not hear which direction you want, such as 'Uptown', 'Downtown', or 'Brooklyn Bound'. "
    if (train == 'None'):
        missing_msg += "I did not hear which train you want, such as 'Six train' or 'L train'. "
    if (station == 'None'):
        missing_msg += "I did not hear which station you want, such as 'Union Square' or 'West 4th Street'. "
    
    if (missing_msg != ""):
        print(missing_msg)
        return statement(missing_msg)
    
    
    # lookup user-spoken direction, train, and station to get standardized values
    
    try:
        train_direction = direction_dict[str(direction).lower()]
    except KeyError:
        return statement("Sorry, I don't recongnize direction " + str(direction))
        
    try:    
        train_name = train_dict[str(train).lower()]
    except KeyError:
        return statement("Sorry, I don't understand train " + str(train))
        
    try:
        # use fuzzy matching on station names in StationDict.txt to determine which station id to query
        # TODO: look into converting numbers ordinals (eg, 42nd) to words in the dict and the Alexa response
        #       to improve quality of station name matching
        # TODO: look into subsetting the list of stations to attempt to match based on the user's stated train
        #       line. For example, when user is asking for 6 train, only consider stations along the 6 route. This
        #       addresses problem of similary named stations (ie, 14th street, 42nd street)
        station_match = process.extractOne(str(station).lower(), station_dict.keys(), scorer=fuzz.token_set_ratio)[0] 
        print("Station Match:" + str(station_match))
        station_id = station_dict[str(station_match)]
        print("Station ID: " + str(station_id))
    except KeyError:
        return statement("Sorry, I don't understand station " + str(station))
    
    MTARequest = requests.get(mta_api_url + "/by-id/" + str(station_id))
    
    data = json.loads(MTARequest.text)
    
    print("json loaded")
    
    current_time = parser.parse(data['updated'])
    print("updated time: " + str(current_time))

    times = []
    
    # Look through MTA response and get next arrival times and time in minutes from now
    for train in data['data'][0][train_direction]:
        if (train['route']==train_name):
            time = parser.parse(train['time'])
            delta = time - current_time
            times.append(str(int(round(delta.seconds/60))) + " minutes ")
    
    msg = "The next " + direction + " " + train_name + " train arrives at " + station + " in " + " and ".join(times)
    print(msg)
    return statement(msg) 


@ask.intent("AMAZON.StopIntent")

def stop():
    print ("Intent: AMAZON.StopIntent")
    return statement("Goodbye.")
 
 
if __name__ == '__main__':

    app.run(debug=True)

  