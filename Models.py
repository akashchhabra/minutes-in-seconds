from pydantic import BaseModel
from secrets import USER_ID

MY_BASE_URL = "https://1bcc-202-43-120-227.ngrok.io"


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


class MeetingTimeModel(BaseModel):
    dateTime: str
    timeZone: str


class SubscriptionSuccessModel(BaseModel):
    id: str
    changeType: str
    expirationDateTime: str


class MeetingModel(BaseModel):
    eventId: str = None
    meetingId: str = None
    joinUrl: str = None
    subject: str = None
    startTime: MeetingTimeModel = None
    endTime: MeetingTimeModel = None
    transcriptSubscription: SubscriptionSuccessModel = None
    transcriptContentUrls: list = []