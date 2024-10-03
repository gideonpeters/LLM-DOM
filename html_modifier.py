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
from new_splitter import HTMLChunker
from uuid import uuid4
import time
import tiktoken
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
        self.temperature = 0.2

    def send_to_llm(self, html_part, audit_issues):
        prompt = f"""
        You are a web performance expert. 
        Based on the following Lighthouse audit issues: 
       
        __________________
        "{audit_issues}"
        __________________

        Due to the huge token size of HTML files, 
        You are given the HTML in chunks. 
        Please modify this HTML code chunk to resolve the performance issues given above.:

        1. Return the modified HTML code alone, making only necessary changes for performance optimization.
        2. If no optimizations are possible, return the original code.
        3. If any optimizations are made, return `<!-- Optimized by LLM -->` at the beginning point of only the changed portion and `<!-- End of Optimization -->` at the end of the changed portion.
        4. If the change is within a `<style>` tag, replace the HTML comment with a CSS comment.
        5. Because the code is split into chunks, there might be some unclosed or cut elements, do not worry about that.

        The original HTML code is as follows:

        ```html
        {html_part}
        ```

        """

        prompt_uuid = uuid4()
        with open(f"prompts/new-prompts/{self.dom_name}_{prompt_uuid}.txt", 'w') as file:
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
            try:
                with open("response_times.json", 'r') as file:
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
            with open("response_times.json", 'w') as file:
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


    def modify_html_with_llm(self, audit_issue):
        soup = BeautifulSoup(self.html, 'html.parser')

        chunker = HTMLChunker(self.html, TOKEN_LIMIT)
        
        # Split the entire document into chunks
        chunks = chunker.split_html()
        json_chunks = chunker.to_json()

        with open("NEW_HTML_CHUNKS.json", 'w') as file:
            json.dump(chunks, file, indent=4)
        
        # Iterate through each chunk, send it to the LLM, and replace it in the soup
        modified_chunks = []
        chunk_json = {}
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} with {chunker.estimate_tokens(str(chunk))} tokens...")

            modified_chunk = self.send_to_llm(chunk['content'], audit_issue)

            chunker.modify_chunk(chunk['id'], modified_chunk)
            modified_chunks.append(modified_chunk)
            
            chunk_json[i] = {
                "name": self.dom_name,
                "original": chunk,
                "original_chunk_size": chunker.estimate_tokens(str(chunk)),
                "modified": modified_chunk,
                "modified_chunk_size": chunker.estimate_tokens(str(modified_chunk))
            }

            with open(f"MODIFIED_CHUNKS.json", 'w') as file:
                json.dump(chunk_json, file, indent=4)

        # Join all modified parts back into the original structure
        # modified_html = ''.join(modified_chunks)

        modified_html = chunker.reassemble_html()
        # with open(f"modified-doms/{self.dom_name}.html", 'w') as file:
        #     file.write(modified_html)
        
        return modified_html
    
    def get_audit_issues(self, with_location=False):
        # Get audits from lh-reports/original/audits/{self.dom_name}.json
        audit_file = f"lh-reports/original/audits/{self.dom_name}.json"

        with open(audit_file, 'r') as file:
            audit_data = json.load(file)

        formatted_audit = ""

        for index, audit in audit_data.keys():
            audit_title = audit_data[audit]['title']
            audit_description = audit_data[audit]['description']

            formatted_audit += f"""
            {index + 1}. {audit_title}: {audit_description}\n \n
            """

            if with_location:
                formatted_audit += f"Location: {audit_data[audit]['location']}\n \n"

        return formatted_audit

    def estimate_tokens(self, text):
        """
        Returns the number of tokens in the element using gpt3.5 encoder and tiktoken
        """
        encoding = tiktoken.get_encoding("o200k_base")

        tokens = encoding.encode(text)

        return len(tokens)

# Example of usage:
if __name__ == '__main__':
    html_file = "extracted-doms/original/airbnb.html"

    with open(html_file, 'r') as file:
        original_html = file.read()

    # Example Lighthouse audit issue
    lighthouse_audit_issue = "Reduce unused JavaScript. The page loads unnecessary JavaScript code that slows down rendering."

    html_name = os.path.basename(html_file).split('.')[0]
    html_splitter = HTMLSplitter(original_html, html_name)
    lighthouse_audit_issue = html_splitter.get_audit_issues()

    # Modify the HTML with the LLM based on the Lighthouse audit
    modified_html = html_splitter.modify_html_with_llm(lighthouse_audit_issue)

    # Save the modified HTML back to a file
    with open(f'modified-doms/{html_name}.html', 'w') as file:
        file.write(modified_html)
    
    print("HTML modifications completed and saved.")