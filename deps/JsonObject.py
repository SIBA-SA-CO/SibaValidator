import json

class JsonObject (object):

	def __init__ (self,jsonString):
		self.__dict__ = json.loads(jsonString)