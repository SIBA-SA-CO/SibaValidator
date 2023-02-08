import sublime
import sublime_plugin
import urllib.request
import urllib.parse
import json
import os
import zipfile
import shutil

from .deps.JsonObject import JsonObject

class UpdateCommand(sublime_plugin.TextCommand):

	def run(self, edit):

		#Se obtiene el ultimo commit del repositorio
		url = 'https://api.github.com/repos/{owner}/{repo}/commits?per_page=1'.format(owner="SIBA-SA-CO", repo="SibaValidator")
		response = urllib.request.urlopen(url=url).read()
		data = json.loads(response.decode())
		lastCommit = data[0]['html_url'].split("/")[-1]
		

		#Lee el archivo .lastComment o  lo crea si no existe
		ruta_final = os.path.dirname(os.path.realpath(__file__))
		pathFileLasCommit = os.path.dirname(os.path.realpath(__file__)) + '/.lastCommit'
		if not os.path.isfile(pathFileLasCommit):
			os.chdir(ruta_final)
			f = open(".lastCommit", "w")
			f.write("")
			f.close()


		openFileLasCommit = open(pathFileLasCommit, "r")
		fileLasCommit = openFileLasCommit.read()
		openFileLasCommit.close()

		if(lastCommit == fileLasCommit):
	
			self.view.show_popup("<style>body { margin: 1px;  } html { background-color: green }</style>Está ejecutando la última versión del plugin, versión: " +  lastCommit[0:6],location= 700,max_width = 320, max_height = 240)

		else:
			    
			try:

				#Crea la carpeta tmp si no existe
				tmpFolderPath = ruta_final + "/tmp"

				if not os.path.isdir(tmpFolderPath):
				   
				    os.makedirs(tmpFolderPath)

				#Se descargar el archivo .Zip
				os.chdir(tmpFolderPath)
				url = 'https://github.com/SIBA-SA-CO/SibaValidator/archive/refs/heads/master.zip'
				local_filename,headers = urllib.request.urlretrieve(url,"SibaValidator.zip")
				html = open(local_filename)
				html.close()

				#Se descomprime el archivo .zip
				ruta_zip = os.path.dirname(os.path.realpath(__file__)) + "/tmp/SibaValidator.zip"
				ruta_extraccion = os.path.dirname(os.path.realpath(__file__)) + "/tmp"
				archivo_zip = zipfile.ZipFile(ruta_zip, "r")
				archivo_zip.extractall(path=ruta_extraccion)

				#Se recorre los archivos de la carpeta y se mueven al modulo principal
				ruta_archivos = ruta_extraccion + "/SibaValidator-master"
				folderFiles = os.listdir(ruta_archivos)
				
				lenFileGit = len(folderFiles) - 1
				count = 0

				for file in folderFiles:

					if(file != "SibaValidator.sublime-settings"):

						ruta_completa = ruta_archivos + "/" +file

						if(os.path.isfile(ruta_completa)):

							try:

								os.remove(ruta_final + "/" + file)
								if(shutil.move(ruta_archivos + "/" + file, ruta_final + "/" + file)):
									count+=1

							except:
								
								if(os.path.exists(ruta_archivos + "/" + file)):
									if(shutil.move(ruta_archivos + "/" + file, ruta_final + "/" + file)):
										count+=1


						elif(os.path.isdir(ruta_completa)):
							try:

								shutil.rmtree(ruta_final + "/" + file)
								if(shutil.copytree(ruta_archivos + "/" + file, ruta_final + "/" + file)):
									count+=1

							except:

								if(os.path.exists(ruta_archivos + "/" + file)):
									if(shutil.copytree(ruta_archivos + "/" + file, ruta_final + "/" + file)):
										count+=1

				if(count != lenFileGit):

					self.view.show_popup("<style>body { margin: 1px } html { background-color: red }</style>Ocurrió un error en la actualización: No coincide la cantidad de archivos actualizados, contactar a soporte.",max_width = 320, max_height = 240)

				else:

					self.view.show_popup("<style>body { margin: 1px } html { background-color: green }</style>Se ejecutó correctamente la actualización",max_width = 320, max_height = 240)
					#Se modifica el commit del archivo local
					openFileLasCommit = open(pathFileLasCommit, "w")
					openFileLasCommit.write(lastCommit)
					openFileLasCommit.close()

			except Exception as e:

				self.view.show_popup("<style>body { margin: 1px } html { background-color: red }</style>Ocurrió un error en la actualización: " + str(e),max_width = 320, max_height = 240)
				pass

			
			try:

				os.chdir(ruta_final)
				archivo_zip.close()
				shutil.rmtree(tmpFolderPath)

			except Exception as e:

				pass