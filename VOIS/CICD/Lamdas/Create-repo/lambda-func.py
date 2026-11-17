import json
import requests
import os
import time
import logging
import botocore
from botocore.exceptions import ClientError
import boto3
from services.sqs import SQS
from services.ssm import SSM

# Define Logger Object
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# global variables
region_name = 'eu-central-1'

# Simulated SQS Handler (replace this with actual SQS handler in production)
# class SQS:
#     def __init__(self, logger):
#         self.logger = logger

#     def send_message(self, queue_name, message):
#         # Simulated SQS message sending (replace with actual SQS logic)
#         self.logger.info(f"Sending message to {queue_name}: {message}")

# Instantiate SQS Handler
sqs_handler = SQS(logger)
ssm_handler = SSM(logger)

# Define SQS Queue names
closure_sqs_name = "vdf-dev-01-sqs-rca-automated-redmine-ticket-status"
ews_sqs_name = "vdf-dev-01-sqs-rca-send-emails"
Github_token_SSM = ssm_handler.getparameter("/vdf-dev-01-params/rca/Github/GithubToken")
Github_OrgName_SSM = ssm_handler.getparameter("/vdf-dev-01-params/rca/Github/OrganizationName")
Github_Templatename_SSM = ssm_handler.getparameter("/vdf-dev-01-params/rca/Github/Templatename")
Github_TemplateLibraryname_SSM = ssm_handler.getparameter("/vdf-dev-01-params/rca/Github/TemplateLibraryName")


# Function to fetch repositories of an organization
def fetch_repositories(org_name, headers):
    github_api_url = f'https://api.github.com/orgs/{org_name}/repos'
    try:
        response = requests.get(github_api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        repos = response.json()
        repo_names = [repo['name'] for repo in repos]
        return repo_names
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f'Error fetching repositories: {str(http_err)}. Response: {response.text}')
    except requests.exceptions.RequestException as req_err:
        raise Exception(f'Error fetching repositories: {str(req_err)}')

# Function to list branches in the template repository
def list_branches_in_template(template_owner, template_repo, headers):
    github_branches_url = f'https://api.github.com/repos/{template_owner}/{template_repo}/branches'
    try:
        response = requests.get(github_branches_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        branches = response.json()
        branch_list = [{'name': branch['name'], 'commit_sha': branch['commit']['sha']} for branch in branches]
        return branch_list
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f'Error listing branches: {str(http_err)}. Response: {response.text}')
    except requests.exceptions.RequestException as req_err:
        raise Exception(f'Error listing branches: {str(req_err)}')

# Function to fetch the default branch commit SHA of a repository
def get_default_branch_commit_sha(new_owner, new_repo, headers):
    github_repo_url = f'https://api.github.com/repos/{new_owner}/{new_repo}'
    try:
        response = requests.get(github_repo_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        repo_data = response.json()
        default_branch = repo_data.get('default_branch', 'main')
        
        # Fetch the latest commit SHA on the default branch
        default_branch_url = f'https://api.github.com/repos/{new_owner}/{new_repo}/git/refs/heads/{default_branch}'
        response = requests.get(default_branch_url, headers=headers)
        response.raise_for_status()
        commit_sha = response.json()['object']['sha']
        return commit_sha
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error fetching commit SHA: {str(http_err)}. Response: {response.text}")
        return None

# Function to fetch the commit SHA of a specific branch in a repository
def get_branch_commit_sha(owner, repo, branch, headers):
    """
    Fetch the latest commit SHA for a given branch in a GitHub repository.

    :param owner: Repository owner/org
    :param repo: Repository name
    :param branch: Branch name to fetch SHA for
    :param headers: Authentication headers
    :return: Commit SHA string or None if failed
    """
    branch_url = f'https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}'
    try:
        response = requests.get(branch_url, headers=headers)
        response.raise_for_status()
        commit_sha = response.json()['object']['sha']
        return commit_sha
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error fetching commit SHA for branch '{branch}': {str(http_err)}. Response: {response.text}")
        return None
    except Exception as err:
        logger.error(f"Unexpected error fetching SHA for branch '{branch}': {str(err)}")
        return None

# Function to create a branch in the new repository
def create_branch_in_new_repo(new_owner, new_repo, branch_name, commit_sha, headers):
    github_create_branch_url = f'https://api.github.com/repos/{new_owner}/{new_repo}/git/refs'
    data = {
        "ref": f"refs/heads/{branch_name}",
        "sha": commit_sha
    }
    try:
        response = requests.post(github_create_branch_url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        logger.info(f"Branch '{branch_name}' created successfully.")
        return True
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error creating branch '{branch_name}': {str(http_err)}. Response: {response.text}")
        return False



# Function to create a repository from a template
def create_repository_from_template(org_name, repo_name, template_owner, template_repo, headers):
    github_create_repo_url = f'https://api.github.com/repos/{template_owner}/{template_repo}/generate'
    data = {
        "owner": org_name,
        "name": repo_name,
        "private": True,
        "description": f"Created from template '{template_repo}'"
    }
    try:
        response = requests.post(github_create_repo_url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Repository '{repo_name}' created successfully from template '{template_repo}'.")
        time.sleep(5)
        return True
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error creating repository: {str(http_err)}. Response: {response.text}")
        return False









# Function to add repository to a team
def add_repo_to_team(org_name, team_slug, repo_name, owner, permission, headers):
    url = f"https://api.github.com/orgs/{org_name}/teams/{team_slug}/repos/{owner}/{repo_name}"
    data = {
        "permission": permission  # e.g., "pull", "push", or "admin"
    }
    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 204:
        logger.info(f"Successfully added {repo_name} to {team_slug} with {permission} permissions.")
        return True
    else:
        logger.error(f"Failed to add {repo_name} to {team_slug}. Status code: {response.status_code}")
        logger.error(response.text)
        return False

#Pass Records as dict for easy access      
def get_custom_field_value(custom_fields, field_name):
    # Iterate over custom_fields to find the matching field by name
    for field in custom_fields:
        if field['name'] == field_name:
            return field['value']
    return None  # Return None if the field is not found
    
def get_key_from_value(d, target_value):
    for key, value in d.items():
        if value == target_value:
            return key
    return None  # Return None if the value is not found
        
        

# Main Lambda handler function
def lambda_handler(event, context):
    issue_id = ""
    roles_dict = {"Operations Change Manager":["ao-cm","ao"],
                  "Operations":["ao-cm","ao"],
                  "AD Developer/Senior Developer":["ad-developers","ad-seniors"],
                  "LM UK Developer/Senior Developer":["uk-developers","uk-seniors"],
                  "LM IT Developer/Senior Developer":["it-developers","it-seniors"],
                  "LM PT Developer/Senior Developer":["pt-developers","pt-seniors"],
                  "LM RO Developer/Senior Developer":["ro-developers","ro-seniors"],
                  "LM VNO Developer/Senior Developer":["vno-developers","vno-seniors"],
                  "DevOps":["devops"]
                  
                  }
    try:
        print("json dumpppssss",json.dumps(event))
        for record in event['Records']:
            record_body_in_json = json.loads(record["body"].replace("\'", "\""))
            logger.info(f"Record Body: {record_body_in_json}")
            issue_id = record_body_in_json["id"]
            custom_fields = record_body_in_json['custom_fields']
            org_name = Github_OrgName_SSM
            process_name = get_custom_field_value(custom_fields, 'Process Name').strip()
            process_market = get_custom_field_value(custom_fields, 'Process Market')
            process_function = get_custom_field_value(custom_fields, 'Process Function')
            ppm_id = get_custom_field_value(custom_fields, 'PPM ID').strip()
            repo_name = ppm_id + "_" + process_function + "_" + process_market + "_" + process_name
            # team_slug = roles_dict[record_body_in_json["team_slug"]]
            profile_role = get_custom_field_value(custom_fields, 'User Role')
            print("Profilr ROLLLEE IS ",profile_role)
            team_slugs = roles_dict.get(profile_role, 'default_team_slug')  # Use 'default_team_slug' if role not found
            print(f"Profile Role: {profile_role}, Team Slug: {team_slugs}")
            Process_template_repo_name = Github_Templatename_SSM
            Library_repo_name = Github_TemplateLibraryname_SSM
            a = "RPA"
            Repo_Type = get_custom_field_value(custom_fields, 'Repository Type')
            if Repo_Type == "Process":
                template_repo_name =  Process_template_repo_name
                repo_name = ppm_id + "_" + process_function + "_" + process_market + "_" + process_name
            else:
                template_repo_name = Library_repo_name
                repo_name = "Lib"+"_"+process_function + "_" + process_market + "_" + process_name
            


            # Fetch GitHub token from environment variables
            # github_token = os.getenv("GITHUB_TOKEN")
            github_token = Github_token_SSM
            if not github_token:
                raise Exception("GitHub token is missing.")

            # Headers for GitHub API
            headers = {
                'Authorization': f'Bearer {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }

            # Check if repository already exists
            if repo_name in fetch_repositories(org_name, headers):
                message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Repository '{repo_name}' already exists."}
                sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                return f"Repository '{repo_name}' already exists."

            # Create repository from template
            if create_repository_from_template(org_name, repo_name, org_name, template_repo_name, headers):
                # Get default branch SHA
                default_branch_sha = get_default_branch_commit_sha(org_name, repo_name, headers)
                if not default_branch_sha:
                    message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Failed to retrieve default branch commit SHA for '{repo_name}'."}
                    sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                    return

                # Create additional branches
                branches_to_create = ['develop', 'release','hc-deployment','prod-changes']
                for branch in branches_to_create:
                    branch_sha = get_branch_commit_sha(org_name, template_repo_name, branch, headers)
                    print("Branch SHA: ",branch_sha)
                    if not create_branch_in_new_repo(org_name, repo_name, branch, branch_sha, headers):
                        message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Failed to create branch '{branch}' in repository '{repo_name}'."}
                        sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                        return

                # Add repository to team if created successfully
                for team_slug in team_slugs:
                    if team_slug == "devops":
                        team_permission = "admin"
                    else:
                        team_permission = "push"
                    if add_repo_to_team(org_name, team_slug, repo_name, org_name, team_permission, headers):
                        print("Add to ",team_slug)
                        # message = {"IssueID": issue_id, "Status": "resolved", "Message": f"Repository '{repo_name}' created, branches added, and added to team '{team_slug}'."}
                        # sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                        # return f"Repository '{repo_name}' created, branches added, and added to team '{team_slug}'."
                    else:
                        message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Failed to add repository '{repo_name}' to team '{team_slug}'."}
                        sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                message = {"IssueID": issue_id, "Status": "resolved", "Message": f"Repository '{repo_name}' created, branches added, and added to team '{get_key_from_value(roles_dict,team_slugs)}'."}
                sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                return f"Repository '{repo_name}' created, branches added, and added to team '{get_key_from_value(roles_dict,team_slugs)}'."        
            else:
                message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Failed to create repository '{repo_name}'."}
                sqs_handler.send_message(closure_sqs_name, json.dumps(message))

    except botocore.exceptions.ClientError as e:
        logger.error(f"ClientError: {e.response['Error']['Message']}")
        message = {"IssueID": issue_id, "Status": "rejected", "Message": f"ClientError: {e.response['Error']['Message']}"}
        sqs_handler.send_message(closure_sqs_name, json.dumps(message))

    except Exception as e:
        logger.error(f"Exception: {e}")
        message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Exception: {e}"}
        sqs_handler.send_message(closure_sqs_name, json.dumps(message))

