#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Fetches data form a Google Spreadsheet and calculates different variables. """

import configparser
import csv
import gspread
import json
import logging
import os
import sys
from oauth2client.client import SignedJwtAssertionCredentials
from threading import Thread

__author__ = "Codeando México"
__license__ = "GPL"
__version__ = "1.0"
__credits__ = "Miguel Salazar, Ricardo Alanis"
__maintainer__ = "Miguel Salazar"
__email__ = "miguel@codeandomexico.org"
__status__ = "Prototype"

class IrisDimmensionalCalculator(Thread):

	def __init__(self):
		Thread.__init__(self)
		self.api_key = "1aHQHzfb8-hXHwDH7u4ykh6NsuA1NX2Bj845iMWpDnf8" # Google Spreadsheet document key

	def run(self):
		keyset = self.get_keyset()
		auth = self.authenticate(keyset['email'], keyset['password'])
		raw_data = self.read_data(auth, self.api_key)
		data = self.extract_data(raw_data)
		readiness_scores = self.assess_readiness(data)
		print(readiness_scores)

	def get_keyset(self):
		config = configparser.ConfigParser()
		config.read(['./irisdc', os.path.expanduser('~/.irisdc')])
		
		keyset = {}
		keyset['email'] = config['keyset'].get('email')
		keyset['password'] = config['keyset'].get('password')
				
		return keyset

	def authenticate(self, email, password):
		# Warning: ClientLogin is deprecated since April 20, 2015.
		# Should migrate to OAuth2 authentication.

		# These should be placed in the environment variables.
		gc = gspread.login(email, password)
		return gc

	def read_data(self, auth, key):
		# Opens a worksheet from spreadsheet from its key
		sh = auth.open_by_key(key)
		worksheet = sh.sheet1
		# Gets all values from the first row.
		answers_list = worksheet.row_values(2)
		return answers_list

	# Extracts the data and loads it to a dictionary
	def extract_data(self, raw_data):
		# Note: These variables must be loaded form elsewhere, preferrably the stylesheet.
		variables = ['timestamp','lead_official','lead_unofficial',
		'funds_budget','funds_sources','funds_inprocess','funds_exercised','funds_percentage',
		'cap_teamsize','cap_extteam','cap_od_time','cap_od_tools','cap_metadata','cap_management',
		'cap_frequency','cap_quality','cap_methodology','cap_content_tools','cap_content_budget',
		'cap_content_time','opn_physical','opn_scans','opn_spreadsheets','opn_plaintext',
		'opn_geospatial','opn_training','opn_training_technical','opn_training_org','opn_training_legal',
		'opn_training_agencies','leg_license','leg_license_comments','soc_allies','soc_events',
		'leg_decree','leg_local_status','leg_local_reference','leg_state_status','leg_state_reference',
		'imp_self_assessment','cap_dbms','cap_design']
		# Note: Answers that have CSV should be stored as a list.
		answers_dict = dict(zip(variables, raw_data))
		return answers_dict

	def assess_readiness(self, data):
		leadership_score = self.get_leadership_score(data)
		fundings_score = self.get_fundings_score(data)
		capabilities_score = self.get_capabilities_score(data)
		openness_score = self.get_openness_score(data)
		legal_score = self.get_legal_score(data)
		society_score = self.get_society_score(data)
		impact_score = self.get_impact_score(data)
		
		readiness_scores = {}
		readiness_scores['leadership'] = leadership_score
		readiness_scores['fundings'] = fundings_score
		readiness_scores['capabilities'] = capabilities_score
		readiness_scores['openness'] = openness_score
		readiness_scores['legal'] = legal_score
		readiness_scores['society'] = society_score
		readiness_scores['impact'] = impact_score

		return readiness_scores
	
	# Leadership score
	def get_leadership_score(self, data):
		# Calculates the score for official allies.
		official_score = 0
		# Calculates the score for unofficial allies.
		unofficial_score = 0

		official_allies = data['lead_official'].split(', ')
		unofficial_allies = data['lead_unofficial'].split(', ')
		
		# Note: This should be customizable and loaded from elsewhere.
		allies_weight = {
			'Alcalde': 5,
			'Regidores de Oposición': 3,
			'Secretario de Ayuntamiento': 3,
			'Grupos de Empresarios o Sindicatos': 3,
			'Síndicos': 2,
			'Regidores': 2,
			'IFAI': 2,
			'Persona a cargo de las políticas de datos abiertos en la ciudad': 2,
			'Organizaciones de la sociedad civil': 1,
			'Ciudadanos Individuales': 1,
		}
		multiplier = 3  # Determines the factor by which an official ally will be multiplied.
		for ally in official_allies:
			if ally in allies_weight.keys():	
				ally_score = allies_weight[ally]*multiplier	
				official_score += ally_score

		for ally in unofficial_allies:
			if ally in allies_weight.keys():
				unofficial_score += allies_weight[ally]

		leadership_score = (official_score + unofficial_score)/30

		return leadership_score

	# Fundings score
	def get_fundings_score(self, data):
		
		inprocess_sum = 0
		
		# To do: Validate presence, input is s a number, valid characters, ranges[0,100]
		budget_data = data['funds_percentage']
		budget = budget_data.strip("%")
		budget = float(budget)
		budget_percentage = budget/10

		# Note: Need to be extracareful here when handling the 'Otra' field.
		sources_inprocess = data['funds_inprocess'].split(', ')
		
		for source in sources_inprocess:
			inprocess_sum += 1

		fundings_score = budget_percentage * (1+(0.05 * inprocess_sum))
		return fundings_score

	# Institutional Structures and Skills score
	def get_capabilities_score(self, data):

		capabilities_sum = 0

		# To do: Validate fields
		team_size = float(data['cap_teamsize']) # Technical team size.
		team_time = float(data['cap_od_time']) # Total time, in hours, devoted weekly to technical duties.

		if team_size >= 1 and team_time >= 40:
			capabilities_sum += 2

		# Open Data management tools
		# To do: Validate fields
		data_tools = data['cap_od_tools'].split(', ')
		for tool in data_tools:
			if tool == 'No instalado todavía':
				capabilities_sum += 0
			else:
				capabilities_sum += 3

		# Metadata
		metadata = data['cap_metadata']
		# Validate for keywords such as 'Ninguna', 'Ninguno', 'No sé', 'N/A', 'N/D', etc.
		if metadata:
			capabilities_sum += 1

		update_frequency = data['cap_frequency']
		if update_frequency == 'Mensual' or update_frequency == 'Semanal' or update_frequency == 'Inemdiatas':
			capabilities_sum += 2
		elif update_frequency == 'Semestral' or update_frequency == 'Varía':
			capabilities_sum += 1
		elif update_frequency == 'No se actualizan':
			capabilities_sum += 0
		else:
			capabilities_sum += 1

		# Content management tools
		content_tools = data['cap_content_tools']
		if content_tools == 'Ninguno':
			capabilities_sum += 0
		else:
			capabilities_sum += 1

		# Database management system
		cap_dbms = data['cap_dbms']
		if cap_dbms == 'Ninguno':
			capabilities_sum += 0
		else:
			capabilities_sum += 1

		capabilities_score = capabilities_sum/12

		return capabilities_score

	# Degree of Dataset Openness score
	def get_openness_score(self, data):
		openness_sum = 0

		scanned = float(data['opn_scans']) # Validate
		if scanned > 0:
			openness_sum += 1

		spreadsheets = float(data['opn_spreadsheets']) # Validate
		if spreadsheets > 0:
			openness_sum += 2

		plaintext = float(data['opn_plaintext']) # Validate
		if plaintext > 0:
			openness_sum += 3

		geospatial = float(data['opn_geospatial']) # Validate
		if geospatial > 0:
			openness_sum += 3

		#opn_training = data['opn_training']
		#opn_training_technical = data['opn_training_technical']
		#opn_training_org = data['opn_training_org']
		#opn_training_legal = data['opn_training_legal']
		#opn_training_agencies = data['opn_training_agencies']
		
		openness_score = openness_sum/8

		return openness_score

	# Policy/Legal Framework score
	def get_legal_score(self, data):
		legal_sum = 0
		
		local_law_status = data['leg_local_status']
		if local_law_status == 'Establecida':
			legal_sum += 2
		elif local_law_status == 'En planeación':
			legal_sum += 1

		state_law_status = data['leg_state_status']
		if state_law_status == 'Establecida':
			legal_sum += 2
		elif state_law_status == 'En planeación':
			legal_sum += 1
		
		#license = data['leg_license']
		#leg_license_comments = data['leg_license_comments']
		#leg_decree = data['leg_decree']
		#leg_local_reference = data['leg_local_reference']
		#leg_state_reference = data['leg_state_reference']

		legal_score = legal_sum/4

		return legal_score

	# Society Readiness score
	def get_society_score(self, data):
		society_sum = 0
		
		# Validate this
		allies = data['soc_allies'].split(", ")
		if len(allies) > 1:
			society_sum += 2
		elif len(allies) == 1:
			society_sum += 1

		planned_events = data['soc_events']
		if planned_events == 'Si':
			society_sum += 1

		society_score = society_sum/3
		return society_score

	# Impact Evaluation score
	def get_impact_score(self, data):
		impact_sum = 0
		# Validate this
		assessment_mechanisms = data['imp_self_assessment'].split(", ")
		for element in assessment_mechanisms:
			impact_sum += 1

		impact_score = impact_sum/2
		
		return impact_score

	
def main():
	logging.basicConfig(level=logging.ERROR) # To do: Implement logging.

	iris_calculator = IrisDimmensionalCalculator()
	iris_calculator.start()
	

if __name__ == '__main__':
	main()