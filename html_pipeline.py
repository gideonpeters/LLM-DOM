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


class HTMLPipeline:
    def __init__(self):
        self.experiment_name = ""
        self.mode = "all"
        self.audits = {}
        self.html_modifier = None

    def load_chunker(self, experiment):
        html_file = f"extracted-doms/original/{experiment}.html"

        original_html = ""
        with open(html_file, 'r') as file:
            original_html = file.read()

        html_modifier = HTMLModifier(original_html, experiment)
        html_modifier.experiment_name = self.experiment_name
        html_modifier.mode = self.mode

        self.audits = html_modifier.get_audit_issues()
        self.html_modifier = html_modifier

        return html_modifier
    
    def chunk_and_modify_html(self, experiment):
        if self.audits and self.html_modifier.mode == "all":
            print(f"Starting HTML all modifications for {experiment}...")
            
            self.start_modifications(self.audits)               
        else:
            print("No audits to be resolved.")
    
    def chunk_and_modify_html_single(self, audit):
        print(f"Starting HTML single audit modifications for {audit}...")

        self.start_modifications(lighthouse_audits={audit: self.audits[audit]})

        print(f"HTML modifications for {audit} completed and saved.")
               
    def start_modifications(self, lighthouse_audits):
        lighthouse_audit_issue = self.html_modifier.formatted_audits(lighthouse_audits)

        modified_html = self.html_modifier.modify_html_with_llm(lighthouse_audit_issue)

        self.html_modifier.save_modified_files(modified_html)
        self.html_modifier.save_modifications()

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

def run_pipeline(experiment):
    pipeline = HTMLPipeline()
    pipeline.experiment_name = "xDOM-00001-single"
    pipeline.mode = "single"

    # Chunk and modify HTML
    if pipeline.mode == "all":
        pipeline.chunk_and_modify_html(experiment)
    elif pipeline.mode == "single":

        pipeline.load_chunker(experiment)
        audits = pipeline.audits
        with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
            all_audits = list(audits.keys())
            executor.map(pipeline.chunk_and_modify_html_single, all_audits)

    # # Compare Lighthouse scores
    # if pipeline.mode == "all":
    #     pipeline.generate_lighthouse_reports_for_modified_html(experiment)
    #     pipeline.compare_lighthouse_scores()
    #     # pipeline.compare_html_similarity(experiment)
    # elif pipeline.mode == "single":
    #     audits_path = f"lh-reports/original/audits"

    #     if os.path.exists(audits_path):
    #         for audit in os.listdir(audits_path):
    #             pipeline.generate_lighthouse_reports_for_modified_html(experiment, audit)
    #             pipeline.compare_lighthouse_scores(experiment, audit)
    #             # pipeline.compare_html_similarity(experiment)


if  __name__ == "__main__":
    experiments = [
        'airbnb', 
        # 'aliexpress', 
                #    'ebay', 'facebook', 
                #    'github', 'linkedin', 
                #    'medium', 'netflix', 
                #    'pinterest', 'quora', 
                #    'reddit', 'twitch', 
                #    'twitter', 'walmart', 
                #    'youtube'
                   ]

    run_pipeline(experiments[0])

    # with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
    #     executor.map(run_pipeline, experiments)