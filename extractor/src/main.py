from data_model import *
from apscheduler.schedulers.blocking import BlockingScheduler
import pytz
import datetime
import time
import csv
import urllib
from text_cleaners import clean_cell
from process_data import coms_row_processor
import io
from utils import get_missing_org_name, send_email_message
from titlecase import titlecase
import traceback
import requests
from bs4 import BeautifulSoup
import re
from text_cleaners import normalize_text

def fuzzy_dict_builder():
    people_name = {str(x['_id']): "%s %s" % (x['first_name'], x['last_name']) for x in person_collection.find()}
    org_name = {str(x['_id']): x['org_name'] for x in parent_org_collection.find()}
    return people_name, org_name


def check_for_new_reports():
    restart = True
    attempts = 0
    n_reports = comm_report_collection.count()
    n_orgs = child_org_collection.count()
    n_persons = dpoh_name_collection.count({'verified_by': None})

    while restart == True:
        attempts += 1
        people_name_dict, org_name_dict = fuzzy_dict_builder()

        try:
            url = "https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/rcntCmLgs?csv=Export+to+CSV%2FText"
            file = urllib.request.urlopen(url)
            data = csv.reader(io.TextIOWrapper(file))
            for n, row in enumerate(data):
                if n > 1:
                    row = [clean_cell(c) for c in row]
                    if not row[3]:
                        row[3] = get_missing_org_name(row[0])
                    else:
                        row[3] = titlecase(row[3])

                    people_name_dict, org_name_dict = coms_row_processor(row, people_name_dict, org_name_dict)

            log_str = "Success getting new data. New communications added: %d. New organizationss for review: %d. New names for review: %d" \
                      % (comm_report_collection.count() - n_reports,
                         child_org_collection.count() - n_orgs,
                         dpoh_name_collection.count({'verified_by': None}) - n_persons,
                         )
            log_collection.insert(dict(event_dt=datetime.datetime.utcnow(),
                                       event='get new data',
                                       message=log_str,
                                       error_trace=None))
            restart = False
            return True, log_str


        except:
            if attempts > 9:
                restart = False
                error_str = str(traceback.print_exc())
                log_str = "Error getting new data. This is failed attempt %d. Not retrying today." % attempts
                log_collection.insert(dict(event_dt=datetime.datetime.utcnow(),
                                           event='get new data',
                                           message=log_str,
                                           error_trace=error_str))

                return False, "%s Final error trace is:\n%s" % (log_str, error_str)



            else:
                log_str = "Error getting new data. This is attempt %d. Retrying in 10 minutes." % attempts
                log_collection.insert(dict(event_dt=datetime.datetime.utcnow(),
                                           event='get new data',
                                           message=log_str,
                                           error_trace=str(traceback.print_exc())))

                print(traceback.print_exc())
                time.sleep(600)

def check_for_amendments():
    com_num_regex = re.compile(r'\d+-\d+')
    amended_regex = re.compile('amended from')
    restart = True
    attempts = 0

    while restart == True:
        attempts += 1

        try:
            n_modded = 0
            for pg in range(0, 50):
                response = requests.get('https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/rcntCmLgs?rt=1&lang=eng&pg=%s' % pg)

                html_soup = BeautifulSoup(normalize_text(response.text), 'html.parser')

                finds = html_soup.find_all('strong', text=amended_regex)

                for a in finds:
                    amend = normalize_text(a.text)
                    matches = com_num_regex.findall(amend)
                    mod = comm_report_collection.update({'communication_number': matches[1]}, {'$set': {'amended': True}})
                    n_modded += mod['nModified']

            log_str = "Success checking for amendments. %d existing communications reports marked as amendments." % n_modded
            log_collection.insert(dict(event_dt=datetime.datetime.utcnow(),
                                       event='check for amendments',
                                       message=log_str,
                                       error_trace=None))
            return True, log_str

        except:
            if attempts > 9:
                restart = False
                error_str = str(traceback.print_exc())
                log_str = "Error checking for amendments. This is failed attempt %d. Not retrying today." % attempts
                log_collection.insert(dict(event_dt=datetime.datetime.utcnow(),
                                           event='check for amendments',
                                           message=log_str,
                                           error_trace=error_str))

                return False, "%s Final error trace is:\n%s" % (log_str, error_str)


            else:
                log_str = "Error checking for amendments. This is attempt %d. Retrying in 10 minutes." % attempts
                log_collection.insert(dict(event_dt=datetime.datetime.utcnow(),
                                           event='check for amendments',
                                           message=log_str,
                                           error_trace=str(traceback.print_exc())))

                print(traceback.print_exc())
                time.sleep(600)

def check_for_updates():
    new_report_result = check_for_new_reports()
    amendment_result = check_for_amendments()

    msg_str = """
    New reports complete: %s
    Amendments complete: %s

    Details:
    New reports:
    %s

    Amendments:
    %s

    """ % (new_report_result[0], amendment_result[0], new_report_result[1], amendment_result[1])

    recipients = [x['email'] for x in user_collection.find({'email_system_updates': True})]
    if recipients:
        send_email_message(recipients, "Polytics.ca Nightly Data Update Results", msg_str)


check_for_updates()

sched = BlockingScheduler(timezone=pytz.timezone('Canada/Eastern'))
sched.add_job(check_for_updates, 'cron', hour=3, minute=00, id="check_updates")
sched.start()