"""
@author Andrew Ferrin (AndJF)
Created: September 11, 2020
"""

from bs4 import BeautifulSoup
from datetime import datetime
import requests
import smtplib

# gathering information about the gmail login
# from the text file: files/login.txt
login_info = open("files/login.txt", 'r')
login_info.seek(0)
gmail_sender = login_info.readline().replace("\n", "")
gmail_sender_password = login_info.readline().replace("\n", "")
gmail_notify = login_info.readline().replace("\n", "")
login_info.close()

# Info class stores the info for one entry of the dashboard
class Info(object):
    def __init__(self, tr_data):
        date_string_split = tr_data[0].split("/")
        self.date = datetime(2020, int(date_string_split[0]), int(date_string_split[1]))
        self.total_tests = int(tr_data[1].replace(",", ""))
        self.total_positive = int(tr_data[2].replace(",", ""))
        self.seven_day_average = float(tr_data[3].replace(",", ""))
        if self.total_tests == 0:
            self.percent_positive_on_day = 0
        else:
            self.percent_positive_on_day = float(self.total_positive / self.total_tests)
    
    def __str__(self):
        build = "Date: " + self.date.strftime("%B %d, %Y") + "\n"
        build += "Total Positive: " + str(self.total_positive) + "\n"
        build += "Total Tests: " + str(self.total_tests) + "\n"
        build += "Percent Positive Today: " + str(round(self.percent_positive_on_day, 2)) + "%\n"
        build += "7 Day Average: " + str(round(self.seven_day_average, 2))
        return build
    
    # returns a string of the date with only the month and day
    # mm/dd
    def short_date(self):
        long_date = self.date.strftime("%x")
        return long_date[1 if long_date[0] == '0' else 0:5]

# creates the server to send the emails
def create_server():
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(gmail_sender, gmail_sender_password)
    return server

# returns the full email text to send
def get_email_text_for(sender, recipient, subject, body):
    return "From: %s\nTo: %s\nSubject: %s\n\n%s" % (sender, recipient, subject, body)

# attempts to use the given server to send the email to a certain recipient
# returns true if successful, false if fails
def send_email(server, recipient, subject, body):
    try:
        server.sendmail(gmail_sender, recipient, get_email_text_for(gmail_sender, recipient, subject, body))
        return True
    except:
        return False

# converts a list of <tr> tags to a list of Info objects
def convert_to_info(list_of_tr):
    build = []
    for tr in list_of_tr:
        build.append(tr.text)
    return Info(build)

# returns true if the input can be a valid int, false otherwise.
# this is used for the number of people in quarantine because for 
# some reason (when I created this) in their list of entries, there were random <td> 
# tags with '&nbsp' (a space)
def can_be_int(num):
    try:
        int(num)
        return True
    except:
        return False

# attempts to scrape the VT Dashboard.
# The url you see is the website that 
# the vt ready page has an <iframe> tag to
#
# If some part of it fails, it sends an email
# to the email stored in the gmail_notify string
try:
    url = "https://dzdn64j22d0kn.cloudfront.net/microstrategy-public/servlet/mstrWeb?evt=2048001&src=mstrWeb.2048001&visMode=0&currentViewMedia=1&documentID=BE130BCA11EAEDE7B6E90080EF3597B4&Server=BI-PROD-2.DB.VT.EDU&Project=Public%20Facing%20Project&Port=34952&share=1&hiddensections=header,path,dockTop,dockLeft,footer"
    html_content = requests.get(url).text
    soup = BeautifulSoup(html_content, "lxml")

    # gets the full list of entries. This will be converted into a list of Info objects
    covid_table = soup.findAll("table", attrs={"class": "r-cssDefault_W458 view-grid"})[0]
    all_entries = covid_table.find_all("tr")

    total_info = []
    for i in range(1, len(all_entries)):
        total_info.append(convert_to_info(all_entries[i].find_all("td")))

    # gets the full historical list of people in quarantine
    quar_table = soup.findAll("table", attrs={"class": "r-cssDefault_W487 view-grid"})[0]
    quar_entries = quar_table.find_all("tr")

    quar_info = []
    for row in quar_entries:
        if can_be_int(row.text):
            quar_info.append(row.text)

    # Gets average positive case info for the last 7 days
    last_7_days_table = soup.findAll("table", attrs={"id": "table_grid_W187_0"})[0]
    last_7_days_entries = last_7_days_table.find_all("tr")
    last_7_days_current_raw = last_7_days_entries[1].find_all("td")
    last_7_days_current = []
    for entry in last_7_days_current_raw:
        last_7_days_current.append(entry.text)


    # puts the entries in chronological order
    # where the first entry is the most recent 
    total_info.reverse()

    # Unused, but finds the day with 
    # the max total positive cases
    max_info = total_info[0]
    for entry in total_info:
        if entry.total_positive > max_info.total_positive:
            max_info = entry

    # info for when the website was updated
    update_info = str(soup.find(id='W421'))
    update_info = update_info[update_info.index("<br/>") + len("<br/>"):update_info.index("</span>")].replace("<br/>", "\n")

    # total cases for students and employees
    positive_student_cases = int(soup.find(id='W66').text)
    positive_employee_cases = int(soup.find(id='W88').text)
    total_positive = positive_employee_cases + positive_student_cases
except Exception as inst:
    # Notification that there was a problem
    body = "There was a problem in gathering data...\nyou should get on that\n"
    body += "Error: " + str(type(inst)) + "\n"
    body += str(inst)
    server = create_server()
    send_email(server, gmail_notify, "Web Scrape Failure", body)
    server.close()
    exit()

# gets all of the emails to send the report to
send_to_file = open("files/sendto.txt", 'r')
send_to_file.seek(0)
raw_emails = send_to_file.readlines()
send_to_file.close()
to = []
for email in raw_emails:
    to.append(email.replace('\n', '').strip())

# populating the contents of the email
subject = datetime.now().strftime("%B %d, %Y VT COVID Report")
body = """
{0}
Number Of People In Isolation/Quarantine: {1}

Total Positive Cases:
    Students: {2}
    Employees: {3}
    Combined: {4}

Last 7 Days Positive Cases:
    Students: {5}
    Employees: {6}
    Combined: {7}

{8}

Reply STOP to stop receiving emails

Stay Safe and Go Hokies
<https://ready.vt.edu/dashboard.html>
""".format(str(total_info[-1]), 
           quar_info[0], 
           str(positive_student_cases), 
           str(positive_employee_cases), 
           str(total_positive), 
           last_7_days_current[0], 
           last_7_days_current[1], 
           last_7_days_current[2], 
           update_info)

# sends the gmail_notify an email reporting
# success or failure of each email
successes = []
failures = []
server = create_server()
for recipient in to:
    if send_email(server, recipient, subject, body):
        successes.append(recipient)
    else:
        failures.append(recipient)
report = "Successful: " + str(len(successes)) + "\nFailures: " + str(len(failures))+"\n\n"
report += "Received:" + ("None" if len(successes) == 0 else "") + "\n"
for success in successes:
    report += "\t" + success + "\n"
report += "Failed To Receive: " + ("None" if len(failures) == 0 else "\n")
for failure in failures:
    report += "\t" + failure + "\n"
print("\n\n"+report+"\n\n")
send_email(server, gmail_notify, "Email Blast Report", report)
server.close()
print("Done.")