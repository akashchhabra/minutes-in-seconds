import logging

from fastapi import BackgroundTasks
from fastapi.responses import PlainTextResponse
from fastapi_utils.tasks import repeat_every

from Minutes import app, config

from Minutes.Authorization import Authorization
from Minutes.SubscriptionManager import SubscriptionManager
from Minutes.logic import (
    create_new_event_subscription,
    create_new_transcript_subscription,
    handel_new_events_notification,
    handel_new_transcript_notification
)


@app.on_event("startup")
@repeat_every(seconds=60*60*24)
def manage_subs():
    SubscriptionManager.manage_event_subscription()


@app.on_event("shutdown")
def shutdown_db_client():
    logging.info("shutting down")
    app.mongodb_client.close()


@app.get("/")
def hello():
    return {"message": "hello world from get endpoint"}


# helper route
@app.get("/token")
def getToken(secret: str):
    if secret == config["API_SECRET"]:
        return Authorization.getHeaders()
    else:
        return {"message": "Enter correct secret"}


# helper route
@app.post("/create-new-event-subscription")
def event_subscription(secret: str):
    if secret == config["API_SECRET"]:
        create_new_event_subscription()
        return {"message": "done"}
    else:
        return {"message": "Enter correct secret"}


# helper route
@app.post("/create-new-transcript-subscription/{meeting_id}")
def transcript_subscription(meeting_id: str, secret: str):
    if secret == config["API_SECRET"]:
        create_new_transcript_subscription(meeting_id)
        return {"message": "executed"}
    else:
        return {"message": "Enter correct secret"}


@app.post("/handle/new-events", response_class=PlainTextResponse)
def handel_new_events(validationToken: str = None, notification: dict = None, background_task: BackgroundTasks = None):
    # Validating subscription creation
    if validationToken:
        logging.info("validation_token: " + validationToken)
        return validationToken

    logging.info("New event notification received...")
    background_task.add_task(handel_new_events_notification, notification)
    return "event received, Thank you"


@app.post("/handle/new-transcripts", response_class=PlainTextResponse)
def handle_new_transcripts(validationToken: str = None, notification: dict = None,
                           background_task: BackgroundTasks = None):
    # Validating subscription creation
    if validationToken:
        logging.info("validation_token: " + validationToken)
        return validationToken

    logging.info("New transcript notification received...")
    background_task.add_task(handel_new_transcript_notification, notification)

    return "event received, Thank you"
