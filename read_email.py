# Code from https://codehandbook.org/how-to-read-email-from-gmail-using-python/
import smtplib
import time
import imaplib
import email

import ConfigParser, os

class ConfigStruct:
    #https://stackoverflow.com/questions/1305532/convert-nested-python-dict-to-object
    def __init__(self, **entries):
        self.__dict__.update(entries)

# -------------------------------------------------
#
# Utility to read email from Gmail Using Python
#
# ------------------------------------------------

class Email(object):
    def __init__(self, cfg_path="account.cfg"):
        self.cfg = None
        config = ConfigParser.SafeConfigParser(allow_no_value=False)
        with open("account.cfg") as f:
            config.readfp(f)
            section = "email"
            if section in config._sections:
                self.cfg = ConfigStruct(**config._sections[section])


    def get_from_gmail(self, filter="Task"):
        mails = []
        try:
            mail = imaplib.IMAP4_SSL(self.cfg.smtp_server)
            mail.login(self.cfg.from_email, self.cfg.from_pwd)
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
                            print 'From : ' + email_from
                            print 'Subject : ' + email_subject
                            body = self.get_email_body(msg).strip()
                            if body:
                                #print body
                                mails.append(body)

                # todo: get unread and then mark as read
        except Exception, e:
            print str(e)
        return mails

    # https://stackoverflow.com/questions/17874360/python-how-to-parse-the-body-from-a-raw-email-given-that-raw-email-does-not
    def get_email_body(self, b):
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
    mail = Email()
    mail.get_from_gmail()

