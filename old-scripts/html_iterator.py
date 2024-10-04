from bs4 import BeautifulSoup
import json
import re
import os
import tiktoken

MAX_TOKENS = 10000

def count_tokens(text):
    encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)

    return len(tokens)

def split_head(html_content, max_tokens = MAX_TOKENS):
    soup = BeautifulSoup(html_content, 'html.parser')
    head = soup.head

    # Filter out non-tag elements
    if(head is None or head.contents is None):
        return []
    
    head_elements = [element for element in head.contents if element.name is not None]

    head_chunks = []

    for i, element in enumerate(head_elements):
        element_str = str(element)
        element_position = f"html > head > {element.name}:nth-child({i+1})"
        element_tokens = count_tokens(element_str)
        head_chunks.append((element_position, element_str, element_tokens))

    return head_chunks

def split_body(html_content, max_tokens):
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.body

    body_chunks = split_element(body, max_tokens, 'html > body')

    return body_chunks

def split_element(element, max_tokens, base_selector):
    chunks = []
    current_chunk = []
    current_tokens = 0

    if element is None or element.contents is None:
        return []

    # Filter out non-tag elements
    children = [child for child in element.children if child.name is not None]

    for i, child in enumerate(children):
        child_str = str(child)
        child_tokens = count_tokens(child_str)
        child_selector = f"{base_selector} > {child.name}:nth-child({i+1})"

        if current_tokens + child_tokens > max_tokens:
            if current_chunk:
                chunks.append((base_selector, wrap_with_parent(element, current_chunk), current_tokens))
                current_chunk = []
                current_tokens = 0

        current_chunk.append(child_str)
        current_tokens += child_tokens

        # Append the chunk with the correct child selector
        if current_tokens > max_tokens:
            chunks.append((child_selector, wrap_with_parent(element, current_chunk), current_tokens))
            current_chunk = []
            current_tokens = 0

    if current_chunk:
        chunks.append((base_selector, wrap_with_parent(element, current_chunk), current_tokens))

    return chunks

def wrap_with_parent(parent, elements):
    parent_copy = BeautifulSoup(str(parent), 'html.parser')
    parent_copy.clear()
    for element in elements:
        parent_copy.append(BeautifulSoup(element, 'html.parser'))
    return str(parent_copy)

def generate_prompt(chunk, selector, type = "body"):
    escaped_chunk = chunk.replace("{", "{{").replace("}", "}}")
    audit = ''

    if(type == "body"):
        prompt_template = f"""
            Given the following skeleton of a DOM tree, 
            fix the lighthouse audit {audit} present, 
            return the modified element within the skeleton 
            as well as the original position selector:

            _____ 
            <!DOCTYPE html>
            <html> 
                <head> // Rest of <head> element </head> 
                <body> 
                    <!-- Original position of the element to be modified: {selector} --> 
                    {chunk}
                    <!-- End of element to be modified --> 
                </body> 
            </html> 
            _____
            """
    else:
        prompt_template = f"""
            Given the following skeleton of a DOM tree, fix any performance issues present, return the modified element within the skeleton as well as the original position selector:

            _____ 
            <!DOCTYPE html>
            <html> 
                <head>
                    <!-- Original position of the element to be modified: {selector} --> 
                    {escaped_chunk}
                    <!-- End of element to be modified --> 
                </head>
            </html> 
            _____
            """
    return prompt_template

def apply_body_changes(html_content, llm_responses):
    soup = BeautifulSoup(html_content, 'html.parser')

    for response in llm_responses:
        selector = response['selector']
        modified_element = BeautifulSoup(response['modified_element'], 'html.parser')
        original_element = soup.select_one(selector)
        if original_element:
            original_element.replace_with(modified_element)

    return str(soup)

def extract_nth_child(selector):
    match = re.search(r'nth-child\((\d+)\)', selector)
    if match:
        return int(match.group(1))
    return None

def apply_head_changes(html_content, llm_responses):
    # Add head elements back into head tag, note that their selectors are not actual selectors, use the position to just add it back
    soup = BeautifulSoup(html_content, 'html.parser')

    for response in llm_responses:
        position = extract_nth_child(response['selector'])

        #remove the older element then add the modified element based on the position
        modified_element = BeautifulSoup(response['modified_element'], 'html.parser')
        head = soup.head
        head_elements = [element for element in head.contents if element.name is not None]
        if position is not None and position > 0:
            head_elements.pop(position - 1)
            head_elements.insert(position - 1, modified_element)

            head.clear()
            for element in head_elements:
                head.append(element)
        else:
            head.append(modified_element)

    return str(soup)
    

# # Main script
# html_content = """<!DOCTYPE html>
# <html>
# <head>
#     <title>Example Page</title>
#     <style> body { font-family: Arial; } </style>
# </head>
# <body>
#     <h1>Welcome to the Example Page</h1>
#     <p>This is a simple paragraph.</p>
#     <div class="container">
#         <ul>
#             <li>Item 1</li>
#             <li>Item 2</li>
#             <li>Item 3</li>
#         </ul>
#     </div>
# </body>
# </html>"""

def main():
    # iterate over sorted list of original extracted doms and store the body and head prompts in a file
    path_to_extracted_dom_trees = "extracted-doms/original"

    # create directory for body prompts and head prompts if they don't exist
    path_to_body_prompts = "prompts/body-prompts"
    path_to_head_prompts = "prompts/head-prompts"

    if not os.path.exists(path_to_body_prompts):
        os.makedirs(path_to_body_prompts)
    
    if not os.path.exists(path_to_head_prompts):
        os.makedirs(path_to_head_prompts)

    for filename in sorted(os.listdir(path_to_extracted_dom_trees)):
        if filename.endswith(".html"):
            dom_path = os.path.join(path_to_extracted_dom_trees, filename)

            dom_name = os.path.splitext(filename)[0]

            with open(dom_path, 'r') as file:
                dom_tree = file.read()

            if not dom_tree:
                continue

            head_chunks = split_head(dom_tree, MAX_TOKENS)
            body_chunks = split_body(dom_tree, MAX_TOKENS)

            body_prompts = [generate_prompt(chunk, selector) for selector, chunk, tokens in body_chunks]
            head_prompts = [generate_prompt(chunk, selector, type="head") for selector, chunk, tokens in head_chunks]

            # Store the prompts in a json
            with open(os.path.join(path_to_body_prompts, f"{dom_name}_body_prompts.json"), "w") as f:
               json_dump = []
               for i, prompt in enumerate(body_prompts):
                 json_dump.append({
                        "index": i,
                        "total_tokens": count_tokens(prompt),
                        "prompt": prompt
                 })

               json.dump(json_dump, f, indent=4)

            with open(os.path.join(path_to_head_prompts, f"{dom_name}_head_prompts.json"), "w") as f:
                json_dump = []
                for i, prompt in enumerate(head_prompts):
                    json_dump.append({
                            "index": i,
                            "total_tokens": count_tokens(prompt),
                            "prompt": prompt
                    })

                json.dump(json_dump, f, indent=4)
          
main()

# head_chunks = split_head(html_content, MAX_TOKENS)
# body_chunks = split_body(html_content, MAX_TOKENS)

# body_prompts = [generate_prompt(chunk, selector) for selector, chunk, tokens in body_chunks]
# head_prompts = [generate_prompt(chunk, selector, type="head") for selector, chunk, tokens in head_chunks]

# # Simulate LLM response
# llm_body_responses = [
#     {"selector": "html > body > div.container:nth-child(3)", "modified_element": "<div class=\"container-newman\"><ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul></div>"}
# ]

# llm_head_responses = [
#     {"selector": "html > head > style:nth-child(2)", "modified_element": "<style> body { font-family: Arial-Newww; } </style>"}
# ]

# modified_body = apply_body_changes(html_content, llm_body_responses)
# modified_head = apply_head_changes(html_content, llm_head_responses)
# with open("modified_body.html", "w") as f:
#     f.write(modified_body)

# with open("modified_head.html", "w") as f:
#     f.write(modified_head)

# # Store the prompts in a file
# with open("body_prompts.txt", "w") as f:
#     for prompt in body_prompts:
#         f.write(prompt + "\n\n")

# with open("head_prompts.txt", "w") as f:
#     for prompt in head_prompts:
#         f.write(prompt + "\n\n")

# # Store chunks in a json file
# with open("body_chunks.json", "w") as f:
#     json.dump(body_chunks, f, indent=4)

# with open("head_chunks.json", "w") as f:
#     json.dump(head_chunks, f, indent=4)