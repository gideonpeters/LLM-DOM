from bs4 import BeautifulSoup, NavigableString, Tag, Comment
import json
import uuid
import re
import tiktoken
import os

class HTMLChunker:
    def __init__(self, html_content, chunk_size=15000, filename=None):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.chunk_size = chunk_size
        self.chunks = []
        self.filename = None
        self.current_chunk = None
        self.current_size = 0
        self.script_store = {}
        self.style_store = {}
        self.attrs_store = {}

    def split_html(self):
        self.process_section(self.soup.head, 'head')
        self.process_section(self.soup.body, 'body')
        self.finish_current_chunk()


        # with open("test.json", 'w') as f:
        #     f.write(json.dumps(self.attrs_store, indent=2))
        return self.chunks
    
    def estimate_tokens(self, text):
        """
        Returns the number of tokens in the element using gpt4 encoder and tiktoken
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
            if isinstance(element, Comment):
                self.process_comment(element)
            elif isinstance(element, NavigableString):
                self.process_string(element)
            elif isinstance(element, Tag):
                self.process_tag(element)

    def process_string(self, string):
        string_content = str(string)
        if self.current_size + self.estimate_tokens(string_content) > self.chunk_size:
            self.start_new_chunk(self.current_chunk['section'])
        self.add_to_chunk(string_content)

    def process_comment(self, comment):
        comment_content = f"<!--{comment}-->"
        if self.current_size + self.estimate_tokens(comment_content) > self.chunk_size:
            self.start_new_chunk(self.current_chunk['section'])
        self.add_to_chunk(comment_content)

    def format_attributes(self, tag):
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

    def process_tag(self, tag):
        tag_uuid = str(uuid.uuid4())
        opening_tag = str(tag.name)

        if tag.name == 'script':
            self.script_store[tag_uuid] = tag.string
            opening_tag += f' data-chunk-uuid="{tag_uuid}"'
            tag.string = f"// chunk_script_{tag_uuid}\n"
        elif tag.name == 'style':
            self.style_store[tag_uuid] = tag.string
            opening_tag += f' data-chunk-uuid="{tag_uuid}"'
            tag.string = f"/* chunk_style_{tag_uuid} */\n"

        if tag.attrs:
            attr_str = self.format_attributes(tag)
            self.attrs_store[tag_uuid] = attr_str
            opening_tag += f' {attr_str}'
        opening_tag = f'<{opening_tag}>'
        closing_tag = f'</{tag.name}>'

        if self.current_size + self.estimate_tokens(opening_tag) + self.estimate_tokens(closing_tag) > self.chunk_size:
            self.start_new_chunk(self.current_chunk['section'])

        self.add_to_chunk(opening_tag)

        for child in tag.children:
            if isinstance(child, Comment):
                self.process_comment(child)
            elif isinstance(child, NavigableString):
                self.process_string(child)
            elif isinstance(child, Tag):
                self.process_tag(child)

        self.add_to_chunk(closing_tag)

    def to_json(self):
        return json.dumps(self.chunks, indent=2)

    def modify_chunk(self, chunks, chunk_id, modified_content):
        for chunk in chunks:
            if chunk['id'] == chunk_id:
                chunk['content'] = modified_content
        
        return chunks

    def reassemble_html(self, chunks=None):
        head_content = ''.join(chunk['content'] for chunk in chunks if chunk['section'] == 'head')
        body_content = ''.join(chunk['content'] for chunk in chunks if chunk['section'] == 'body')

        style_store_chunk = next((chunk for chunk in chunks if chunk['id'] == 'style_store'), None)
        script_store_chunk = next((chunk for chunk in chunks if chunk['id'] == 'script_store'), None)

        # head_content = self.correct_script_comments(head_content, True)
        # head_content = self.correct_comment_styles(head_content)

        # body_content = self.correct_script_comments(body_content)
        # body_content = self.correct_comment_styles(body_content)

        head_content = self.replace_styles(head_content, style_store_chunk['content'])
        head_content = self.replace_scripts(head_content, script_store_chunk['content'])
        body_content = self.replace_styles(body_content, style_store_chunk['content'])
        body_content = self.replace_scripts(body_content, script_store_chunk['content'])

        self.soup.head.clear()
        self.soup.head.append(BeautifulSoup(head_content, 'html.parser'))
        self.soup.body.clear()
        self.soup.body.append(BeautifulSoup(body_content, 'html.parser'))
        self.soup.prettify()

        return self.soup.prettify()
    
    def correct_comment_styles(self, content):
        # Function to replace comments within a matched tag
        def replace_comments_in_tag(match):
            tag_content = match.group(1)
            # Replace HTML comments with CSS comments <!-- Optimized by LLM -->
            tag_content = re.sub(r'<!--\s*Optimized by LLM\s*-->', '/* Optimized  */', tag_content)
            tag_content = re.sub(r'<!--\s*LLM processed end\s*-->', '/* LLM processed end */', tag_content)
            return f'<style>{tag_content}</style>'

        # Correct comments in <style> tags
        content = re.sub(r'<style>(.*?)</style>', replace_comments_in_tag, content, flags=re.DOTALL)
        
        return content

    def correct_script_comments(self, content, is_head=False):
        # Function to replace comments within a matched tag
        def replace_comments_in_tag(match):
            tag_content = match.group(1)
            # Replace HTML comments with CSS comments
            start_replacement = '// LLM processed start' if is_head else '<!-- LLM processed start -->'
            end_replacement = '// LLM processed end' if is_head else '<!-- LLM processed end -->'

            tag_content = re.sub(r'<!--\s*LLM processed start\s*-->', start_replacement, tag_content)
            tag_content = re.sub(r'<!--\s*LLM processed end\s*-->', end_replacement, tag_content)
            return f'<script>{tag_content}</script>'

        # Correct comments in <script> tags
        content = re.sub(r'<script>(.*?)</script>', replace_comments_in_tag, content, flags=re.DOTALL)
        
        return content

    def replace_styles(self, content, style_store):
        if style_store is None:
            return content
            
        for chunk_id, style_content in style_store.items():
            if style_content is None:
                continue

            content = content.replace(f'/* chunk_style_{chunk_id} */', style_content)
        return content
    
    def replace_scripts(self, content, script_store):
        if script_store is None:
            return content
        
        for chunk_id, script_content in script_store.items():
            if script_content is None:
                continue

            content = content.replace(f'// chunk_script_{chunk_id}', script_content)
        return content

    def store_chunks(self, chunks, chunked_file_directory="chunked-doms/original/", direct=False):

        os.makedirs(chunked_file_directory, exist_ok=True)

        all_chunks = []
        if not direct:
            for chunk in chunks:
                chunk_id = chunk['id']
                chunk_content = chunk['content']
                all_chunks.append({
                    "id": chunk_id,
                    "content": chunk_content,
                    "chunk_token_size": self.estimate_tokens(chunk_content),
                    "section": chunk['section']
                })

            # add script and style stores to all_chunks with different section name
            all_chunks.append({
                "id": "script_store",
                "content": self.script_store,
                "section": "script_store"
            })

            all_chunks.append({
                "id": "style_store",
                "content": self.style_store,
                "section": "style_store"
            })
        else:
            all_chunks = chunks
        
        with open(chunked_file_directory + self.filename + '.json', 'w') as f:
            f.write(json.dumps(all_chunks, indent=2))

def rahhh():
    files_to_be_chunked_directory = "extracted-doms/original/"
    chunked_file_directory = "chunked-doms/original/"

    merged_chunks_file_directory = "merged-chunks/original/"

    os.makedirs(chunked_file_directory, exist_ok=True)
    os.makedirs(merged_chunks_file_directory, exist_ok=True)

    files_to_exclude = ['amazon', 'ubereats', 'glassdoor', 'ziprecruiter', 'behance']
    
    for file in os.listdir(files_to_be_chunked_directory):
        # create chunks from only html files then store them
        filename = file.split('.')[0]

        if file.endswith(".html") and filename not in files_to_exclude:

            with open(files_to_be_chunked_directory + file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            chunker = HTMLChunker(html_content)
            chunks = chunker.split_html()
            
            chunker.store_chunks(chunks)
            
            # merge chunks and store them
            chunked_file = chunked_file_directory + filename + '.json'
            created_chunks = []

            with open(chunked_file, 'r') as f:
                created_chunks = json.load(f)

            reassembled_html = chunker.reassemble_html(created_chunks)
            with open(merged_chunks_file_directory + filename + '.html', 'w', encoding='utf-8') as f:
                f.write(reassembled_html)   

            print(f"Processed {filename}")
        else:
            print(f"Skipping {filename}")