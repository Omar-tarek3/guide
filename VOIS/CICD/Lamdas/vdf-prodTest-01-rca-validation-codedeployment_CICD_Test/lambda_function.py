import json
import pandas as pd
from io import StringIO
import logging
import warnings
import os


# my own modules
from services.github import GitHub
from services import Redmine
from services.GeneralF import *
from services.helper import Helper
from services.s3 import S3
from services.sqs import SQS
from services.sns import SNS
from services.orchestrator import orchestrator
from services.ssm import SSM

# Ignore all warnings
warnings.filterwarnings("ignore")

# logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# sns ARN (uncomment if needed)
# sns_arn = "arn:aws:sns:eu-central-1:264313199387:RCA-Prod-Tickets-Updates"

# handlers
redmine_handler = Redmine.Redmine(logger)
sqs_handler = SQS(logger)
s3_handler = S3(logger)
h = Helper(logger)
sns_handler = SNS(logger)
orch_handler = orchestrator(logger)
ssm_handler = SSM(logger)

# release note model file link
ReleaseNoteModelfile = "https://vodafone.sharepoint.com/:X:/s/VF-DevOps/EekmkkHskxVGtkHuw9wNebgB46yedWdv8QluM8Tmntx_Wg?e=r1Ujo7"

# Get Values from Paramater store
Github_Token_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/GithubToken")
Github_OrgName_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/OrganizationName")


def lambda_handler(event, context):
    for record in event["Records"]:
        data = json.loads(record["body"])
        ticket_id = data.get("id")
        custom_fields = []
        with_lambda_value = ""

        
        try:
            # Step 1: Retrieve Issue Details from Redmine
            automation_approved_status = redmine_handler.get_issue_details(ticket_id)
            if not automation_approved_status:
                logger.error("Proxy issue, back to the DevOps team.")
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment="Proxy issue, back to the DevOps team."
                )
                return {"statusCode": 404, "body": "Proxy issue, back to the DevOps team."}

            custom_fields = automation_approved_status["issue"]["custom_fields"]
            attachments_array = automation_approved_status["issue"]["attachments"]
            logger.info(f"Attachments: {attachments_array}")
            repo_name=h.custom_fields_value("Github Repo Name",custom_fields)
            
            # Step 1: Check GitHub Repository Existence
            github = GitHub(
                logger,
                token= Github_Token_SSM,
                repo_owner=Github_OrgName_SSM,
                repo_name=repo_name
                
            )

            repo_check = github.check_repo_exists()
            if repo_check["statusCode"] != 200:
                logger.error("GitHub repository does not exist.")
                # Send closure message to SQS
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment="GitHub repository does not exist. The ticket has been closed."
                )
                # Close the ticket in Redmine
                return {"statusCode": 404, "body": json.dumps({"error": "GitHub repository does not exist. The ticket has been closed."})}
            
            # Step 2: Retrieve Issue Details from Redmine
            automation_approved_status = redmine_handler.get_issue_details(ticket_id)
            if not automation_approved_status:
                logger.error("Proxy issue, back to the DevOps team.")
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment="Proxy issue, back to the DevOps team."
                )
                return {"statusCode": 404, "body": "Proxy issue, back to the DevOps team."}

            custom_fields = automation_approved_status["issue"]["custom_fields"]
            attachments_array = automation_approved_status["issue"]["attachments"]
            logger.info(f"Attachments: {attachments_array}")

            # Step 3: Check for `project.json` in Specific Directories
            loader_count = int(h.custom_fields_value("Loader Max Count",custom_fields) or 0)
            worker_count = int(h.custom_fields_value("Worker Max Count",custom_fields) or 0)
            handoff_count = int(h.custom_fields_value("HandOff Max Count",custom_fields) or 0)
            print("Loader Count: ",loader_count)
            print("Worker Count: ",worker_count)
            print("handoff Count: ",handoff_count)

            folders_to_check = []
            if loader_count > 0:
                folders_to_check.append("RPA_Loader")
            if worker_count > 0:
                folders_to_check.append("RPA_Worker")
            if handoff_count > 0:
                folders_to_check.append("RPA_Handoff")

            # Verify `project.json` exists in each specified folder
            directory_path = ""
            target_file = "project.json"
            for folder in folders_to_check:
                project_check = github.check_file_exists(
                    directory_path=f"{folder}/Code",
                    target_file="project.json",
                    branch="develop"
                )
                directory_path=f"{folder}/Code"
                if project_check["statusCode"] != 200:
                    logger.error(f"`project.json` does not exist in the {folder} folder.")
                    sqs_handler.send_results_to_closure_func(
                        ticket_id=ticket_id,
                        ticket_status="Rejected",
                        comment=f"The project does not exist in the {folder} folder."
                    )
                    # Optionally, close the ticket in Redmine
                    return {"statusCode": 404, "body": json.dumps({"error": f"`project.json` does not exist in the {folder} folder."})}
                else:

                    download_ProjectjSON = github.download_file(
                        file_path=directory_path+"/"+target_file,
                        local_path="/tmp/"+target_file,
                        branch="develop"
                    )
                    print("JSONNN",download_ProjectjSON)
                    Package_name = h.read_json_file_and_extract_name("/tmp/"+target_file)
                    print(Package_name)
                    Package_Exist = orch_handler.check_package_exists(Package_name)
                    if Package_Exist:
                        logger.error(f"`project.json` does not exist in the {folder} folder.")
                        sqs_handler.send_results_to_closure_func(
                            ticket_id=ticket_id,
                            ticket_status="Rejected",
                            comment=f"Package '{Package_name}' already exists in the Orchestrator."
                        )
                        return {"statusCode": 404, "body": json.dumps({"error": f"Package '{Package_name}' already exists."})}


            # Step 4: Check for Release Note Existence
            file_pattern = "_releasenote.xlsx"
            directory_path="Attached-releases"
            repo_files = github.list_files_in_directory(directory_path)
            matching_files = [f for f in repo_files if f.endswith(file_pattern)]
            if not matching_files:
            #  if file_check["statusCode"] != 200:
                logger.error("Release notes file does not exist in the repository.")
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment="Release notes file does not exist in the repository."
                )
                return {"statusCode": 404, "body": json.dumps({"error": "Release notes file does not exist in the repository."})}
            file_path = matching_files[0]
            file_name = os.path.basename(file_path)
            print("FILE PATH",file_name)
            # Step 5: Download the Release Notes File
            download_result = github.download_file(
                file_path=file_path,
                local_path="/tmp/"+file_name,
                branch="develop"
            )
            if download_result["statusCode"] != 200:
                logger.error("Failed to download the release notes file.")
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment="Failed to download the release notes file."
                )
                return {"statusCode": 500, "body": "Failed to download the release notes file."}

            # Step 6: Validate Release Notes
            error_list = h.releasenote_validator(file_name,"", custom_fields)
            print("ERROOORRR LISTTTTT111111",error_list)
            if error_list != True:
                print("ERROOORRR LISTTTTT",error_list)
                error_string = "\n".join(error_list)
                logger.error(f"Release note validation failed: {error_string}")
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment=f"Release note validation failed:\n{error_string}\nPlease check our constraints and rules in this link: {ReleaseNoteModelfile}"
                )
                return {"statusCode": 400, "body": json.dumps({"error": "Release note validation failed.", "details": error_string})}
            else:
                logger.info("Release note passed successfully and is valid.")
            
            # Step 7: Additional Processing Based on `with_lambda_value`
            with_lambda_value = h.custom_fields_value('with_lambda', custom_fields)
            if with_lambda_value == "1":
                # file_pattern = "Parameters.xlsx"
                # # directory_path="RPA_Loader/Loader"
                # Attached-releases
                # directory_path="Attached-releases"

                # repo_files = github.list_files_in_directory(directory_path)
                # matching_files = [f for f in repo_files if f.endswith(file_pattern)]
                # if not matching_files:
                #     logger.error("Paramaters file does not exist in the repository.")
                #     sqs_handler.send_results_to_closure_func(
                #         ticket_id=ticket_id,
                #         ticket_status="Rejected",
                #         comment="Paramaters file does not exist in the repository."
                #     )
                #     return {"statusCode": 404, "body": json.dumps({"error": "Paramaters file does not exist in the repository."})}
                # print("Done also")
                # logger.info("WITH LAMBDA: Proceeding to next part for DEV.")


                # Define the directory and pattern for finding the releasenote file
                directory_path = "Attached-releases"
                file_pattern = "Parameters.xlsx"

                # Use GitHubHandler to list files in the specified directory path
                repo_files = github.list_files_in_github_directory(repo_name, directory_path)
                matching_files = [f for f in repo_files if f.endswith(file_pattern)]

                if not matching_files:
                    raise FileNotFoundError("Paramaters file does not exist in the repository.")

                file_path = matching_files[0]  # Use the first matched file
                logger.info(f"Found file: {file_path}")

                # Fetch the file content from GitHub
                file_content = github.fetch_file_from_github(file_path, repo_name)

            else:
                print("DONNNNNNNNNNEEE")
                sqs_handler.send_results_to_closure_func(
                ticket_id=ticket_id,
                ticket_status="In Progress",
                comment=f"First Stage - Done With the Validation")
                print("iddddddd",ticket_id)



                logger.info("NO LAMBDA: Proceeding to next part for PROD.")

            logger.info("Validation and processing completed successfully.")
            
            
            
            # Fetch all groups
            groups = redmine_handler.get_groups()
            
            # Print all groups and their IDs
            for group in groups:
                print(f"Group ID: {group['id']}, Name: {group['name']}")
            
            # Find a specific group by name
            specific_group = next((group for group in groups if group['name'] == "DM Test"), None)
            if specific_group:
                print(f"Found group: {specific_group['name']}, ID: {specific_group['id']}")
            else:
                print("Group not found.")
                
            group_id = int(specific_group['id'])    
            print(type(group_id))

            response=redmine_handler.set_issue_assignee(ticket_id, group_id )
            print("hii hii")
            print(response.status_code)
            if response.status_code == 204:
                print("Assignee updated successfully.")
                sqs_handler.send_results_to_closure_func(ticket_id=ticket_id,ticket_status="Awaiting_DM_SM_Approval",comment="Validation completed successfully. The ticket is now awaiting necessary approvals from DM/SM.")                
      
            else:
                print("Failed to update assignee.")
            
                
            
            # #end

        except Exception as e:
            logger.exception("An error occurred during processing.")
            sqs_handler.send_results_to_closure_func(
                ticket_id=ticket_id,
                ticket_status="Rejected",
                comment=f"An error occurred: {str(e)}. Please ensure the release note is valid and contains all necessary sheets."
            )
            return {"statusCode": 500, "body": json.dumps({"error": "An unexpected error occurred.", "details": str(e)})}

    return {"statusCode": 200, "body": json.dumps("Processing completed successfully.")}
