# alexa-subway
Alexa app to provide real-time NYC subway arrival times at a given station

# to get started, create a virtualenv and activate it
virtualenv -p /usr/bin/python2.7 .venv
source .venv/bin/activate

# had to install special urllib3 for AWS to work right and not have SSL error
pip install urllib3[secure]

# current AWS URL as created by Zappa deploy
https://aai276h0nf.execute-api.us-east-1.amazonaws.com/dev

# to run server locally (after starting virtualenv)
python app.py

# to open local server to Alexa. Get https URL and past into endpoint URL config page in Alexa developer console
./ngrok http 5000

# /data/*Dict.txt
these files are used to map Alexa responses to specific, handled values.
TODO: create automated way of creating Dict files from inputs from MTA
