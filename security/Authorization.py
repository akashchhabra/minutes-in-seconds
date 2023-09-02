import time
import requests
import jwt
from secrets import TENANT_ID, CLIENT_ID, CLIENT_SECRET


class Authorization:
    access_token = None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    @staticmethod
    def getHeaders():
        if Authorization.access_token is None or Authorization.isTokenAboutToExpire():
            Authorization.updateToken()
        return Authorization.headers

    @staticmethod
    def updateToken():
        print("fetching new token")
        token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        token_data = {
            "grant_type": "client_credentials",
            "CLIENT_ID": CLIENT_ID,
            "CLIENT_SECRET": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default"
        }
        try:
            token_response = requests.post(token_url, data=token_data, timeout=10)
            Authorization.access_token = token_response.json()["access_token"]
            Authorization.headers['Authorization'] = f"Bearer {Authorization.access_token}"
        except requests.exceptions.RequestException as ex:
            print("Error Occurred:", ex)

    @staticmethod
    def isTokenAboutToExpire():
        try:
            # TODO verify sinature before using
            decoded_token = jwt.decode(Authorization.access_token, options={"verify_signature": False})
            expiry_timestamp = decoded_token['exp']
            # print(expiry_timestamp)
            current_timestamp = int(time.time())
            # print(current_timestamp)
            delta = expiry_timestamp - current_timestamp
            # print("delta", delta)
            # Check if the token has expired or about to expired
            if delta < 15*60:
                print("Token has expired or is about to expire")
                return True
            else:
                # print("Token is valid")
                return False
        except jwt.DecodeError as ex:
            print("Invalid token", ex)

