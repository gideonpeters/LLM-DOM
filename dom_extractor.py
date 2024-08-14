from bs4 import BeautifulSoup
import requests
import json
import os
from datetime import datetime
from report_generator import run_lighthouse

path_to_links = "websites.json"

output_original_dir = "extracted-doms/original"
output_llm_dir = "extracted-doms/llm-modified"

lh_report_original_dir ="lh-reports/original"
lh_report_llm_dir ="lh-reports/llm-modified"

port = 8000

def extract_dom_trees():
    os.makedirs(output_original_dir, exist_ok=True)

    # Read and parse the JSON file
    with open(path_to_links, 'r') as file:
        links = json.load(file)

    for link in links:
        url = links[link]['url']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        output_file = os.path.join(output_original_dir, f"{link}.html")
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(soup.prettify())

        print(f"DOM extracted for {link}")

    print("All DOMs extracted successfully!")



def generate_lighthouse_reports():
    results = {}
    
    current_formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    original_result_path = f"{lh_report_original_dir}/{current_formatted_datetime}"

    # Ensure the result_path and raw_result_path directories exists
    os.makedirs(original_result_path, exist_ok=True)

    for filename in os.listdir(output_original_dir):
        if filename.endswith(".html"):
            print(f"Generating Lighthouse report for {filename}...")

            html_file = os.path.join(output_original_dir, filename)

            formatted_filename = filename.replace(".html", "")

            raw_report_output = os.path.join(original_result_path, f"{formatted_filename}.json")

            scores = run_lighthouse(html_file,raw_report_output, port)
            if scores:
                results[filename] = scores
            else:
                print(f"Failed to generate Lighthouse report for {filename}")

     # Store the scores in a JSON file in the report_dir
    
    os.makedirs(lh_report_original_dir, exist_ok=True)
    
    report_output = os.path.join(lh_report_original_dir, f"{current_formatted_datetime}.json")
    with open(report_output, 'w') as file:
        json.dump(results, file, indent=4)

    print("All Lighthouse reports generated successfully!")

    return results

       


# extract_dom_trees()
generate_lighthouse_reports()


