import uuid
import json
from bs4 import BeautifulSoup

# Function to generate a unique UUID
def generate_uuid():
    return str(uuid.uuid4())

# Function to replace text content with placeholders and collect text with UUIDs
def replace_text_with_placeholders(soup):
    text_content_map = {}

    # Recursively find all elements with text content
    for element in soup.find_all(True):  # True means find all tags
        element_uuid = generate_uuid()
        element['data-element-uuid'] = element_uuid
        if element.string and element.string.strip():  # Check if the element has text content
            text_content_map[element_uuid] = element.string.strip()

            # Replace text with placeholder and add data-element-uuid attribute
            # if within a regular element replace with <!-- text here -->, if in a style tag replace with /* text here */ and if in a script tag replace with // text here
            if element.name == 'style':
                element.string.replace_with(f"/* text-{element_uuid} */")
            else:
                element.string.replace_with(f"<!-- text-{element_uuid} -->")

    
    return text_content_map

# Function to restore original text from JSON
def restore_text_from_placeholders(soup, text_content_map):
    for element in soup.find_all(True):  # True means find all tags
        if 'data-element-uuid' in element.attrs:
            element_uuid = element['data-element-uuid']
            if element_uuid in text_content_map:
                # Restore original text content only if the UUID is present in the map
                element.string.replace_with(text_content_map[element_uuid])


# Sample HTML content
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
            <p>This is a very long paragraph with a lot of text that exceeds the threshold...</p>
        </div>
    </div>
</body>
</html>
"""

with open('extracted-doms/original/airbnb.html', 'r') as file:
    html_content = file.read()

# Parse the HTML with BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# Replace text with placeholders and generate the text content map
text_content_map = replace_text_with_placeholders(soup)

# Convert the updated HTML back to a string
modified_html = soup.decode_contents(formatter=None, indent_level=4)

# Generate the JSON object of original text content with UUIDs
text_content_json = json.dumps(text_content_map, indent=4)

# Output the modified HTML and the JSON object
with open('modified_html.html', 'w') as file:
    file.write(modified_html)

with open('text_content.json', 'w') as file:
    file.write(text_content_json)

# Now, restore the original text back into the HTML
restore_text_from_placeholders(soup, text_content_map)

# Output the restored HTML
restored_html = soup.decode_contents(formatter=None, indent_level=4)
with open('restored_html.html', 'w') as file:
    file.write(restored_html)
