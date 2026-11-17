import os
import json
import requests
import logging


class GitHubOrganization:
    def __init__(self, logger):
        self.logger = logger
        self.org_name = "VFGTVOIS-IAP-RPA"  # Organization name
        # self.create_token = os.getenv('CREATE_GITHUB_TOKEN')  # Token for creating PR
        # self.approve_token = os.getenv('APPROVE_GITHUB_TOKEN')  # Token for approving PR
        self.create_token = "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"
        self.approve_token = "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"

        self.github_api_url = "https://api.github.com"  # GitHub API URL
        self.create_headers = {
            'Authorization': f'token {self.create_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        self.approve_headers = {
            "Authorization": f'token {self.approve_token}',          # PAT or GitHub App installation token
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "your-app/approve-pr"
        }
        self.logger.info(f"Initialized GitHubOrganization for org: {self.org_name}")

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
            response = requests.post(url, headers=self.create_headers, json=payload)
            response.raise_for_status()
            pr_data = response.json()
            self.logger.info(f"Pull request created successfully: {pr_data['html_url']}")
            return pr_data  # Returns PR data if successful
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error creating pull request: {e}")
            raise

    def approve_pull_request(self, repo_name, pr_number):
        """Approve a pull request in a specific repository within the GitHub organization."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}/reviews"
        payload = {
            "event": "APPROVE",
            "body": "Approved via automated system"
        }

        try:
            response = requests.post(url, headers=self.approve_headers, json=payload)
            #########################################################
            if response.status_code == 422:
                error_details = response.json() if response.content else {}
                self.logger.error(f"422 Error details: {error_details}")
                self.logger.error(f"Request payload: {payload}")
                self.logger.error(f"Request headers: {self.approve_headers}")
            response.raise_for_status()
            review_data = response.json()
            self.logger.info(f"Pull request #{pr_number} approved successfully.")
            return review_data  # Returns review data if successful
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error approving pull request: {e}")
            raise

    def squash_and_merge_pull_request(self, repo_name, pr_number, commit_title, commit_message, force=True):
        """Squash and merge a pull request in a specific repository within the GitHub organization."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}/merge"
        payload = {
            "merge_method": "squash",
            "commit_title": commit_title,
            "commit_message": commit_message
        }

        try:
            response = requests.put(url, headers=self.create_headers, json=payload)
            if response.status_code == 405:  # Conflict detected
                self.logger.warning(f"Conflicts detected for PR #{pr_number}. Attempting to resolve conflicts...")
                if force:
                    self.resolve_conflicts(repo_name, pr_number)
                    # Retry squash and merge after resolving conflicts
                    self.squash_and_merge_pull_request(repo_name, pr_number, commit_title, commit_message, force=True)
                else:
                    raise Exception("Merge conflict. Manual resolution required.")
            elif response.status_code == 409:  # Method not allowed
                self.logger.error(f"Squash and merge not allowed for PR #{pr_number}. Check repository settings.")
                raise Exception("Squash and merge not allowed. Check repository settings.")
            else:
                response.raise_for_status()
                merge_data = response.json()
                self.logger.info(f"Pull request #{pr_number} squashed and merged successfully.")
                return merge_data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error squashing and merging pull request: {e}")
            raise

    def resolve_conflicts(self, repo_name, pr_number):
        """Resolve conflicts by adding missing files/folders from the head branch to the base branch."""
        base_branch, head_branch = self.get_branch_details(repo_name, pr_number)
        files = self.get_pr_files(repo_name, pr_number)

        for file in files:
            file_path = file['filename']
            file_status = file['status']

            if file_status in ['modified', 'added']:
                # Get the content from the head branch
                head_content = self.get_file_contents(repo_name, file_path, head_branch)

                if head_content:
                    head_decoded = head_content['content']

                    # Check if the file exists in the base branch
                    base_file = self.get_file_contents(repo_name, file_path, base_branch)

                    if base_file:
                        # Update the file in the base branch to resolve conflicts
                        self.update_file_contents(
                            repo_name,
                            file_path,
                            head_decoded,
                            f"Resolve conflict in {file_path} by using head branch content",
                            base_branch,
                            base_file['sha']
                        )
                    else:
                        # Add the missing file to the base branch
                        self.create_file_in_branch(
                            repo_name,
                            file_path,
                            head_decoded,
                            f"Add missing file {file_path} from head branch to resolve conflict",
                            base_branch
                        )
                else:
                    self.logger.warning(f"Unable to fetch content for {file_path} in {head_branch}")

        self.logger.info(f"Conflicts resolved in pull request #{pr_number}.")

    def create_file_in_branch(self, repo_name, path, content, message, branch):
        """Create a new file in the repository."""
        url = f"{self.get_repo_url(repo_name)}/contents/{path}"
        payload = {
            "message": message,
            "content": content,
            "branch": branch
        }
        response = requests.put(url, headers=self.create_headers, json=payload)
        response.raise_for_status()
        return response.json()

    def update_file_contents(self, repo_name, path, content, message, branch, sha):
        """Update an existing file in the repository."""
        url = f"{self.get_repo_url(repo_name)}/contents/{path}"
        payload = {
            "message": message,
            "content": content,
            "branch": branch,
            "sha": sha
        }
        response = requests.put(url, headers=self.create_headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_pr_files(self, repo_name, pr_number):
        """Retrieve the list of files in a pull request."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.create_headers)
        response.raise_for_status()
        return response.json()

    def get_file_contents(self, repo_name, path, branch):
        """Get the contents of a file in a specific branch."""
        url = f"{self.get_repo_url(repo_name)}/contents/{path}"
        response = requests.get(url, headers=self.create_headers, params={"ref": branch})
        if response.status_code == 404:
            return None  # File does not exist in the branch
        response.raise_for_status()
        return response.json()

    def get_branch_details(self, repo_name, pr_number):
        """Retrieve branch details for a pull request."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}"
        response = requests.get(url, headers=self.create_headers)
        response.raise_for_status()
        pr_data = response.json()
        return pr_data['base']['ref'], pr_data['head']['ref']

    def get_pull_request_info(self, repo_name, pr_number):
        """Get detailed information about a pull request."""
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}"
        try:
            response = requests.get(url, headers=self.create_headers)
            response.raise_for_status()
            pr_data = response.json()
            self.logger.info(f"PR #{pr_number} state: {pr_data.get('state')}, "
                           f"mergeable: {pr_data.get('mergeable')}, "
                           f"author: {pr_data.get('user', {}).get('login')}")
            return pr_data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching PR info: {e}")
            raise

    def approve_pull_request_by_pr(self, repo_name, pr_number):
        """
        Approve a pull request in a specific repository within the GitHub organization.

        Args:
            repo_name (str): The name of the repository.
            pr_number (int): The number of the pull request to approve.

        Returns:
            dict: The response data from the GitHub API for the approval action.
        """
        # API endpoint for approving a pull request
        url = f"{self.get_repo_url(repo_name)}/pulls/{pr_number}/reviews"
        payload = {
            "event": "APPROVE",  # Action to approve the pull request
            "body": "Approved via automated system"
        }

        try:
            # Send a POST request to approve the pull request
            response = requests.post(url, headers=self.approve_headers, json=payload)
            if response.status_code == 422:
                error_details = response.json() if response.content else {}
                self.logger.error(f"422 Error details: {error_details}")
                self.logger.error(f"Request payload: {payload}")
                self.logger.error(f"Request headers: {self.approve_headers}")
            response.raise_for_status()  # Raise an exception for HTTP errors
            review_data = response.json()
            self.logger.info(f"Pull request #{pr_number} approved successfully.")
            return review_data  # Return the response data
        except requests.exceptions.RequestException as e:
            # Log any errors encountered during the request
            self.logger.error(f"====> github >>  Error approving pull request #{pr_number}: {e}")
            raise



    # def check_comments_and_approve_pr(self, repo_name, pr_number, target_users, target_comment):
    def check_comments_and_approve_pr(self, repo_name, pr_number, target_team, target_comment):
        """
        # Check the comments on a pull request for a specific comment from specific users
        Check the comments on a pull request for a specific comment from team members
        and approve the pull request if the conditions are met.

        Args:
            repo_name (str): The name of the repository.
            pr_number (int): The number of the pull request.
            # target_users (list): A list of usernames to check for comments.
            target_team (str): The GitHub team slug to check for member comments.
            target_comment (str): The specific comment to check for.

        Returns:
            dict: The response from the approval API if approved, or None if conditions are not met.
        """
        # First, get PR information to check its state
        try:
            pr_info = self.get_pull_request_info(repo_name, pr_number)
            if pr_info.get('state') != 'open':
                self.logger.error(f"PR #{pr_number} is not open (state: {pr_info.get('state')})")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get PR info: {e}")
            return None

        team_members = self.get_team_members(target_team)
        if not team_members:
            self.logger.error(f"No members found for team '{target_team}' or error fetching team members")
            return None

        # URL to fetch comments on the pull request
        url = f"{self.get_repo_url(repo_name)}/issues/{pr_number}/comments"

        try:
            # Fetch all comments on the pull request
            response = requests.get(url, headers=self.create_headers)
            response.raise_for_status()
            comments = response.json()

            self.logger.info(comments)
            self.logger.info(f"Found {len(comments)} comments on PR #{pr_number}")

            # Iterate through comments and check if any target user made the target comment
            for comment in comments:
                commenter = comment['user']['login']
                comment_body = comment['body']
                self.logger.info(commenter)
                self.logger.info(comment_body)

                self.logger.info(f"Checking comment by {commenter}: {comment_body}")
                
                if commenter in team_members and target_comment.lower() in comment_body.lower():
                    self.logger.info(f"Found matching comment by team member {commenter}: {comment_body}")
                # if commenter in target_users and target_comment.lower() in comment_body.lower():
                #     self.logger.info(f"Found matching comment by {commenter}: {comment_body}")
                    # Approve the pull request
                    approval_response = self.approve_pull_request(repo_name, pr_number)
                    self.logger.info(f"Pull request #{pr_number} approved successfully.")
                    return self.squash_and_merge_pull_request(repo_name,pr_number,commit_title="Squashed Commit Title",commit_message="This commit includes all changes from the pull request.")

            # self.logger.info(f"No matching comment found on pull request #{pr_number}.")
            self.logger.info(f"No matching comment found from team '{target_team}' members on pull request #{pr_number}.")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"======>>>>Error checking comments on pull request #{pr_number}: {e}")
            raise



    def get_team_members(self, team_slug):
        """
        Get all members of a GitHub team.
        
        Args:
            team_slug (str): The team slug (team name in lowercase with hyphens)
            
        Returns:
            list: List of team member usernames, or empty list if error
        """
        url = f"{self.github_api_url}/orgs/{self.org_name}/teams/{team_slug}/members"
        
        try:
            response = requests.get(url, headers=self.create_headers)
            response.raise_for_status()
            members_data = response.json()
            
            team_members = [member['login'] for member in members_data]
            self.logger.info(f"Found {len(team_members)} members in team '{team_slug}': {team_members}")
            return team_members
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching team members for '{team_slug}': {e}")
            return []