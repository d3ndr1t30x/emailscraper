import re
import urllib.request
import time

emailRegex = re.compile(r'''
#example :
#something-.+_@somedomain.com
(
([a-zA-Z0-9_.+]+
@
[a-zA-Z0-9_.+]+)
)
''', re.VERBOSE)

# Extacting Emails
def extractEmailsFromUrlText(urlText, emailFile):
    extractedEmail = emailRegex.findall(urlText)
    allemails = []
    for email in extractedEmail:
        allemails.append(email[0])
    lenh = len(allemails)
    print("\tNumber of Emails : %s\n" % lenh)
    seen = set()
    for email in allemails:
        if email not in seen:  # faster than `word not in output`
            seen.add(email)
            emailFile.write(email + "\n")  # appending Emails to a file


# HtmlPage Read Func
def htmlPageRead(url, i, emailFile):
    try:
        start = time.time()
        headers = {'User-Agent': 'Mozilla/5.0'}
        request = urllib.request.Request(url, None, headers)
        response = urllib.request.urlopen(request)
        urlHtmlPageRead = response.read()
        urlText = urlHtmlPageRead.decode()
        print("%s.%s\tFetched in : %s" % (i, url, (time.time() - start)))
        extractEmailsFromUrlText(urlText, emailFile)
    except Exception as e:
        print("Error:", e)


# EmailsLeechFunction
def emailsLeechFunc(url, i, emailFile):
    try:
        htmlPageRead(url, i, emailFile)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            try:
                url = 'http://webcache.googleusercontent.com/search?q=cache:' + url
                htmlPageRead(url, i, emailFile)
            except Exception as e:
                print("Error:", e)


# Prompt user for input file
urlFilePath = input("Enter the path of the input text file containing URLs: ")

# Open input and output files
try:
    urlFile = open(urlFilePath, 'r')
    emailFile = open("emails.txt", 'a')
except FileNotFoundError:
    print("File not found. Please provide a valid file path.")
    exit()

start = time.time()
i = 0
# Iterate Opened file for getting single url
for urlLink in urlFile.readlines():
    urlLink = urlLink.strip('\'"')
    i = i + 1
    emailsLeechFunc(urlLink, i, emailFile)

print("Elapsed Time: %s" % (time.time() - start))

urlFile.close()
emailFile.close()