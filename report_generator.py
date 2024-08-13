import os
import subprocess
import json
import logging


# Configure logging
logging.basicConfig(filename='error.log', level=logging.ERROR, 
                    format='%(asctime)s:%(levelname)s:%(message)s')


def run_lighthouse(html_file, result_path, port=8000):
    file_name = os.path.basename(html_file)

    try:
        url = f"http://localhost:{port}/{file_name}"

        print(f"Running Lighthouse for {url}")

        print(f"Saving report to {result_path}")

        # Run the Lighthouse CLI command on the HTML file
        command = [
            "lighthouse",
            url,
            "--output=json",
            "--output-path=" + result_path,
            "--chrome-flags=--headless",
            "--only-categories=performance,accessibility,best-practices,seo"
        ]
        subprocess.run(command, check=True)
        
        # Read the Lighthouse report
        with open(result_path, 'r') as file:
            report = json.load(file)
        
        # Extract scores
        scores = {
            'performance': report['categories']['performance']['score'] * 100,
            'accessibility': report['categories']['accessibility']['score'] * 100,
            'best-practices': report['categories']['best-practices']['score'] * 100,
            'seo': report['categories']['seo']['score'] * 100
        }
        
        return scores
    except Exception as e:
        logging.error(f"{file_name} --- An error occurred: {e}")
        return None
