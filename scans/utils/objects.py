import csv

import xlsxwriter as xw

from .helper import *


class ObjectParser():
	"""
	This object parses a CSV file into a list of dicts
	ex:
		csv:
			id;first_name;last_name
			1;john;doe
			2;jane;dee
		parsed output:
			[
				{"id": "1", "first_name":"john", "last_name":"doe"},
				{"id": "2", "first_name":"jane", "last_name":"dee"}
			]
	"""
	def __init__(self, file, debug):
		self.csv_file = file
		self.debug = debug

	def parse(self) -> list:
		self.objects = []

		if self.debug:
			info(f"Reading from {self.csv_file}")

		with open(self.csv_file, 'r', encoding="utf-8") as f:
			rows = [row for row in csv.reader(f, delimiter=';')]
			header = rows[0]
			rows = rows[1:]
			
			for row in rows:
				row_cleaned = [cell.strip() for cell in row]
				self.objects.append({k:v for k,v in zip(header,row_cleaned)})

		return self.objects



class ObjectSerializer:
    """
    This object does the exact opposite of ObjectParser, it turns a list of dicts into an XLSX file
    """

    def __init__(self, objects: list[dict], output_file: str, debug: bool):
        self.objects = objects
        self.output = output_file
        self.debug = debug

    def serialize(self):
        if self.debug:
            info(f"Writing to {self.output}")

        workbook = xw.Workbook(self.output)
        worksheet = workbook.add_worksheet("Output")

        header = list(self.objects[0].keys())

        bold_format = workbook.add_format({"bold": True})
        cell_formats = {
            "True": workbook.add_format({"bg_color": "#9ee866"}),
            "False": workbook.add_format({"bg_color": "#e86666"}),
            "Error": workbook.add_format({"bg_color": "#e8a566"}),
            "NotApplicable": workbook.add_format({"bg_color": "#adadad"}),
        }

        for column, value in enumerate(header):
            worksheet.write(0, column, value, bold_format)

        for row, dic in enumerate(self.objects, start=1):
            status = dic.get("status", "NotApplicable")
            format_ = cell_formats.get(status, workbook.add_format())
            for column, value in enumerate(dic.values()):
                worksheet.write(row, column, value, format_)

        workbook.close()
