from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re  

app = Flask(__name__)
CORS(app) 

def fetch_and_parse_dependencies(repo_url):
    clean_url = repo_url.replace(".git", "").rstrip('/')
    url_parts = clean_url.split('/')
    
    if len(url_parts) < 2:
        return None
        
    owner = url_parts[-2]
    repo = url_parts[-1]
    branches = ["main", "master"]

    target_files = [
        {"name": "package.json", "ecosystem": "npm", "type": "json_npm"},
        {"name": "requirements.txt", "ecosystem": "PyPI", "type": "text_pypi"},
        {"name": "composer.json", "ecosystem": "Packagist", "type": "json_composer"},
        {"name": "pom.xml", "ecosystem": "Maven", "type": "xml_maven"},
        {"name": "go.mod", "ecosystem": "Go", "type": "text_go"}]
  
    session = requests.Session()

    for branch in branches:
        for target in target_files:
          
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{target['name']}"
            try:
                response = requests.get(raw_url, timeout=5)
                
                if response.status_code == 200:
                    parsed_deps = []
                    
                    if target["type"] == "json_npm":
                        data = response.json()
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                        for name, ver in deps.items():
                            clean_ver = ver.lstrip('^~<>=').split(' ')[0]
