import os
from pymongo import MongoClient
client = MongoClient()

db_ip = os.environ.get('MONGO_PORT_27017_TCP_ADDR', 'localhost')
mogo_client = MongoClient(db_ip, 27017)
db = mogo_client.polytics_db


comm_report_collection = db.comm_report_collection
child_org_collection = db.child_org_collection
parent_org_collection = db.parent_org_collection

comm_report_collection.create_index("communication_number")
child_org_collection.create_index("org_id")

dpoh_name_collection = db.dpoh_name_collection

# 30 days * 24 hr * 60 min * 60 sec
ttl_seconds = 30*24*60*60

log_collection = db.log_collection
log_collection.create_index("event_dt", expireAfterSeconds=ttl_seconds)

user_collection = db.user_collection

person_collection = db.person_collection
person_collection.create_index('api_person_id', unique=True)

