from os import environ
import pymongo
import urllib
import urllib2
from collections import defaultdict
import redis
import pyres
import simplejson as json

DBPATH=environ.get('MONGODBPATH')
DBNAME=environ.get('MONGODBDATABASE')
connection = pymongo.Connection(DBPATH)
db = connection[DBNAME]

redisHost = environ.get("REDIS_QUEUE_HOST")
redisPort = int(environ.get("REDIS_QUEUE_PORT"))
redisPassword = environ.get("REDIS_QUEUE_PASSWORD")

redisObject = redis.Redis(host=redisHost, port=redisPort, password=redisPassword)

redisQueue = pyres.ResQ(redisObject)

def fql(fql, token, args=None):
	if not args:
		args = {}
	
	args["q"], args["format"], args["access_token"] = fql, "json", token

	return json.loads(
		urllib2.urlopen("https://graph.facebook.com/fql?" +
						urllib.urlencode(args)).read())
						
def fb_call(call, args=None):
	return json.loads(urllib2.urlopen("https://graph.facebook.com/" + call +
									  '?' + urllib.urlencode(args)).read())	
						
					
class AggregateCheckins:
	
	queue = "aggregate_checkins"
		
	@staticmethod	
	def perform(user, token, limit, offset):
		checkin_metadata = {}
		collection = db[user]
		
		friends = fql("SELECT uid2 FROM friend WHERE uid1=me() LIMIT %s OFFSET %s" % (limit, offset), token)
		
		for friend in friends['data']:
			checkins = fb_call(friend['uid2'] + '/checkins', args={'limit':2000, 'access_token':token})
			for checkin in checkins['data']:
				if 'from' in checkin:
					if 'name' in checkin['from']:
						checkin_metadata['author_name'] = checkin['from']['name']
					if 'id' in checkin['from']:
						checkin_metadata['author_uid'] = checkin['from']['id']
				if 'message' in checkin:
					checkin_metadata['comment'] = checkin['message']
				if 'place' in checkin:
					if 'id' in checkin['place']:
						checkin_metadata['place_id'] = checkin['place']['id']
					if 'name' in checkin['place']:
						checkin_metadata['place_name'] = checkin['place']['name']
					if 'location' in checkin['place']:
						checkin_metadata['place_city'] = checkin['place']['location']
				
				collection.insert(checkin_metadata)
	