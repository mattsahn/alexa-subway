
<p align="center">
  <img src="https://images-na.ssl-images-amazon.com/images/I/516aDn++z7L.png" alt="NextSubway"/>
</p>

# alexa-subway
Alexa app called NextSubway to provide real-time NYC subway arrival times at a given station

Available for Alexa on Amazon here: https://www.amazon.com/Matt-Sahn-NextSubway/dp/B01N9MO4DT/

# to get started, create a virtualenv and activate it
virtualenv -p /usr/bin/python2.7 .venv

source .venv/bin/activate

# had to install special urllib3 for AWS to work right and not have SSL error
pip install urllib3[secure]

# current AWS URL as created by Zappa deploy
https://aai276h0nf.execute-api.us-east-1.amazonaws.com/dev

## v5
//https://s490itlmml.execute-api.us-east-1.amazonaws.com/v2
https://e8k7etqp31.execute-api.us-east-1.amazonaws.com/v5

# to run server locally (after starting virtualenv)
python app.py

# to open local server to Alexa. Get https URL and past into endpoint URL config page in Alexa developer console
./ngrok http 5000

# /data/*Dict.txt
these files are used to map Alexa responses to specific, handled values.
TODO: create automated way of creating Dict files from inputs from MTA

# make StationLine list
python make_station_line.py  > data/StationLine.txt

# make StationDict list
# List needs to be manually craafted for accuracy in alexa!
python make_station_dict.py  | sort | uniq > StationDict.txt

# post process the station dict file to clear up spelling/words for matching 

sh -x post_process_stations.cmd