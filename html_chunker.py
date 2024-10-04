from bs4 import BeautifulSoup, NavigableString, Tag
import json
import uuid
import re
import tiktoken

class HTMLChunker:
    def __init__(self, html_content, chunk_size=1000):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.chunk_size = chunk_size
        self.chunks = []
        self.current_chunk = None
        self.current_size = 0

    def split_html(self):
        self.process_section(self.soup.head, 'head')
        self.process_section(self.soup.body, 'body')
        self.finish_current_chunk()
        return self.chunks
    
    def estimate_tokens(self, text):
        """
        Returns the number of tokens in the element using gpt3.5 encoder and tiktoken
        """
        encoding = tiktoken.get_encoding("o200k_base")

        tokens = encoding.encode(text)

        return len(tokens)

    def start_new_chunk(self, section):
        self.finish_current_chunk()
        self.current_chunk = {'id': str(uuid.uuid4()), 'section': section, 'content': ''}
        self.current_size = 0

    def finish_current_chunk(self):
        if self.current_chunk and self.current_chunk['content']:
            self.chunks.append(self.current_chunk)

    def add_to_chunk(self, content):
        if not self.current_chunk:
            raise ValueError("No current chunk to add to")
        self.current_chunk['content'] += content
        self.current_size += self.estimate_tokens(content)

    def process_section(self, section, section_name):
        if section is None:
            return

        self.start_new_chunk(section_name)

        for element in section.children:
            if isinstance(element, NavigableString):
                self.process_string(element)
            elif isinstance(element, Tag):
                self.process_tag(element)

    def process_string(self, string):
        string_content = str(string)
        if self.current_size + self.estimate_tokens(string_content) > self.chunk_size:
            self.start_new_chunk(self.current_chunk['section'])
        self.add_to_chunk(string_content)

    def process_tag(self, tag):
        opening_tag = str(tag.name)
        if tag.attrs:
            attr_str = ' '.join(f'{k}="{v}"' for k, v in tag.attrs.items())
            opening_tag += f' {attr_str}'
        opening_tag = f'<{opening_tag}>'
        closing_tag = f'</{tag.name}>'

        if self.current_size + self.estimate_tokens(opening_tag) + self.estimate_tokens(closing_tag) > self.chunk_size:
            self.start_new_chunk(self.current_chunk['section'])

        self.add_to_chunk(opening_tag)

        for child in tag.children:
            if isinstance(child, NavigableString):
                self.process_string(child)
            elif isinstance(child, Tag):
                self.process_tag(child)

        self.add_to_chunk(closing_tag)

    def to_json(self):
        return json.dumps(self.chunks, indent=2)

    def modify_chunk(self, chunk_id, modified_content):
        for chunk in self.chunks:
            if chunk['id'] == chunk_id:
                chunk['content'] = modified_content
                return True
        return False

    def reassemble_html(self):
        head_content = ''.join(chunk['content'] for chunk in self.chunks if chunk['section'] == 'head')
        body_content = ''.join(chunk['content'] for chunk in self.chunks if chunk['section'] == 'body')

        head_content = self.correct_comment_styles(head_content)
        body_content = self.correct_comment_styles(body_content)

        self.soup.head.clear()
        self.soup.head.append(BeautifulSoup(head_content, 'html.parser'))
        self.soup.body.clear()
        self.soup.body.append(BeautifulSoup(body_content, 'html.parser'))
        self.soup.prettify()

        return str(self.soup)
    
    def correct_comment_styles(self, content):
        # Function to replace comments within a matched tag
        def replace_comments_in_tag(match):
            tag_content = match.group(1)
            # Replace HTML comments with CSS comments
            tag_content = re.sub(r'<!--\s*LLM processed start\s*-->', '/* LLM processed start */', tag_content)
            tag_content = re.sub(r'<!--\s*LLM processed end\s*-->', '/* LLM processed end */', tag_content)
            return f'<style>{tag_content}</style>'

        # Correct comments in <style> tags
        content = re.sub(r'<style>(.*?)</style>', replace_comments_in_tag, content, flags=re.DOTALL)
        
        return content

# Example usage
html_content = """
<html>
<head>
    <title>Sample Page</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; }
    </style>
</head>
<body>
    <h1>Welcome to our website</h1>
    <p>This is a sample paragraph with some text.</p>
    <div>
        <p>Another paragraph inside a div.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
    </div>
    <div>
        <p>Another paragraph inside a div.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
    </div>
    <div>
        <p>Another paragraph inside a div.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
    </div>
    <div>
        <p>Another paragraph inside a div.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
    </div>
    <p>A final paragraph with more text to demonstrate splitting between elements.</p>
</body>
</html>
"""

# # 1. Store each chunk in a JSON
# chunker = HTMLChunker(html_content, chunk_size=100)
# chunks = chunker.split_html()
# json_chunks = chunker.to_json()

# with open("chunks_NEW8475.json", 'w') as f:
#     f.write(json_chunks)

# # 2. Send each chunk to an LLM to modify (simulated here)
# def simulate_llm_modification(chunk):
#     return f"<!-- LLM processed start -->\n{chunk}\n <!-- LLM processed end -->\n"

# for chunk in chunks:
#     modified_content = simulate_llm_modification(chunk['content'])
#     chunker.modify_chunk(chunk['id'], modified_content)

# # 3. Replace the modified chunks and reassemble the HTML document
# modified_html = chunker.reassemble_html()
# with open("modified_html_NEW8475.html", 'w') as f:
#     f.write(modified_html)