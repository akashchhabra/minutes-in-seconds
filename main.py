import datetime
import requests
import logging
import re

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import PlainTextResponse
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from secrets import USER_ID, MONGO_DB_URL, DB_NAME
from Models import EventSubscriptionModel, TranscriptSubscriptionModel, MeetingModel, MeetingTimeModel, SubscriptionSuccessModel
from security.Authorization import Authorization

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.on_event("startup")
def startup_mongo_client():
    app.mongodb_client = MongoClient(MONGO_DB_URL, server_api = ServerApi('1'))
    logging.info("connected to mongoDB!!!")
    app.db = app.mongodb_client[DB_NAME]

@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_BETA_BASE_URL = "https://graph.microsoft.com/beta"


def save_event_subscription_to_db(subscription: SubscriptionSuccessModel):
    update_result = app.db["subscriptions"].insert_one(jsonable_encoder(subscription))
    print("update_result", update_result.acknowledged)
    if update_result.acknowledged:
        logging.info("Event subscription saved to database")
    else:
        logging.error(f"Error: cannot save event subscriptions details to database\n{update_result}")


def save_transcription_subscription_to_db(meeting_id: str, subscription: SubscriptionSuccessModel):
    update_result = app.db["meetings"].update_one(
        {"meetingId": meeting_id},
        {"$set": {"transcriptSubscription": jsonable_encoder(subscription)}}
    )
    if update_result.modified_count == 1:
        logging.info("Transcript details saved to database.")
    else:
        logging.error(f"Error: cannot saving transcript subscriptions details to database\n{update_result}")


def create_new_event_subscription():
    subscription_url = f"{GRAPH_BASE_URL}/subscriptions"
    subscription_model = EventSubscriptionModel()

    # Calculate dynamic expiration date
    today = datetime.datetime.now().date()

    expiration_date = today + datetime.timedelta(days=1)
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    logging.info("Creating New Event Subscription")
    # print(subscription_model.model_dump())
    response = requests.post(subscription_url, json=subscription_model.model_dump(), headers=Authorization.getHeaders())

    if response.status_code == 201:
        subscription_info = response.json()
        logging.info("Event subscription created successfully.")
        save_event_subscription_to_db(SubscriptionSuccessModel(**subscription_info))
        return True
    else:
        print("Error creating subscription")
        print(response.text)
        return False


def create_new_transcript_subscription(meeting_id: str):
    logging.info(f"Now creating new transcript subscription for meeting {meeting_id[:4]}...{meeting_id[-4:]}")
    subscription_url = f"{GRAPH_BETA_BASE_URL}/subscriptions"
    subscription_model = TranscriptSubscriptionModel()

    # Calculate dynamic expiration date
    today = datetime.datetime.now(datetime.timezone.utc)

    expiration_date = today + datetime.timedelta(hours=2)
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    # adding meeting id to request body
    subscription_model.resource = subscription_model.resource.replace("<onlineMeetingId>", meeting_id)

    logging.info("Creating New Transcript Subscription")
    # print(subscription_model.model_dump())
    response = requests.post(subscription_url, json=subscription_model.model_dump(), headers=Authorization.getHeaders())

    if response.status_code == 201:
        subscription_info = response.json()
        logging.info("Transcript subscription created successfully.")
        save_transcription_subscription_to_db(meeting_id, SubscriptionSuccessModel(**subscription_info))
    else:
        logging.error(f"Error in creating transcript subscription\n{response.text}")


def get_meeting_id_using_event_id(event_id: str):
    meeting = MeetingModel(eventId=event_id)
    event_url = f"{GRAPH_BASE_URL}/users/{USER_ID}/events/{event_id}"
    meeting_url = f"{GRAPH_BASE_URL}/users/{USER_ID}/onlineMeetings"
    # print("calling",event_url)
    event_response = requests.get(event_url, headers=Authorization.getHeaders(), timeout=10)
    if event_response.status_code == 200:
        event = event_response.json()
        if event["isOnlineMeeting"] and event["onlineMeetingProvider"] == "teamsForBusiness":
            meeting.subject = event["subject"]
            meeting.startTime = MeetingTimeModel(**event["start"])
            meeting.endTime = MeetingTimeModel(**event["end"])
            meeting.joinUrl = event["onlineMeeting"]["joinUrl"]
            params = {
                "$filter": f"JoinWebUrl eq '{meeting.joinUrl}'"
            }
            # print("calling", meeting_url)
            meeting_response = requests.get(meeting_url, params=params, headers=Authorization.getHeaders(), timeout=10)
            if meeting_response.status_code == 200:
                meeting_json = meeting_response.json()
                meeting.meetingId = meeting_json["value"][0]["id"]
                # save meeting details to db
                app.db["meetings"].insert_one(jsonable_encoder(meeting))
                logging.info("Meeting Details extracted and stored in database")
            else:
                logging.error(f"Error fetching event\n{meeting_response.text}")
    else:
        logging.error(f"Error fetching event\n{event_response.text}")
    return meeting.meetingId


def replyall_summary_to_meeting_invite(meeting_id, summary, action_points):
    print("fetching meeting from db")
    meeting = MeetingModel(**app.db["meetings"].find_one(
        {"meetingId": meeting_id}
    ))
    print("meeting from db",meeting.eventId)
    replyall_url = f"{GRAPH_BASE_URL}/users/{USER_ID}/messages/{event_id}/replyAll"
    reply_content = f"""
    Hi Team,
    
    Here are minutes of the meeting\n
    {summary}\n\n
    Here are some action points\n
    {action_points}\n
    Regards,
    MinutesInSeconds
    """
    reply_data = {
            "message": {
                "body": {
                    "contentType": "text",
                    "content": reply_content
                }
            }
        }
    response = requests.post(replyall_url, headers=Authorization.getHeaders(), json=reply_data)
    print("response.status_code",response.status_code)
    if response.status_code == 202:
        logging.info("Transcript summary and action points sent successful")
    else:
        logging.error(f"Error in sending summary in mail\n{response.text}")

def summarize_transcript(transcripts_vtt: str):
    return transcripts_vtt, "action points"

def get_transcripts(meeting_id, transcript_id):
    transcripts_vtt = ""
    transcript_url = f"{GRAPH_BETA_BASE_URL}/users/{USER_ID}/onlineMeetings/{meeting_id}/transcripts/{transcript_id}/content"
    params = {
        "$format": "text/vtt"
    }
    transcript_response = requests.get(transcript_url, params=params, headers=Authorization.getHeaders(), timeout=10)
    if transcript_response.status_code == 200:
        logging.info("Transcripts fetched successfully")
        transcripts_vtt = str(transcript_response.text)
        print(f"vtt\n{transcripts_vtt}")
    else:
        logging.error(f"Error in fetching transcript\n{transcript_response.text}")
    return transcripts_vtt

def handel_new_transcript_notification(notification: dict):
    transcript_resource_url = notification["value"][0]["resource"]
    logging.info(f"received transcript_resource_url {transcript_resource_url}")
    regex = "\(.*?\)"
    ids: list[str] = re.findall(regex, transcript_resource_url)
    meeting_id, transcript_id = [id.lstrip("('").rstrip("')") for id in ids]

    # TODO save_transcript_id_in_db()

    transcripts_vtt = get_transcripts(meeting_id, transcript_id)

    summary, action_points = summarize_transcript(transcripts_vtt)

    replyall_summary_to_meeting_invite(meeting_id, summary, action_points)


def handel_new_events_notification(notification: dict):
    # fetching event dict from notification
    event = notification["value"][0]
    print("event_id", event["resourceData"]["id"])
    change_type = event["changeType"]
    if change_type == "created":
        meeting_id = get_meeting_id_using_event_id(event["resourceData"]["id"])
        if meeting_id != "":
            create_new_transcript_subscription(meeting_id)


@app.get("/")
def hello():
    return {"message": "hello world from get endpoint"}


@app.post("/")
def hello():
    return {"id": "notification"}

@app.get("/token")
def getToken():
    return Authorization.getHeaders()
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
    create_new_transcript_subscription(meeting_id)
    return {"message": "executed"}


@app.post("/handle/new-events", response_class=PlainTextResponse)
def handel_new_events(validationToken: str = None, notification: dict = None, background_task: BackgroundTasks = None):
    # Validating subscription creation
    if validationToken:
        print("validation_token: " + validationToken)
        return validationToken

    logging.info("New event notification received...")
    background_task.add_task(handel_new_events_notification, notification)
    return "event received, Thank you"


@app.post("/handle/new-transcripts", response_class=PlainTextResponse)
def handle_new_transcripts(validationToken: str = None, notification: dict = None, background_task: BackgroundTasks = None):
    # Validating subscription creation
    if validationToken:
        print("validation_token: " + validationToken)
        return validationToken

    logging.info("New transcript notification received...")
    background_task.add_task(handel_new_transcript_notification, notification)

    return "event received, Thank you"

