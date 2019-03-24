# https://codehandbook.org/how-to-read-email-from-gmail-using-python/
import smtplib
import time
import imaplib
import email

ORG_EMAIL   = "***REMOVED***"
FROM_EMAIL  = "***REMOVED***" + ORG_EMAIL
FROM_PWD    = "***REMOVED***"
SMTP_SERVER = "***REMOVED***"
SMTP_PORT   = 993

# -------------------------------------------------
#
# Utility to read email from Gmail Using Python
#
# ------------------------------------------------

def get_from_gmail(filter="Task"):
    mails = []
    try:
        mail = imaplib.IMAP4_SSL(SMTP_SERVER)
        mail.login(FROM_EMAIL,FROM_PWD)
        mail.select('inbox')

        #type, data = mail.search(None, 'ALL')
        type, data = mail.search(None, 'UNSEEN')
        #print data
        mail_ids = data[0]
        id_list = [int(i) for i in mail_ids.split()]

        #for i in range(latest_email_id,first_email_id, -1):
        for i in id_list:
            #print "email id %d" % (i,)
            typ, data = mail.fetch(i, '(RFC822)' )
            #print typ, data

            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_string(response_part[1])
                    email_subject = msg['subject']
                    email_from = msg['from']
                    if email_subject == filter:
                        #print 'From : ' + email_from
                        #print 'Subject : ' + email_subject
                        body = get_email_body(msg).strip()
                        if body:
                            #print body
                            mails.append(body)

            # todo: get unread and then mark as read
    except Exception, e:
        print str(e)
    return mails

# https://stackoverflow.com/questions/17874360/python-how-to-parse-the-body-from-a-raw-email-given-that-raw-email-does-not
def get_email_body(b):
    body = ""
    if b.is_multipart():
        for part in b.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            # skip any text/plain (txt) attachments
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
                break
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = b.get_payload(decode=True)
    return body

if __name__ == '__main__':
    get_from_gmail()
