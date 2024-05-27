import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# Define the printer URLs and file path for storing errors
printer_default_url = "http://192.168.0.33/"
printer_info_url = "http://192.168.0.33/general/information.html?kind=item"
report_dir_path = "C:/Users/Wilson/Desktop/generatePrinter/reports/"

# Function to fetch the printer page
def fetch_printer_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return None

# Function to parse the toner level from the default page
def parse_toner_level(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    toner_element = soup.find('img', {'class': 'tonerremain', 'alt': 'Black'})
    toner_level = toner_element['height'] if toner_element else 'Unknown'
    return toner_level

# Function to parse the model name, serial number, and error history from the information page
def parse_info_and_errors(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract model name and serial number
    model_name_element = soup.find('dt', string='Model Name')
    serial_number_element = soup.find('dt', string='Serial no.')
    
    model_name = model_name_element.find_next('dd').text.strip() if model_name_element else 'Unknown'
    serial_number = serial_number_element.find_next('dd').text.strip() if serial_number_element else 'Unknown'
    
    # Extract error history
    error_history = []
    error_rows = soup.select('div.contentsGroup table.list.errorHistory tbody tr')
    
    for row in error_rows:
        columns = row.find_all('td')
        if len(columns) >= 2:
            error = columns[0].text.strip()
            page = columns[1].text.strip().replace('Page : ', '')  # Replace non-breaking spaces
            error_history.append({
                'error': error,
                'page': page
            })
    
    return model_name, serial_number, error_history

# Function to read stored errors from a file
def read_stored_errors(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []

# Function to write errors to a file
def write_stored_errors(file_path, errors):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(errors, file, indent=4)

# Function to write a report to a file
def write_report(report_dir, model_name, serial_number, toner_level, new_errors):
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file_path = os.path.join(report_dir, f"report_{timestamp}.txt")
    with open(report_file_path, 'w') as file:
        file.write("Daily Printer Status Report\n")
        file.write("==========================\n")
        file.write(f"Model Name: {model_name}\n")
        file.write(f"Serial Number: {serial_number}\n")
        file.write(f"Toner Level (height value): {toner_level}\n")
        if new_errors:
            file.write("\nNew Errors:\n")
            for error in new_errors:
                file.write(f"Error: {error['error']}, Page: {error['page']}\n")
        else:
            file.write("\nNo new errors.\n")
    print(f"Report saved as {report_file_path}")

# Main script execution
def main():
    # Fetch and parse the toner level from the default page
    default_page_content = fetch_printer_page(printer_default_url)
    if default_page_content:
        toner_level = parse_toner_level(default_page_content)
    else:
        print("Failed to retrieve toner level.")
        return

    # Fetch and parse the model name, serial number, and error history from the information page
    info_page_content = fetch_printer_page(printer_info_url)
    if info_page_content:
        model_name, serial_number, error_history = parse_info_and_errors(info_page_content)
    else:
        print("Failed to retrieve model name, serial number, and error history.")
        return

    # Read stored errors
    error_file_path = os.path.join(report_dir_path, 'stored_errors.json')
    stored_errors = read_stored_errors(error_file_path)
    
    # Identify new errors
    new_errors = [error for error in error_history if error not in stored_errors]
    
    # Print new errors
    if new_errors:
        print("New Errors:")
        for error in new_errors:
            print("Error: {}, Page: {}".format(error['error'], error['page']))
        # Update stored errors
        write_stored_errors(error_file_path, error_history)
    else:
        print("No new errors.")
    
    # Print the daily printer status report
    print("\nDaily Printer Status Report")
    print("==========================")
    print(f"Model Name: {model_name}")
    print(f"Serial Number: {serial_number}")
    print("Toner Level (height value): {}".format(toner_level))
    
    # Write report to a file with a timestamp
    write_report(report_dir_path, model_name, serial_number, toner_level, new_errors)

if __name__ == "__main__":
    main()
