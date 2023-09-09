import logging
import datetime
import requests
import re
import openai

from fastapi.encoders import jsonable_encoder

from Minutes import db, config
from Minutes.Authorization import Authorization
from Minutes.Models import (
    EventSubscriptionModel,
    TranscriptSubscriptionModel,
    MeetingModel,
    MeetingTimeModel,
    SubscriptionSuccessModel
)


def save_event_subscription_to_db(subscription: SubscriptionSuccessModel):
    update_result = db["subscriptions"].insert_one(jsonable_encoder(subscription))
    if update_result.acknowledged:
        logging.info("Event subscription saved to database")
    else:
        logging.error(f"Error: cannot save event subscriptions details to database\n{update_result}")


def save_transcription_subscription_to_db(meeting_id: str, subscription: SubscriptionSuccessModel):
    update_result = db["meetings"].update_one(
        {"meetingId": meeting_id},
        {"$set": {"transcriptSubscription": jsonable_encoder(subscription)}}
    )
    if update_result.modified_count == 1:
        logging.info("Transcript subscription details saved to database")
    else:
        logging.error(f"Error: cannot saving transcript subscriptions details to database\n{update_result}")


def create_new_event_subscription():
    subscription_url = f"{config.get('GRAPH_BASE_URL')}/subscriptions"
    subscription_model = EventSubscriptionModel()

    # Calculate dynamic expiration date
    today = datetime.datetime.now().date()

    expiration_date = today + datetime.timedelta(days=config['MAX_EVENT_SUB_PERIOD'])
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    logging.info("Creating New Event Subscription")
    # print(subscription_model.model_dump())
    response = requests.post(subscription_url, json=subscription_model.dict(), headers=Authorization.getHeaders(),
                             timeout=10)

    if response.status_code == 201:
        subscription_info = response.json()
        logging.info("Event subscription created successfully.")
        save_event_subscription_to_db(SubscriptionSuccessModel(**subscription_info))
    else:
        logging.info(f"Error creating subscription\n{response.text}")


def create_new_transcript_subscription(meeting_id: str):
    logging.info(f"Now creating new transcript subscription for meeting {meeting_id[:4]}...{meeting_id[-4:]}")
    subscription_url = f"{config.get('GRAPH_BETA_BASE_URL')}/subscriptions"
    subscription_model = TranscriptSubscriptionModel()

    # Calculate dynamic expiration date
    today = datetime.datetime.now(datetime.timezone.utc)

    expiration_date = today + datetime.timedelta(days=config['MAX_TRANSCRIPT_SUB_PERIOD'])
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    # adding meeting id to request body
    subscription_model.resource = subscription_model.resource.replace("<onlineMeetingId>", meeting_id)

    logging.info("Creating New Transcript Subscription")
    # print(subscription_model.model_dump())
    response = requests.post(subscription_url, json=subscription_model.dict(), headers=Authorization.getHeaders(),
                             timeout=10)

    if response.status_code == 201:
        subscription_info = response.json()
        logging.info("Transcript subscription created successfully")
        save_transcription_subscription_to_db(meeting_id, SubscriptionSuccessModel(**subscription_info))
    else:
        logging.error(f"Error in creating transcript subscription\n{response.text}")


def get_meeting_id_using_event_id(event_id: str):
    meeting = MeetingModel(eventId=event_id)
    event_url = f"{config.get('GRAPH_BASE_URL')}/users/{config.get('USER_ID')}/events/{event_id}"
    meeting_url = f"{config.get('GRAPH_BASE_URL')}/users/{config.get('USER_ID')}/onlineMeetings"
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
                db["meetings"].insert_one(jsonable_encoder(meeting))
                logging.info("Meeting Details extracted and stored in database")
            else:
                logging.error(f"Error fetching event\n{meeting_response.text}")
    else:
        logging.error(f"Error fetching event\n{event_response.text}")
    return meeting.meetingId


def reply_all_summary_to_meeting_invite(meeting_id, minutes, action_points):
    reply_content = f"""
        Hi Team,

        Here are minutes of the meeting\n
        {minutes}\n\n
        Here are some action points\n
        {action_points}\n\n
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
    message_url = f"{config.get('GRAPH_BASE_URL')}/users/{config.get('USER_ID')}/messages"
    params = {
        "$expand": f"microsoft.graph.eventMessage/event($select = id;$filter = id eq '{meeting_id}')"
    }
    response = requests.get(message_url, headers=Authorization.getHeaders(), params=params, timeout=10)
    if response.status_code == 200:
        message_id = response.json()["value"][0]["id"]
        reply_all_url = f"{config.get('GRAPH_BASE_URL')}/users/{config.get('USER_ID')}/messages/{message_id}/replyAll"
        response = requests.post(reply_all_url, headers=Authorization.getHeaders(), json=reply_data, timeout=10)
        if response.status_code == 202:
            logging.info("ReplyAll Successful: Meeting minutes and action points sent to event invite")
        else:
            logging.error(f"Error in sending summary in mail, maybe this resource dont allow replyAll\n{response.text}")
    else:
        logging.error("Error fetching message id")


def clean_transcript_text(transcripts_vtt: str):
    cleaned_lines = []
    for line in transcripts_vtt.split("\n"):
        if line != "" and "-->" not in line:
            cleaned_lines.append(
                line.lstrip("<v ")
                .rstrip("</v>")
                .replace("(Guest)", "")
            )

    return "\n".join(cleaned_lines[1:])


def summarize_transcript(transcripts_vtt: str):
    cleaned_transcript = clean_transcript_text(transcripts_vtt)

    logging.info("hang tight, chatGPT is here...")

    # OpenAI config
    openai.organization = config["OPENAI_ORG"]
    openai.api_key = config["OPENAI_API_KEY"]

    minutes_prompt = f"""write a short summary from the following meeting transcript,
    keep the summary concise and informative ignore Introduction, Greetings and goodbyes
    do not list basic details like Date, Time, Attendees etc
    {cleaned_transcript}
    """
    action_prompt = f"""extract action points from the following meeting transcript
    keep it concise, one or max two points per person
    {cleaned_transcript}"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": minutes_prompt}]
    )
    minutes = response["choices"][0]["message"]["content"]
    logging.info("Minutes generated using chatGPT")

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": action_prompt}]
    )
    action_points = response["choices"][0]["message"]["content"]
    logging.info("Action points generated using chatGPT")
    return minutes, action_points


def get_transcripts(meeting_id, transcript_id):
    transcripts_vtt = ""
    transcript_url = f"{config.get('GRAPH_BETA_BASE_URL')}/users/{config.get('USER_ID')}/onlineMeetings/{meeting_id}/transcripts/{transcript_id}/content"
    params = {
        "$format": "text/vtt"
    }
    transcript_response = requests.get(transcript_url, params=params, headers=Authorization.getHeaders(), timeout=10)
    if transcript_response.status_code == 200:
        logging.info("Transcripts fetched successfully")
        transcripts_vtt = str(transcript_response.text)
        # print(f"vtt\n{transcripts_vtt}")
    else:
        logging.error(f"Error in fetching transcript\n{transcript_response.text}")
    return transcripts_vtt


def handel_new_transcript_notification(notification: dict):
    transcript_resource_url = notification["value"][0]["resource"]
    regex = r"\(.*?\)"
    ids: list[str] = re.findall(regex, transcript_resource_url)
    meeting_id, transcript_id = [id.lstrip("('").rstrip("')") for id in ids]

    # TODO save_transcript_id_in_db()

    transcripts_vtt = get_transcripts(meeting_id, transcript_id)

    minutes, action_points = summarize_transcript(transcripts_vtt)

    reply_all_summary_to_meeting_invite(meeting_id, minutes, action_points)


def handel_new_events_notification(notification: dict):
    # fetching event dict from notification
    event = notification["value"][0]
    # print("event_id", event["resourceData"]["id"])
    change_type = event["changeType"]
    if change_type == "created":
        meeting_id = get_meeting_id_using_event_id(event["resourceData"]["id"])
        if meeting_id != "":
            create_new_transcript_subscription(meeting_id)
