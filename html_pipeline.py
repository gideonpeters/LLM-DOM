# A pipeline to:
# Split HTML to chunks
# Merge chunks
# Modify original chunks with an LLM using lighthouse audits from original html
# Merge modified chunks
# Generate lighthouse reports for the modified html
# Assess similarity between original and modified HTML
# Assess similarity between original and modified Lighthouse reports

from html_chunker import HTMLChunker
from html_modifier import HTMLModifier
import os
import json
import logging
import subprocess
import concurrent.futures
import time
from datetime import datetime
from report_generator import run_lighthouse
from audit_analyser import run as run_audit_analyser
from joblib import Parallel, delayed


class HTMLPipeline:
    def __init__(self):
        self.experiment_name = ""
        self.mode = "all"
        self.audits = {}

    def load_chunker(self, experiment):
        html_file = f"extracted-doms/original/{experiment}.html"

        original_html = ""
        with open(html_file, 'r') as file:
            original_html = file.read()

        html_modifier = HTMLModifier(original_html, experiment)
        html_modifier.experiment_name = self.experiment_name
        html_modifier.mode = self.mode

        self.audits = HTMLModifier.get_audit_issues(experiment)

        return html_modifier
    
    def chunk_and_modify_html(self, experiment):
        html_modifier = self.load_chunker(experiment)

        if self.audits and html_modifier.mode == "all":
            print(f"Starting HTML all modifications for {experiment}...")
            
            self.start_modifications(html_modifier, self.audits)               
        else:
            print("No audits to be resolved.")
    
    def chunk_and_modify_html_single(self, experiment: str, audit):
        html_modifier = self.load_chunker(experiment)

        audit_list = list(self.audits.keys())
        audit_index = audit_list.index(audit)

        print(f"Starting HTML single audit modifications for {audit} - {audit_index + 1}/{len(audit_list)}...")

        self.start_modifications(html_modifier, lighthouse_audits={audit: self.audits[audit]}, audit_key=audit)

        print(f"HTML modifications for {audit} completed and saved.")
               
    def start_modifications(self, html_modifier: HTMLModifier, lighthouse_audits, audit_key=None):
        lighthouse_audit_issue = html_modifier.formatted_audits(lighthouse_audits)

        modified_html = html_modifier.modify_html_with_llm(lighthouse_audit_issue, audit_key=audit_key)

        html_modifier.save_modified_files(modified_html, audit_key=audit_key)
        html_modifier.save_modifications(audit_key=audit_key)

        print("HTML modifications completed and saved.")

    def generate_lighthouse_reports_for_modified_html(self, filename, audit_key=None):
        modified_html_path = f"modified-doms/{self.experiment_name}"

        if audit_key:
            modified_html_path = f"{modified_html_path}/single"

        report_dir = f"lh-reports/modified/{self.experiment_name}"

        if audit_key:
            report_dir = f"{report_dir}/{audit_key}"

        os.makedirs(report_dir, exist_ok=True)

        modified_html_file = f"{modified_html_path}/{filename}.html" if not audit_key else f"{modified_html_path}/{filename}_{audit_key}.html"

        report_dir = f"{report_dir}/{filename}.json"
        scores = run_lighthouse(modified_html_file, report_dir)

        if scores:
            print(f"Lighthouse scores for modified HTML: {modified_html_path}")
        else: 
            print(f"Failed to generate Lighthouse report for {modified_html_path}")

        return scores
    
    def compare_html_similarity(self, experiment):
        pass

    def compare_lighthouse_scores(self, filename, audit_key=None, ):
        report_folder = f"dom-analysis/{self.experiment_name}"

        if audit_key:
            report_folder = f"{report_folder}/single"

        os.makedirs(report_folder, exist_ok=True)

        llm_modified_reports_path = f"lh-reports/modified/{self.experiment_name}" if not audit_key else f"lh-reports/modified/{self.experiment_name}/{audit_key}"

        if os.path.exists(llm_modified_reports_path):
            run_audit_analyser(reports_folder=report_folder, llm_modified_reports_path=llm_modified_reports_path)
        else:
            print(f"Failed to compare Lighthouse scores for {llm_modified_reports_path}")

def run_pipeline(experiment: str, audit_key=None):
    pipeline = HTMLPipeline()
    pipeline.experiment_name = "xDOM-00001-single"
    pipeline.mode = "single"

    # Chunk and modify HTML
    if pipeline.mode == "all":
        pipeline.chunk_and_modify_html(experiment)
    elif pipeline.mode == "single":
        pipeline.chunk_and_modify_html_single(experiment, audit_key)

    print("Pipeline execution completed.")

if  __name__ == "__main__":
    experiments = [
        # 'airbnb', 
        # 'aliexpress', 
                   'ebay', 
                # 'facebook', 
                #    'github', 'linkedin', 
                #    'medium', 'netflix', 
                #    'pinterest', 'quora', 
                #    'reddit', 'twitch', 
                #    'twitter', 'walmart', 
                #    'youtube'
                   ]

    # run_pipeline(experiments[0])

    current_experiment = experiments[0]
    print("Running pipeline for: ", current_experiment)

    audits = HTMLModifier.get_audit_issues(current_experiment)
    audits_list = list(audits.keys())

    results = Parallel(n_jobs=5)(delayed(run_pipeline)(current_experiment, audit) for audit in audits_list)

    print("All experiments completed: ", len(results))


    


