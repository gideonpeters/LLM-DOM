from bs4 import BeautifulSoup
from openai import OpenAI
from time import sleep
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
) 
import re
import os
import json
from html_chunker import HTMLChunker
from uuid import uuid4
import time
import tiktoken
import speedtest
import sys
from dotenv import load_dotenv

load_dotenv()

# OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TOKEN_LIMIT = 12000
MAX_LIMIT = 16100

ref_api_keys = [
    {
        "api_key": os.getenv("OPENAI_API_KEY_ME"),
        "key": "me",
        "rate_limit": 2000000,
        "tokens_used": 0,
        "no_of_requests": 0,
        "last_request": time.time(),
    },
     {
        "api_key": os.getenv("OPENAI_API_KEY_ALOR"),
        "key": "alor",
        "rate_limit": 20000000,
        "tokens_used": 0,
        "no_of_requests": 0,
        "last_request": time.time(),
    },
     {
        "api_key": os.getenv("OPENAI_API_KEY_CAREN"),
        "key": "caren",
        "rate_limit": 2000000,
        "tokens_used": 0,
        "no_of_requests": 0,
        "last_request": time.time(),
    },
     {
        "api_key": os.getenv("OPENAI_API_KEY_MAYRA"),
        "key": "mayra",
        "rate_limit": 2000000,
        "tokens_used": 0,
        "no_of_requests": 0,
        "last_request": time.time(),
    },
     {
        "api_key": os.getenv("OPENAI_API_KEY_CHAIMA"),
        "key": "chaima",
        "rate_limit": 2000000,
        "tokens_used": 0,
        "no_of_requests": 0,
        "last_request": time.time(),
    },
    {
        "api_key": os.getenv("OPENAI_API_KEY_WAMIRI"),
        "key": "wamiri",
        "rate_limit": 2000000,
        "tokens_used": 0,
        "no_of_requests": 0,
        "last_request": time.time(),
    }
]


def get_existing_tokens_usage():
    existing_token_file = "tokens_usage.json"

    existing_usage = []
    if os.path.exists(existing_token_file):
        with open(existing_token_file, 'r') as file:
            existing_usage = json.load(file)

    # existing_usage = []
    for usage in existing_usage:
        for key in ref_api_keys:
            if key['key'] == usage['key']:
                usage['api_key'] = key['api_key']
                
    return existing_usage

def save_tokens_usage(prompt: str, api_key, estimator: callable):
    try:
        existing_token_file = "tokens_usage.json"

        existing_usage = get_existing_tokens_usage()

        api_keys = existing_usage

        # Update token usage
        for key in api_keys:
            if key['api_key'] == api_key:
                key['tokens_used'] += estimator(prompt)
                key['no_of_requests'] += 1
                key['last_request'] = time.time()

        api_keys_copy = api_keys.copy()
        for key in api_keys_copy:
            key.pop("api_key")

        with open(existing_token_file, 'w') as file:
            json.dump(api_keys_copy, file, indent=4)

    except Exception as e:
        print(f"Error saving token usage: {e}")

# Class to split HTML into chunks and send each chunk to the LLM for modification
# Directories
# - chunked-doms/original/ - Original HTML chunks
# - chunked-doms/modified/ - Modified HTML chunks
# - modified-doms/ - Modified HTML files
# - prompts/{experiment_name}/{dom_name}/{prompt_uuid} - LLM prompts for each chunk for all audit mode
# - prompts/{experiment_name}/single/{dom_name}/{prompt_uuid}_{audit_key} - LLM prompts for each chunk for single audit mode
# - response_times/{experiment_name}/{dom_name}.json - Response times for each chunk for all audit mode
# - response_times/{experiment_name}/single/{dom_name}.json - Response times for each chunk for single audit mode
# - modifications.json - Modified HTML files for all audit mode
# - modifications_single.json - Modified HTML files for single audit mode
# - lh-reports/original/audits/{dom_name}.json - Lighthouse audits for each HTML file
# - lh-reports/original/audits/{dom_name}.json - Lighthouse audits for each HTML file
# - extracted-doms/original/{dom_name}.html - Original HTML files
# - modified-doms/{dom_name}.html - Modified HTML files
# - error_{dom_name}.log - Error log file


class HTMLModifier:
    def __init__(self, html, dom_name):
        # check_for_existing_tokens_usage()
        self.api_key = os.getenv("OPENAI_API_KEY_CAREN")

        if self.api_key is None:
            raise Exception("All API keys have exceeded their rate limits.")

        self.html = html
        self.max_tokens = TOKEN_LIMIT
        self.model = "gpt-4o-mini"
        self.experiment_name = "html_modifier_batch_0001B-alpha"
        self.dom_name = dom_name
        self.no_of_modifications = 0
        self.temperature = 0.2
        self.mode = "single"
        self.audits = {}
        self.formatted_audit_text = ""
        self.style_store = {}
        self.script_store = {}
        self.only_estimate_tokens = False

    def get_api_key(self, api_keys):
        # Get the most recently used API key that has not exceeded the rate limit
        # Sort the API keys by the last request time

        api_keys.sort(key=lambda x: x['last_request'])

        selected_key = None
        for key in api_keys:
            if key['tokens_used'] < key['rate_limit']:
                selected_key = key
                break
        
        return selected_key['api_key']

    def get_experiment_details(self):

        chunker = HTMLChunker(self.html, TOKEN_LIMIT)
        
        chunks = chunker.split_html()

        chunks = chunker.store_chunks(chunks, store_chunks=False)

        no_of_chunks = len(chunks)

        prompts = []
        if self.mode == "all":
            for chunk in chunks:
                audits = self.audits
                formatted_audit = self.formatted_audits(audits)

                prompt = self.send_to_llm(chunk['content'], formatted_audit, None, True)
                prompts.append({
                    "dom_name": self.dom_name,
                    "chunk": chunk['id'],
                    "audits": list(audits.keys()),
                    "tokens":self.estimate_tokens(prompt),
                    "content": prompt,
                })
        else:
            audits = self.audits
            for audit in audits:
                for chunk in chunks:
                    formatted_audit = self.formatted_audits({audit: audits[audit]})
                    prompt = self.send_to_llm(chunk['content'], formatted_audit, audit, True)
                    prompts.append({
                        "dom_name": self.dom_name,
                        "chunk": chunk['id'],
                        "audits": [audit],
                        "tokens":self.estimate_tokens(prompt),
                        "content": prompt,
                    })
        
        no_of_prompts = len(prompts)

        return {
            "no_of_chunks": no_of_chunks,
            "dom_name": self.dom_name,
            "no_of_prompts": no_of_prompts,
            "total_tokens": sum([prompt['tokens'] for prompt in prompts]),
            "prompts": prompts
        }

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(4))
    def measure_speed(self):
        try: 
            st = speedtest.Speedtest()
            
            st.get_best_server()
            
            download_speed = st.download()  
            upload_speed = st.upload()  # in bits per second
            ping = st.results.ping  # in milliseconds

            # Convert speeds to Mbps
            download_speed_mbps = download_speed / 1_000_000
            upload_speed_mbps = upload_speed / 1_000_000

            return {
                "download_speed": download_speed_mbps,
                "upload_speed": upload_speed_mbps,
                "ping": ping
            }
        except Exception as e:
            return {
                "download_speed": 0,
                "upload_speed": 0,
                "ping": 0,
                "error": str(e)
            }

    def store_prompt(self, prompt, audit_key=None):
        prompt_uuid = uuid4()
        prompt_path = f"prompts/{self.experiment_name}/{self.dom_name}" if self.mode == "all" else f"prompts/{self.experiment_name}/single/{self.dom_name}"
        prompt_filename = f"{prompt_path}/{prompt_uuid}.txt" if self.mode == "all" else f"{prompt_path}/{prompt_uuid}_{audit_key}.txt"

        os.makedirs(prompt_path, exist_ok=True)

        with open(prompt_filename, 'w') as file:
            file.write(prompt)
        
        return prompt_uuid

    def store_response_time(self, start_time, end_time, prompt_uuid, prompt_token_size, audit_key=None):
        duration = end_time - start_time

        response_times = []
        response_time_path = f"response_times/{self.experiment_name}" if self.mode == "all" else f"response_times/{self.experiment_name}/single/{self.dom_name}"
        response_time_filename = f"{response_time_path}/{self.dom_name}.json" if self.mode == "all" else f"{response_time_path}/{audit_key}.json"

        os.makedirs(response_time_path, exist_ok=True)

        try:
            with open(response_time_filename, 'r') as file:
                existing_response_times = json.load(file)
                if existing_response_times:
                    response_times.extend(existing_response_times)
        except (json.JSONDecodeError, FileNotFoundError):
            response_times = []

        # Append new data
        response_times.append({
            "prompt_uuid": str(prompt_uuid),
            "dom_name": self.dom_name,
            "prompt_token_size": prompt_token_size,
            "duration": duration,
            'mode': self.mode,
            "audit_key": audit_key,
            "experiment_name": self.experiment_name,
            "speed": self.measure_speed()
        })

        # Write updated data back to the file
        with open(response_time_filename, 'w') as file:
            json.dump(response_times, file, indent=4)

    def send_to_llm(self, html_part, audit_issues, audit_key=None, only_return_prompt=False):
        issue_text = "issues" if self.mode == "all" else "issue"
            
        prompt = f"""
        You are a web performance expert. 
        Based on the following Lighthouse audit {issue_text}: 
       
        __________________
        "{audit_issues}"
        __________________

        Due to the huge token size of HTML files, 
        You are given the HTML in chunks, one at a time. 
        Please modify each HTML code chunk to resolve the performance {issue_text} given above.

        Make sure you:
        1. Remember the code is split into chunks and you are only receiving one chunk at a time, there might be some unclosed or cut elements, do not worry about that.
        2. Consider that a chunk might be a part of a larger element, so the code might not be complete.
        3. Consider that the HTML as a whole is from production and might be minified, uglified or compressed.
        4. DO NOT modify class names
        5. DO NOT remove any comments already in the code.
        6. DO NOT change any styles or functionalities of the code.
        7. DO NOT change the structure of the code.
        8. DO NOT change the order of the code.
        9. DO NOT remove critical elements.
        10. If any optimizations are made, return `<!-- Optimized by LLM -->` at the beginning point of only the changed portion
           and `<!-- End of Optimization: {{audit_key of issue being resolved}} => {{one line short description of elements/things resolved}} -->` at the end of the changed portion. 
           Do not indicate any resolution outside of the End of Optimization comment, where there are multiple resolutions being made, seperate them with commas within the End of optimization comment.
        11. Return the modified HTML code alone, making only necessary changes for performance optimization.
        12. If no optimizations are possible, return the original code.
        13. Never add any additional comments to the code besides that of the instruction in #7.
        14. If the change is within a `<style>` tag, replace the HTML comment with a CSS comment.

        The original HTML code is as follows:

        ```html
        {html_part}
        ```
        """

        if only_return_prompt:
            return prompt   

        prompt_uuid = self.store_prompt(prompt, audit_key)

        try:
            start_time = time.time()

            response = self.chatgpt_response_with_backoff(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=MAX_LIMIT        
            )

            end_time = time.time()
            
            self.store_response_time(start_time, end_time, prompt_uuid, self.estimate_tokens(prompt), audit_key)

        except Exception as e:
            print(e)
            return html_part

        # sleep for 1 or 2 seconds to avoid hitting the rate limit
        sleep(random.uniform(1, 2))

        response_content = ""
        try:
            # check reason for completition - if not "stop" then log error (stop means completed successfully)

            finish_reason = response.choices[0].finish_reason
            if finish_reason != 'stop':
                self.log_error(prompt_uuid, finish_reason, {
                    "trace": response
                })

            else:
                response_content = response.choices[0].message.content
                
                # save_tokens_usage(prompt, self.api_key, self.estimate_tokens)

                response_content = self.parse_chatgpt_response(response_content)

                no_of_modifications = response_content.count("<!-- Optimized by LLM -->")
                self.no_of_modifications += no_of_modifications
        except Exception as e:
            print(f"Error: {e}")
            self.log_error(prompt_uuid, "No finish reason", {
                "trace": response
            })
            response_content = html_part
        
        return response_content
            
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(4))
    def chatgpt_response_with_backoff(self, **kwargs):

        client = OpenAI(
            api_key=self.api_key
        )

        return client.chat.completions.create(**kwargs)
    
    def parse_chatgpt_response(self, response: str):
        # Parse the response from the ChatGPT API call to get the code snippet
        # Right now, I ask ChatGPT to only return code, but it may not always be the case so I have to ensure that what I am parsing is actually code.
        # Right now I am not using this function yet. Just taking the raw output for testing. 

        parsed_response = re.sub(r'```html', '', response)
        parsed_response = re.sub(r'```', '', parsed_response)
        
        return parsed_response
    
    def log_error(self, prompt_uuid: int, finish_reason: str, trace=None):
        log_name = f"error_{self.dom_name}_{self.experiment_name}_{self.mode}.log"

        error_file_path = os.path.join(os.getcwd(), f"{log_name}")

        with open(error_file_path, 'a') as file:
            file.write(f"{prompt_uuid}, {finish_reason}, {trace}\n")


    def modify_html_with_llm(self, audit_issue, audit_key=None):
        chunker = HTMLChunker(self.html, TOKEN_LIMIT)
        
        # Split the entire document into chunks
        chunks = chunker.split_html()

        # Store original chunks
        original_chunks_path = f"chunked-doms/original/{self.experiment_name}"
        os.makedirs(original_chunks_path, exist_ok=True)

        chunks = chunker.store_chunks(chunks, f"{original_chunks_path}/{self.dom_name}")

        # Iterate through each chunk, send it to the LLM, and replace it in the soup
        chunk_json = {}
        current_chunks = chunks

        style_store = next((item for item in chunks if item["id"] == "style_store"), None)
        script_store = next((item for item in chunks if item["id"] == "script_store"), None)

        chunk_count = len(chunks)
        if style_store: chunk_count -= 1
        if script_store: chunk_count -= 1

        for i, chunk in enumerate(chunks):
            if chunk['id'] != 'style_store' and chunk['id'] != 'script_store':
                print(f"Processing chunk {i+1}/{chunk_count} with {chunker.estimate_tokens(str(chunk['content']))} tokens...")
                modified_chunk = self.send_to_llm(chunk['content'], audit_issue, audit_key, self.only_estimate_tokens)
                # modified_chunk = chunk['content']

                current_chunks = chunker.modify_chunk(current_chunks, chunk['id'], modified_chunk)
                
                chunk_json[i] = {
                    "name": self.dom_name,
                    "experiment_name": self.experiment_name,
                    "audit_key": audit_key,
                    "dom_name": self.dom_name,
                    "original_chunk_id": chunk['id'],
                    "mode": self.mode,
                    "original": chunk['content'],
                    "original_section": chunk['section'],
                    "original_chunk_token_size": chunker.estimate_tokens(str(chunk['content'])),
                    "modified": modified_chunk,
                    "modified_chunk_token_size": chunker.estimate_tokens(str(modified_chunk))
                }
            else:
                print(f"Skipping {chunk['id']} chunk...")

        # Store modified chunks
        modified_chunk_path = f"chunked-doms/modified/{self.experiment_name}"
        os.makedirs(modified_chunk_path, exist_ok=True)

        chunker.store_chunks(chunk_json, f"{modified_chunk_path}/{self.dom_name}", True)

        # Add style and script stores for remapping later
        if style_store is not None: current_chunks.append(style_store)
        if script_store is not None: current_chunks.append(script_store)

        # Reassemble the modified HTML
        modified_html = chunker.reassemble_html(current_chunks)
        
        return modified_html
    
    @staticmethod
    def get_audit_issues(dom_name):
        audit_file = f"lh-reports/original/audits/{dom_name}.json"

        with open(audit_file, 'r') as file:
            audit_data = json.load(file)
        
        return audit_data

    def formatted_audits(self, audits, with_location=False):
        formatted_audit = ""

        for index, (audit_key, audit_value) in enumerate(audits.items()):
            audit_title = audits[audit_key]['title']
            audit_description = audits[audit_key]['description']

            formatted_audit += f"""
            {index + 1}. {audit_key} => {audit_title}: {audit_description}\n \n
            """

            if with_location:
                formatted_audit += f"Location: {audits[audit_key]['location']}\n \n"

        return formatted_audit

    def estimate_tokens(self, text):
        """
        Returns the number of tokens in the element using gpt4-o encoder and tiktoken
        """
        encoding = tiktoken.get_encoding("o200k_base")

        tokens = encoding.encode(text)

        return len(tokens)
    
    def clear_storage(self):
        os.system("rm -rf chunked-doms")
        os.system("rm -rf modified-doms")
        os.system("rm -rf prompts")
        os.system("rm -rf response_times")
        os.system("rm -rf error_*.log")
        os.system("rm -rf modifications.json")
        os.system("rm -rf modifications_single.json")
        os.system("rm -rf modifications")
        os.system("rm -rf modifications_single")

        print("Storage cleared.")

    def save_modified_files(self, modified_html, audit_key=None):
        modified_dom_path = f"modified-doms/{self.experiment_name}" if self.mode == "all" else f"modified-doms/{self.experiment_name}/single"
        modified_dom_filename = f"{modified_dom_path}/{self.dom_name}.html" if self.mode == "all" else f"{modified_dom_path}/{self.dom_name}_{audit_key}.html"
        
        os.makedirs(modified_dom_path, exist_ok=True)

        with open(modified_dom_filename, 'w') as file:
            file.write(modified_html)

    def save_modifications(self, audit_key=None): 
        modifications = []
        modifications_path = f"modifications" if self.mode == "all" else f"modifications_single"
        modifications_filename = f"{modifications_path}/{self.experiment_name}.json" if self.mode == "all" else f"{modifications_path}/{self.experiment_name}.json"

        os.makedirs(modifications_path, exist_ok=True)

        if os.path.exists(modifications_filename):
            with open(modifications_filename, 'r') as file:
                modifications = json.load(file)

        modification_tracker = {}
        modification_tracker['name'] = self.dom_name
        modification_tracker['modifications'] = self.no_of_modifications
        modification_tracker['no_of_issues'] = len(self.audits)
        modification_tracker['experiment_name'] = self.experiment_name
        modification_tracker['mode'] = self.mode
        if(self.mode == "single"):
            modification_tracker['audit_key'] = audit_key

        modifications.append(modification_tracker)

        with open(modifications_filename, 'w') as file:
            json.dump(modifications, file, indent=4)


def run_changes(html_modifier: HTMLModifier, lighthouse_audits, audit_key=None):
    lighthouse_audit_issue = html_modifier.formatted_audits(lighthouse_audits)

    modified_html = html_modifier.modify_html_with_llm(lighthouse_audit_issue, audit_key)

    if html_modifier.only_estimate_tokens:
        return
    
    html_modifier.save_modified_files(modified_html, audit_key)
    html_modifier.save_modifications(audit_key)


# # Example of usage:
# if __name__ == '__main__':
#     # check if command has optional --clear flag
#     if len(sys.argv) > 1:
#         if sys.argv[1] == "--clear":
#             html_modifier = HTMLModifier("", "")
#             html_modifier.clear_storage()
#             exit()
#         elif sys.argv[1] == "--describe":
#             mode = None
#             experiment_name = None
#             if len(sys.argv) > 2:
#                 mode = sys.argv[2].split('=')[1]

#             if len(sys.argv) > 3:
#                 # argument has to be in the format --experiment-name=experiment_name, then extract everything after the =
#                 experiment_name = sys.argv[3].split('=')[1]
#                 if experiment_name is None:
#                     print("Please provide an experiment name.")
#                     exit()
                
#             if mode is None:
#                 print("Please provide a mode.")
#                 exit()

#             experiments = ['airbnb', 'aliexpress', 'ebay', 'facebook', 'github', 'linkedin', 'medium', 'netflix', 'pinterest', 'quora', 'reddit', 'twitch', 'twitter', 'walmart', 'youtube']

#             all_experiment_details = []
#             for experiment in experiments:
#                 html_file = f"extracted-doms/original/{experiment}.html"
#                 with open(html_file, 'r') as file:
#                     original_html = file.read()

#                     html_modifier = HTMLModifier(original_html, experiment)
#                     html_modifier.mode = mode
#                     html_modifier.only_estimate_tokens = True
#                     html_modifier.get_audit_issues()
#                     experiment_details = html_modifier.get_experiment_details()

#                     all_experiment_details.append(experiment_details)

#                     os.makedirs(f"experiment_details/{experiment_name}", exist_ok=True)
                    
#                     with open(f"experiment_details/{experiment_name}/{experiment}.json", 'w') as file:
#                         json.dump(experiment_details, file, indent=4)

#             experiments_summary = {
#                 "mode": mode,
#                 "no_of_experiments": len(experiments),
#                 "no_of_prompts": sum([experiment['no_of_prompts'] for experiment in all_experiment_details]),
#                 "total_tokens": sum([experiment['total_tokens'] for experiment in all_experiment_details]),
#             }

#             with open(f"experiment_details/{experiment_name}/_summary.json", 'w') as file:
#                 json.dump(experiments_summary, file, indent=4)
#             exit()

#     html_file = "extracted-doms/original/youtube.html"

#     files_to_exclude = ['amazon', 'ubereats', 'glassdoor', 'ziprecruiter', 'behance']
#     audits_to_exclude = []

#     if any(exclude in html_file for exclude in files_to_exclude):
#         print(f"Skipping {html_file}...")
#         exit()

#     with open(html_file, 'r') as file:
#         original_html = file.read()

#     # Example Lighthouse audit issue
#     lighthouse_audit_issue = ""

#     html_name = os.path.basename(html_file).split('.')[0]
#     html_modifier = HTMLModifier(original_html, html_name)

#     lighthouse_audits = html_modifier.get_audit_issues()

#     if lighthouse_audits and html_modifier.mode == "all":
#         print("Starting HTML all modifications...")

#         run_changes(html_modifier, lighthouse_audits)

#         print("HTML modifications completed and saved.")
#     elif lighthouse_audits and html_modifier.mode == "single":
#         audit_count = len(lighthouse_audits)
#         print(f"Starting HTML single audit modifications for {audit_count} audits...")

#         for audit in lighthouse_audits:
#             print(f"Starting HTML single audit modifications for {audit}...")

#             run_changes(html_modifier, {audit: lighthouse_audits[audit]}, audit)
        
#         print("HTML modifications completed and saved.")
#     else:
#         print("No audits to be resolved.")
        