from bs4 import BeautifulSoup, Tag
import requests
import tiktoken
import json

def estimate_tokens(text):
        """
        Returns the number of tokens in the element using gpt4 encoder and tiktoken
        """
        encoding = tiktoken.get_encoding("o200k_base")

        tokens = encoding.encode(text)

        return len(tokens)

def chunk_html(html_content, max_tokens=15000):
    soup = BeautifulSoup(html_content, 'html.parser')
    chunks = []
    current_chunk = []
    current_tokens = 0

    def format_attributes(tag):
        formatted_attrs = []
        for k, v in tag.attrs.items():
            if isinstance(v, str):
                # Check if it's a JSON-like structure and avoid modifying it
                try:
                    # Attempt to parse as JSON
                    json_val = json.loads(v)
                    # If successful, re-serialize it as a valid JSON string
                    formatted_attrs.append(f'{k}=\'{json.dumps(json_val)}\'')
                except json.JSONDecodeError:
                    # If not valid JSON, leave the value as it is
                    formatted_attrs.append(f'{k}="{v}"')
            else:
                # Handle cases where the value is not a string
                formatted_attrs.append(f'{k}="{" ".join(v)}"')

        return ' '.join(formatted_attrs)

    def process_element(element, depth=0):
        nonlocal current_chunk, current_tokens
        
        if isinstance(element, Tag):
            opening_tag = str(element.name)
            if element.attrs:
                attrs = format_attributes(element)
                opening_tag += f" {attrs}"
            
            tokens = estimate_tokens(f"<{opening_tag}>")
            if current_tokens + tokens > max_tokens and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(f"<{opening_tag}>")
            current_tokens += tokens
            
            for child in element.children:
                process_element(child, depth + 1)
            
            closing_tag = f"</{element.name}>"
            tokens = estimate_tokens(closing_tag)
            if current_tokens + tokens > max_tokens:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(closing_tag)
            current_tokens += tokens
        else:
            text = str(element)
            tokens = estimate_tokens(text)
            if current_tokens + tokens > max_tokens:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                current_chunk = []
                current_tokens = 0
                
                # If a single text element exceeds max_tokens, split it
                if tokens > max_tokens:
                    words = text.split()
                    temp_chunk = []
                    temp_tokens = 0
                    for word in words:
                        word_tokens = estimate_tokens(word + ' ')
                        if temp_tokens + word_tokens > max_tokens:
                            chunks.append(''.join(temp_chunk))
                            temp_chunk = []
                            temp_tokens = 0
                        temp_chunk.append(word + ' ')
                        temp_tokens += word_tokens
                    if temp_chunk:
                        current_chunk = temp_chunk
                        current_tokens = temp_tokens
                else:
                    current_chunk.append(text)
                    current_tokens = tokens
            else:
                current_chunk.append(text)
                current_tokens += tokens

    process_element(soup.html)
    if current_chunk:
        chunks.append(''.join(current_chunk))
    
    return chunks

def process_with_llm(chunk):
    # This is a placeholder for the actual LLM processing
    # In a real scenario, you would send the chunk to your LLM and get the processed result
    return chunk # Simple lowercase transformation as an example

def merge_chunks(processed_chunks):
    merged = ''.join(processed_chunks)
    soup = BeautifulSoup(merged, 'html.parser')
    return str(soup)



# Example usage
url = "https://youtube.com"  # Replace with your HTML source
response = requests.get(url)
html_content = response.text

chunks = chunk_html(html_content)
processed_chunks = [process_with_llm(chunk) for chunk in chunks]
merged_html = merge_chunks(processed_chunks)

with open("merged.html", "w") as f:
    merged_html = BeautifulSoup(merged_html, 'html.parser').prettify()
    f.write(merged_html)

with open("omo_chunks.json", "w") as f:
    json.dump(chunks, f, indent=4)

print(f"Number of chunks: {len(chunks)}")
print(f"Merged HTML length: {len(merged_html)}")