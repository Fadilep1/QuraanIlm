import sys
import os
import time
import asyncio
import threading
import schedule as scheduleModule
from datetime import datetime, timezone

from collections.abc import Iterable
from pymongo.server_api import ServerApi
from pymongo.mongo_client import MongoClient

from bot.handlers.helpers.utils import LimitedStack
from bot.utils import getArguments
from bot.utils import getLogger

# Logger and arguments setup
logger = getLogger(__name__)
ARGS = getArguments()

# Configuration without `.env`
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://fdtekkz7:B3p1bSOUiDQkCrqo@cluster0.lul0q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
LOCAL = os.getenv("LOCAL", "False").lower() in ["true", "1"] or ARGS.ARG_LOCAL

if LOCAL or ARGS.ARG_FIX_MONGO:
    # For `pymongo.errors.ConfigurationError: cannot open /etc/resolv.conf`
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ["8.8.8.8"]


class _LocalDB:
    """Local Database to store users and chats in memory."""

    def __init__(self, users, chats, channels) -> None:
        self.users = list(users)
        self.chats = list(chats)
        self.channels = list(channels)
        self.admins = [i["_id"] for i in self.users if i.get("is_admin")]
        logger.info(f"LocalDB: {len(self.users)} users, {len(self.chats)} chats")

    def findUser(self, userID: int) -> dict:
        return next((i for i in self.users if i["_id"] == userID), None)

    def findChat(self, chatID: int) -> dict:
        return next((i for i in self.chats if i["_id"] == chatID), None)

    def findChannel(self, channelID: int) -> dict:
        return next((i for i in self.channels if i["_id"] == channelID), None)

    def addUser(self, user) -> None:
        self.users.append(user)
        return None

    def addChat(self, chat) -> None:
        self.chats.append(chat)
        return None

    def addChannel(self, channel) -> None:
        self.channels.append(channel)
        return None

    def updateUser(self, userID: int, settings: dict) -> dict:
        user = self.findUser(userID)
        if not user:
            user = self.addUser(userID)

        user["settings"] = {**user["settings"], **settings}
        return user

    def updateChat(self, chatID: int, settings: dict) -> dict:
        chat = self.findChat(chatID)
        if not chat:
            chat = self.addChat(chatID)

        chat["settings"] = {**chat["settings"], **settings}
        return chat

    def updateChannel(self, channelID: int, settings: dict) -> dict:
        channel = self.findChannel(channelID)
        if not channel:
            channel = self.addChannel(channelID)

        channel["settings"] = {**channel["settings"], **settings}
        return channel

    def getAllUsers(self) -> list:
        return self.users

    def getAllChat(self) -> list:
        return self.chats

    def getAllAdmins(self) -> list:
        return self.admins

    def getAllChannels(self) -> list:
        return self.channels


class Database:
    def __init__(self) -> None:
        self.client = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
        self.db = self.client.quranbot if not LOCAL else self.client.quranbot_local

        self.defaultSettings = {
            "font": 1,  # 1 -> Uthmani, 2 -> Simple
            "showTafsir": True,
            "reciter": 1,  # 1 -> Mishary Rashid Al-Afasy, 2 -> Abu Bakr Al-Shatri
            "primary": "ar",
            "secondary": "en",
            "other": None,
        }
        self.defaultGroupSettings = {
            "handleMessages": False,  # Sending `x:y` for ayah
            "allowAudio": True,  # Allow sending audio recitations
            "previewLink": False,  # Show preview of the Tafsir link
            "restrictedLangs": ["ar"],
        }
        self.defaultChannelSettings = {}

        # --- Local DB ---
        self.queue = []
        channels = self.db.channels.find({})
        chats = self.db.chats.find({}) or []
        users = self.db.users.find({}) or []

        self.localDB = _LocalDB(users, chats, channels)

        # --- Scheduled Tasks ---
        interval = 60 if not LOCAL else 20
        scheduleModule.every(interval).seconds.do(self.runQueue)

        def runScheduledTasks():
            while True:
                try:
                    scheduleModule.run_pending()
                except Exception as e:
                    logger.info("Error in scheduled tasks:", e)
                time.sleep(1)

        if not ARGS.ARG_STOP_THREAD:
            threading.Thread(target=runScheduledTasks).start()
        else:
            logger.warning("Database thread is stopped by user")

    def runQueue(self):
        logger.info("--- Running Queue ---")
        start = time.time()

        for func, value in self.queue:
            if isinstance(value, tuple):
                try:
                    func(*value)
                except Exception as e:
                    logger.info("Error in queue:", e)
            else:
                try:
                    func(value)
                except Exception as e:
                    logger.info("Error in queue:", e)

        end = time.time()
        self.queue = []
        timeMs = (end - start) * 1000
        if timeMs > 100:
            logger.info(f"Time taken: {timeMs:.2f} ms")


db = Database()


async def main():
    users = db.getAllUsers()
    chats = db.getAllChat()
    print("Total Users:", len(users))
    print("Total Chats:", len(chats))


if __name__ == "__main__":
    asyncio.run(main())
