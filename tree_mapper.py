from bs4 import BeautifulSoup
import json
import uuid

# Helper function to generate unique references
def generate_ref():
    return str(uuid.uuid4())

# Function to split HTML elements into groups without exceeding the threshold
def group_elements_by_threshold(element, threshold, parent_ref=None, depth=0):
    groups = []
    group = {
        'ref': generate_ref(),
        'parent_ref': parent_ref,
        'depth': depth,
        'elements': [],
        'size': 0  # Track the size of the group
    }

    for child in element.children:
        if child.name is not None:  # Only consider actual HTML elements, not text nodes
            child_str = str(child)
            child_size = len(child_str)

            # Recursively group child elements
            child_groups = group_elements_by_threshold(child, threshold, group['ref'], depth + 1)

            # If adding this child would exceed the threshold, finalize the current group and start a new one
            if group['size'] + child_size > threshold:
                groups.append(group)
                group = {
                    'ref': generate_ref(),
                    'parent_ref': parent_ref,
                    'depth': depth,
                    'elements': [],
                    'size': 0
                }

            group['elements'].append({
                'tag': child.name,
                'attrs': child.attrs,
                'content': child_str,
                'ref': generate_ref(),
                'child_refs': [g['ref'] for g in child_groups]  # Store references to child groups
            })
            group['size'] += child_size
            groups.extend(child_groups)

    if group['elements']:
        groups.append(group)

    return groups

# Function to convert HTML into JSON tree
def html_to_json(html_content, threshold=5000):
    soup = BeautifulSoup(html_content, 'html.parser')
    root = soup.body or soup  # Start from <body> if exists, otherwise from the document root
    return group_elements_by_threshold(root, threshold)

# Rebuild HTML from JSON tree
def reconstruct_html_from_json(json_tree):
    # Create a lookup map for references
    ref_map = {group['ref']: group for group in json_tree}

    def build_element(element):
        # Create a BeautifulSoup tag for the element
        tag = element['tag']
        attrs = element['attrs']
        soup = BeautifulSoup('', 'html.parser')
        tag_element = soup.new_tag(tag, **attrs)

        # Recursively build child elements if they exist
        for child_ref in element.get('child_refs', []):
            child_group = ref_map[child_ref]
            child_html = build_group(child_group)
            child_soup = BeautifulSoup(child_html, 'html.parser')
            tag_element.append(child_soup)

        return str(tag_element)

    def build_group(group):
        # Rebuild each element in the group
        elements_html = []
        for element in group['elements']:
            elements_html.append(build_element(element))
        return "".join(elements_html)

    # Find the root group (without parent_ref)
    root_group = next(group for group in json_tree if group['parent_ref'] is None)
    return build_group(root_group)

# Read HTML file and convert to JSON tree
def parse_html_file_to_json(file_path, threshold=5000):
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    json_tree = html_to_json(html_content, threshold)
    return json_tree

# Save JSON output
def save_json_tree(json_tree, output_file='html_tree.json'):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(json_tree, file, indent=2)

# Load JSON tree from file
def load_json_tree(input_file='html_tree.json'):
    with open(input_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# Save reconstructed HTML to a file
def save_reconstructed_html(html_content, output_file='reconstructed.html'):
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(html_content)

# Example usage
if __name__ == "__main__":
    # Parsing HTML and saving JSON
    file_path = 'extracted-doms/original/airbnb.html'  # Replace with your HTML file path
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    from html_chunking import get_html_chunks
    merged_chunks = get_html_chunks(html_content, max_tokens=1000, is_clean_html=True)
    with open('resss.json', 'w') as f:
        json.dump(merged_chunks, f)
    # threshold = 5000  # Replace with desired threshold
    # json_tree = parse_html_file_to_json(file_path, threshold)
    # save_json_tree(json_tree)
    # print(f"JSON tree saved to 'html_tree.json'")

    # # Loading JSON tree and reconstructing HTML
    # input_file = 'html_tree.json'  # Replace with your JSON file path
    # json_tree = load_json_tree(input_file)
    # reconstructed_html = reconstruct_html_from_json(json_tree)
    # save_reconstructed_html(reconstructed_html)
    # print(f"Reconstructed HTML saved to 'reconstructed.html'")
