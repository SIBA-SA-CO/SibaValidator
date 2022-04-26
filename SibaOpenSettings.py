import sublime
import sublime_plugin
import os


class OpenSettingsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		rutaActual=os.path.dirname(os.path.realpath(__file__))
		rutaFinal= rutaActual+'/SibaValidator.sublime-settings'
		sublime.active_window().open_file(rutaFinal)
