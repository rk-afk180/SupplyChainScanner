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
        {"name": "go.mod", "ecosystem": "Go", "type": "text_go"}
    ]
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
                            parsed_deps.append({"name": name, "version": clean_ver, "ecosystem": target["ecosystem"]})
                            
                    elif target["type"] == "text_pypi":
                        lines = response.text.split('\n')
                        for line in lines:
                            line = line.split('#')[0].strip()
                            if not line: continue
                            match = re.split(r'==|>=|~=', line)
                            if len(match) == 2:
                                parsed_deps.append({"name": match[0].strip(), "version": match[1].strip(), "ecosystem": target["ecosystem"]})
                    
                    elif target["type"] == "json_composer":
                        data = response.json()
                        deps = {**data.get("require", {}), **data.get("require-dev", {})}
                        for name, ver in deps.items():
                            if name.lower() == "php" or "/" not in name: continue
                            clean_ver = ver.lstrip('^~<>=').split(' ')[0].replace('*', '')
                            if clean_ver:
                                parsed_deps.append({"name": name, "version": clean_ver, "ecosystem": target["ecosystem"]})

                    elif target["type"] == "xml_maven":
                        matches = re.findall(r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>', response.text)
                        for group, artifact, version in matches:
                            if not version.startswith('$'):
                                parsed_deps.append({"name": f"{group}:{artifact}", "version": version, "ecosystem": target["ecosystem"]})

                    elif target["type"] == "text_go":
                        matches = re.findall(r'^\s*([a-zA-Z0-9\.\-\/\_]+)\s+(v[0-9\.\-\w]+)', response.text, re.MULTILINE)
                        for name, version in matches:
                            parsed_deps.append({"name": name, "version": version.lstrip('v'), "ecosystem": target["ecosystem"]})

                    return parsed_deps
            except Exception:
                continue
                
    return None

def scan_dependencies(parsed_deps):
    if not parsed_deps:
        return {"status": "success", "total_scanned": 0, "vulnerabilities_found": 0, "vulnerable_libraries": []}

    queries = []
    
    for dep in parsed_deps:
        queries.append({
            "version": dep["version"],
            "package": {"name": dep["name"], "ecosystem": dep["ecosystem"]}
        })

    try:
        osv_batch_url = "https://api.osv.dev/v1/querybatch"
        response = requests.post(osv_batch_url, json={"queries": queries}, timeout=15)
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            vulnerable_libraries = []
            
            for index, result in enumerate(results):
                if "vulns" in result:
                    package_info = parsed_deps[index]
                    package_issues = []
                    
                    for vuln in result["vulns"]:
                        summary = vuln.get("summary")
                        if not summary:
                            details = vuln.get("details")
                            if details:
                                summary = details[:200] + "..." if len(details) > 200 else details
                            else:
                                aliases = vuln.get("aliases", [])
                                vuln_id = vuln.get("id", "Unknown ID")
                                if aliases:
                                    alias_str = ", ".join(aliases[:2]) 
                                    summary = f"Security flaw identified ({alias_str}). Read the advisory link for full impact details."
                                else:
                                    summary = f"Security vulnerability ({vuln_id}) detected. See OSV database link for details."
                        
                        solution = None
                        for affected in vuln.get("affected", []):
                            for r in affected.get("ranges", []):
                                for ev in r.get("events", []):
                                    if "fixed" in ev:
                                        solution = f"Upgrade to v{ev['fixed']}"
                                        break

                        if not solution:
                            references = vuln.get("references", [])
                            if references:
                                solution = references[0].get("url", "No URL")
                            else:
                                vuln_id = vuln.get("id", "")
                                solution = f"https://osv.dev/vulnerability/{vuln_id}"
                        
                        package_issues.append({
                            "id": vuln.get("id"),
                            "summary": summary,
                            "solution": solution
                        })
                        
                    vulnerable_libraries.append({
                        "library_name": package_info["name"],
                        "current_version": package_info["version"],
                        "issue_count": len(package_issues),
                        "specific_issues": package_issues
                    })
            
            return {
                "status": "success",
                "total_scanned": len(parsed_deps),
                "vulnerabilities_found": len(vulnerable_libraries),
                "vulnerable_libraries": vulnerable_libraries
            }
            
        return {"status": "error", "error": f"OSV API Error: {response.status_code}"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.route("/scan", methods=["POST"])
def handle_scan():
    incoming_data = request.get_json()
    repo_url = incoming_data.get("repo_url") if incoming_data else None
    
    if not repo_url:
        return jsonify({"error": "No repository URL provided"}), 400

    parsed_deps = fetch_and_parse_dependencies(repo_url)
    
    if parsed_deps is None:
        return jsonify({"error": "Could not find a supported dependency file (package.json, requirements.txt, pom.xml, go.mod, composer.json) in main branches."}), 404

    results = scan_dependencies(parsed_deps)
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
