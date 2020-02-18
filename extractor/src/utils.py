import requests
from bs4 import BeautifulSoup
from text_cleaners import normalize_text
import re
from data_model import *


def detect_reg_type(soup):
    if "In-house Corporation" in soup.find('h1').text:
        return "In-house corp"
    elif "In-house Organization" in soup.find('h1').text:
        return "In-house org"
    elif "Consultant" in soup.find('h1').text:
        return "Consultant"


def get_org_name(reg_type, soup):
    if "In-house corp" in reg_type:
        return get_inline_child(soup, "In-house Corporation name")
    elif "In-house org" in reg_type:
        return get_inline_child(soup, "In-house Organization name")
    elif "Consultant" in reg_type:
        return get_inline_child(soup, "Client name")


def get_inline_child(soup, regex_text):
    org_name_tags = soup.find(text=re.compile(regex_text))
    item = list(org_name_tags.parent.descendants)[1]
    return " ".join(item.text.split())


def get_missing_org_name(comm_id):
    reg_org_id, com_no = comm_id.split('-')
    org_obj = child_org_collection.find({'org_id': reg_org_id})
    if org_obj.count() > 0:
        return org_obj[0]['org_name']
    else:
        reg_url_base = "https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/vwRg?cno="
        request = requests.get("%s%s" % (reg_url_base,reg_org_id))
        html_soup = BeautifulSoup(normalize_text(request.text), 'html.parser')
        reg_type = detect_reg_type(html_soup)
        return get_org_name(reg_type, html_soup)


def send_email_message(recipient_list, subject, text):
    return requests.post(
        "https://api.mailgun.net/v3/XXXXXXXXXXXXXXXXX/messages",
        auth=("api", "XXXXXXXXXXXXXXXXX"),
        data={"from": "XXXXXXXXXXXXXXXXX",
              "to": recipient_list,
              "subject": subject,
              "text": text})