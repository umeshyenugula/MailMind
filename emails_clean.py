from pymongo import MongoClient
import datetime

db_client = MongoClient("your_mongo_uri")
db = db_client['Emails']

def cleanup_old_emails():
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    for col_name in db.list_collection_names():
        if "_events" in col_name:
            db[col_name].delete_many({"added_at": {"$lt": cutoff}})
        else:
            db[col_name].delete_many({"fetched_at": {"$lt": cutoff}})
