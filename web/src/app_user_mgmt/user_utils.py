from flask_login import current_user, UserMixin, AnonymousUserMixin, LoginManager
from functools import wraps
from data_model import user_collection
from bson import ObjectId
import datetime
import re
import sys

class User(UserMixin):
    def __init__(self, name, id, password, roles, active):
        self.name = name
        self.id = id
        self.roles = roles
        self.password = password
        self.active = active

    @property
    def is_active(self):
        return self.active

    def get_roles(self):
        return self.roles

    def has_role(self, role):
        return role in self.roles

    def get_id(self):
        return self.id

    def get_username(self):
        return self.name

class AnonymousUser(AnonymousUserMixin):
    def __init__(self):
        self.roles = False
        self.name = None

    def has_role(self, role):
        return False


def make_user(user_dict):
    user = User(user_dict[u"username"], str(user_dict[u"_id"]), user_dict[u"password"], user_dict[u"roles"], user_dict["active"])
    user_collection.update({"_id": ObjectId(user_dict[u"_id"])}, {"$set": {"most_recent_activity": datetime.datetime.utcnow()}})
    return user


def load_user(uid):
    user_dict = user_collection.find_one({"_id": ObjectId(uid)})
    return make_user(user_dict)


def requires_role(*role):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # role variable is passed as a tuple
            if not current_user.has_role(role[0]):
                return "Not authorized"
            return f(*args, **kwargs)
        return wrapped
    return wrapper


def get_duplicate_username_field_from_error(error_msg):
    error_msg_str = str(sys.exc_info()[1])
    results = re.search(r'(?<=user_collection\.\$)(.*)(?=dup key)', error_msg_str)
    if results:
        if results.group(1).startswith('username'):
            return 'username'
    return None


def pw_complexity(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        8 characters length or more
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """
    # calculating the length
    length_error = len(password) < 8

    # searching for digits
    digit_error = re.search(r"\d", password) is None

    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # searching for symbols
    # symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None

    # overall result
    return not (length_error or digit_error or uppercase_error or lowercase_error)
