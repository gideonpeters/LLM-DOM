import os
import re
from time import sleep
from openai import OpenAI
import pandas as pd
import random
import difflib
import json
import tiktoken
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
from html_iterator import HTMLIterator
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = "gpt-4o-mini"

class Programmer:
    def program(self, dom_tree: str, audit: str) -> str:
        #Programmer's main method. Takes a question and returns a code snippet.
        #Should be implemented by child classes.
        raise NotImplementedError()

class PythonProgrammer(Programmer):
    def __init__(
            self,
            model: str,
            temperature: float,
            max_tokens: int,

    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    
    def program(self, dom_name: str, dom_tree: str, audit: str) -> str:
        prompt = self._generate_prompt(dom_tree=dom_tree, audit=audit)

        response = self._chatgpt_response_with_backoff(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        #sleep for 1 or 2 seconds to avoid hitting the rate limit
        sleep(random.uniform(1, 2))

        response_content = ""

        try:
            #check reason for completition - if not "stop" then log error (stop means completed successfully)
            finish_reason = response['choices'][0]['finish_reason']
            if finish_reason != 'stop':
                self._log_error(dom_name, finish_reason)

            else:
                response_content = response['choices'][0]['message']['content']
                response_content = self._parse_chatgpt_response(response_content)
        except:
            self._log_error(dom_name, "No finish reason")
        
        return response_content

    # exponential backoff decorator for the ChatGPT API call
    # source: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_handle_rate_limits.ipynb
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(4))
    def _chatgpt_response_with_backoff(self, **kwargs):
        client = OpenAI(
            api_key=api_key
        )

        return client.chat.completions.create(**kwargs)
    
    #THIS IS TO PARSE PYTHON CODE, YOU DON'T HAVE TO USE THIS. 
    def _parse_chatgpt_response(self, response: str):
        # Parse the response from the ChatGPT API call to get the code snippet
        # Right now, I ask ChatGPT to only return code, but it may not always be the case so I have to ensure that what I am parsing is actually code.
        # Right now I am not using this function yet. Just taking the raw output for testing. 

        parsed_response = re.sub(r'```python', '', response)
        parsed_response = re.sub(r'```', '', parsed_response)
        
        return parsed_response

    #CHANGE YOUR PROMPT HERE
    def _generate_prompt(self, dom_tree=None, audit=None) -> str:
        if dom_tree is None or audit is None:
            return ""
            # raise ValueError("DOM tree or audit is None")
        
        prompt = f"""
                    The following DOM tree is one from a production website, 
                    it has probably been minified, transpiled and uglified.
                    After running a performance analysis on it using 
                    Lighthouse, we obtain audits.
                    Improve the performance without changing the 
                    styles or scripts, using the audit below and
                    return the modified DOM tree, the output should only contain code. No explanation:

                    DOM Tree: ```{dom_tree}```

                    Audit: ```{audit}```
                  """
        
        return prompt
    
    def _log_error(self, dom_name: int, finish_reason: str):
        error_file_path = os.path.join(os.getcwd(), "error.log")

        with open(error_file_path, 'a') as file:
            file.write(f"{dom_name}, {finish_reason}\n")

    @staticmethod
    def _count_tokens(itext: str):
        try:
            encoding = tiktoken.get_encoding("cl100k_base")

            tokens = encoding.encode(itext)

            return len(tokens)
        except Exception as e:
            print(f"Error in token count: {e}")

            return 5000000

    def _split_dom_into_chunks(self, dom_tree: str) -> list:
        # Split the DOM tree into chunks of 90,000 tokens
        # The maximum token limit for the GPT-3 API is 90,000 tokens
        # So, we need to split the input into chunks of 90,000 tokens or less
        # The chunk size is set to 90,000 tokens to account for the additional tokens in the prompt
        # Split it in a way that elements do are not clipped, if the current chunk ends in the middle of an element, move back to the last full element.
        # Chunk should be a text chunk, not an array of elements.
        chunk_size = 90000
        chunks = []


if __name__ == "__main__":
    dom_trees_path = "extracted-doms/original"

    #CHANGE PARAMS AS NEEDED. 
    programmer = PythonProgrammer(model, 0.7, 16000)

    filenames = sorted(os.listdir(dom_trees_path))

    for filename in filenames:
        if filename.endswith(".html"):
            dom_path = os.path.join(dom_trees_path, filename)
            
            dom_name = os.path.splitext(filename)[0]
            dom_tree = ""
            with open(dom_path, 'r') as file:
                dom_tree = file.read()

            if not dom_tree:
                continue

            html_iterator = HTMLIterator(dom_tree)

            element, path = html_iterator.get_next_element()
            if element is None:
                break
            print(f"Element path: {path}")
            # print(f"Element HTML: {element}")
            print("----")

            # audit_path = os.path.join("lh-reports/original/audits", f"{dom_name}.json")

            # if not os.path.exists(audit_path):
            #     print(f"Audit file not found for {dom_name}, skipping...")
            #     continue

            # audits = {}
            # with open(audit_path, 'r') as file:
            #     audits = json.load(file)
            
            # for audit_key, audit in audits.items():

            #     output = programmer.program(dom_name, dom_tree, audit)

            #     if not output:
            #         continue

            #     output_path = os.path.join("extracted-doms/llm-modified-v2", f"{dom_name}_{audit_key}.html")

            #     with open(output_path, 'w') as file:
            #         file.write(output)
                
                # break
        
        
print("Text files created successfully.")
