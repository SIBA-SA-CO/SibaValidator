import sublime
import sublime_plugin
import urllib.request
import urllib.parse
import json
import re

#from .Mauricio import MmClase
from .deps.JsonObject import JsonObject
from .SibaValidator import Siba_validatorCommand


class ValidatorCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		sibaValidator = Siba_validatorCommand(0)
		sibaValidator.run(edit)
