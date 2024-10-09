import json
from bs4 import BeautifulSoup

def html_to_json_tree(html_content, threshold):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    def process_element(element, depth=0, parent_ref=None):
        if isinstance(element, str):
            return None
        
        element_length = len(str(element))
        element_ref = f"ref_{id(element)}"
        attributes = {}
        for attr, value in element.attrs.items():
            if isinstance(value, list):
                attributes[attr] = value
            else:
                attributes[attr] = str(value)

        result = {
            "tag": element.name,
            "depth": depth,
            "ref": element_ref,
            "parent_ref": parent_ref,
            "attributes": attributes,
            "length": element_length,
            "is_self_closing": element.is_empty_element
        }
        
        if element_length > threshold:
            result["content_truncated"] = True
            result["original_length"] = element_length
            return result
        
        if element.name != 'script' and not element.is_empty_element:
            text_content = element.string
            if text_content:
                result["text_content"] = text_content.strip()
        
        children = []
        for child in element.children:
            child_result = process_element(child, depth + 1, element_ref)
            if child_result:
                children.append(child_result)
        
        if children:
            result["children"] = children
        
        return result
    
    html_element = soup.find('html')
    if html_element:
        tree = process_element(html_element)
    else:
        tree = {"tag": "html", "depth": 0, "ref": "ref_root", "parent_ref": None, "children": []}
        
        head = soup.find('head')
        if head:
            head_tree = process_element(head, 1, "ref_root")
            if head_tree:
                tree["children"].append(head_tree)
        
        body = soup.find('body')
        if body:
            body_tree = process_element(body, 1, "ref_root")
            if body_tree:
                tree["children"].append(body_tree)
    
    return tree

def json_tree_to_html(json_tree):
    def build_element(node):
        if node["tag"] == "html":
            element = "<!DOCTYPE html>\n<html"
        else:
            element = f"<{node['tag']}"
        
        for attr, value in node["attributes"].items():
            if isinstance(value, list):
                element += f' {attr}="{" ".join(value)}"'
            else:
                element += f' {attr}="{value}"'
        
        if node["is_self_closing"]:
            element += "/>"
            return element
        
        element += ">"
        
        if "content_truncated" in node:
            element += f"<!-- Content truncated. Original length: {node['original_length']} -->"
        elif "text_content" in node:
            element += node["text_content"]
        elif "children" in node:
            for child in node["children"]:
                element += "\n" + build_element(child)
        
        element += f"</{node['tag']}>"
        return element
    
    return build_element(json_tree)

# Example usage
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample Page</title>
    <link rel="stylesheet" href="styles.css">
    <link rel="alternate stylesheet" href="alternate.css">
</head>
<body>
    <div class="container main-content">
        <h1>Hello, World!</h1>
        <p class="intro highlight">This is a paragraph.</p>
        <img src="example.jpg" alt="An example image" />
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <div class="large-content">
            <!-- Imagine this div has a lot of content -->
            <p>This is a very long paragraph with a lot of text that exceeds the threshold...</p>
            <!-- More content -->
        </div>
    </div>
</body>
</html>
"""

threshold = 200  # Set a lower threshold to demonstrate the truncation
json_tree = html_to_json_tree(html_content, threshold)
with open("html_tree.json", "w") as file:
    json.dump(json_tree, file, indent=2)

reconstructed_html = json_tree_to_html(json_tree)
with open("reconstructed.html", "w") as file:
    file.write(reconstructed_html)
