import sublime
import sublime_plugin
import urllib.request
import urllib.parse
import json
import re

#from .Mauricio import MmClase
from .deps.JsonObject import JsonObject
from datetime import datetime, timedelta

class Siba_validatorCommand(sublime_plugin.TextCommand):

	today=datetime.today()
	settings = None
	backDate= None 
	upload=None

	def __init__(self,upload=0):
		self.upload = upload
	
	def run(self, edit):
		self.settings = sublime.load_settings("SibaValidator.sublime-settings")
		self.backDate = (self.today+timedelta(days=self.settings.get("siba_validator_number_days_ago"))).strftime('%Y-%m-%d')  
		autosave = self.settings.get("siba_validator_autosave_file")
		#postUrl = 'http://192.168.1.8:8800/api/dataload/validate'
		postUrl = self.settings.get("siba_validator_ws_endpoint")
		headers={}
		headers['Content-Type'] = self.settings.get("siba_validator_ws_req_cont_type")
		#postData = urllib.parse.urlencode({'data':'MMMMMMAAAAAAAA'}).encode('ascii')
		#postResponse = urllib.request.urlopen(url=postUrl,data=postData)
		#print("HTTP Response: %s \n" % postResponse.read())
		#return True

		reportsData = []
		listFirstDates = []

		for sheet in sublime.active_window().sheets():
			#print("\n=======================\n")
			#print("%s \n" % sheet)
			viewText = self.get_text(sheet.view())
			if len(viewText) <= 1:
				print("No hay contenido en el archivo")
				continue
			#print("%s"%viewText)
			 
			try:
				if sheet.view().file_name() != None:
					p = re.compile('([^/]){5,100}\.[txTX]{3}$')
					fileNameMatchObject = p.search(sheet.view().file_name())
					fullName = re.split('/|\\\\',sheet.view().file_name())
					fileName = fullName[(len(fullName)-1)]
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
		#viewText = self.get_text()
		#print("%s" % viewText)
		#Itera por todos los archivos abiertos

	def get_text(self,view):
		if not self.has_selection(view):
			region = sublime.Region(0, view.size())
			return view.substr(region)

		selected_text = ''
		for region in view.sel():
			selected_text = selected_text + view.substr(region) + '\n'

		return selected_text

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
			p = re.compile('([^/]){5,100}\.[txTX]{3}$')
			fileNameMatchObject = p.search(report.sheet.view().file_name())
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
		reportView.insert(edit,0, fullTextReport)
						
		return True

	def textCleanUp(self,sheet,viewText,edit,autosave):
		dateLocation = viewText.find(self.backDate)
		firstDate = viewText[0:10]
		if dateLocation == -1:
			return [firstDate,False]
		else:
			sheet.view().erase(edit, sublime.Region(0,dateLocation))
			if(autosave.lower().strip()== "yes"):
				sheet.view().run_command("save")
				
			return [firstDate,True]