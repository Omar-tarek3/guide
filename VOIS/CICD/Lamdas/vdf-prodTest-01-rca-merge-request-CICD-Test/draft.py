import os
import json
import requests
import time


class GitHubOrganization:
    def __init__(self, logger):
        self.logger = logger
        self.org_name = "VFGroup-IT4ITPlatformEngineering"  # Organization name
        self.create_token = os.getenv('CREATE_GITHUB_TOKEN')  # Token for creating PR
        self.approve_token = os.getenv('APPROVE_GITHUB_TOKEN')  # Token for approving PR
        
        self.github_api_url = "https://api.github.com"  # GitHub API URL
        self.create_headers = {
            'Authorization': f'token {self.create_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.approve_headers = {
            'Authorization': f'token {self.approve_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.logger.info(f"Initialized GitHubOrganization for org: {self.org_name}")
        self.flag = 0

    def get_repo_url(self, repo_name):
        """Generate the full URL for the specified repository in the organization."""
        return f"{self.github_api_url}/repos/{self.org_name}/{repo_name}"

    def create_pull_request(self, repo_name, base_branch, head_branch, title, body=""):
        """Create a pull request in a specific repository within the GitHub organization."""
        url = f"{self.get_repo_url(repo_name)}/pulls"
        payload = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
        }

        try:
            # Make the API request with the create token
            response = requests.post(url, headers=self.create_headers, json=payload)
            response.raise_for_status()
            pr_data = response.json()
            self.logger.info(f"Pull request created successfully: {pr_data['html_url']}")
            return pr_data  # Returns PR data if successful
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error creating pull request: {e}")
            raise  # Re-raise the exception to handle it later

    def approve_pull_request(self, repo_name, pr_number):
        """Approve a pull request in a specific repository within the GitHub organization."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}/reviews"
        payload = {
            "event": "APPROVE"
        }

        try:
            # Make the API request with the approve token
            response = requests.post(url, headers=self.approve_headers, json=payload)
            response.raise_for_status()
            review_data = response.json()
            self.logger.info(f"Pull request #{pr_number} approved successfully.")
            return review_data  # Returns review data if successful
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error approving pull request: {e}")
            raise  # Re-raise the exception to handle it later
    def squash_and_merge_pull_request(self, repo_name, pr_number, commit_title, commit_message):
        """Squash and merge a pull request in a specific repository within the GitHub organization."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}/merge"
        payload = {
            "merge_method": "squash",
            "commit_title": commit_title,
            "commit_message": commit_message
        }

        try:
            response = requests.put(url, headers=self.create_headers, json=payload)
            response.raise_for_status()
            merge_data = response.json()
            self.logger.info(f"Pull request #{pr_number} squashed and merged successfully.")
            return merge_data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error squashing and merging pull request: {e}")
            raise        
