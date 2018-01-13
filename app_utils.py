import requests
import json
from dateutil import parser
from fuzzywuzzy import process, fuzz

def dict_from_file(file):
    """ Returns a dict object based on a file of pipe-delimited key/value pairs """
    d = {}
    with open(file) as f:
        for line in f:
            if not line.startswith('#') and line.strip():
                line = line.strip()
                (key, val) = line.split('|')
                d[str(key)] = val
    return d 

def list_from_file(file):
    """ Returns a list of tuples object based on a file of pipe-delimited key/value pairs """
    l = []
    with open(file) as f:
        for line in f:
            if not line.startswith('#') and line.strip():
                line = line.strip()
                (key, val) = line.split('|')[:2]
                l.append((str(key),val))
    return l 

def word_combine(x):
    """ Returns a string that combines a list of words with proper commas and trailing 'and' """
    num_words = len(x)
    if num_words == 1: return x[0]

    combined = ""
    i = 1
    for item in x:
        if i == num_words:
            combined += "and " + item
            break

        if (num_words == 2 and i == 1):
            combined += item + " "
        else:
            combined += item + ", "

        i+=1
    
    return combined
    
def get_train_times(mta_api_url,station_id,station_name,train_name,direction,train_direction,station_line):
    MTARequest = requests.get(mta_api_url + "/by-id/" + str(station_id))
    
    data = json.loads(MTARequest.text)
    
    print("json loaded")
    
    # wrap in try since a completely empty station will have no updated time
    try:
        current_time = parser.parse(data['updated'])
        print("updated time: " + str(current_time))
    except:
        current_time = ""

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
        
        # train may be temporarily not running. check against known station/line dict for that case
        t = (train_name,station_id)
        if t in station_line:
            error_code = 2
            print("found " + train_name + " train at station " + station_id + " in station line list. Train must not be running now.")
            return error_code,("Hmm, there's no arrival data currently for the " + direction + " " + train_name + " train at " + station_name + \
            ". It may be out of service for that station at this time. Goodbye.")
            
        # otherwise, give user info that might be of use for the station they asked for and reprompt.
        
        if (len(routes) == 1):
            trains_msg = " only has the " + routes.keys()[0] + " train. Which station or train do you want?"
        elif(len(routes) == 0):
            error_code = 1
            trains_msg = " does not have any MTA data available. Which station do you want?"
        else:
            trains_msg = " has the " + word_combine(routes) + " trains. Which station or train do you want?"
        return error_code,("Hmm. I don't see any information for the " + train_name + " train at " + station_name + ". " + \
        station_name + trains_msg)
    
    msg = "The next " + direction + " " + train_name + " train arrives at " + station_name + " in " + word_combine(times)
    print(msg)
    return(error_code,msg)
    
## get station ID
def find_station_id(train,station,station_dict,station_line,session):
    error_code=0
    try:
        # use fuzzy matching on station names in StationDict.txt to determine which station id to query

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
        # Subset stations based on the train line the user stated. If match percentage is high enough, use this instead of
        # initial match based solely on station name response from user. This increases accuracy of station match since the 
        # train is more easily/accurately recognized and we can use that information to exclude stations not along that line
        # and only look for matches on stations associated with that line.
        
        stations_in_line = [j for (i,j) in station_line if i == train]
        filtered_station_dict = [t for t in station_dict if t[0] in stations_in_line]
        station_match = process.extractOne(str(station).lower(), [j for i,j in filtered_station_dict], scorer=fuzz.token_set_ratio)
        print("Filtered Station Match:" + str(station_match[0]) + " Score: " + str(station_match[1]) + " vs " + str(score))
        station_ids = [t for t in filtered_station_dict if t[1] == station_match[0]]
        print(station_ids)
        if (station_match[1] >= 85) or ( station_match[1] >= 70 and station_match[1] >= (score - 5) ):
            # if subset match is higher than 85, use it, or if it's equal to non-subsetted score
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
    

## get direction
def find_direction(direction,direction_dict):
    # Given a user-provided direction response and a list of direction names and associated direction code,
    # find the best match and return the name and code
    error_code=0
    try:
        # use fuzzy matching on direction names in direction_dict
        direction_match = process.extractOne(str(direction).lower(), [i for i,j in direction_dict], scorer=fuzz.token_set_ratio)
        score = direction_match[1]
        direction_name = direction_match[0]
        print("Direction Match:" + direction_name + " Score: " + str(score))
        direction_ids = [j for j in direction_dict if j[0] == direction_name]
        direction_id = direction_ids[0][1]
        
    except KeyError:
        error_code = 1
        return 0,0,error_code,("Sorry, I don't understand direction, " + str(direction) + "'. Which direction do you want?")
    
    if (score < 70):
        ## If fuzzy match score is very low, confirm the direction with user
        error_code = 3
        return direction_name, direction_id, error_code, ("Sorry, I don't understand direction, " + str(direction) + "'. Which direction do you want?")
    
    return direction_name, direction_id, error_code, ""