import os
import subprocess
import json
import logging
from datetime import datetime

path_to_links = "websites.json"

output_original_dir = "extracted-doms/original"
output_llm_dir = "extracted-doms/llm-modified"

lh_report_original_dir ="lh-reports/original"
lh_report_llm_dir ="lh-reports/llm-modified"
lh_report_production_dir ="lh-reports/production"

new_modified_dir = "modified-doms/xDOM-00001-single/single"
modified_reports_dir = "lh-reports/new-modified"

port = 8000

# Configure logging
logging.basicConfig(filename='error.log', level=logging.ERROR, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

def run_lighthouse(url, result_path):
    try:

        print(f"Running Lighthouse for {url}")

        print(f"Saving report to {result_path}")

        # Run the Lighthouse CLI command on the HTML file
        command = [
            "lighthouse",
            url,
            "--output=json",
            "--output-path=" + result_path,
            "--chrome-flags=--headless  --no-sandbox --disable-gpu",
            "--only-categories=performance"
        ]
        subprocess.run(command, check=True)
        
        # Read the Lighthouse report
        with open(result_path, 'r') as file:
            report = json.load(file)
        
        # Extract scores
        scores = {
            'performance': report['categories']['performance']['score'] * 100
        }
        
        return scores
    except Exception as e:
        logging.error(f"{url} --- An error occurred: {e}")
        return None



def generate_lighthouse_reports(report_dir, output_dir=output_original_dir):
    results = {}
    
    current_formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # result_path = f"{report_dir}/full/{current_formatted_datetime}"
    result_path = f"{report_dir}"

    # Ensure the result_path and raw_result_path directories exists
    os.makedirs(result_path, exist_ok=True)

    for filename in os.listdir(output_dir):
        if filename.endswith(".html"):
            print(f"Generating Lighthouse report for {filename}...")

            html_file_path = os.path.join(output_dir, filename)

            formatted_filename = filename.replace(".html", "")

            report_output_path = os.path.join(result_path, f"{formatted_filename}.json")

            file_name = os.path.basename(html_file_path)

            url = f"http://localhost:{port}/{file_name}"

            scores = run_lighthouse(url, report_output_path)

            if scores:
                results[filename] = scores
            else:
                print(f"Failed to generate Lighthouse report for {filename}")

     # Store the scores in a JSON file in the report_dir
    os.makedirs(report_dir, exist_ok=True)
    
    summary_report_output = os.path.join(report_dir, f"summaries/{current_formatted_datetime}.json")
    with open(summary_report_output, 'w') as file:
        json.dump(results, file, indent=4)

    print("All Lighthouse reports generated successfully!")

    return results


def generate_lh_production_reports():
    results = {}
    current_formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_path = f"{lh_report_production_dir}/full/{current_formatted_datetime}"

    # Ensure the result_path and raw_result_path directories exists
    os.makedirs(result_path, exist_ok=True)

    # Read and parse the JSON file
    with open(path_to_links, 'r') as file:
        links = json.load(file)

    for link in links:
        url = links[link]['url']

        print(f"Generating Lighthouse report for {link}...")

        report_output_path = os.path.join(result_path, f"{link}.json")

        scores = run_lighthouse(url, report_output_path)

        if scores:
            results[link] = scores
        else:
            print(f"Failed to generate Lighthouse report for {link}")


     # Store the scores in a JSON file in the report_dir
    os.makedirs(lh_report_production_dir, exist_ok=True)
    
    summary_report_output = os.path.join(lh_report_production_dir, f"summaries/{current_formatted_datetime}.json")
    with open(summary_report_output, 'w') as file:
        json.dump(results, file, indent=4)

    print("All Lighthouse reports generated successfully!")

    return results

def main():
    # generate_lighthouse_reports(lh_report_original_dir)
    # generate_lighthouse_reports(lh_report_llm_dir)
    generate_lighthouse_reports(output_dir=new_modified_dir, report_dir=modified_reports_dir)
    # generate_lh_production_reports()
    
if __name__ == "__main__":
    main()