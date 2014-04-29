from lxml.html import fromstring
from urllib2 import urlopen
from os import system
import sys
import re
import twitter

import smtplib
from email.mime.text import MIMEText


'''
tellmeaboutyourday

using @livetellshowsee for development purposes

respond to DMs, schedule periodic DMs based on message content
organize the DM responses into a database that will be rendered by a webapp

first iteration: respond to messages based on user state
"good morning" -> "good morning! I will ask you to tell me about every hour of today until you message me the word 'goodnight'" -> schedule all messages including immediately right now
if receive message from someone active, say "okay, thank you, I will get back to you in an hour."
"goodnight" -> "thank you for sharing your day. I will not message you again unless you message me 'good morning' again."

on scheduled message: "hi again! Tell me about something you thought, saw, did, or felt this hour. You can attach a picture if you like."


improvements:
  * if script dies, gracefully restart
    * read internal state from some backing store
    * consume unread messages from REST api, queue responses
      * if more than 5 messages to send, ABORT w/email
  * log to backing store for all messages sent/received w/ pictures
  * BACKING STORE! WEBAPP!

if anything ever goes horribly wrong, email me instead


'''



def error_out(msg,alert=False):
  if alert:
    # increment the comicnum so we don't get repeated alerts
    emsg = MIMEText(msg)
    emsg['Subject'] = 'trigramosaurus error!'
    emsg['From'] = 'kaytwo@kaytwo.org'
    emsg['To'] = 'kaytwo@gmail.com'
    # this smtp server might change but oh well...
    s = smtplib.SMTP('gmail-smtp-in.l.google.com')
    s.sendmail(emsg['From'],[emsg['To']],emsg.as_string())
  else:
    print msg
  sys.exit()

def post_to_twitter(msg):
  '''
  todo:
  check if trigramosaurus has been updated today, if so, skip updating.
  '''
  oauth_token, oauth_secret = twitter.read_token_file('accountucredentials')
  consumer_key, consumer_secret = twitter.read_token_file('app_credentials')
  t = twitter.Twitter(
            auth=twitter.OAuth(oauth_token, oauth_secret,
                       consumer_key, consumer_secret)
           )
  try:
    result = t.statuses.update(status=msg)
  # invalid status causes twitter.api.TwitterHTTPError
  except:
    error_out("some sort of twitter error")
  return result

def update_comicnum(today):
  ''' read and return the comic number for today.
  regardless of errors, try to put today's comic number
  in the file.'''
  curnum = -1
  try:
    cn = open('trigramosaurus.txt','r+')
    try:
      curnum = int(cn.read().strip())
    except:
      pass
    cn.seek(0)
    cn.truncate()
    cn.write(str(today))
    cn.close()
    if curnum != -1:
      return curnum
    else:
      error_out("could not determine current comic number, reset it to %d" % today,True)
  except Exception as e:
    error_out("couldn't read comic number: "+e.message,True)

if __name__ == "__main__":
  comicid = ''
  if len(sys.argv) == 2:
    comicid = '?comic=' + str(sys.argv[1])
  today_comic = urlopen('http://www.qwantz.com/index.php' + comicid)
  result = today_comic.read()
  todayparsed = fromstring(result)
  try:
    comicurl = todayparsed.cssselect('img.comic')[0].attrib['src']
    comicnum = int(re.findall(r'comic2-([0-9]+)\.png',comicurl)[0])
  except Exception as e:
    error_out("failed parsing qwantz.com: " + e.message,True)
  if comicid == '':
    prev_comic = update_comicnum(comicnum)
    if comicnum == prev_comic:
      error_out("same comic")
    if comicnum != prev_comic + 1:
      error_out("unexpected comic number: previous was %d, this was %d" % (prev_comic,comicnum),True)
  system('curl %s > /tmp/comic.png' % comicurl)
  d = Dinocr('/tmp/comic.png')
  if d.erased_pixels > 2000:
    error_out('large amount of erases in a new comic (%d erases, %d uncertainty)' % (d.erased_pixels,d.uncertainty),True)
  trigram = d.choose_random_trigram()
  anything = False
  # don't acept a trigram that has a non-alphanumeric word in it
  if any([all([not x.isalnum() for x in word]) for word in trigram.split()]):
    error_out('words in this trigram are weird: %s' % trigram,True)
  result = post_to_twitter(trigram)
  infofile = open('trigramosaurus.txt','w')
  infofile.write(str(comicnum))
  infofile.close()
