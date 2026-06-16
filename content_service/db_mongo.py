import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(
    os.getenv("MONGO_URI")
)

db = client[
    os.getenv("MONGO_DB")
]

collection = db[
    os.getenv("MONGO_COLLECTION")
]

def get_comments(task_name, offset, limit):
    if limit <= 0:
        limit = 10

    comments = collection.find(
        {"task_name": task_name}
    ).skip(offset).limit(limit)

    result = []

    for comment in comments:
        result.append({
            "author_name": comment.get("author_name", ""),
            "text": comment.get("text", ""),
            "date": comment.get("date", "")
        })

    return result


def add_comment(task_name, author_name, text, date):
    collection.insert_one({
        "task_name": task_name,
        "author_name": author_name,
        "text": text,
        "date": date
    })