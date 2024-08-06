import sublime
import sublime_plugin
import urllib.request
import urllib.parse
import json
import re
import time
import pickle
import os
from .deps.JsonObject import JsonObject
from datetime import datetime, timedelta

class Siba_validatorCommand(sublime_plugin.TextCommand):

	today=datetime.today()
	settings = None
	backDate= None 
	upload=None
	authToken = None
	tokenExpiryTime = None



	def __init__(self,upload=0):
		self.upload = upload
	
	def run(self, edit):
		self.settings = sublime.load_settings("SibaValidator.sublime-settings")
		days_ago = self.settings.get("siba_validator_number_days_ago")
		self.backDate = (self.today+timedelta(days=days_ago)).strftime('%Y-%m-%d')
		self.load_token()

		if not self.authToken or self.is_token_expired():
			self.show_login_panel(sublime.active_window(),edit)
		else:
			self.validate_files(sublime.active_window(),edit)

	def show_login_panel(self,view,edit):
		view.show_input_panel("Username:", "", lambda username: self.get_password(view,edit,username), None, None)

	def get_password(self, view,edit, username):
		self.username = username
		view.show_input_panel("Password:", "", lambda password: self.authenticate(view,edit,username,password), None, None)

	def authenticate(self,view,edit,username,password):
		authUrl = self.settings.get("siba_validator_auth_endpoint")
		authData = json.dumps({"username": username, "password": password}).encode('utf-8')
		req = urllib.request.Request(authUrl, data=authData, headers={'Content-Type': 'application/json'})

		try:
			with urllib.request.urlopen(req) as response:
				authResponse = json.loads(response.read().decode('utf-8'))
				self.authToken = authResponse['token']
				self.tokenExpiryTime = time.time() + authResponse.get('expires_in', self.settings.get("siba_validator_token_expiration"))
				self.save_token()
				self.validate_files(view,edit)
				for window in sublime.windows():
					for view in window.views():
						view.set_status('siba_status', 'Sesión iniciada correctamente')
				sublime.set_timeout_async(self.clear_status, 60000) 
		except urllib.error.HTTPError as e:
			sublime.error_message("Authentication failed: HTTP error {}: {}".format(e.code, e.reason))
		except Exception as e:
			sublime.error_message("Authentication failed: {}".format(str(e)))

	def get_text(self,view):
		if not self.has_selection(view):
			region = sublime.Region(0, view.size())
			return view.substr(region)

		selected_text = ''
		for region in view.sel():
			selected_text = selected_text + view.substr(region) + '\n'

		return selected_text

	def load_token(self):
		try:
			cache_path = sublime.cache_path()
			token_file_path = os.path.join(cache_path, "siba_validator_token.pkl")
			with open(token_file_path, "rb") as f:
				data= pickle.load(f)
				self.authToken = data.get("token")
				self.tokenExpiryTime = data.get("expiry")
		except (FileNotFoundError, EOFError) as e:
			print("Token file not found or empty: ", str(e))
		except Exception as e:
			print("Error loading token: ", str(e))

	def save_token(self):
		try:
			cache_path = sublime.cache_path()
			if not os.path.exists(cache_path):
				os.makedirs(cache_path)
			token_file_path = os.path.join(cache_path, "siba_validator_token.pkl")
			with open(token_file_path , "wb") as f:
				data = {"token": self.authToken,"expiry": self.tokenExpiryTime}
				pickle.dump(data,f) 
		except (FileNotFoundError, EOFError) as e:
			print("Error saving token: ", str(e))

	def is_token_expired(self):
		if not self.tokenExpiryTime:
			return True
		return time.time() > self.tokenExpiryTime

	def clear_status(self):
		for window in sublime.windows():
			for view in window.views():
				view.erase_status('siba_status')
	def validate_files(self,view,edit):

		reportsData = []
		listFirstDates = []
		headers = {'Content-Type': self.settings.get("siba_validator_ws_req_cont_type")}
		autosave = self.settings.get("siba_validator_autosave_file")
		postUrl = self.settings.get("siba_validator_ws_endpoint")+"?token="+self.authToken

		for sheet in view.sheets():
			viewText = self.get_text(sheet.view())
			if len(viewText) <= 1:
				print("No hay contenido en el archivo")
				continue

			try:
				if sheet.view().file_name() != None:
					p = re.compile('([^/]){2,100}\.[txTX]{3}$')
					fullName = re.split('/|\\\\',sheet.view().file_name())
					fileName = fullName[(len(fullName)-1)]
					fileNameMatchObject = p.search(fileName)
					if fileNameMatchObject:
						listFirstDates.append(self.textCleanUp(sheet,viewText,edit,autosave))
						viewText = self.get_text(sheet.view())				
						postData = urllib.parse.urlencode({'data':viewText,'fileName':fileName,'upload':self.upload}).encode('ascii')
						postResponse = urllib.request.urlopen(url=postUrl,data=postData)
						response = JsonObject(postResponse.read().decode('utf-8'))
						response.sheet = sheet
						reportsData.append(response)
			except urllib.error.HTTPError as e:
				response = JsonObject('{"value": 500,"notes": ["Error HTTP '+str(e.code)+': '+e.reason+'"],"status":false}')
				response.sheet = sheet
				reportsData.append(response)
				print("HTTP error "+str(e.code)+" para el archivo %s " %fileName," el error es: "+e.reason)
			except Exception as e :
				response = JsonObject('{"value": 600,"notes": ["Error '+str(e)+'"],"status":false}')
				response.sheet = sheet
				reportsData.append(response)
				print("Error 600 para el archivo %s " %fileName," error desconocido")

		self.writeReportView(reportsData,edit,listFirstDates)

	def has_selection(self,view):
		for sel in view.sel():
			start = sel.a
			end = sel.b
			if start != end:
				return True
		return False


	def writeReportView(self,reportData,edit,listFirstDates):

		fullTextReport = ''
		md = "# Reporte archivos de texto Sublime \n"
		mdArchivo = "| Archivo" + " "*56
		md = md + mdArchivo + '| Estado |\n'
		md = md + "|----------------------------------------------------------------|:------:|\n"
		lenArchivo = len(mdArchivo)
		for report,firstDate in zip(reportData,listFirstDates):
			p = re.compile('([^/]){2,100}\.[txTX]{3}$')
			fullName = re.split('/|\\\\',report.sheet.view().file_name())
			fileName = fullName[(len(fullName)-1)]
			fileNameMatchObject = p.search(fileName)
			if fileNameMatchObject:
				fileName = fileNameMatchObject.group()
				fullTextReport = fullTextReport + "Reporte de revisión para el archivo: "+fileName+"\n"
				if (report.status == True):

					mdFileName = "| "+fileName.split('\\')[-1]
					lenFileName = len(mdFileName)
					if(lenFileName < lenArchivo):
						lenDiff = lenArchivo - lenFileName
						mdFileName = mdFileName + " "*lenDiff
					md = md + mdFileName + "| OK     |\n"
					fullTextReport = fullTextReport + "Estado de la revisión: OK\n"

					if (firstDate[1] is False and firstDate[0] > self.backDate):
						fullTextReport = fullTextReport + "El archivo contiene contenido desde "+firstDate[0]+"\n"
					elif (firstDate[1] is False):
						fullTextReport = fullTextReport + "No se borro contenido"
					elif (firstDate[0] == self.backDate and firstDate[1] is True):
						fullTextReport = fullTextReport + "El archivo esta limpio\n"
					elif (firstDate[1] is True):
						fullTextReport = fullTextReport + "Se borro el contenido desde "+firstDate[0]+" hasta la fecha "+self.backDate+" \n"

				else:
					mdFileName = "| "+fileName.split('\\')[-1]
					lenFileName = len(mdFileName)
					if(lenFileName < lenArchivo):
						lenDiff = lenArchivo - lenFileName
						mdFileName = mdFileName + " "*lenDiff
					md = md + mdFileName + "| Error  |\n"
					fullTextReport = fullTextReport +"Estado de la revisión: Error"+"\n"
					fullTextReport = fullTextReport +"\nLos siguientes son los detalles del error:\n\n"
					for note in report.notes:
						if type(note) is str:
							fullTextReport = fullTextReport +"Descripción: "+note+"\n"
							fullTextReport = fullTextReport +'-----'+"\n"
						else:
							
							ctrlLineNumberAttr = True
							try:
								tmp = note['linenumber']
							except:
								ctrlLineNumberAttr  = False
							if ctrlLineNumberAttr:
								fullTextReport = fullTextReport +"Linea: "+str(note['linenumber'])+"\n"
							else:
								print("No tiene linenumber")

							fullTextReport = fullTextReport +"Descripción: "+note['desc']+"\n"
							fullTextReport = fullTextReport +'-----'+"\n"

					if (firstDate[1] is False and firstDate[0] > self.backDate):
						fullTextReport = fullTextReport + "El archivo contiene contenido desde "+firstDate[0]+"\n"
					elif (firstDate[1] is False):
						fullTextReport = fullTextReport + "No se borro contenido"
					elif (firstDate[0] == self.backDate and firstDate[1] is True):
						fullTextReport = fullTextReport + "El archivo esta limpio\n"
					else:
						fullTextReport = fullTextReport + "Se borro el contenido desde "+firstDate[0]+" hasta la fecha "+self.backDate+" \n"
				#print("%s" % fileNameMatchObject.group())
				fullTextReport = fullTextReport +"\n=======================\n"
		

		#print("%s" % fullTextReport)
		fullTextReport = md + '\n' + fullTextReport
		reportView = sublime.active_window().new_file()
		reportView.set_name("Reporte validación archivos TXT.md")
		reportView.run_command("insert",{"characters": fullTextReport})
						
		return True

	def textCleanUp(self,sheet,viewText,edit,autosave):
		dateLocation = viewText.find(self.backDate)
		firstDate = viewText[0:10]
		if dateLocation == -1:
			return [firstDate,False]
		else:
			region = sublime.Region(dateLocation, sheet.view().size())
			newText = sheet.view().substr(region)
			sheet.view().run_command("select_all")
			sheet.view().run_command("insert",{"characters": newText})
			if(autosave.lower().strip()== "yes"):
				sublime.set_timeout(lambda: sheet.view().run_command('save'))
				
			return [firstDate,True]