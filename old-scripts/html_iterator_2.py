import os
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict
import tiktoken
import json

class HTMLChunker:
    def __init__(self, html_file: str, max_tokens: int = 15000):
        self.html_file = html_file
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.soup = None
        self.load_html()

    def load_html(self):
        with open(self.html_file, 'r', encoding='utf-8') as file:
            self.soup = BeautifulSoup(file, 'html.parser')

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def get_position(self, element) -> str:
        if element.name == 'html':
            return 'html'
        if element.name == 'head':
            return 'head'
        if element.name == 'body':
            return 'body'

        siblings = element.find_previous_siblings()
        index = len(siblings) + 1
        parent_position = self.get_position(element.parent)
        return f"{parent_position} > {element.name}:nth-child({index})"

    def chunk_element(self, element, depth: int = 0) -> List[Tuple[str, str, int]]:
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for child in element.children:
            if child.name is None:
                text = child.strip()
                if text:
                    tokens = self.count_tokens(text)
                    if current_tokens + tokens > self.max_tokens:
                        if current_chunk:
                            chunks.append((self.get_position(element), current_chunk, current_tokens))
                        current_chunk = text
                        current_tokens = tokens
                    else:
                        current_chunk += text
                        current_tokens += tokens
            else:
                child_html = str(child)
                child_tokens = self.count_tokens(child_html)

                if child_tokens > self.max_tokens:
                    if current_chunk:
                        chunks.append((self.get_position(element), current_chunk, current_tokens))
                        current_chunk = ""
                        current_tokens = 0
                    chunks.extend(self.chunk_element(child, depth + 1))
                elif current_tokens + child_tokens > self.max_tokens:
                    chunks.append((self.get_position(element), current_chunk, current_tokens))
                    current_chunk = child_html
                    current_tokens = child_tokens
                else:
                    current_chunk += child_html
                    current_tokens += child_tokens

        if current_chunk:
            chunks.append((self.get_position(element), current_chunk, current_tokens))

        return chunks

    def chunk_html(self) -> List[Dict[str, any]]:
        head_chunks = self.chunk_element(self.soup.head)
        body_chunks = self.chunk_element(self.soup.body)
        all_chunks = head_chunks + body_chunks

        return [
            {
                "position": position,
                "content": content,
                "tokens": tokens
            }
            for position, content, tokens in all_chunks
        ]

    def apply_changes(self, changes: List[Dict[str, any]]):
        for change in changes:
            position = change['position']
            new_content = change['content']
            
            # Find the element using the position
            selector = ' > '.join([part.split(':')[0] for part in position.split(' > ')])
            element = self.soup.select_one(selector)
            
            if element:
                # Replace the content of the element
                element.clear()
                element.append(BeautifulSoup(new_content, 'html.parser'))
            else:
                print(f"Element not found at position: {position}")

        # Save the modified HTML
        with open(self.html_file, 'w', encoding='utf-8') as file:
            file.write(str(self.soup))

def main():
    html_file = "extracted-doms/original/airbnb.html"
    chunker = HTMLChunker(html_file)
    chunks = chunker.chunk_html()

    # store chunks to json file
    with open("new_chunks.json", 'w') as f:
        json.dump(chunks, f, indent=4)

    # Example of how you might use the chunks with an LLM
    # for chunk in chunks:
        # Send chunk to LLM and get changes
        # This is a placeholder for the actual LLM interaction
        # changes = process_with_llm(chunk)
        
        # Apply the changes
        # chunker.apply_changes([changes])

def process_with_llm(chunk):
    # This is a placeholder function for LLM processing
    # In a real scenario, you would send the chunk to an LLM and get the changes
    # For this example, we'll just return the chunk as is
    return {
        "position": chunk["position"],
        "content": chunk["content"]
    }

if __name__ == "__main__":
    main()