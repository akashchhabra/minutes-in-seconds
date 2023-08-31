import json
import requests
import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import PlainTextResponse

from secrets import client_id, client_secret, user_id, tenant_id
from Models import EventSubscriptionModel, TranscriptSubscriptionModel

app = FastAPI()

access_token = "eyJ0eXAiOiJKV1QiLCJub25jZSI6IlhtaTA3Wk9WeVktR2lzMUVfcm1hUjBZTDd4aXg4ZkZQWFJ6WDcwd0MtNDQiLCJhbGciOiJSUzI1NiIsIng1dCI6Ii1LSTNROW5OUjdiUm9meG1lWm9YcWJIWkdldyIsImtpZCI6Ii1LSTNROW5OUjdiUm9meG1lWm9YcWJIWkdldyJ9.eyJhdWQiOiJodHRwczovL2dyYXBoLm1pY3Jvc29mdC5jb20iLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC81NWMzMDFjNi02ZDBmLTQwY2EtOTU5NS0zODYxZWYzNzg1YWUvIiwiaWF0IjoxNjkzMzE3MzM1LCJuYmYiOjE2OTMzMTczMzUsImV4cCI6MTY5MzMyMTIzNSwiYWlvIjoiRTJGZ1lQQmxFZUhRbURDVjJmU3daTC9qOXRXK0FBPT0iLCJhcHBfZGlzcGxheW5hbWUiOiJvdXRsb29rQm90QXBpcyIsImFwcGlkIjoiNGQyOTRhNzgtNmE5Yi00N2EyLWE4MDgtNzg2ZWZhNTBiOGUzIiwiYXBwaWRhY3IiOiIxIiwiaWRwIjoiaHR0cHM6Ly9zdHMud2luZG93cy5uZXQvNTVjMzAxYzYtNmQwZi00MGNhLTk1OTUtMzg2MWVmMzc4NWFlLyIsImlkdHlwIjoiYXBwIiwib2lkIjoiZGM4ODc0OTQtNDE1ZC00NDA2LTk3NWQtZjVhMjI2ZjAwN2U5IiwicmgiOiIwLkFVb0F4Z0hEVlE5dHlrQ1ZsVGhoN3plRnJnTUFBQUFBQUFBQXdBQUFBQUFBQUFDSkFBQS4iLCJyb2xlcyI6WyJPbmxpbmVNZWV0aW5ncy5SZWFkLkFsbCIsIk1haWwuUmVhZFdyaXRlIiwiQ2FsZW5kYXJzLlJlYWQiLCJNYWlsLlJlYWRCYXNpYy5BbGwiLCJVc2VyLlJlYWQuQWxsIiwiT25saW5lTWVldGluZ1RyYW5zY3JpcHQuUmVhZC5BbGwiLCJDYWxlbmRhcnMuUmVhZEJhc2ljLkFsbCIsIk1haWwuUmVhZCIsIk1haWwuU2VuZCIsIk1haWwuUmVhZEJhc2ljIl0sInN1YiI6ImRjODg3NDk0LTQxNWQtNDQwNi05NzVkLWY1YTIyNmYwMDdlOSIsInRlbmFudF9yZWdpb25fc2NvcGUiOiJBUyIsInRpZCI6IjU1YzMwMWM2LTZkMGYtNDBjYS05NTk1LTM4NjFlZjM3ODVhZSIsInV0aSI6InUtcjNURHF0WEVXckIzVlFWSkNkQUEiLCJ2ZXIiOiIxLjAiLCJ3aWRzIjpbIjA5OTdhMWQwLTBkMWQtNGFjYi1iNDA4LWQ1Y2E3MzEyMWU5MCJdLCJ4bXNfdGNkdCI6MTY4OTMyOTUxMH0.Nvw3fkAyCamIRyeEQufWzHn5R-XQyPpS3QWZT_33E1f_XZQPZRGIMWgA_bIaIquhxxCnS9EKtRBGL5NHHrtCRLxKhJnJJ4Tbw4B6Yqw9OPCPWF0TENSerLP_0VKGL6VF_htXnK9ytddKw56ZKkzXm5zZTdmw0e28_q1WEWYyTw1RfIpbKQBJMN4v-HSpJFszLBk9Mz5WBC_CH8GfpYkJGKDfZWtPz9e3ww3VvPrkWGmIvhZaiT7xebugVG86hMYCv82_tgtTT4cFbO3k8Gm8f37l_zemZ3QRMV9K-TRHG-srVtQnz7lQ47aXA_aayE0wvTElvjbVwTAdboM2Uuk_5Q"


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_BETA_BASE_URL = "https://graph.microsoft.com/beta"

headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def get_token(force_refresh_token: bool):
    global access_token
    if not force_refresh_token and access_token:
        return access_token
    print("fetching new token")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    token_response = requests.post(token_url, data=token_data)
    access_token = token_response.json()["access_token"]
    headers['Authorization'] = f"Bearer {access_token}"
    return access_token


def create_new_event_subscription():
    subscription_url = f"{GRAPH_BASE_URL}/subscriptions"
    subscription_model = EventSubscriptionModel()

    # Calculate dynamic expiration date
    today = datetime.datetime.now().date()

    expiration_date = today + datetime.timedelta(days=1)
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    print("sending")
    print(subscription_model.model_dump())
    response = requests.post(subscription_url, json=subscription_model.model_dump(), headers=headers)

    if response.status_code == 201:
        subscription_info = response.json()
        print("Subscription created successfully.")
        print(subscription_info)
        return True
    else:
        print("Error creating subscription")
        print(response.text)
        return False


def create_new_transcript_subscription(meeting_id: str):
    subscription_url = f"{GRAPH_BETA_BASE_URL}/subscriptions"
    subscription_model = TranscriptSubscriptionModel()

    # Calculate dynamic expiration date
    today = datetime.datetime.now(datetime.timezone.utc)

    expiration_date = today + datetime.timedelta(hours=1)
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    # adding meeting id to request body
    subscription_model.resource = subscription_model.resource.replace("<onlineMeetingId>", meeting_id)

    print("sending")
    print(subscription_model.model_dump())
    response = requests.post(subscription_url, json=subscription_model.model_dump(), headers=headers)

    if response.status_code == 201:
        subscription_info = response.json()
        print("Subscription created successfully.")
        print(subscription_info)
        return True
    else:
        print("Error creating subscription")
        print(response.text)
        return False


def get_meeting_id_using_event_id(event_url: str):
    meeting_id: str = ""
    event_url = f"{GRAPH_BASE_URL}/{event_url}"
    meeting_url = f"{GRAPH_BASE_URL}/users/{user_id}/onlineMeetings"
    # print("calling",event_url)
    event_response = requests.get(event_url, headers=headers) # check 200 status before processing
    if event_response.status_code == 200:
        event = event_response.json()
        join_web_url: str = event["onlineMeeting"]["joinUrl"]
        # print("join_web_url", join_web_url)

        params = {
            "$filter": f"JoinWebUrl eq '{join_web_url}'"
        }
        print("calling", meeting_url)
        meeting_response = requests.get(meeting_url, params=params, headers=headers)
        if meeting_response.status_code == 200:
            meeting = meeting_response.json()
            meeting_id = meeting["value"][0]["id"]
        else:
            print("Error fetching event")
            print(event_response.text)
    else:
        print("Error fetching event")
        print(event_response.text)
    return meeting_id

def handel_new_events_notification(data: dict):
    # fetching event dict from response
    event = data["value"][0]
    change_type = event["changeType"]
    meeting_id = get_meeting_id_using_event_id(event["resource"])
    if change_type == "created" and meeting_id != "":
        print("meeting id extracted", meeting_id)
        if create_new_transcript_subscription(meeting_id):
            print("Subscribed to meeting for new transcripts")
        else:
            print("Error occure while creating new transcript subscription")


@app.get("/")
def hello():
    return {"message": "hello world from get endpoint"}


@app.post("/")
def hello():
    return {"message": "hello world from post endpoint"}


@app.get("/token")
def get_route(force_refresh_token: bool = False):
    get_token(force_refresh_token)
    return {"message": access_token}


# helper route
@app.post("/create-new-event-subscription")
def event_subscription():
    if create_new_event_subscription():
        return {"message": "success"}
    else:
        return {"message": "error occured"}


# helper route
@app.post("/create-new-transcript-subscription/{meeting_id}")
def transcript_subscription(meeting_id: str):
    if create_new_transcript_subscription(meeting_id):
        return {"message": "success"}
    else:
        return {"message": "error occured"}


@app.post("/handle/new-events", response_class=PlainTextResponse)
def handel_new_events(validationToken: str = None, data: dict = None, background_task: BackgroundTasks = None):
    print("received new event")

    # Validating subscription creation
    if validationToken:
        print("validation_token: " + validationToken)
        return validationToken

    print(json.dumps(data, indent=4))
    background_task.add_task(handel_new_events_notification, data)
    print("task added to background")
    return "event received, Thank you"


@app.post("/handle/new-transcripts", response_class=PlainTextResponse)
def handle_new_transcripts(validationToken: str = None, notification: dict = None):
    print("received new transcript")

    # Validating subscription creation
    if validationToken:
        print("validation_token: " + validationToken)
        return validationToken

    print(json.dumps(notification, indent=4))
    return "event received, Thank you"

