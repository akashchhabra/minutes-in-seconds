from pydantic import BaseModel
from Minutes import config


class EventSubscriptionModel(BaseModel):
    changeType: str = "created,deleted"
    notificationUrl: str = f"{config.get('MY_BASE_URL')}/handle/new-events"
    resource: str = f"users/{config.get('USER_ID')}/calendar/events"
    expirationDateTime: str = ""


class TranscriptSubscriptionModel(BaseModel):
    changeType: str = "created"
    notificationUrl: str = f"{config.get('MY_BASE_URL')}/handle/new-transcripts"
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