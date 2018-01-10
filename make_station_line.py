import requests
import json
mta_api_url = "https://rcgj41hz63.execute-api.us-east-1.amazonaws.com/v2"

# submitting request to get list of train lines
MTARequest = requests.get(mta_api_url+"/routes")
data = json.loads(MTARequest.text)
stations = []

# iterate over each train line and get associated station IDs
for line in data['data']:
    if(str(line) == ''):
        continue
    MTARequest = requests.get(mta_api_url+"/by-route/" + line)
    data = json.loads(MTARequest.text)
    for station in data['data']:
        print(line + "|" + str(station['id']) + "|" + str(station['name']) )
