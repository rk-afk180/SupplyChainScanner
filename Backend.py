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
        return {"error": "Invalid GitHub repository URL format."}
        
    owner = url_parts[-2]
    repo = url_parts[-1]

    target_map = {
        "package.json": {"ecosystem": "npm", "type": "json_npm"},
        "requirements.txt": {"ecosystem": "PyPI", "type": "text_pypi"},
        "composer.json": {"ecosystem": "Packagist", "type": "json_composer"},
        "pom.xml": {"ecosystem": "Maven", "type": "xml_maven"},
        "go.mod": {"ecosystem": "Go", "type": "text_go"},
        "pyproject.toml": {"ecosystem": "PyPI", "type": "toml_pypi"},
        "Pipfile": {"ecosystem": "PyPI", "type": "toml_pypi"},
        "build.gradle": {"ecosystem": "Maven", "type": "gradle_maven"},
        "Cargo.toml": {"ecosystem": "crates.io", "type": "toml_rust"},
        "Gemfile": {"ecosystem": "RubyGems", "type": "text_ruby"}
    }
    
    session = requests.Session()
    session.headers.update({"Accept": "application/vnd.github.v3+json"})

    try:
        repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_response = session.get(repo_api_url, timeout=10)
        
        if repo_response.status_code == 403:
            return {"error": "GitHub API Rate Limit Exceeded. You hit the 60 requests/hr limit. Please wait an hour and try again."}
        elif repo_response.status_code == 404:
            return {"error": "Repository not found. Check the URL and ensure it is public."}
        elif repo_response.status_code != 200:
            return {"error": f"Failed to fetch repo info. GitHub Status: {repo_response.status_code}"}
            
        default_branch = repo_response.json().get("default_branch", "main")

        tree_api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_response = session.get(tree_api_url, timeout=15)
        
        if tree_response.status_code == 403:
            return {"error": "GitHub API Rate Limit Exceeded while fetching the repository tree."}
        elif tree_response.status_code != 200:
            return {"error": f"Failed to fetch repository tree. GitHub Status: {tree_response.status_code}"}

        tree_data = tree_response.json().get("tree", [])
        
        matching_files = []
        for item in tree_data:
            if item["type"] == "blob": 
                filename = item["path"].split('/')[-1]
                if filename in target_map:
                    matching_files.append({"path": item["path"], "info": target_map[filename]})

        if not matching_files:
            return {"error": "No supported dependency files found anywhere in this repository."}

        all_parsed_deps = []
        for file_data in matching_files:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{file_data['path']}"
            target_info = file_data['info']
            
            raw_session = requests.Session()
            file_response = raw_session.get(raw_url, timeout=5)
            
            if file_response.status_code == 200:
                text_content = file_response.text
                
                if target_info["type"] == "json_npm":
                    try:
                        data = file_response.json()
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                        for name, ver in deps.items():
                            clean_ver = ver.lstrip('^~<>=').split(' ')[0]
                            all_parsed_deps.append({"name": name, "version": clean_ver, "ecosystem": target_info["ecosystem"]})
                    except: pass
                        
                elif target_info["type"] == "text_pypi":
                    for line in text_content.split('\n'):
                        line = line.split('#')[0].strip()
                        if not line: continue
                        match = re.split(r'==|>=|~=', line)
                        if len(match) == 2:
                            all_parsed_deps.append({"name": match[0].strip(), "version": match[1].strip(), "ecosystem": target_info["ecosystem"]})
                        elif len(match) == 1:
                            all_parsed_deps.append({"name": match[0].strip(), "version": "UNPINNED", "ecosystem": target_info["ecosystem"]})
                
                elif target_info["type"] == "json_composer":
                    try:
                        data = file_response.json()
                        deps = {**data.get("require", {}), **data.get("require-dev", {})}
                        for name, ver in deps.items():
                            if name.lower() == "php" or "/" not in name: continue
                            clean_ver = ver.lstrip('^~<>=').split(' ')[0].replace('*', '')
                            if clean_ver:
                                all_parsed_deps.append({"name": name, "version": clean_ver, "ecosystem": target_info["ecosystem"]})
                    except: pass

                elif target_info["type"] == "xml_maven":
                    for group, artifact, version in re.findall(r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>', text_content):
                        if not version.startswith('$'):
                            all_parsed_deps.append({"name": f"{group}:{artifact}", "version": version, "ecosystem": target_info["ecosystem"]})

                elif target_info["type"] == "text_go":
                    for name, version in re.findall(r'^\s*([a-zA-Z0-9\.\-\/\_]+)\s+(v[0-9\.\-\w]+)', text_content, re.MULTILINE):
                        all_parsed_deps.append({"name": name, "version": version.lstrip('v'), "ecosystem": target_info["ecosystem"]})

                elif target_info["type"] == "toml_pypi":
                    for name, version in re.findall(r'^([a-zA-Z0-9\-_]+)\s*=\s*["\']([^\*"\']+)["\']', text_content, re.MULTILINE):
                        if name.lower() not in ["python", "name", "version", "description"]:
                            all_parsed_deps.append({"name": name, "version": version.lstrip('^~<>=').split(' ')[0], "ecosystem": target_info["ecosystem"]})

                elif target_info["type"] == "gradle_maven":
                    for group, artifact, version in re.findall(r'(?:implementation|api|compileOnly|testImplementation)\s*[\'"]([^\:]+)\:([^\:]+)\:([^\'"]+)[\'"]', text_content):
                        if not version.startswith('$'): 
                            all_parsed_deps.append({"name": f"{group}:{artifact}", "version": version, "ecosystem": target_info["ecosystem"]})

                elif target_info["type"] == "toml_rust":
                    for match in re.findall(r'^([a-zA-Z0-9\-_]+)\s*=\s*(?:["\']([^"\']+)["\']|\{[^}]*version\s*=\s*["\']([^"\']+)["\'])', text_content, re.MULTILINE):
                        name, version = match[0], match[1] if match[1] else match[2]
                        if name not in ["name", "version"] and version:
                            all_parsed_deps.append({"name": name, "version": version.lstrip('^~= '), "ecosystem": target_info["ecosystem"]})

                elif target_info["type"] == "text_ruby":
                    for name, version in re.findall(r'^\s*gem\s+[\'"]([^\'"]+)[\'"](?:\s*,\s*[\'"]([^\'"]+)[\'"])?', text_content, re.MULTILINE):
                        all_parsed_deps.append({"name": name, "version": version.lstrip('~> =') if version else "UNPINNED", "ecosystem": target_info["ecosystem"]})

        return {"data": all_parsed_deps} if all_parsed_deps else {"error": "Supported files found, but they were empty or unreadable."}
        
    except Exception as e:
        return {"error": f"An unexpected backend error occurred: {str(e)}"}

def scan_dependencies(parsed_deps):
    if not parsed_deps:
        return {"status": "success", "total_scanned": 0, "vulnerabilities_found": 0, "vulnerable_libraries": []}

    queries, unpinned_libs, vulnerable_libraries = [], [], []
    
    for dep in parsed_deps:
        if dep["version"] == "UNPINNED":
            unpinned_libs.append(dep)
        else:
            queries.append({
                "version": dep["version"],
                "package": {"name": dep["name"], "ecosystem": dep["ecosystem"]}
            })

    for unpinned in unpinned_libs:
        vulnerable_libraries.append({
            "library_name": unpinned["name"],
            "current_version": "UNPINNED",
            "issue_count": 1,
            "specific_issues": [{
                "id": "CONFIG-RISK-01",
                "summary": "Supply Chain Risk: Unpinned dependency.",
                "solution": f"Pin a specific version (e.g., {unpinned['name']}==1.0.0)"
            }]
        })

    if queries:
        try:
            response = requests.post("https://api.osv.dev/v1/querybatch", json={"queries": queries}, timeout=15)
            if response.status_code == 200:
                for index, result in enumerate(response.json().get("results", [])):
                    if "vulns" in result:
                        package_info, package_version = queries[index]["package"], queries[index]["version"]
                        package_issues = []
                        
                        for vuln in result["vulns"]:
                            summary = vuln.get("summary") or vuln.get("details", "")[:200] + "..."
                            if not summary: summary = f"Security vulnerability ({vuln.get('id', 'Unknown')}) detected."
                            
                            solution = None
                            for affected in vuln.get("affected", []):
                                for r in affected.get("ranges", []):
                                    for ev in r.get("events", []):
                                        if "fixed" in ev:
                                            solution = f"Upgrade to v{ev['fixed']}"
                                            break

                            solution = solution or (vuln.get("references", [{}])[0].get("url") or f"https://osv.dev/vulnerability/{vuln.get('id', '')}")
                            
                            package_issues.append({"id": vuln.get("id"), "summary": summary, "solution": solution})
                            
                        vulnerable_libraries.append({
                            "library_name": package_info["name"], "current_version": package_version,
                            "issue_count": len(package_issues), "specific_issues": package_issues
                        })
            else:
                return {"error": f"OSV API Error: {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to connect to OSV database: {str(e)}"}

    return {
        "status": "success", "total_scanned": len(parsed_deps),
        "vulnerabilities_found": len(vulnerable_libraries), "vulnerable_libraries": vulnerable_libraries
    }

@app.route("/scan", methods=["POST"])
def handle_scan():
    incoming_data = request.get_json()
    if not incoming_data or not incoming_data.get("repo_url"):
        return jsonify({"error": "No repository URL provided"}), 400

    parsed_result = fetch_and_parse_dependencies(incoming_data.get("repo_url"))
    
    if "error" in parsed_result:
        return jsonify({"error": parsed_result["error"]}), 400

    results = scan_dependencies(parsed_result["data"])
    
    if "error" in results:
        return jsonify({"error": results["error"]}), 500
        
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
