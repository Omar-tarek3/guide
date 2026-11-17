import json
import requests
import base64

class GitHub:
    def __init__(self, token, repo_owner, repo_name, proxy_url="http://vpce-0974f7457e940e4bf-0s4t8nsz.vpce-svc-0ffc3575422275d21.eu-central-1.vpce.amazonaws.com:8081"):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        
        # Set up proxy if provided
        self.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        } if proxy_url else None

    def check_repo_exists(self):
        """
        Check if the GitHub repository exists.

        Returns:
            dict: Status code and message about repository existence.
        """
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(self.base_url, headers=headers, proxies=self.proxies)
            if response.status_code == 200:
                return {
                    "statusCode": 200,
                    "body": json.dumps({"message": f"The repository '{self.repo_name}' exists."})
                }
            elif response.status_code == 404:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": f"The repository '{self.repo_name}' does not exist."})
                }
            else:
                return {
                    "statusCode": response.status_code,
                    "body": json.dumps({
                        "message": "Error occurred while checking repository existence.",
                        "details": response.json()
                    })
                }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "An error occurred.", "error": str(e)})
            }

    def check_file_exists(self, directory_path="RPA_Worker/Code", target_file="releasenote.xlsx", branch="develop"):
        url = f"{self.base_url}/contents/{directory_path}?ref={branch}"
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers, proxies=self.proxies)
            if response.status_code == 200:
                files = response.json()
                file_names = [file['name'] for file in files if file['type'] == 'file']
                
                if target_file in file_names:
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"message": f"{target_file} exists in the directory."})
                    }
                else:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"message": f"{target_file} does not exist in the directory."})
                    }

            elif response.status_code == 404:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": "Directory does not exist in the repository."})
                }
            else:
                return {
                    "statusCode": response.status_code,
                    "body": json.dumps({
                        "message": "Error occurred",
                        "details": response.json(),
                        "hint": "Check the directory path, branch name, and token permissions."
                    })
                }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "An error occurred.", "error": str(e)})
            }

    def get_file_content(self, file_path, branch="develop"):
        url = f"{self.base_url}/contents/{file_path}?ref={branch}"
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers, proxies=self.proxies)
            if response.status_code == 200:
                file_data = response.json()
                
                # Decode the base64 content
                file_content = base64.b64decode(file_data['content']).decode('utf-8')
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": f"Successfully fetched content of {file_path}.",
                        "content": file_content
                    })
                }
            elif response.status_code == 404:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": f"{file_path} does not exist in the repository."})
                }
            else:
                return {
                    "statusCode": response.status_code,
                    "body": json.dumps({
                        "message": "Error occurred",
                        "details": response.json(),
                        "hint": "Check the file path, branch name, and token permissions."
                    })
                }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "An error occurred.", "error": str(e)})
            }

    def download_file(self, file_path, local_path, branch="develop"):
        url = f"{self.base_url}/contents/{file_path}?ref={branch}"
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers, proxies=self.proxies)
            if response.status_code == 200:
                file_data = response.json()
                
                # Decode the base64 content and save it to the specified local path
                file_content = base64.b64decode(file_data['content'])
                
                with open(local_path, "wb") as file:
                    file.write(file_content)
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": f"File downloaded successfully to {local_path}.",
                    })
                }
            elif response.status_code == 404:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": f"{file_path} does not exist in the repository."})
                }
            else:
                return {
                    "statusCode": response.status_code,
                    "body": json.dumps({
                        "message": "Error occurred",
                        "details": response.json(),
                        "hint": "Check the file path, branch name, and token permissions."
                    })
                }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "An error occurred.", "error": str(e)})
            }

    def list_files_in_directory(self, repo_name, directory_path, branch="develop"):
        """
        List files in the specified directory within a GitHub repository branch.

        Args:
            repo_name (str): Name of the GitHub repository.
            directory_path (str): Path of the directory to list files.
            branch (str): Branch name to look within (default is 'develop').

        Returns:
            list: List of file paths in the specified directory.
        """
        url = f"{self.base_url}/contents/{directory_path}?ref={branch}"

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            
           # url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/contents/{directory_path}?ref={branch}"
            response = requests.get(url, headers=headers, proxies=self.proxies)

            if response.status_code == 200:
                contents = response.json()
                file_paths = [item['path'] for item in contents if item['type'] == 'file']
                self.logger.info(f"Files in directory '{directory_path}' in branch '{branch}': {file_paths}")
                return file_paths
            else:
                self.logger.error(f"Failed to list files in {directory_path}: {response.text}")
                return []

        except Exception as e:
            self.logger.error(f"Error listing files in directory '{directory_path}': {e}")
            return []  