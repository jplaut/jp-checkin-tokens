import base64
import os
import simplejson as json
import urllib
import urllib2

from flask import Flask, request, redirect, url_for
import redis
import pyres
from tasks import *

app = Flask(__name__)
app.config.from_object(__name__)

if os.environ.get('FACEBOOK_APP_ID'):
	app.config.from_object('conf.Config')
else:
	app.config.from_envvar('MAIN_CONFIG')

APP_ID = os.environ.get('FACEBOOK_APP_ID')
APP_SECRET = os.environ.get('FACEBOOK_SECRET')

redisHost = os.environ.get("REDIS_QUEUE_HOST")
redisPort = int(os.environ.get("REDIS_QUEUE_PORT"))
redisPassword = os.environ.get("REDIS_QUEUE_PASSWORD")

redisObject = redis.Redis(host=redisHost, port=redisPort, password=redisPassword)

redisQueue = pyres.ResQ(redisObject)

def oauth_login_url(preserve_path=True, next_url=None):
	fb_login_uri = ("https://www.facebook.com/dialog/oauth"
					"?client_id=%s&redirect_uri=%s" %
					(APP_ID, next_url))

	if app.config['FBAPI_SCOPE']:
		fb_login_uri += "&scope=%s" % ",".join(app.config['FBAPI_SCOPE'])
	return fb_login_uri


def simple_dict_serialisation(params):
	return "&".join(map(lambda k: "%s=%s" % (k, params[k]), params.keys()))


def base64_url_encode(data):
	return base64.urlsafe_b64encode(data).rstrip('=')


def fbapi_get_string(path, domain=u'graph', params=None, access_token=None,
					 encode_func=urllib.urlencode):
	"""Make an API call"""
	if not params:
		params = {}
	params[u'method'] = u'GET'
	if access_token:
		params[u'access_token'] = access_token

	for k, v in params.iteritems():
		if hasattr(v, 'encode'):
			params[k] = v.encode('utf-8')

	url = u'https://' + domain + u'.facebook.com' + path
	params_encoded = encode_func(params)
	url = url + params_encoded
	print url
	result = urllib2.urlopen(url).read()

	return result


def fbapi_auth(code):
	params = {'client_id': APP_ID,
			  'redirect_uri': get_facebook_callback_url(),
			  'client_secret': APP_SECRET,
			  'code': code}

	result = fbapi_get_string(path=u"/oauth/access_token?", params=params,
							  encode_func=simple_dict_serialisation)
	pairs = result.split("&", 1)
	result_dict = {}
	for pair in pairs:
		(key, value) = pair.split("=")
		result_dict[key] = value
	return (result_dict["access_token"], result_dict["expires"])
	
def get_facebook_callback_url():
	return 'http://jp-checkin-tokens.herokuapp.com/callback/'
	
username = ''
friendCount = 1
offset = 0
requestsPerToken = 300

	
@app.route('/callback/', methods=['GET', 'POST'])
def callback():
	global offset
	global username
	global friendCount
	interval = 20
	
	while offset <= friendCount:
		if request.method == 'POST':
			username = request.args.get('user')
			friendCount = int(request.args.get('friends'))
			return redirect(oauth_login_url(next_url=get_facebook_callback_url()))

		if request.method == 'GET':
			appToken = request.args.get('code')
			token = fbapi_auth(appToken)[0]
			for i in xrange(0, requestsPerToken, interval):
				redisQueue.enqueue(AggregateCheckins, username, token, interval, i)
				offset += requestsPerToken
			return redirect(oauth_login_url(next_url=get_facebook_callback_url()))
		
if __name__ == '__main__':
	port = int(os.environ.get("PORT", 6000))
	if APP_ID and APP_SECRET:
		app.run(host='0.0.0.0', port=port)
	else:
		print 'Cannot start application without Facebook App Id and Secret set'