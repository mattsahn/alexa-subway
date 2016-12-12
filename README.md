# alexa-subway
Alexa app to provide real-time NYC subway arrival times at a given station

# to get started, create a virtualenv and activate it
virtualenv -p /usr/bin/python2.7 .venv
source .venv/bin/activate

# had to install special urllib3 for AWS to work right and not have SSL error
pip install urllib3[secure]


