import gzip
from warcio.archiveiterator import ArchiveIterator
import os
import json
# import re
import hashlib
from dom_modifier import PythonProgrammer

extraction_details = {}

def save_html(content, url, output_dir="output_html"):
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if url is None:
        print("URL is None, skipping...")
        return
    
    original_url = url  
    # Remove query parameters from the URL
    url = url.split('?')[0]

    # Replace special characters with underscores
    sanitized_url = url.replace("/", "_").replace(":", "_")

    # Hash the sanitized URL to ensure the filename is unique and within length limits
    url_hash = hashlib.md5(sanitized_url.encode('utf-8')).hexdigest()
    filename = f"{url_hash}.html"

    # Create a valid filename from the URL
    filename = os.path.join(output_dir, filename)

    extraction_details[url_hash] = {
        "original_url": original_url,
        "sanitized_url": sanitized_url,
        "filename": filename,
        "url_hash": url_hash,
        "no_of_tokens": PythonProgrammer._count_tokens(content)
    }

    # Save the HTML content to a file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def extract_html_from_warc(file_path):
    with gzip.open(file_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == 'response':
                url = record.rec_headers.get_header('WARC-Target-URI')
                content_type = record.http_headers.get_header('Content-Type')

                # Check if the URL and content_type are not None
                if url is None or content_type is None:
                    print("URL or Content-Type is None, skipping...")
                    continue

                if 'text/html' in content_type:
                    html_content = record.content_stream().read().decode('utf-8', errors='ignore')
                    save_html(html_content, url)

    # Save the extraction details to a JSON file
    with open("extraction_details.json", "w") as f:
        json.dump(extraction_details, f, indent=4)

# Path to your .warc.gz file
warc_file_path = 'CC-MAIN-20240806095414-20240806125414-00893.warc.gz'
extract_html_from_warc(warc_file_path)


