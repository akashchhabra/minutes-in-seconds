import logging
import os

from dotenv import dotenv_values, find_dotenv
from fastapi import FastAPI
from pymongo import MongoClient
from pymongo.server_api import ServerApi


app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
    handlers=[
        logging.FileHandler("logs.log"),
        logging.StreamHandler()
    ]
)

# loading env variables
config = {
    **dotenv_values(".env"),
    # comment below line on local
    **os.environ
}
logging.info(f"config loaded successfully: {len(config)}")

# mongodb connection config
app.mongodb_client = MongoClient(config["MONGO_DB_URL"], server_api=ServerApi('1'))
app.mongodb_client.admin.command("ping")
logging.info("connected to mongoDB!!!")
db = app.mongodb_client[config["DB_NAME"]]

from Minutes import routes
