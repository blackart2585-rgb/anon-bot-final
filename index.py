import os
import json
import telebot
from telebot import types
import pymongo
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = "8851949538:AAGmN3HkV_owJo2FTed094758T82Mm8Wt9Q" 


OWNER_ID = 1540835004
MONGODB_URI = mongodb+srv://blackart2585_db_userIuFprmlAp3EasGK6
:@cluster0.luuc6x8.mongodb.net/?appName=Cluster0

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
client = pymongo.MongoClient(MONGODB_URI)
db = client.get_database("anon_bot")
msg_map_col = db["msg_map"]
last_sender_col = db["last_sender"]

@bot.message_handler(func=lambda m: True)
def handle_message(message: types.Message):
    last_sender_doc = last_sender_col.find_one({"_id": "last_sender"})
    last_sender = last_sender_doc["value"] if last_sender_doc else None

    if message.from_user.id == OWNER_ID:
        if message.reply_to_message:
            replied_msg_id = str(message.reply_to_message.message_id)
            doc = msg_map_col.find_one({"owner_msg_id": replied_msg_id})
            sender_id = doc["sender_id"] if doc else last_sender
            if not sender_id:
                bot.reply_to(message, "❌ Не могу определить получателя.")
                return
            try:
                bot.copy_message(chat_id=sender_id, from_chat_id=OWNER_ID, message_id=message.message_id)
                bot.reply_to(message, "✅ Ответ отправлен.")
            except Exception as e:
                bot.reply_to(message, f"⚠️ Ошибка: {e}")
        else:
            bot.reply_to(message, "ℹ️ Чтобы ответить, сделайте Reply на сообщение собеседника.")
        return

    sender = message.from_user
    sender_info = f"{sender.full_name} (@{sender.username})" if sender.username else sender.full_name
    prefix = f"📨 От {sender_info} (ID {sender.id})"

    last_sender_col.update_one({"_id": "last_sender"}, {"$set": {"value": sender.id}}, upsert=True)
    notify_msg = bot.send_message(OWNER_ID, prefix)
    msg_map_col.insert_one({"owner_msg_id": str(notify_msg.message_id), "sender_id": sender.id})

    try:
        copied = bot.copy_message(chat_id=OWNER_ID, from_chat_id=message.chat.id,
                                  message_id=message.message_id, reply_to_message_id=notify_msg.message_id)
        msg_map_col.insert_one({"owner_msg_id": str(copied.message_id), "sender_id": sender.id})
    except Exception as e:
        bot.send_message(OWNER_ID, f"⚠️ Ошибка пересылки: {e}", reply_to_message_id=notify_msg.message_id)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data)
        bot.process_new_updates([telebot.types.Update.de_json(update)])
        self.send_response(200)
        self.end_headers()
