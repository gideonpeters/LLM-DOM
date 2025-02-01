import json
import os

# A function to load up a lighthouse report json and extract the audit messages, then store those into new json files.
def extract_audit(report_path, filename):
    output_dir = "lh-reports/original/audits"

    os.makedirs(output_dir, exist_ok=True)
    
    with open(report_path, 'r') as file:
        report = json.load(file)

    audits = report['audits']

    filtered_report = {}

    for audit_key, audit in audits.items():
        if audit['scoreDisplayMode'] != 'notApplicable':
            if ((audit['scoreDisplayMode'] == 'binary' and audit['score'] == 1) or  
                (audit['scoreDisplayMode'] == 'informative') or  
                (audit['scoreDisplayMode'] == 'manual') or  
                (audit['scoreDisplayMode'] == 'metricSavings' and audit['score'] == 1) or 
                (audit['scoreDisplayMode'] == 'numeric' and audit['score'] == 1)):
                continue
            filtered_report[audit_key] = audit

    output_path = os.path.join(output_dir, f"{filename}") 

    with open(output_path, 'w') as file:
        json.dump(filtered_report, file, indent=4)

    print(f"Audit extraction complete for {filename}!")


def main():
    reports_path = "lh-reports/original/full/2024-08-13_15-40-23"

    for filename in os.listdir(reports_path):
        if filename.endswith(".json"):
            report_path = os.path.join(reports_path, filename)
            extract_audit(report_path, filename)


if __name__ == "__main__":
    main()