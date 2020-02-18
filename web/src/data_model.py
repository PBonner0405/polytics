import os
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from passlib.hash import pbkdf2_sha256
import redis

redis_ip = os.environ.get('REDIS_PORT_6379_TCP_ADDR', 'localhost')
r = redis.StrictRedis(host=redis_ip, port=6379, db=0, decode_responses=True)

db_ip = os.environ.get('MONGO_PORT_27017_TCP_ADDR', 'localhost')
mogo_client = MongoClient(db_ip, 27017)
db = mogo_client.polytics_db

person_collection = db.person_collection
person_collection.create_index('api_person_id', unique=True)

group_collection = db.group_collection
group_collection.create_index('group_id', unique=True)

dpoh_name_collection = db.dpoh_name_collection
dpoh_name_collection.create_index(
    [
        ("name_ngrams", "text"),
        ("name_prefixes", "text"),
    ],
    name="search_dpoh_name_ngrams",
    weights={
        "name_ngrams": 100,
        "name_prefixes": 200,
    }
)

dpoh_name_collection.create_index([('name', 1), ('title', 1), ('inst', 1)])

user_collection = db.user_collection
user_collection.create_index('username', unique=True)


comm_report_collection = db.comm_report_collection
comm_report_collection.create_index("communication_number")



child_org_collection = db.child_org_collection
child_org_collection.create_index("org_id")
child_org_collection.create_index(
    [
        ("name_ngrams", "text"),
        ("name_prefixes", "text"),
    ],
    name="search_child_org_name_ngrams",
    weights={
        "name_ngrams": 100,
        "name_prefixes": 200,
    }
)
parent_org_collection = db.parent_org_collection
parent_org_collection.create_index("org_name", unique=True)
parent_org_collection.create_index(
    [
        ("name_ngrams", "text"),
        ("name_prefixes", "text"),
    ],
    name="search_parent_org_name_ngrams",
    weights={
        "name_ngrams": 100,
        "name_prefixes": 200,
    }
)


defualt_admin = {u"username": u"admin", u"password": pbkdf2_sha256.hash(u"aFEfrTZ5SmX9p4n9"), u"roles": [u"admin"], "active": True}

if user_collection.count() == 0:
    print("No admin user - creating default")
    user_collection.insert(defualt_admin)

