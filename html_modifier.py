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
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TOKEN_LIMIT = 12000
MAX_LIMIT = 16100

class HTMLSplitter:
    def __init__(self, html, dom_name):
        self.html = html
        self.max_tokens = TOKEN_LIMIT
        self.model = "gpt-4o-mini"
        self.dom_name = dom_name
        self.no_of_modifications = 0
        self.temperature = 0.2
        self.mode = "all"
        self.audits = {}
        self.formatted_audits = ""

    def measure_speed():
        st = speedtest.Speedtest()
        
        st.get_best_server()
        
        download_speed = st.download()  
        upload_speed = st.upload()  # in bits per second
        ping = st.results.ping  # in milliseconds

        # Convert speeds to Mbps
        download_speed_mbps = download_speed / 1_000_000
        upload_speed_mbps = upload_speed / 1_000_000

        print(f"Download Speed: {download_speed_mbps:.2f} Mbps")
        print(f"Upload Speed: {upload_speed_mbps:.2f} Mbps")
        print(f"Ping: {ping:.2f} ms")

        return {
            "download_speed": download_speed_mbps,
            "upload_speed": upload_speed_mbps,
            "ping": ping
        }

    def send_to_llm(self, html_part, audit_issues, audit_key=None):
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
        1. Return the modified HTML code alone, making only necessary changes for performance optimization.
        2. If no optimizations are possible, return the original code.
        3. Do not modify class names
        4. If any optimizations are made, return `<!-- Optimized by LLM -->` at the beginning point of only the changed portion
           and `<!-- End of Optimization: {{one line short description of elements/things fixed}} -->` at the end of the changed portion.
        5. If the change is within a `<style>` tag, replace the HTML comment with a CSS comment.
        6. Because the code is split into chunks, there might be some unclosed or cut elements, do not worry about that.
        7. Do not change any styles or functionalities of the code.
        8. Consider that a chunk might be a part of a larger element, so the code might not be complete.
        9. Consider that HTML as a whole is from production and might be minified, uglified or compressed.

        The original HTML code is as follows:

        ```html
        {html_part}
        ```
        """

        prompt_uuid = uuid4()
        prompt_path = f"prompts/new-prompts/{self.dom_name}" if self.mode == "all" else f"prompts/new-prompts/single/{self.dom_name}"
        prompt_filename = f"{prompt_path}/{prompt_uuid}.txt" if self.mode == "all" else f"{prompt_path}/{prompt_uuid}_{audit_key}.txt"

        os.makedirs(prompt_path, exist_ok=True)

        with open(prompt_filename, 'w') as file:
            file.write(prompt)

        try:
            start_time = time.time()

            response = self.chatgpt_response_with_backoff(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=MAX_LIMIT        
            )

            end_time = time.time()
            duration = end_time - start_time

            response_times = []
            response_time_path = f"prompts/response_times" if self.mode == "all" else f"prompts/response_times/single/{self.dom_name}"
            response_time_filename = f"{response_time_path}/{self.dom_name}.json" if self.mode == "all" else f"{response_time_path}/{self.dom_name}_{audit_key}.json"

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
                "chunk_size": self.estimate_tokens(prompt),
                "duration": duration
            })

            # Write updated data back to the file
            with open(response_time_filename, 'w') as file:
                json.dump(response_times, file, indent=4)

        except Exception as e:
            print(e)
            return ""

        #sleep for 1 or 2 seconds to avoid hitting the rate limit
        sleep(random.uniform(1, 2))

        response_content = ""
        try:
            # check reason for completition - if not "stop" then log error (stop means completed successfully)

            finish_reason = response.choices[0].finish_reason
            if finish_reason != 'stop':
                self.log_error(self.dom_name, finish_reason)

            else:
                response_content = response.choices[0].message.content
                response_content = self.parse_chatgpt_response(response_content)

                no_of_modifications = response_content.count("<!-- Optimized by LLM -->")
                self.no_of_modifications += no_of_modifications
        except Exception as e:
            print(f"Error: {e}")
            self.log_error(self.dom_name, "No finish reason",e, response)
        
        return response_content
            
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(4))
    def chatgpt_response_with_backoff(self, **kwargs):
        client = OpenAI(
            api_key=OPENAI_KEY
        )

        return client.chat.completions.create(**kwargs)
    
    def parse_chatgpt_response(self, response: str):
        # Parse the response from the ChatGPT API call to get the code snippet
        # Right now, I ask ChatGPT to only return code, but it may not always be the case so I have to ensure that what I am parsing is actually code.
        # Right now I am not using this function yet. Just taking the raw output for testing. 

        parsed_response = re.sub(r'```html', '', response)
        parsed_response = re.sub(r'```', '', parsed_response)
        
        return parsed_response
    
    def log_error(self, dom_name: int, finish_reason: str, trace=None):
        error_file_path = os.path.join(os.getcwd(), "new_error.log")

        with open(error_file_path, 'a') as file:
            file.write(f"{dom_name}, {finish_reason}, {trace}\n")

    def modify_html_with_llm(self, audit_issue, audit_key=None):
        chunker = HTMLChunker(self.html, TOKEN_LIMIT)
        
        # Split the entire document into chunks
        chunks = chunker.split_html()

        original_chunk_path = f"prompts/original-chunks/{self.dom_name}"
        original_chunk_filename = f"{original_chunk_path}/{self.dom_name}.json"

        os.makedirs(original_chunk_path, exist_ok=True)

        with open(original_chunk_filename, 'w') as file:
            json.dump(chunks, file, indent=4)
        
        # Iterate through each chunk, send it to the LLM, and replace it in the soup
        modified_chunks = []
        chunk_json = {}
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} with {chunker.estimate_tokens(str(chunk))} tokens...")

            modified_chunk = self.send_to_llm(chunk['content'], audit_issue, audit_key)

            chunker.modify_chunk(chunk['id'], modified_chunk)
            modified_chunks.append(modified_chunk)
            
            chunk_json[i] = {
                "name": self.dom_name,
                "original": chunk,
                "original_chunk_size": chunker.estimate_tokens(str(chunk)),
                "modified": modified_chunk,
                "modified_chunk_size": chunker.estimate_tokens(str(modified_chunk))
            }

            modified_chunk_path = f"prompts/modified-chunks/{self.dom_name}"
            modified_chunk_filename = f"{modified_chunk_path}/{self.dom_name}.json"

            os.makedirs(modified_chunk_path, exist_ok=True)

            with open(modified_chunk_filename, 'w') as file:
                json.dump(chunk_json, file, indent=4)

        modified_html = chunker.reassemble_html()
        
        return modified_html
    
    def get_audit_issues(self):
        audit_file = f"lh-reports/original/audits/{self.dom_name}.json"

        with open(audit_file, 'r') as file:
            audit_data = json.load(file)
        
        self.audits = audit_data

        return audit_data

    def formatted_audits(self, audits, with_location=False):
        formatted_audit = ""

        for index, (audit_key, audit_value) in enumerate(audits.items()):
            audit_title = audits[audit_key]['title']
            audit_description = audits[audit_key]['description']

            formatted_audit += f"""
            {index + 1}. {audit_title}: {audit_description}\n \n
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


def run_changes(html_splitter: HTMLSplitter, lighthouse_audits, audit_key=None):
    lighthouse_audit_issue = html_splitter.formatted_audits(lighthouse_audits)

    modifications = []
    modifications_filename = "modifications.json" if html_splitter.mode == "all" else "modifications_single.json"

    if os.path.exists(modifications_filename):
        with open(modifications_filename, 'r') as file:
            modifications = json.load(file)

    modified_html = html_splitter.modify_html_with_llm(lighthouse_audit_issue, audit_key)

    # Save the modified HTML back to a file
    modified_dom_path = "modified-doms" if html_splitter.mode == "all" else "modified-doms/single"
    modified_dom_filename = f"{modified_dom_path}/{html_splitter.dom_name}.html" if html_splitter.mode == "all" else f"{modified_dom_path}/{html_splitter.dom_name}_{audit_key}.html"
    
    os.makedirs(modified_dom_path, exist_ok=True)

    with open(modified_dom_filename, 'w') as file:
        file.write(modified_html)

    modification_tracker = {}
    modification_tracker['name'] = html_splitter.dom_name
    modification_tracker['modifications'] = html_splitter.no_of_modifications
    if(html_splitter.mode == "single"):
        modification_tracker['audit_key'] = audit_key

    modifications.append(modification_tracker)

    with open(modifications_filename, 'w') as file:
        json.dump(modifications, file, indent=4)


# Example of usage:
if __name__ == '__main__':
    html_file = "extracted-doms/original/netflix.html"

    with open(html_file, 'r') as file:
        original_html = file.read()

    # Example Lighthouse audit issue
    lighthouse_audit_issue = ""

    html_name = os.path.basename(html_file).split('.')[0]
    html_splitter = HTMLSplitter(original_html, html_name)
    lighthouse_audits = html_splitter.get_audit_issues()

    if lighthouse_audits and html_splitter.mode == "all":
        run_changes(html_splitter, lighthouse_audits)
        print("HTML modifications completed and saved.")

    elif lighthouse_audits and html_splitter.mode == "single":
        for audit in lighthouse_audits:
            run_changes(html_splitter, {audit: lighthouse_audits[audit]}, audit)
        
        print("HTML modifications completed and saved.")
    else:
        print("No audits to be fixed.")
        