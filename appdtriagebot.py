"""

Copyright (c) 2018 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.0 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

from __future__ import absolute_import, division, print_function

__author__ = "Tim Taylor <timtayl@cisco.com>"
__contributors__ = []
__copyright__ = "Copyright (c) 2018 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.0"

from flask import Flask , request
import requests
import json
import os
import datetime as dt

app = Flask(__name__)

def verify_incoming_request(request):

    date_time = dt.datetime.now()
    print("{}, verify_incoming_request start".format(date_time))

    # The 'Triage-Auth-Token' is something added to the header on the AppD Controller side by you.
    # It is basically a mechanism to provide some authentication.  Cause otherwise, folks could hammer your bot all day
    # with unauthorized requests and create spark rooms.  Remember never to store the triage auth token in code.

    appDAlertToken = request.headers.get('Triage-Auth-Token')

    if appDAlertToken == os.environ.get('APPD_ALERT_TRIAGE_TOKEN'):
        print("{}:   Request had the appropriate token for the appdtriagebot.".format(date_time))
        return True
    else:
        print("{}:   Request DID NOT HAVE the appropriate token for the appdtriagebot.".format(date_time))

    return False

def populate_spark_room_members(room_id, bot_token, email_list):
    # Use the Spark Memberships API to add people to the room.
    the_url = "https://api.ciscospark.com/v1/memberships"

    # Iterage through the mail list.
    for email_address in email_list:
        message_json = {"roomId": room_id,
                        "personEmail": email_address}
        date_time = dt.datetime.now()
        print("{},   sending request to add folks to the room".format(date_time))
        message_response = requests.post(the_url, json=message_json, verify=True,
                                         headers={'Authorization': 'Bearer {}'.format(bot_token), 'Accept':
                                             'application/json'})
        if message_response.status_code == 200:
            date_time = dt.datetime.now()
            print("{}: Successfully added to the room!".format(date_time))
        else:
            date_time = dt.datetime.now()
            print("{}: DID NOT Successfully add a person to the room!.  Status Code: {}".format(date_time,
                                                                                                message_response.status_code))

def populate_spark_room_message(room_id, bot_token, events):

    event = events[0]

    app_name = event['app']
    event_name = event['name']
    event_summary = event['message']
    event_deep_link_url = event['deeplink']

    post_url = "https://api.ciscospark.com/v1/messages"

    # Going crazy with the mark down, but the message should look good.
    # We could also potentially post other stuff here, like logs or similar.  But you get the idea.
    post_data = {'roomId': room_id,
                 'markdown': "## **{}** Had a Major Application Event!! \n\n * **Application Event:**  _{}_\n\n* **Event Summary:** {}\n\n * The event can be found here: {}".format(
                     app_name, event_name, event_summary, event_deep_link_url)}

    request_response_results = requests.post(post_url, json=post_data, headers={"Accept": "application/json",
                                                                                "Content-Type": "application/json",
                                                                                "Authorization": "Bearer {}".format(
                                                                                    bot_token)})

    if request_response_results.status_code == 200:
        date_time = dt.datetime.now()
        print("{}: Successfully posted the event to the room!".format(date_time))
    else:
        date_time = dt.datetime.now()
        print("{}: DID NOT Successfully post to the room!.  Status Code: {}".format(date_time,
                                                                                    request_response_results.status_code))


def build_triage_room(appd_request_json):

    the_url = "https://api.ciscospark.com/v1/rooms"
    date_time = dt.datetime.now()
    print("{}, build_triage_room start".format(date_time))

    # Get the event from the request json
    event = appd_request_json['events'][0]

    # Get the app name from the event
    app_name = event['app']

    # Create the title of the room from the app name we just pulled
    message_json = {"title": "AppD: {} Triage".format(app_name)}

    #Grab our bot_token that we stored in the environment because it's not a good thing to store it in code.
    bot_token = os.environ.get('APPD_TRIAGE_BOT_ACCESS_TOKEN')

    # Create the HTTP Post for creating the triage room
    message_response = requests.post(the_url, json=message_json, verify=True, headers={'Authorization': 'Bearer {}'.format(bot_token),'Accept':
                                                                   'application/json'})

    # Handle potential errors gracefully.  In this case just print something to STDOUT
    if message_response.status_code==200:
        message_response_json = json.loads(message_response.text)
        date_time = dt.datetime.now()
        print("{}: Creation of the room was successful".format(date_time))

        # Creating the room was successful.  Now we need to populate the room with people necessary to triage it.
        #
        # First we need the room id of the room we just created.
        room_id = message_response_json['id']

        date_time = dt.datetime.now()

        # We get that list of people from the json message.

        email_list = appd_request_json['triageEmailList']

        populate_spark_room_members(room_id, bot_token, email_list)

        # Retrieve the event that caused this and post it as a message to the room
        # Post to the room
        date_time = dt.datetime.now()
        print("{}: Posting event info to the room".format(date_time))

        events = appd_request_json['events']
        populate_spark_room_message(room_id, bot_token, events)



    else:
        date_time = dt.datetime.now()
        print("{}: failure, received status code: {}".format(date_time, message_response.status_code))

    date_time = dt.datetime.now()
    print("{}, build_triage_room end".format(date_time))


def delete_triage_rooms():

    date_time = dt.datetime.now()
    print("{}, delete_triage_rooms start".format(date_time))

    bot_token = os.environ.get('APPD_TRIAGE_BOT_ACCESS_TOKEN')

    date_time = dt.datetime.now()

    the_url = "https://api.ciscospark.com/v1/memberships"

    # We want to delete all the rooms that the triage bot is involved in.  So first we get a list of rooms that the bot
    # is currently located in.
    message_response = requests.get(the_url, verify=True,
                                     headers={'Authorization': 'Bearer {}'.format(bot_token), 'Accept':
                                         'application/json'})

    # Handle the errors.
    if message_response.status_code==200:
        date_time = dt.datetime.now()
        print("{},   getting memberships successful".format(date_time))
        message_response_json = json.loads(message_response.text)

        items = message_response_json['items']

        # Okay, now that we have the list of rooms, iterate through them.
        for item in items:
            print("{},     deleting rooms".format(date_time))
            room_id = item['roomId']

            the_url = "https://api.ciscospark.com/v1/rooms/{}".format(room_id)
            message_response = requests.delete(the_url, headers={'Authorization': 'Bearer {}'.format(bot_token)})

            if message_response.status_code == 204:
                print("{},        deleting room successful".format(date_time))
            else:
                print("{},        deleting room NOT successful.  Status Code: {}".format(date_time, message_response.status_code))

    print("{}, delete_triage_rooms end".format(date_time))



@app.route('/appdtriagebot', methods =['POST'])
def triage_room_required():

    date_time = dt.datetime.now()
    
    if verify_incoming_request(request):

        print("{}, POST request was successfully verified.".format(date_time))
        request_json = request.json

        build_triage_room(request_json)
    else:
        print("{}, POST request was NOT successfully verified.".format(date_time))

    return "Ok"


@app.route('/appdtriagebot', methods =['DELETE'])
def delete_triage_room():
    print("delete_triage_room:  got a request from /")

    date_time = dt.datetime.now()
    if verify_incoming_request(request):

        print("{}, DELETE request was successfully verified.".format(date_time))
        delete_triage_rooms()

    else:
        print("{}, DELETE request was NOT successfully verified.".format(date_time))

    return "Ok"

if __name__ == "__main__":
    app.run(host='0.0.0.0')
