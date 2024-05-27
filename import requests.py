import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

class Printer:
    def __init__(self, config):
        self.name = config['printer_name']
        self.default_url = config['default_url']
        self.info_url = config['info_url']
        self.toner_selector = config['toner_selector']
        self.model_selector = config['model_selector']
        self.serial_selector = config['serial_selector']
        self.error_selector = config['error_selector']
        self.report_dir_path = "C:/Users/Wilson/Desktop/generatePrinter/reports/"
        self.serial_number = None

    def fetch_page(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to fetch page: {url}")
            return None

    def parse_toner_level(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        toner_element = soup.find(self.toner_selector['type'], self.toner_selector['attrs'])
        toner_level = toner_element['height'] if toner_element else 'Unknown'
        return toner_level

    def parse_model_and_serial(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        model_name_element = soup.find(self.model_selector['type'], string=self.model_selector['string'])
        serial_number_element = soup.find(self.serial_selector['type'], string=self.serial_selector['string'])
        
        model_name = model_name_element.find_next(self.model_selector['next']).text.strip() if model_name_element else 'Unknown'
        serial_number = serial_number_element.find_next(self.serial_selector['next']).text.strip() if serial_number_element else 'Unknown'
        
        self.serial_number = serial_number
        return model_name, serial_number

    def parse_error_history(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        error_history = []
        error_section = soup.find(self.error_selector['type'], self.error_selector['attrs'])
        
        if error_section is None:
            print("Error: Unable to find the error section.")
            return error_history
        
        error_table = error_section.find('table', {'class': self.error_selector['table_class']})
        if error_table is None:
            print("Error: Unable to find the error table.")
            return error_history
        
        error_rows = error_table.find_all(self.error_selector['row_tag'])
        for row in error_rows:
            columns = row.find_all('td')
            if len(columns) > max(self.error_selector['error_index'], self.error_selector['page_index']):
                error = columns[self.error_selector['error_index']].text.strip()
                page = columns[self.error_selector['page_index']].text.strip().replace('Page : ', '')  # Replace non-breaking spaces
                error_history.append({
                    'error': error,
                    'page': page
                })
        return error_history

    def read_stored_errors(self):
        file_path = os.path.join(self.report_dir_path, f"{self.serial_number}_stored_errors.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        return []

    def write_stored_errors(self, errors):
        file_path = os.path.join(self.report_dir_path, f"{self.serial_number}_stored_errors.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(errors, file, indent=4)

    def write_report(self, model_name, toner_level, new_errors):
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
            if new_errors:
                file.write("\nNew Errors:\n")
                for error in new_errors:
                    file.write(f"Error: {error['error']}, Page: {error['page']}\n")
            else:
                file.write("\nNo new errors.\n")
        print(f"Report saved as {report_file_path}")

    def check_for_new_errors(self, error_history):
        stored_errors = self.read_stored_errors()
        new_errors = [error for error in error_history if error not in stored_errors]
        
        if new_errors:
            print(f"New Errors for {self.name} (Serial: {self.serial_number}):")
            for error in new_errors:
                print(f"Error: {error['error']}, Page: {error['page']}")
            self.write_stored_errors(error_history)
        else:
            print(f"No new errors for {self.name} (Serial: {self.serial_number}).")
        
        return new_errors

    def run(self):
        # Fetch and parse the toner level from the default page
        default_page_content = self.fetch_page(self.default_url)
        if default_page_content:
            toner_level = self.parse_toner_level(default_page_content)
        else:
            print(f"Failed to retrieve toner level for {self.name}.")
            return

        # Fetch and parse the model name and serial number from the information page
        info_page_content = self.fetch_page(self.info_url)
        if info_page_content:
            model_name, serial_number = self.parse_model_and_serial(info_page_content)
        else:
            print(f"Failed to retrieve model name and serial number for {self.name}.")
            return

        # Fetch and parse the error history from the information page
        if info_page_content:
            error_history = self.parse_error_history(info_page_content)
        else:
            print(f"Failed to retrieve error history for {self.name}.")
            return

        # Check for new errors
        new_errors = self.check_for_new_errors(error_history)
        
        # Print the daily printer status report
        print(f"\nDaily Printer Status Report for {self.name} (Serial: {self.serial_number})")
        print("==========================")
        print(f"Model Name: {model_name}")
        print(f"Serial Number: {serial_number}")
        print(f"Toner Level (height value): {toner_level}")
        
        # Write report to a file with a timestamp
        self.write_report(model_name, toner_level, new_errors)

class BrotherDCP_L2540DW(Printer):
    def __init__(self, config):
        super().__init__(config)


def load_printers(config_dir_path):
    config_files = [f for f in os.listdir(config_dir_path) if f.endswith('.json')]
    printers = []

    for config_file in config_files:
        with open(os.path.join(config_dir_path, config_file), 'r') as file:
            config = json.load(file)
        
        if config['printer_name'] == "Brother DCP-L2540DW":
            printer = BrotherDCP_L2540DW(config)
        else:
            printer = Printer(config)
        
        printers.append(printer)
    
    return printers

def main():
    config_dir_path = "C:/Users/Wilson/Desktop/generatePrinter/configs/"
    
    # Ensure the configuration directory exists
    if not os.path.exists(config_dir_path):
        print(f"Configuration directory does not exist: {config_dir_path}")
        return

    # Load printers
    printers = load_printers(config_dir_path)

    if not printers:
        print("No configuration files found.")
        return
    
    # Run each printer
    for printer in printers:
        printer.run()

if __name__ == "__main__":
    main()
