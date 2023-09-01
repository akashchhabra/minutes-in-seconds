import json
import requests
import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pymongo import MongoClient

from secrets import USER_ID, MONGO_DB_URL, DB_NAME
from Models import EventSubscriptionModel, TranscriptSubscriptionModel
from security.Authorization import Authorization

app = FastAPI()


@app.on_event("startup")
def startup_mongo_client():
    app.mongodb_client = MongoClient(MONGO_DB_URL)
    db = app.mongodb_client[DB_NAME]


@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_BETA_BASE_URL = "https://graph.microsoft.com/beta"


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
    response = requests.post(subscription_url, json=subscription_model.model_dump(), headers=Authorization.getHeaders())

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
    response = requests.post(subscription_url, json=subscription_model.model_dump(), headers=Authorization.getHeaders())

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
    meeting_url = f"{GRAPH_BASE_URL}/users/{USER_ID}/onlineMeetings"
    # print("calling",event_url)
    event_response = requests.get(event_url, headers=Authorization.getHeaders()) # check 200 status before processing
    if event_response.status_code == 200:
        event = event_response.json()
        join_web_url: str = event["onlineMeeting"]["joinUrl"]
        # print("join_web_url", join_web_url)

        params = {
            "$filter": f"JoinWebUrl eq '{join_web_url}'"
        }
        print("calling", meeting_url)
        meeting_response = requests.get(meeting_url, params=params, headers=Authorization.getHeaders())
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

