from bs4 import BeautifulSoup
import requests
import json
import os

path_to_links = "websites.json"
output_dir = "extracted-doms"

os.makedirs(output_dir, exist_ok=True)

# Read and parse the JSON file
with open(path_to_links, 'r') as file:
    links = json.load(file)

for link in links:
    url = links[link]['url']
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    output_file = os.path.join(output_dir, f"{link}.html")
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(soup.prettify())

    print(f"DOM extracted for {link}")

print("All DOMs extracted successfully!")