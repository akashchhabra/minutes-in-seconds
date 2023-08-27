import json
import requests
import datetime
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from secrets import client_id, client_secret, user_id, tenant_id
from Models import EventSubscriptionModel

app = FastAPI()

access_token = None

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


@app.post("/create-new-event-subscription")
def create_new_event_subscription(subscription_model: EventSubscriptionModel):
    graph_url = f"https://graph.microsoft.com/v1.0/subscriptions"

    # Calculate dynamic expiration date
    today = datetime.datetime.now().date()

    expiration_date = today + datetime.timedelta(days=1)
    expiration_date_iso = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    subscription_model.expirationDateTime = expiration_date_iso

    print("sending")
    print(subscription_model.model_dump())
    response = requests.post(graph_url, json=subscription_model.model_dump(), headers=headers)

    if response.status_code == 201:
        subscription_info = response.json()
        print("Subscription created successfully.")
        print(subscription_info)
    else:
        print("Error creating subscription")
        print(response.text)
    return response.json()


@app.post("/handle-new-events", response_class=PlainTextResponse)
def handel_new_events(validationToken: str = None, data: dict = None):
    print("received new event")
    print(json.dumps(data, indent=4))
    # Validating subscription creation
    if validationToken:
        print("validation_token: " + validationToken)
        return validationToken
    else:
        # Handle other notificationss
        return "event received, Thank you"

