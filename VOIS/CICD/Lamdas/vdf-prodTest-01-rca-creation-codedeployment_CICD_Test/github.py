import os
import requests
import base64
import logging
from ssm import SSM

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize SQS handler
ssm_handler = SSM(logger)
Github_OrgName_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/OrganizationName")
Github_Token_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/GithubToken")

class GitHubHandler:
    def __init__(self, logger,proxy_url="http://vpce-0974f7457e940e4bf-0s4t8nsz.vpce-svc-0ffc3575422275d21.eu-central-1.vpce.amazonaws.com:8081"):
        self.logger = logger
        self.org_name = Github_OrgName_SSM  # Set your GitHub organization name
        self.github_token = Github_Token_SSM  # Ensure the token is set in your environment
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.logger.info(f"Initialized GitHubHandler for org: {self.org_name}")
        
                
        # Set up proxy if provided
        self.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        } if proxy_url else None
        
        
        
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
        try:
            url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/contents/{directory_path}?ref={branch}"
            response = requests.get(url, headers=self.headers, proxies=self.proxies)

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


    # def fetch_file_from_github(self, file_path,repo_name):
    #     """Fetch a file's content from a GitHub repository, decode it from Base64, and return as binary data."""
    #     url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/contents/{file_path}"
    #     response = requests.get(url, headers=self.headers,proxies=self.proxies)
        
    #     if response.status_code == 200:
    #         file_info = response.json()
    #         file_content_encoded = file_info.get("content")
    #         file_content = base64.b64decode(file_content_encoded)  # Decode Base64 to binary
    #         self.logger.info(f"Fetched file: {file_path} successfully.")
    #         return file_content  # Return binary content
    #     else:
    #         self.logger.error(f"Failed to fetch file from GitHub: {response.text}")
    #         raise Exception(f"Failed to fetch file from GitHub: {response.text}")
    
    
    
    def fetch_file_from_github(self, file_path, repo_name, branch="develop"):
        """Fetch a file's content from a GitHub repository in a specific branch, decode it from Base64, and return as binary data."""
        url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/contents/{file_path}?ref={branch}"
        response = requests.get(url, headers=self.headers, proxies=self.proxies)
        
        if response.status_code == 200:
            file_info = response.json()
            file_content_encoded = file_info.get("content")
            file_content = base64.b64decode(file_content_encoded)  # Decode Base64 to binary
            self.logger.info(f"Fetched file: {file_path} from branch: {branch} successfully.")
            return file_content  # Return binary content
        else:
            self.logger.error(f"Failed to fetch file from GitHub: {response.text}")
            raise Exception(f"Failed to fetch file from GitHub: {response.text}")


    # def create_repo_env_var(self, var_name, var_value,repo_name):
    #     """
    #     Create or update an environment variable in the repository or a specific environment.
        
    #     :param var_name: Name of the environment variable.
    #     :param var_value: Value of the environment variable.
    #     """


    #     url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/actions/variables"
    #     payload = {
    #         "name": var_name,
    #         "value": var_value
    #     }
    #     response = requests.post(url, headers=self.headers, json=payload, proxies=self.proxies)
    
    #     # Check response and log results
    #     if response.status_code in [200, 201]:

    #             self.logger.info(f"Repository-wide variable '{var_name}' created successfully.")
    #     else:
    #         self.logger.error(f"Failed to create/update variable '{var_name}': {response.text}")
    #         raise Exception(f"Failed to create/update variable '{var_name}': {response.text}")

    # def create_environment_variables(self, variables,repo_name):
    #     """
    #     Creates multiple environment variables in the GitHub repository or a specified environment.
        
    #     :param variables: Dictionary of variable names and values.
    #     """
    #     try:
    #         for var_name, var_value in variables.items():
    #             self.create_repo_env_var(var_name, var_value,repo_name)
    #         self.logger.info("Successfully created all environment variables.")
    #     except Exception as e:
    #         self.logger.error(f"Error creating environment variables: {e}")



    def create_repo_env_var(self, var_name, var_value, repo_name):
        """
        Create or update an environment variable in the repository.
        
        :param var_name: Name of the environment variable.
        :param var_value: Value of the environment variable.
        :param repo_name: Name of the repository.
        """
        # Check if the environment variable exists
        check_url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/actions/variables/{var_name}"
        check_response = requests.get(check_url, headers=self.headers, proxies=self.proxies)
        
        if check_response.status_code == 200:
            # Update the existing variable
            url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/actions/variables/{var_name}"
            payload = {"name": var_name, "value": var_value}
            response = requests.patch(url, headers=self.headers, json=payload, proxies=self.proxies)
            
            if response.status_code == 204:
                self.logger.info(f"Repository-wide variable '{var_name}' updated successfully.")
            else:
                self.logger.error(f"Failed to update variable '{var_name}': {response.text}")
                raise Exception(f"Failed to update variable '{var_name}': {response.text}")
        elif check_response.status_code == 404:
            # Create the variable if it does not exist
            url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/actions/variables"
            payload = {"name": var_name, "value": var_value}
            response = requests.post(url, headers=self.headers, json=payload, proxies=self.proxies)
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Repository-wide variable '{var_name}' created successfully.")
            else:
                self.logger.error(f"Failed to create variable '{var_name}': {response.text}")
                raise Exception(f"Failed to create variable '{var_name}': {response.text}")
        else:
            self.logger.error(f"Failed to check existence of variable '{var_name}': {check_response.text}")
            raise Exception(f"Failed to check existence of variable '{var_name}': {check_response.text}")


    def create_environment_variables(self, variables, repo_name):
        """
        Creates or updates multiple environment variables in the GitHub repository.
        
        :param variables: Dictionary of variable names and values.
        :param repo_name: Name of the repository.
        """
        try:
            for var_name, var_value in variables.items():
                self.create_repo_env_var(var_name, var_value, repo_name)
            self.logger.info("Successfully created or updated all environment variables.")
        except Exception as e:
            self.logger.error(f"Error creating or updating environment variables: {e}")
