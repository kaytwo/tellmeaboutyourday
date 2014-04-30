from lxml.html import fromstring
from urllib2 import urlopen
from os import system
import sys
import re
import twitter
from pprint import pprint

import smtplib
from email.mime.text import MIMEText


'''
tellmeaboutyourday

using @livetellshowsee for development purposes

main tasks:
respond to DMs, schedule periodic DMs based on message content
organize the DM responses into a database that will be rendered by a webapp

first iteration: respond to messages based on user state
"good morning" 
  -> "good morning! I will ask you to tell me about 
    every hour of today until you message me the word 'goodnight'" 
  -> schedule all messages including immediately right now
if receive message from someone active, say "okay, thank you, I will get back to you in an hour."
"goodnight" -> "thank you for sharing your day. I will not message you again unless you message me 'good morning' again."

on scheduled message: "hi again! Tell me about something you thought, saw, did, or felt this hour. You can attach a picture if you like."

problems:
  twitter api doesn't have an "accept follower" call, 'accept' and 'deny' rest endpoints might work, TODO.
    this will only matter if acct is protected. current workaround: different account for bot and output
    other option is to manually update accepted users, PITA but nbd, premature optimization
  to remove a follower, block then unblock them.


improvements:
  * if script dies, gracefully restart
    * read internal state from some backing store
    * consume unread messages from REST api, queue responses
      * if more than 5 messages to send, ABORT w/email
  * log to backing store for all messages sent/received w/ pictures
  * BACKING STORE! WEBAPP!
  * pull list of subscribers from db, update following/allowed followers

if anything ever goes horribly wrong, email me


'''

def error_out(msg,alert=False):
  if alert:
    # increment the comicnum so we don't get repeated alerts
    emsg = MIMEText(msg)
    emsg['Subject'] = 'Tellme error!'
    emsg['From'] = 'kaytwo@kaytwo.org'
    emsg['To'] = 'kaytwo@gmail.com'
    # this smtp server might change but oh well...
    s = smtplib.SMTP('gmail-smtp-in.l.google.com')
    s.sendmail(emsg['From'],[emsg['To']],emsg.as_string())
  else:
    print msg
  sys.exit()

class Tellme(object):

  rest_t = None
  stream_t = None
  conversation_states = {}
  my_id = None

  def __init__(self):
    self.connect_to_twitter()
    self.my_id = self.rest_t.account.verify_credentials()['id']


  def connect_to_twitter(self):
    oauth_token, oauth_secret = twitter.read_token_file('account_credentials')
    consumer_key, consumer_secret = twitter.read_token_file('app_credentials')
    authpoop = twitter.OAuth(oauth_token, oauth_secret,
                         consumer_key, consumer_secret)

    self.rest_t = twitter.Twitter(auth=authpoop )
    self.stream_t = twitter.TwitterStream(domain='userstream.twitter.com',auth=authpoop,timeout=30)
    print "connected to twitter."
    print dir(self.rest_t)


  def choose_response(self,sid,message_text):
    if sid not in self.conversation_states:
      pass
    pass

  def respond_to_message(self,msg):
    sid = msg['sender_id']
    message_text = msg['text']
    response = self.choose_response(sid,message_text)
    if response:
      self.rest_t.direct_messages.new(user_id=sid,text=response)

  def follow_back(self,msg):
    ''' check if following, if not, follow'''
    pass



  def dm_loop(self):
    print self.stream_t
    for msg in self.stream_t.user():
      if 'direct_message' in msg:
        self.respond_to_msg(msg['direct_message'])
      elif 'event' in msg and msg['event'] == 'follow':
        self.follow_back(msg)
      pprint(msg)

if __name__ == "__main__":
  tellme = Tellme()
  tellme.dm_loop()
