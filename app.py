import logging
import requests
import json
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
from dateutil import parser
from fuzzywuzzy import process, fuzz
from app_utils import dict_from_file, list_from_file, word_combine

## URL of MTA realtime subway API. I am hosting on Lambda
mta_api_url = "https://pbdexmgg8g.execute-api.us-east-1.amazonaws.com/dev"

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)

## get station ID
def find_station_id(train,station,station_dict,station_line):
    error_code=0
    try:
        # use fuzzy matching on station names in StationDict.txt to determine which station id to query
        # TODO: look into converting numbers ordinals (eg, 42nd) to words in the dict and the Alexa response
        #       to improve quality of station name matching
        #       line. For example, when user is asking for 6 train, only consider stations along the 6 route. This
        #       addresses problem of similary named stations (ie, 14th street, 42nd street)
        station_match = process.extractOne(str(station).lower(), [j for i,j in station_dict], scorer=fuzz.token_set_ratio)
        score = station_match[1]
        station_name = station_match[0]
        print("Station Match:" + station_name + " Score: " + str(score))
        station_ids = [t for t in station_dict if t[1] == station_name]
        print(station_ids)
        station_id = station_ids[0][0]
        print("Station ID: " + str(station_id))
        
    except KeyError:
        error_code = 1
        return 0,0,error_code,("Sorry, I don't understand station, " + str(station) + "'. Which station do you want?")
    
    
    try:
        # use fuzzy matching on station names in StationDict.txt to determine which station id to query
        # Subset based on the train line the user stated. If match percentage is high enough, use this.
        
        stations_in_line = [j for (i,j) in station_line if i == train]
        filtered_station_dict = [t for t in station_dict if t[0] in stations_in_line]
        station_match = process.extractOne(str(station).lower(), [j for i,j in filtered_station_dict], scorer=fuzz.token_set_ratio)
        print("Filtered Station Match:" + str(station_match[0]) + " Score: " + str(station_match[1]) + " vs " + str(score))
        station_ids = [t for t in filtered_station_dict if t[1] == station_match[0]]
        print(station_ids)
        if (station_match[1] >= 85):
            print("using subsetted match " + station_match[0] + "instead of " + station_name)
            station_id = station_ids[0][0]
            station_name = station_match[0]

        print("Using Station ID: " + str(station_id))
        
    except KeyError:
        error_code = 2
        return 0,0,error_code,("Sorry, I don't understand station, " + str(station) + "." + \
        " What station do you want? For example, 'Grand Central'")
    
    session.attributes['station_id'] = station_id
    session.attributes['station_name'] = station_name
    
    if(score < 70):
        error_code = 3
        return station_name,station_id,error_code,("Is " + station_name + " the station you want?")
    
    return station_name,station_id,error_code,""
    
def get_train_times(station_id,station_name,train_name,direction,train_direction):
    MTARequest = requests.get(mta_api_url + "/by-id/" + str(station_id))
    
    data = json.loads(MTARequest.text)
    
    print("json loaded")
    
    current_time = parser.parse(data['updated'])
    print("updated time: " + str(current_time))

    times = []
    routes ={}
    error_code = 0
    # Look through MTA response and get next arrival times and time in minutes from now
    for train in data['data'][0][train_direction]:
        routes[train['route']]=1
        if (train['route']==train_name):
            time = parser.parse(train['time'])
            delta = time - current_time
            mins = " minutes"
            if (int(round(delta.seconds/60)) == 1): mins = " minute"
            times.append(str(int(round(delta.seconds/60))) + mins)
    if(not times):
        error_code = 1
        if (len(routes) == 1):
            trains_msg = " only has the " + routes.keys()[0] + " train."
        else:
            trains_msg = " has the " + word_combine(routes) + " trains."
        return error_code,("Hmm. I don't see any information for the " + train_name + " train at " + station_name + ". " + \
        "Perhaps that is not the train or station you want. " + station_name + trains_msg )
    
    msg = "The next " + direction + " " + train_name + " train arrives at " + station_name + " in " + word_combine(times)
    print(msg)
    return(error_code,msg)

## Get dict files
direction_dict = dict_from_file("data/DirectionDict.txt")
train_dict = dict_from_file("data/TrainDict.txt")
station_dict = list_from_file("data/StationDict.txt")

## Get Line/Station data from file
station_line = list_from_file("data/StationLine.txt")

@ask.launch

def welome():

    welcome_msg = "welcome to Next Subway! You can ask me questions like: What lines are available? " + \
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
        
    return statement("The available lines are " + word_combine(data['data'])) 
    
@ask.intent("NextSubwayIntent")
## This intent is to get the next arrival times for a given subway line
    
def next_subway(direction,train,station):
    print("Intent: NextSubwayIntent")
    
    # print what Alexa returned for each slot. Helps with debugging.
    print("User Spoke")
    print("----------")
    print("Heard direction: " + str(direction))
    print("Heard train: " + str(train))
    print("Heard station: " + str(station))
    
    # If Alexa returns 'None' for a slot value, we can't continue, so let user know what is missing.
    # Save known slot values to session in case of re-prompt so that they don't have to restate those values.
    missing_msg = ""
    missing_direction = False
    missing_station = False
    missing_train = False
    
    if (str(direction) == 'None'):
        missing_msg += "I did not hear which direction you want. "
        missing_direction = True
    else:
        session.attributes['direction'] = direction
    
        try:
            train_direction = direction_dict[str(direction).lower()]
            session.attributes['train_direction'] = train_direction
        except KeyError:
            return question("Sorry, I don't recognize direction, '" + str(direction) + "'." + \
            " Which direction do you want? For example, 'uptown' or 'downtown'")
    
    if (str(train) == 'None'):
        missing_msg += "I did not hear which train you want. "
        missing_train = True
    else:
        session.attributes['train'] = train
        try:    
            train_name = train_dict[str(train).lower()]
            session.attributes['train_name'] = train_name
        except KeyError:
            return question("Sorry, I don't understand train, '" + str(train) + "'." + \
            " Which train do you want? For example, 'the five train'")
    
    if (str(station) == 'None'):
        missing_station = True
    else:
        session.attributes['station'] = station
    
    if (missing_station):
        print(missing_msg)
        return question(" What station do you want? For example, 'Grand Central'")
    
    if (missing_train):
        print(missing_train)
        return question(" Which train do you want? For example, 'the five train'")
        
    if (missing_direction):
        print(missing_direction)
        return question(" Which direction do you want? For example, 'uptown' or 'downtown'")
    
    
    # lookup user-spoken direction, train, and station to get standardized values
        

        
    station_name,station_id,error_code,error_msg = find_station_id(train_name,station,station_dict,station_line)
    
    if(error_code > 0):
        print("Error type: " + str(error_code))
        return question(error_msg)
        
    
    error_code,msg = get_train_times(station_id,station_name,train_name,direction,train_direction)

    if error_code > 0:
        print("Error code: " + str(error_code))
        return question(msg)
    else:
        return statement(msg) 


@ask.intent("StationIntent")
## This intent is triggered when user replies with just a station as a result of being asked which
## station they want from a previous session. If other values are present in session (train and direction),
## then attempt to return answer based on the new station provided.


def station(station):
    print("Intent: StationIntent")
    print("Session Data")
    print("------------")
    print(str(session) + "\n")
    
    if(session.attributes['direction']):
        direction = session.attributes['direction']

    if(session.attributes['train_direction']):
        train_direction = session.attributes['train_direction']
        
    if(session.attributes['train_name']):
        train_name = session.attributes['train_name']
        
    # print what Alexa returned for each slot. Helps with debugging.
    print("station: " + str(station))


    station_name,station_id,error_code,error_msg = find_station_id(train_name,station,station_dict,station_line)
    
    if(error_code > 0):
        print("Error type: " + str(error_code))
        return question(error_msg)
        
    
    error_code,msg = get_train_times(station_id,station_name,train_name,direction,train_direction)

    if error_code > 0:
        print("Error code: " + str(error_code))
        return question(msg)
    else:
        return statement(msg) 


@ask.intent("AMAZON.YesIntent")
## This intent is when user responds to question about whether the info is correct or not.
## If they say Yes, we want to return results to them based on values already stored in the session.

def yes():
    print("Intent: AMAZON.YesIntent")
    print("Session Data")
    print("------------")
    print(str(session) + "\n")
    
    if(session.attributes['direction']):
        direction = session.attributes['direction']
    
    if(session.attributes['station_id']):
        station_id = session.attributes['station_id']
    
    if(session.attributes['station_name']):
        station_name = session.attributes['station_name']

    if(session.attributes['train_direction']):
        train_direction = session.attributes['train_direction']
        
    if(session.attributes['train_name']):
        train_name = session.attributes['train_name']
        
    
    error_code,msg = get_train_times(station_id,station_name,train_name,direction,train_direction)

    if error_code > 0:
        print("Error code: " + str(error_code))
        return question(msg)
    else:
        return statement(msg)
    
@ask.intent("AMAZON.StopIntent")

def stop():
    print ("Intent: AMAZON.StopIntent")
    return statement("Ok, Goodbye.")
 

@ask.intent("AMAZON.HelpIntent")

def help():
    print ("Intent: AMAZON.HelpIntent")
    return question("You can ask me questions like: What lines are available? " + \
    "or When is the next uptown 6 train at Union Square?")


@ask.intent("AMAZON.CancelIntent")

def cancel():
    print ("Intent: AMAZON.CancelIntent")
    return statement("Ok, Goodbye.") 
 
if __name__ == '__main__':

    app.run(debug=True)

  