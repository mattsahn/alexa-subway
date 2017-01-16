import logging
import requests
import json
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
from app_utils import dict_from_file, list_from_file, word_combine, get_train_times, find_station_id

## URL of MTA realtime subway API. I am hosting on Lambda
## TODO : make this an env variable instead of hard-coding
mta_api_url = "https://pbdexmgg8g.execute-api.us-east-1.amazonaws.com/dev"

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)

## Get dict files
direction_dict = dict_from_file("data/DirectionDict.txt")
train_dict = dict_from_file("data/TrainDict.txt")
station_dict = list_from_file("data/StationDict.txt")

## Get Line/Station data from file. Used for improving station recognition based on train requested
station_line = list_from_file("data/StationLine.txt")

## Main Intent Processing function
## -------------------------------

def process_intent(session,intent_name,station=None,train=None,direction=None):
    """ Processes intent based on session object and which Intent called it. Returns a question() or statement() object """
    
    print("Station: " + str(station))
    print("Train: " + str(train))
    print("Direction: " + str(direction))
    
    
    
    ## Attempt to resolve the train to use from latest user inputs or from previous session
    if(train != None):
        session.attributes['train'] = train
        try:    
            train_name = train_dict[str(train).lower()]
            session.attributes['train_name'] = train_name
            print("Successfully resolved train: " + str(train_name))
        except KeyError:
            return question("Sorry, I don't understand train, '" + str(train) + "'." + \
            " Which train do you want? For example, 'the five train'")
    else:
        try:
            train_name = session.attributes['train_name']
            print("Found train: " + str(train_name))
        except:
            print("No train in session")
            return question(" Which train do you want? For example, 'the five train'")
   
   
    
    ## Attempt to resolve the direction to use from session or latest user inputs
    if(direction != None):
        session.attributes['direction'] = direction
        try:
            direction_full = direction
            train_direction = direction_dict[str(direction).lower()]
            session.attributes['train_direction'] = train_direction
        except KeyError:
            return question("Sorry, I don't recognize direction, '" + str(direction) + "'." + \
            " Which direction do you want? For example, 'uptown' or 'downtown'")
    else:
        try:
            train_direction = session.attributes['train_direction']
            direction_full = session.attributes['direction']
            print("Found direction: " + str(train_direction))
        except:
            print("No direction in session")
            return question(" Which direction do you want? For example, 'uptown' or 'downtown'")
        
    
    ## Attempt to resolve the station ID and name to use from session or latest user inputs
    if(station != None):
         
        station_name,station_id,error_code,error_msg = find_station_id(train_name,station,station_dict,station_line,session)
        
        if(error_code > 0):
            print("Error type: " + str(error_code))
            return question(error_msg)
        print("Found station based on user input: " + str(station_name) + "[" + station_id + "]")
            
    else:
        try:
            station_name = session.attributes['station_name']
            station_id = session.attributes['station_id']
            print("Found station in session: " + str(station_name) + "[" + station_id + "]")
        except:
            print("No station in session")
            return question(" What station do you want? For example, 'Grand Central'")
    
    
    ## Handle the different Intents ##
    ## ---------------------------- ##
    
    if(intent_name in ["YesIntent","NextSubwayIntent","StationIntent","TrainIntent","DirectionIntent"]):
        
        print("Handling Intent " + intent_name)
        error_code,msg = get_train_times(mta_api_url,station_id,station_name,train_name,direction_full,train_direction)

        if error_code > 0:
            print("Error code: " + str(error_code))
            return question(msg)
        else:
            print("Successfully found train time. Message: " + msg)
            return statement(msg)
    
    return statement("We're done here with intent: " + intent_name)

## END Main Intent Processing function


## BEGIN Alexa flask-ask Intent Functions
## ----------------------------

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
    
    try:
        return process_intent(session,"NextSubwayIntent",train = train, station = station, direction = direction)
        
    except:
        return statement("There was a problem") 


@ask.intent("StationIntent")
## This intent is triggered when user replies with just a station as a result of being asked which
## station they want from a previous session. If other values are present in session (train and direction),
## then attempt to return answer based on the new station provided.


def station(station):
    print("Intent: StationIntent")

    try:
        return process_intent(session,"StationIntent",station = station)
        
    except:
        return statement("There was a problem") 
       
        
@ask.intent("TrainIntent")
## This intent is triggered when user replies with just a train as a result of being asked which
## train they want from a previous session. If other values are present in session (station and direction),
## then attempt to return answer based on the new train provided.


def train(train):
    print("Intent: TrainIntent")
    
    try:
        return process_intent(session,"TrainIntent",train = train)
        
    except:
        return statement("There was a problem") 


@ask.intent("DirectionIntent")
## This intent is triggered when user replies with just a direction as a result of being asked which
## direction they want from a previous session. If other values are present in session (station and train),
## then attempt to return answer based on the new direction provided.


def direction(direction):
    print("Intent: DirectionIntent")
    
    try:
        return process_intent(session,"DirectionIntent",direction = direction)
        
    except:
        return statement("There was a problem") 


@ask.intent("AMAZON.YesIntent")
## This intent is when user responds to question about whether the info is correct or not.
## If they say Yes, we want to return results to them based on values already stored in the session.

def yes():
    print("Intent: AMAZON.YesIntent")
    
    try:
        return process_intent(session,"YesIntent")
        
    except:
        return statement("There was a problem") 
        
@ask.intent("AMAZON.NoIntent")
## This intent is when user responds to question about whether the info is correct or not.
## If they say "No", we ask what station they want.

def no():
    return question("Which Station do you want?")
        
    
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
    
## END Alexa flask-ask Intent Functions


## BEGIN Run Server
## ----------------
if __name__ == '__main__':

    app.run(debug=True)

## END of Server