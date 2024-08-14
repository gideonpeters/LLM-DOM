

from bs4 import BeautifulSoup
import os
import json

path_to_original_extracted_doms = "extracted-doms/original"
path_to_llm_modified_doms = "extracted-doms/llm-modified"

def element_to_json(element):
    node = {
        "tag": element.name,
        "attributes": element.attrs,
        "children": []
    }
    
    for child in element.children:
        if child.name: 
            node["children"].append(element_to_json(child))
        elif child.string and child.string.strip():
            node["children"].append({
                "text": child.string.strip()
            })
    
    return node

def dom_to_json(dom_string):
    soup = BeautifulSoup(dom_string, "html.parser")
    
    dom_json = []
    
    for element in soup.find_all(recursive=False):
        dom_json.append(element_to_json(element))
    
    return dom_json

def analyze_doms(path_to_doms, path_to_store_analysis):
    extracted_doms = os.listdir(path_to_doms)
    results = {}

    for filename in extracted_doms:
        if filename.endswith(".html"):
            print(f"Converting DOM to JSON for {filename}...")
            
            with open(os.path.join(path_to_doms, filename), 'r', encoding='utf-8') as file:
                dom_string = file.read()
            
            dom_json = dom_to_json(dom_string)

            results[filename] = dom_json
              
    if results:
        with open(path_to_store_analysis, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=2)
        print("All DOMs converted to JSON successfully!")

def main():
    analyze_doms(path_to_original_extracted_doms, "dom-analysis/original.json")
    # analyze_doms(path_to_llm_modified_doms, "dom-analysis/llm-modified.json")
    
if __name__ == "__main__":
    main()