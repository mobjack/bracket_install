import ast
import json
import requests
from app import app
from copy import deepcopy
from app.Logit import logit
from flask import jsonify, request
from app.Typeset import typecheck

@app.get('/')
def home():
    return('OK')

@app.route('/api/v1/status', methods=['GET'])
def apiStatus():
    return jsonify({'status': 'good'})

@app.route('/api/v1/setup', methods=['POST'])
def ingest_data():

    try: # if there's no type-key the json(maybe it came from syslog) try to determine the log type
        if request.json['location']:
            set_type = request.json
            pass
    except KeyError:
        #set_type = check_log.typetest(request.json)
        return jsonify({"status": "bad json", "input": request.json})

    
    sendtoextract(set_type) 
    return jsonify({"s":"0"}), 201

