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


	def run(self, edit):
		

		#postUrl = 'http://192.168.1.8:8800/api/dataload/validate'
		settings = sublime.load_settings("SibaValidator.sublime-settings")
		postUrl = settings.get("siba_validator_ws_endpoint")
		headers={}
		headers['Content-Type'] = settings.get("siba_validator_ws_req_cont_type")
		#postData = urllib.parse.urlencode({'data':'MMMMMMAAAAAAAA'}).encode('ascii')
		#postResponse = urllib.request.urlopen(url=postUrl,data=postData)
		#print("HTTP Response: %s \n" % postResponse.read())
		#return True

		reportsData = []

		for sheet in sublime.active_window().sheets():
			#print("\n=======================\n")
			#print("%s \n" % sheet)
			viewText = self.get_text(sheet.view())
			self.sibaClean(sheet,viewText,edit)
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
						postData = urllib.parse.urlencode({'data':viewText,'fileName':fileName,'upload':0}).encode('ascii')
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


		self.writeReportView(reportsData,edit)
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


	def writeReportView(self,reportData,edit):

		fullTextReport = ''
		for report in reportData:
			
			p = re.compile('([^/]){5,100}\.[txTX]{3}$')
			fileNameMatchObject = p.search(report.sheet.view().file_name())
			if fileNameMatchObject:
				fileName = fileNameMatchObject.group()
				fullTextReport = fullTextReport + "Reporte de revisión para el archivo: "+fileName+"\n"
				if (report.status == True):
					fullTextReport = fullTextReport + "Estado de la revisión: OK\n"
				else:
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
				#print("%s" % fileNameMatchObject.group())
				fullTextReport = fullTextReport +"\n=======================\n"
		

		#print("%s" % fullTextReport)

		reportView = sublime.active_window().new_file()
		reportView.set_name("Reporte validación archivos TXT")
		reportView.insert(edit,0,fullTextReport)
						
		return True

	def sibaClean(self,sheet,viewText,edit):
		fecha=datetime.today()
		fechaInicio=fecha+timedelta(days=-15)
		fechaInicio=fechaInicio.strftime('%Y-%m-%d')
		inicio = viewText.find(fechaInicio)
		if inicio == -1:
			pass
		else:
			sheet.view().erase(edit, sublime.Region(0,inicio))
			sheet.view().run_command("save")