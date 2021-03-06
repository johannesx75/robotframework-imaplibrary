import re
import os
import imaplib
import time
import urllib2

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
execfile(os.path.join(THIS_DIR, 'version.py'))

__version__ = VERSION


class ImapLibrary(object):

    ROBOT_LIBRARY_VERSION = VERSION
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    port = 993

    def open_mailbox(self, server, user, password):
        """
        Open the mailbox on a mail server with a valid
        authentication.
        """
        self.imap = imaplib.IMAP4_SSL(server, self.port)
        self.imap.login(user, password)
        self.imap.select()

    def wait_for_mail(self, fromEmail=None, toEmail=None, status=None,
                      timeout=60):
        """
        Wait for an incoming mail from a specific sender to
        a specific mail receiver. Check the mailbox every 10
        seconds for incoming mails until the timeout is exceeded.
        Returns the mail number of the latest email received.

        `timeout` sets the maximum waiting time until an error
        is raised.
        """
        timeout = int(timeout)
        while (timeout > 0):
            self.imap.recent()
            self.mails = self._check_emails(fromEmail, toEmail, status)
            if len(self.mails) > 0:
                return self.mails[-1]
            timeout -= 10
            if timeout > 0:
                time.sleep(10)
        raise AssertionError("No mail received within time")

    def get_links_from_email(self, mailNumber):
        '''
        Finds all links in an email body and returns them

        `mailNumber` is the index number of the mail to open
        '''
        body = self.get_email_body(mailNumber)
        return re.findall(r'href=[\'"]?([^\'" >]+)', body)

    def open_link_from_mail(self, mailNumber, linkNumber=0):
        """
        Find a link in an email body and open the link.
        Returns the link's html.

        `mailNumber` is the index number of the mail to open
        `linkNumber` declares which link shall be opened (link
        index in body text)
        """
        urls = self.get_links_from_email(mailNumber)

        if len(urls) > linkNumber:
            resp = urllib2.urlopen(urls[linkNumber])
            content_type = resp.headers.getheader('content-type')
            if content_type:
                enc = content_type.split('charset=')[-1]
                return unicode(resp.read(), enc)
            else:
                return resp.read()
        else:
            raise AssertionError("Link number %i not found!" % linkNumber)

    def close_mailbox(self):
        """
        Close the mailbox after finishing all mail activities of a user.
        """
        self.imap.close()

    def mark_as_read(self):
        """
        Mark all received mails as read
        """
        for mail in self.mails:
            self.imap.store(mail, '+FLAGS', '\SEEN')

    def get_email_body(self, mailNumber):
        """
        Returns an email body

        `mailNumber` is the index number of the mail to open
        """
        body = self.imap.fetch(mailNumber, '(BODY[TEXT])')[1][0][1].decode('quoted-printable')
        return body

    def _criteria(self, fromEmail, toEmail, status):
        crit = []
        if fromEmail:
            crit += ['FROM', fromEmail]
        if toEmail:
            crit += ['TO', toEmail]
        if status:
            crit += [status]
        if not crit:
            crit = ['UNSEEN']
        return crit

    def _check_emails(self, fromEmail, toEmail, status):
        crit = self._criteria(fromEmail, toEmail, status)
        type, msgnums = self.imap.search(None, *crit)
        return msgnums[0].split()
