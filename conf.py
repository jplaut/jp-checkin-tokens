import os


class Config(object):
	DEBUG = True
	TESTING = False
	LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
	FBAPI_SCOPE = ['user_checkins', 'friends_checkins']