import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import logging
from jsonschema import validate, ValidationError

logging.basicConfig(level=logging.INFO)

# Define a base schema
BASE_SCHEMA = {
    "type": "object",
    "properties": {
        "printer_name": {"type": "string"},
        "default_url": {"type": "string"},
        "info_url": {"type": "string"},
    },
    "required": ["printer_name", "default_url", "info_url"]
}

# Define schema extensions for Brother printers
BROTHER_SCHEMA = {
    "type": "object",
    "properties": {
        "toner_selector": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "attrs": {"type": "object"}
            },
            "required": ["type", "attrs"]
        },
        "model_selector": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "string": {"type": "string"},
                "next": {"type": "string"}
            },
            "required": ["type", "string", "next"]
        },
        "serial_selector": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "string": {"type": "string"},
                "next": {"type": "string"}
            },
            "required": ["type", "string", "next"]
        },
        "error_selector": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "attrs": {"type": "object"},
                "table_class": {"type": "string"},
                "row_tag": {"type": "string"},
                "error_index": {"type": "integer"},
                "page_index": {"type": "integer"}
            },
            "required": ["type", "attrs", "table_class", "row_tag", "error_index", "page_index"]
        }
    },
    "required": ["toner_selector", "model_selector", "serial_selector", "error_selector"]
}

class Printer:
    def __init__(self, config):
        self.name = config['printer_name']
        self.default_url = config['default_url']
        self.info_url = config['info_url']
        self.toner_selector = config.get('toner_selector')
        self.model_selector = config.get('model_selector')
        self.serial_selector = config.get('serial_selector')
        self.error_selector = config.get('error_selector')
        self.report_dir_path = "C:/Users/Wilson/Desktop/generatePrinter/reports/"
        self.serial_number = None

    def fetch_page(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Failed to fetch page: {url}, error: {e}")
            return None

    def parse_toner_level(self, html_content):
        if not self.toner_selector:
            return 'Unknown'
        soup = BeautifulSoup(html_content, 'html.parser')
        toner_element = soup.find(self.toner_selector['type'], self.toner_selector['attrs'])
        return toner_element['height'] if toner_element else 'Unknown'

    def parse_model_and_serial(self, html_content):
        if not self.model_selector or not self.serial_selector:
            return 'Unknown', 'Unknown'
        soup = BeautifulSoup(html_content, 'html.parser')
        model_name_element = soup.find(self.model_selector['type'], string=self.model_selector['string'])
        serial_number_element = soup.find(self.serial_selector['type'], string=self.serial_selector['string'])
        
        model_name = model_name_element.find_next(self.model_selector['next']).text.strip() if model_name_element else 'Unknown'
        serial_number = serial_number_element.find_next(self.serial_selector['next']).text.strip() if serial_number_element else 'Unknown'
        
        self.serial_number = serial_number
        return model_name, serial_number

    def parse_error_history(self, html_content):
        if not self.error_selector:
            logging.error("Error selector is not defined.")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        error_history = []

        try:
            error_section = soup.find('div', self.error_selector['attrs']).find_next('h3', string="Error History(last 10 errors)").find_next('table', {'class': self.error_selector['table_class']})
        except AttributeError:
            logging.error("Error: Unable to find the error section.")
            return error_history
        
        if error_section is None:
            logging.error("Error: Unable to find the error section.")
            return error_history
        
        error_rows = error_section.find_all(self.error_selector['row_tag'])
        for row in error_rows:
            columns = row.find_all(['td', 'th'])
            if len(columns) >= max(self.error_selector['error_index'], self.error_selector['page_index']) + 1:
                error = columns[self.error_selector['error_index']].text.strip()
                page = columns[self.error_selector['page_index']].text.strip().replace('Page : ', '')  # Replace non-breaking spaces
                error_history.append({
                    'error': error,
                    'page': page
                })
            else:
                logging.warning(f"Skipping row with insufficient columns: {row}")
        
        logging.info(f"Parsed error history: {error_history}")
        return error_history


    def read_stored_errors(self):
        file_path = os.path.join(self.report_dir_path, f"{self.serial_number}_stored_errors.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                stored_errors = json.load(file)
                logging.info(f"Stored errors loaded: {stored_errors}")
                return stored_errors
        return []

    def write_stored_errors(self, errors):
        file_path = os.path.join(self.report_dir_path, f"{self.serial_number}_stored_errors.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(errors, file, indent=4)
        logging.info(f"Stored errors written: {errors}")

    def write_report(self, model_name, toner_level, new_errors, initial_run):
        os.makedirs(self.report_dir_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file_path = os.path.join(self.report_dir_path, f"{self.name}_{self.serial_number}_report_{timestamp}.txt")
        with open(report_file_path, 'w') as file:
            file.write("Daily Printer Status Report\n")
            file.write("==========================\n")
            file.write(f"Printer Name: {self.name}\n")
            file.write(f"Model Name: {model_name}\n")
            file.write(f"Serial Number: {self.serial_number}\n")
            file.write(f"Toner Level (height value): {toner_level}\n")
            if initial_run:
                file.write("\nInitial Errors:\n")
                for error in new_errors:
                    file.write(f"Error: {error['error']}, Page: {error['page']}\n")
            elif new_errors:
                file.write("\nNew Errors:\n")
                for error in new_errors:
                    file.write(f"Error: {error['error']}, Page: {error['page']}\n")
            else:
                file.write("\nNo new errors.\n")
        logging.info(f"Report saved as {report_file_path}")

    def check_for_new_errors(self, error_history):
        stored_errors = self.read_stored_errors()

        new_errors = []
        initial_run = False

        if not stored_errors:
            logging.info("No stored errors found. Assuming initial run.")
            self.write_stored_errors(error_history)
            new_errors = error_history
            initial_run = True
        else:
            new_errors = [error for error in error_history if error not in stored_errors]
            if new_errors:
                logging.info(f"New Errors for {self.name} (Serial: {self.serial_number}): {new_errors}")
                self.write_stored_errors(error_history)
            else:
                logging.info(f"No new errors for {self.name} (Serial: {self.serial_number}).")
        
        return new_errors, initial_run

    def run(self):
        default_page_content = self.fetch_page(self.default_url)
        if default_page_content:
            toner_level = self.parse_toner_level(default_page_content)
        else:
            logging.error(f"Failed to retrieve toner level for {self.name}.")
            return

        info_page_content = self.fetch_page(self.info_url)
        if info_page_content:
            model_name, serial_number = self.parse_model_and_serial(info_page_content)
        else:
            logging.error(f"Failed to retrieve model name and serial number for {self.name}.")
            return

        if info_page_content:
            error_history = self.parse_error_history(info_page_content)
        else:
            logging.error(f"Failed to retrieve error history for {self.name}.")
            return

        new_errors, initial_run = self.check_for_new_errors(error_history)
        
        logging.info(f"Daily Printer Status Report for {self.name} (Serial: {self.serial_number})")
        logging.info(f"Model Name: {model_name}")
        logging.info(f"Serial Number: {serial_number}")
        logging.info(f"Toner Level (height value): {toner_level}")
        
        self.write_report(model_name, toner_level, new_errors, initial_run)

class BrotherDCP_L2540DW(Printer):
    def __init__(self, config):
        super().__init__(config)

class BrotherHL_L2350DW(Printer):
    def __init__(self, config):
        super().__init__(config)

PRINTER_TYPE_SCHEMAS = {
    "Brother DCP-L2540DW": BROTHER_SCHEMA,
    "Brother HL-L2350DW": BROTHER_SCHEMA
    # Add more printer-specific schemas here
}

def validate_config(config, schema):
    try:
        validate(instance=config, schema=schema)
        return True
    except ValidationError as e:
        logging.error(f"Configuration file is invalid: {e.message}")
        return False

def load_printers(config_dir_path):
    config_files = [f for f in os.listdir(config_dir_path) if f.endswith('.json')]
    printers = []

    for config_file in config_files:
        with open(os.path.join(config_dir_path, config_file), 'r') as file:
            config = json.load(file)
        
        printer_type = config.get('printer_name')
        schema = PRINTER_TYPE_SCHEMAS.get(printer_type, BASE_SCHEMA)

        if validate_config(config, schema):
            if printer_type == "Brother DCP-L2540DW":
                printer = BrotherDCP_L2540DW(config)
            elif printer_type == "Brother HL-L2350DW":
                printer = BrotherHL_L2350DW(config)
            else:
                printer = Printer(config)
            
            printers.append(printer)
    
    return printers

def main():
    config_dir_path = "C:/Users/Wilson/Desktop/generatePrinter/configs/"
    
    if not os.path.exists(config_dir_path):
        logging.error(f"Configuration directory does not exist: {config_dir_path}")
        return

    printers = load_printers(config_dir_path)

    if not printers:
        logging.error("No configuration files found.")
        return
    
    for printer in printers:
        printer.run()

if __name__ == "__main__":
    main()
