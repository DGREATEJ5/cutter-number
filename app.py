from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import os
import re

app = Flask(__name__)

def get_last_name(author):
    # Define patterns to match and extract the last name based on common formats
    patterns = [
        r'^(?P<last>[\w\-\']+),\s*[\w\.\-\']+',  # Last, First
        r'^(?P<last>[\w\-\']+)$',                # Last (only one name)
        r'^[\w\.\-\']+\s+(?P<last>[\w\-\']+)$',  # First Last
        r'^[\w\.\-\']+\s+(?P<last>[\w\-\']+)\s*$', # First Middle Last
        r'^[\w\.\-\']+\s+(?P<last>[\w\-\']+),',  # First Last, (suffix)
        r'^(?P<last>[\w\-\']+\s[\w\-\']+),',     # Compound last names like "van Gogh, First"
    ]

    # Check if the name has a comma which usually indicates Last, First format
    if ',' in author:
        for pattern in patterns:
            match = re.match(pattern, author)
            if match:
                return match.group('last')
    else:
        # Split the name and filter out initials and titles
        name_parts = re.split(r'[,\s]+', author.strip())
        name_parts = [part for part in name_parts if len(part) > 1 or not part.isalpha()]
        
        # Check for titles and filter them out
        titles = ['Dr', 'Mr', 'Mrs', 'Ms', 'Prof']
        name_parts = [part for part in name_parts if part not in titles]
        
        # Handle compound last names like "van Gogh"
        # Check for common prefixes that indicate a compound surname
        prefixes = ['van', 'de', 'di', 'la', 'da', 'von', 'le', 'del', 'der', 'du', 'van der']
        if len(name_parts) > 1 and name_parts[-2].lower() in prefixes:
            return f"{name_parts[-2]} {name_parts[-1]}"
        
        # Standard case: consider the last part as the last name
        if len(name_parts) > 1:
            return name_parts[-1]

    # Default: return the input if no pattern matches
    return author

def get_cutter_number(last_name):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Set ChromeDriver and Chrome paths correctly for Heroku
    chrome_bin = os.getenv('GOOGLE_CHROME_BIN', '/app/.apt/usr/bin/google-chrome-stable')
    chrome_driver_path = os.getenv('CHROMEDRIVER_PATH', '/app/.chromedriver/bin/chromedriver')

    options.binary_location = chrome_bin
    service = ChromeService(executable_path=chrome_driver_path)

    driver = webdriver.Chrome(service=service, options=options)
    driver.get("http://cutternumber.com/")

    try:
        input_field = driver.find_element(By.NAME, "cutText")
        input_field.send_keys(last_name)
        
        submit_button = driver.find_element(By.XPATH, "//button[@onclick='submitCut()']")
        submit_button.click()
        
        cutter_number = driver.find_element(By.ID, "numero_cut").text
    except Exception as e:
        driver.quit()
        return None
    
    driver.quit()
    return cutter_number

@app.route('/get-cutter-number', methods=['POST'])
def cutter_number_endpoint():
    data = request.json
    author = data.get('author')
    title = data.get('title')
    
    if not author or not title:
        return jsonify({'error': 'Missing author or title'}), 400
    
    last_name = get_last_name(author)
    cutter_number = get_cutter_number(last_name)
    if cutter_number:
        cutter_number = cutter_number + title[0].lower()
        return jsonify({'cutter_number': cutter_number}), 200
    else:
        return jsonify({'error': 'Failed to retrieve Cutter Number'}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))