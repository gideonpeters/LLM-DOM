import requests
import json
import base64

# Set up GitHub API credentials (replace with your token)
GITHUB_TOKEN = ""
headers = {"Authorization": f"token {GITHUB_TOKEN}"}

def get_file_content(repo_url, path):
    """Fetch the content of a file from a GitHub repository."""
    content_url = f"{repo_url}/contents/{path}"
    response = requests.get(content_url, headers=headers)
    if response.status_code == 200:
        content = response.json()
        return content['content']
    return None

def count_lines(content):
    """Count the number of lines in the file content."""
    decoded_content = base64.b64decode(content).decode('utf-8')
    return len(decoded_content.splitlines())

# Step 1: Search for repositories with index.html at the root
search_url = "https://api.github.com/search/code"
params = {
    "q": "index.html in:path language:html size:>0",
    "sort": "forks",
    "per_page": 50  # Adjust per_page as needed
}

response = requests.get(search_url, headers=headers, params=params)
search_results = response.json()

# Step 2: Fetch repository details and filter by language usage
for item in search_results.get("items", []):
    # Fetch repository details to get the star count and language breakdown
    repo_details_url = item["repository"]["url"]
    repo_response = requests.get(repo_details_url, headers=headers)
    repo_details = repo_response.json()

    # Fetch the index.html file content
    file_content = get_file_content(repo_details["url"], "index.html")
    if file_content is None:
        continue

    # Check the line count of the index.html file
    line_count = count_lines(file_content)
    if line_count < 100:
        continue

    languages_url = repo_details["languages_url"]
    language_response = requests.get(languages_url, headers=headers)
    languages = language_response.json()

    if "HTML" in languages:
        total_bytes = sum(languages.values())
        html_percentage = (languages["HTML"] / total_bytes) * 100

        # Step 3: Check if HTML percentage is above 50%
        if html_percentage > 50:
            print(f"Repository: {repo_details['full_name']}, HTML Usage: {html_percentage:.2f}%, Stars: {repo_details['stargazers_count']} Forks: {repo_details['forks']}")
            result = {
                "name": repo_details["full_name"],
                "html_percentage": html_percentage,
                "stars": repo_details["stargazers_count"]
            }
            # store the repo details in a file
            repo_name = str(repo_details["full_name"]).replace("/", "_")

            with open(f"mined-repos/full/{repo_name}.json", "w") as file:
                json.dump(repo_details, file, indent=4)

            with open(f"mined-repos/summary/{repo_name}.json", "w") as file:
                json.dump(result, file, indent=4)

