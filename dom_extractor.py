from bs4 import BeautifulSoup
import requests
import json
import os
from datetime import datetime
from report_generator import run_lighthouse

path_to_links = "websites.json"
output_dir = "extracted-doms"
report_dir ="lh-reports"
raw_report_dir ="raw-lh-reports"
port = 8000

def extract_dom_trees():
    os.makedirs(output_dir, exist_ok=True)

    # Read and parse the JSON file
    with open(path_to_links, 'r') as file:
        links = json.load(file)

    for link in links:
        url = links[link]['url']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        output_file = os.path.join(output_dir, f"{link}.html")
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(soup.prettify())

        print(f"DOM extracted for {link}")

    print("All DOMs extracted successfully!")



def generate_lighthouse_reports():
    results = {}
    
    current_formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    raw_result_path = f"{raw_report_dir}/{current_formatted_datetime}"

    # Ensure the result_path and raw_result_path directories exists
    os.makedirs(raw_result_path, exist_ok=True)

    for filename in os.listdir(output_dir):
        if filename.endswith(".html"):
            print(f"Generating Lighthouse report for {filename}...")

            html_file = os.path.join(output_dir, filename)

            formatted_filename = filename.replace(".html", "")

            raw_report_output = os.path.join(raw_result_path, f"{formatted_filename}.json")

            scores = run_lighthouse(html_file,raw_report_output, port)
            if scores:
                results[filename] = scores
            else:
                print(f"Failed to generate Lighthouse report for {filename}")

     # Store the scores in a JSON file in the report_dir
    
    os.makedirs(report_dir, exist_ok=True)
    
    report_output = os.path.join(report_dir, f"{current_formatted_datetime}.json")
    with open(report_output, 'w') as file:
        json.dump(results, file, indent=4)

    print("All Lighthouse reports generated successfully!")

    return results

       


# extract_dom_trees()
generate_lighthouse_reports()


