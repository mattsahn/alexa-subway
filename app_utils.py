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
    
def get_train_times(mta_api_url,station_id,station_name,train_name,direction,train_direction):
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
            trains_msg = " only has the " + routes.keys()[0] + " train. Which station and or train do you want?"
        elif(len(routes) == 0):
            error_code = 2
            trains_msg = " does not have any live MTA data available, unfortunately. Goodbye"
        else:
            trains_msg = " has the " + word_combine(routes) + " trains. Which station and or train do you want?"
        return error_code,("Hmm. I don't see any information for the " + train_name + " train at " + station_name + ". " + \
        "Perhaps that is not the train or station you want. " + station_name + trains_msg)
    
    msg = "The next " + direction + " " + train_name + " train arrives at " + station_name + " in " + word_combine(times)
    print(msg)
    return(error_code,msg)
    
## get station ID
def find_station_id(train,station,station_dict,station_line,session):
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