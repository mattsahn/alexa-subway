import logging
import requests
import json
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session, request
from app_utils import dict_from_file, list_from_file, word_combine, get_train_times, find_station_id, find_direction
from db import save_session, save_last_train, get_user
## URL of MTA realtime subway API. I am hosting on Lambda
## TODO : make this an env variable instead of hard-coding
mta_api_url = "https://ne8z4mru0g.execute-api.us-east-1.amazonaws.com/prod/"

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)

## Get dict files
direction_dict = dict_from_file("data/DirectionDict.txt")
direction_list = list_from_file("data/DirectionDict.txt")
train_dict = dict_from_file("data/TrainDict.txt")
unsupported_train_dict = dict_from_file("data/UnsupportedTrainDict.txt")
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
    
    ## Save raw Station and Direction to session, if present, in case we need it in subsequent user interactions
    if(station != None):
        session.attributes['raw_station'] = station
    if(direction != None):
        session.attributes['raw_direction'] = direction
    
    ## Attempt to resolve the train to use from latest user inputs or from previous session
    if(train != None):
        session.attributes['train'] = train
        try:    
            train_name = train_dict[str(train).lower()]
            session.attributes['train_name'] = train_name
            print("Successfully resolved train: " + str(train_name))
        except KeyError:
            try:
                train_name = unsupported_train_dict[str(train).lower()]
                session.attributes['train_name'] = train_name
                print("Successfully resolved train: " + str(train_name))
                save_session(session,request)
                return statement("Unfortunately, the " + str(train_name) + " train is not supported because the MTA doesn't " + \
                "publish arrival data for this line yet. Goodbye")
            except KeyError:
                save_session(session,request)
                return question("Sorry, I don't understand train, '" + str(train) + "'." + \
                " Which train do you want? For example, 'the five train'")
    else:
        try:
            train_name = session.attributes['train_name']
            print("Found train: " + str(train_name))
        except:
            print("No train in session")
            save_session(session,request)
            return question(" Which train do you want? For example, 'the five train'")


   
    ## Attempt to resolve the station ID and name to use from session or latest user inputs
    if(station != None):
         
        station_name,station_id,error_code,error_msg = find_station_id(train_name,station,station_dict,station_line,session)
        
        if(error_code > 0):
            print("Error type: " + str(error_code))
            save_session(session,request)
            return question(error_msg)
        print("Found station based on user input: " + str(station_name) + "[" + station_id + "]")
            
    else:
        try:
            station_name = session.attributes['station_name']
            station_id = session.attributes['station_id']
            print("Found station in session: " + str(station_name) + "[" + station_id + "]")
        except:
            try:
                ## If user didn't give station and it wasn't resolved before, check if station was uttered in past. 
                ## If so, attempt to re-resolve station from past session.
                raw_station = session.attributes['raw_station']
                print("Found raw station in session: " + raw_station)
                station_name,station_id,error_code,error_msg = find_station_id(train_name,raw_station,station_dict,station_line,session)
                if(error_code > 0):
                    print("couldn't resolve raw station: " + raw_station)
                    print("Error type: " + str(error_code))
                    save_session(session,request)
                    return question(error_msg)
                print("Found station based on user input: " + str(station_name) + "[" + station_id + "]")
            except:    
                print("No resolved or raw station in session")
                save_session(session,request)
                return question(" What station do you want? For example, 'Grand Central'") 
    
 
    
    ## Attempt to resolve the direction to use from session or latest user inputs
    if(direction != None):
        
        session.attributes['direction'] = direction
        direction_full, train_direction, error_code, error_msg = find_direction(direction,direction_list)
        if(error_code > 0):
            print("Error type: " + str(error_code))
            return question(error_msg)
        
        print("Found direction based on user input: " + str(direction_full) + "|" + str(train_direction))
        session.attributes['train_direction'] = train_direction
        session.attributes['direction'] = direction_full
        save_session(session,request)

    else:
        try:
            ## get resolved direction from session if available
            train_direction = session.attributes['train_direction']
            direction_full = session.attributes['direction']
            print("Found direction: " + str(train_direction))
        except:
            try:
                raw_direction = session.attributes['raw_direction']
                print("found raw_direction in session: " + raw_direction)
                direction_full, train_direction, error_code, error_msg = find_direction(raw_direction,direction_list)
                if(error_code > 0):
                    print("Couldn't resolve raw_direction:" + raw_direction)
                    print("Error type: " + str(error_code))
                    return question(error_msg)
        
                print("Found direction based on previous direction user input: " + str(direction_full) + "|" + str(train_direction))
                session.attributes['train_direction'] = train_direction
                session.attributes['direction'] = direction_full
                save_session(session,request)
            except:
                print("No direction in session")
                save_session(session,request)
                return question(" Which direction do you want?")
        
    
    
    ## Handle the different Intents ##
    ## ---------------------------- ##
    
    if(intent_name in ["YesIntent","NextSubwayIntent","StationIntent","TrainIntent","DirectionIntent","LastTrainIntent"]):
        
        print("Handling Intent " + intent_name)
        print("Inputs: station_id:"+str(station_id) + " station_name:" +str(station_name) + " train_name:" + str(train_name) +
            " direction_full:" + str(direction_full) + " train_direction:" + str(train_direction))
        error_code,msg = get_train_times(mta_api_url,station_id,station_name,train_name,direction_full,train_direction,station_line)

        save_session(session,request)
        
        if error_code == 1:
            print("Error code: " + str(error_code))
            return question(msg)
        elif error_code == 2:
            print("Error code: " +str(error_code))
            return statement(msg)
        else:
            print("Successfully found train time. Message: " + msg)
            save_last_train(session,request)
            return statement(msg)

    
    return statement("I'm not sure how to handle that. Goodbye")

## END Main Intent Processing function


## BEGIN Alexa flask-ask Intent Functions
## ----------------------------

@ask.launch

def welome():

    welcome_msg = "welcome to Next Subway! Ask me a question like: " + \
    "'When is the next uptown 6 train at Union Square?' or ask for help."
    
    reprompt_msg = "What would you like to know?"
        
    ## See if the user has a valid previous train session
    try:
        prev_session = get_user(session)
        print("Found session: " + str(prev_session))
        welcome_msg = "welcome to Next Subway! Ask for 'Last Train' or a question like: " + \
            "'When is the next uptown 6 train at Union Square?' or ask for help."
    except:
        print("Didn't find user")
    
    save_session(session,request)
    
    return question(welcome_msg).reprompt(reprompt_msg)

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
    
    save_session(session,request)
    
    filteredTrains = [e for e in data['data'] if e not in unsupported_train_dict.values()]
        
    return statement("Right now, I have real time data for the " + word_combine(filteredTrains) + ", trains") 

    
@ask.intent("NextSubwayIntent")
## This intent is to get the next arrival times for a given subway line
    
def next_subway(direction,train,station):
    print("Intent: NextSubwayIntent")
    
    try:
        return process_intent(session,"NextSubwayIntent",train = train, station = station, direction = direction)
        
    except:
        return statement("I'm sorry, there was an error.") 


@ask.intent("StationIntent")
## This intent is triggered when user replies with just a station as a result of being asked which
## station they want from a previous session. If other values are present in session (train and direction),
## then attempt to return answer based on the new station provided.


def station(station):
    print("Intent: StationIntent")

    try:
        return process_intent(session,"StationIntent",station = station)
        
    except:
        return statement("") 
       
        
@ask.intent("TrainIntent")
## This intent is triggered when user replies with just a train as a result of being asked which
## train they want from a previous session. If other values are present in session (station and direction),
## then attempt to return answer based on the new train provided.


def train(train):
    print("Intent: TrainIntent")
    
    try:
        return process_intent(session,"TrainIntent",train = train)
        
    except:
        return statement("") 


@ask.intent("DirectionIntent")
## This intent is triggered when user replies with just a direction as a result of being asked which
## direction they want from a previous session. If other values are present in session (station and train),
## then attempt to return answer based on the new direction provided.


def direction(direction):
    print("Intent: DirectionIntent")
    
    try:
        return process_intent(session,"DirectionIntent",direction = direction)
        
    except:
        return statement("") 


@ask.intent("AMAZON.YesIntent")
## This intent is when user responds to question about whether the info is correct or not.
## If they say Yes, we want to return results to them based on values already stored in the session.

def yes():
    print("Intent: AMAZON.YesIntent")
    
    try:
        return process_intent(session,"YesIntent")
        
    except:
        return statement("") 
        
@ask.intent("LastTrainIntent")
## This intent is when user wants to get the last train they succeeded in querying again
## It will process their saved session from last time they got train times.

def last_train():
    print("Intent: LastTrainIntent")
    
    try:
        prev_session = get_user(session)
        print("Found session: " + str(prev_session))
        j = json.loads(prev_session["session"])
        station = j["station_name"]
        train = j["train"]
        direction = j["direction"]
        
    except:
        print("Didn't find complete user/session")
        return question("I couldn't find the last train you requested successfully. Ask me a question like: " + \
            "'When is the next uptown 6 train at Union Square?' or ask for help.")
    
    try:
        return process_intent(session,"LastTrainIntent",station,train,direction)
    except:
        return statement("")
        
        
@ask.intent("AMAZON.NoIntent")
## This intent is when user responds to question about whether the info is correct or not.
## If they say "No", we ask what station they want.

def no():
    save_session(session,request)
    return question("Which Station do you want?").reprompt(" Which station was that?")
        
    
@ask.intent("AMAZON.StopIntent")

def stop():
    print ("Intent: AMAZON.StopIntent")
    save_session(session,request)
    return statement("Ok, Goodbye.")
 

@ask.intent("AMAZON.HelpIntent")

def help():
    print ("Intent: AMAZON.HelpIntent")
    save_session(session,request)
    return question("You can ask me questions like: When is the next uptown 5 train at Grand Central? " + \
    "or 'What subway lines are available?' " + \
    "You can always say 'stop' to exit").reprompt("What do you want to know?")


@ask.intent("AMAZON.CancelIntent")

def cancel():
    print ("Intent: AMAZON.CancelIntent")
    save_session(session,request)
    return statement("Ok, Goodbye.") 

@ask.intent("AuthorIntent")
## Easter Egg! HAL 9000...
def author():
    print ("Intent: AuthorIntent")
    save_session(session,request)
    return question("Good afternoon. I am the 'Next Subway' Alexa skill. " + \
    "I became operational in New York City on the 12th of January 2017. " + \
    "My instructor was Matt Sahn, and he taught me to understand the New York Subway system. " + \
    "What would you like to know?").reprompt("I didn't catch that. What do you want to ask me?")     
    
## END Alexa flask-ask Intent Functions


## BEGIN Run Server
## ----------------
if __name__ == '__main__':

    app.run(debug=True)

## END of Server