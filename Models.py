from pydantic import BaseModel
from secrets import USER_ID

MY_BASE_URL = "https://3fc5-202-148-59-71.ngrok.io"


class EventSubscriptionModel(BaseModel):
    changeType: str = "created,deleted"
    notificationUrl: str = f"{MY_BASE_URL}/handle/new-events"
    resource: str = f"users/{USER_ID}/calendar/events"
    expirationDateTime: str = ""


class TranscriptSubscriptionModel(BaseModel):
    changeType: str = "created"
    notificationUrl: str = f"{MY_BASE_URL}/handle/new-transcripts"
    resource: str = "communications/onlineMeetings/<onlineMeetingId>/transcripts"
    expirationDateTime: str = ""
