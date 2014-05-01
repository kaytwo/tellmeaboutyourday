from lxml.html import fromstring
from urllib2 import urlopen
from os import system
import sys
import re
import time
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

class TellMe(object):

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

  def check_deadlines(self):
    now = time.time()
    for user in self.conversation_states.keys():
      if self.conversation_states[user]['state'] == 'participating':
        if self.conversation_states[user]['deadline'] <= now:
          self.rest_t.direct_messages.new("what did you do, think, or see this hour?")
          self.conversation_states[user]['deadline'] = time.time() + 60*60

  def choose_response(self,sid,message_text):
    if sid not in self.conversation_states and message_text == 'good morning':
      self.conversation_states[sid] = {'state':'participating','deadline':(time.time()+60*60),'firstmsg':time.time()}
      return "thank you for participating. I will message you once an hour to ask you about your day. What's happening now?"
    elif sid in self.conversation_states:
      if self.conversation_states[sid]['state'] == 'participating':
        if message_text == 'goodnight':
          self.conversation_states[sid]['state'] = 'asleep'
          return "thank you for sharing your day"
        print "RECEIVED MESSAGE TO SAVE, SAVE TIMESTAMP, USER, TEXT, PICTURE"
        self.conversation_states[sid]['deadline'] = time.time() + 60*60
        return "thank you. I will message you again in an hour."

  def respond_to_message(self,msg):
    sid = msg['sender_id']
    message_text = msg['text']
    response = self.choose_response(sid,message_text)
    if response:
      self.rest_t.direct_messages.new(user_id=sid,text=response)

  def follow_back(self,follower_id):
    ''' check if following, if not, follow
    this will bomb if the acct has more than 5000 followers,
    but that's a good problem to have.'''
    if follower_id not in self.rest_t.friends.ids()['ids']:
      print self.rest_t.friendships.create(user_id=follower_id)
      print "sent follow command for %d" % follower_id
    else:
      print "already following %d" % follower_id



  def dm_loop(self):
    for msg in self.stream_t.user():
      if 'direct_message' in msg and msg['direct_message']['recipient']['id'] == self.my_id:
        self.respond_to_message(msg['direct_message'])
      elif 'event' in msg:
        if msg['event'] == 'follow' and msg['target']['id'] == self.my_id:
          self.follow_back(msg['source']['id'])
      if 'timeout' in msg and msg['timeout'] == True:
        self.check_deadlines()
      pprint(self.conversation_states)

if __name__ == "__main__":
  tellme = TellMe()
  tellme.dm_loop()
