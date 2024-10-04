from bs4 import BeautifulSoup, Tag
import tiktoken
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
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TOKEN_LIMIT = 15000

class HTMLSplitter:
    def __init__(self, html, dom_name):
        self.html = html
        self.max_tokens = TOKEN_LIMIT
        self.model = "gpt-4o-mini"
        self.dom_name = dom_name
        self.temperature = 0.2

    def send_to_llm(self, html_part, audit_issue):
        prompt = f"""
        You are a web performance expert. 
        Based on the following Lighthouse audit issue: "{audit_issue}",
        please modify this HTML code to resolve the performance issue:

        Return the modified HTML code alone, 
        making only necessary changes for performance optimization. 
        If no optimizations are possible, return the original code.

        The original HTML code is as follows:

        {html_part}

        """
        
        # Send the prompt to the LLM (adjust for the LLM you're using)
         
        response = self.chatgpt_response_with_backoff(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens        
        )

        #sleep for 1 or 2 seconds to avoid hitting the rate limit
        sleep(random.uniform(1, 2))

        response_content = ""
        try:
            #check reason for completition - if not "stop" then log error (stop means completed successfully)
            finish_reason = response['choices'][0]['finish_reason']
            if finish_reason != 'stop':
                self.log_error(self.dom_name, finish_reason)

            else:
                response_content = response['choices'][0]['message']['content']
                response_content = self.parse_chatgpt_response(response_content)
        except:
            self.log_error(self.dom_name, "No finish reason", response)
        
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

    def split_html_into_chunks(self, node, token_limit):
        chunks = []
        current_chunk = []
        current_tokens = 0

        def dfs(element):
            nonlocal current_chunk, current_tokens

            # Get text and token count of the element
            if isinstance(element, str):
                text = element.strip()
                tokens = self.estimate_tokens(text)
            else:
                text = str(element)
                tokens = self.estimate_tokens(text)

            # If a single element exceeds the token limit, break it down further
            if tokens > token_limit:
                if hasattr(element, 'children'):
                    for child in element.children:
                        dfs(child)
                return

            # If adding this element exceeds the limit, finalize the current chunk
            if current_tokens + tokens > token_limit:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0

            # Add element to current chunk
            current_chunk.append(element)
            current_tokens += tokens

            # Recurse into children if it's a Tag
            if hasattr(element, 'children'):
                for child in element.children:
                    dfs(child)

        # Start DFS traversal
        dfs(node)

        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # Function to serialize chunks back to HTML strings
    def serialize_chunks(self, chunks):
        serialized_chunks = []
        for chunk in chunks:
            serialized_html = ''.join(str(element) for element in chunk)
            serialized_chunks.append(serialized_html)
        return serialized_chunks


    def modify_html_with_llm(self, audit_issue):
        soup = BeautifulSoup(self.html, 'html.parser')
        
        # Split the entire document into chunks
        html_chunks = self.split_html_into_chunks(soup, TOKEN_LIMIT)

        serialized_chunks = self.serialize_chunks(html_chunks)

        with open("html_chunks_new.json", 'w') as file:
            json.dump(serialized_chunks, file, indent=4)
        
        # Iterate through each chunk, send it to the LLM, and replace it in the soup
        modified_chunks = []
        chunk_json = {}
        for i, chunk in enumerate(serialized_chunks):
            print(f"Processing chunk {i+1}/{len(serialized_chunks)} with {self.estimate_tokens(chunk)} tokens...")
            modified_chunk = self.send_to_llm(chunk, audit_issue)
            modified_chunks.append(modified_chunk)
            
            chunk_json[i] = {
                "name": self.dom_name,
                "original": chunk,
                "original_chunk_size": self.estimate_tokens(chunk),
                "modified": modified_chunk,
                "modified_chunk_size": self.estimate_tokens(modified_chunk)
            }

            with open(f"chunkerrrrr89.json", 'w') as file:
                json.dump(chunk_json, file, indent=4)

        
        # Join all modified parts back into the original structure
        modified_html = ''.join(modified_chunks)
        
        return modified_html


    def estimate_tokens(self, text):
        """
        Returns the number of tokens in the element using gpt3.5 encoder and tiktoken
        """
        encoding = tiktoken.get_encoding("cl100k_base")

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

    # Modify the HTML with the LLM based on the Lighthouse audit
    modified_html = html_splitter.modify_html_with_llm(lighthouse_audit_issue)

    # Save the modified HTML back to a file
    with open('most_modified_file.html', 'w') as file:
        file.write(modified_html)
    
    print("HTML modifications completed and saved.")

        