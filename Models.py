from pydantic import BaseModel
from secrets import user_id

base_url = "https://642a-202-148-59-230.ngrok.io"


class EventSubscriptionModel(BaseModel):
    changeType: str = "created,deleted"
    notificationUrl: str = f"{base_url}/handle-new-events"
    resource: str = f"users/{user_id}/calendar/events"
    expirationDateTime: str = ""
