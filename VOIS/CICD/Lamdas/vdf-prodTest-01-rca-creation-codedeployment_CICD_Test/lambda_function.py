import os
import logging
import warnings
import json
from github import GitHubHandler
from excel_handler import ExcelHandler
from orchestrator import Orchestrator
from sqs import SQS
from ssm import SSM
from helpers import Helper

warnings.filterwarnings("ignore")

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize SQS handler
sqs_handler = SQS(logger)
ssm_handler = SSM(logger)
helper = Helper(logger)

# Get Values from Paramater store
Github_Token_SSM   = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/GithubToken")
Github_OrgName_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/OrganizationName")



def lambda_handler(event, context):
    github_handler = GitHubHandler(logger)
    excel_handler = ExcelHandler(logger)
    orchestrator = Orchestrator(logger)

    for record in event['Records']:
        try:
            # Parse the SQS message
            data = json.loads(record['body'])
            logger.info(f"Processing data: {data}")
            ticket_id = data['id']
            custom_fields = data['custom_fields']

            file_path = ""
            # Extract values from custom fields
            repo_name = get_custom_field_value(custom_fields, "Github Repo Name")
            logger.info(f"Repository Name: {repo_name}")

            loader_count = get_custom_field_value(custom_fields, "Loader Max Count")
            worker_count = get_custom_field_value(custom_fields, "Worker Max Count")
            handoff_count = get_custom_field_value(custom_fields, "Handoff Max Count")



            # Extract values from custom fields
            with_lambda = get_custom_field_value(custom_fields, "with_lambda")
            logger.info(f"with_lambda value: {with_lambda}")



            processName = get_custom_field_value(custom_fields, "Process name")



            # Define the directory and pattern for finding the releasenote file
            directory_path = "Attached-releases"
            file_pattern = "_releasenote.xlsx"

            # Use GitHubHandler to list files in the specified directory path
            repo_files = github_handler.list_files_in_directory(repo_name, directory_path)
            matching_files = [f for f in repo_files if f.endswith(file_pattern)]

            if not matching_files:
                raise FileNotFoundError("No matching release note file found.")

            file_path = matching_files[0]  # Use the first matched file
            logger.info(f"Found file: {file_path}")

            # Fetch the file content from GitHub
            file_content = github_handler.fetch_file_from_github(file_path, repo_name)

            # Save the file temporarily
            tmp_path = excel_handler.save_to_temp(file_content)

            # Load the Excel file
            excel_data = excel_handler.read_excel(tmp_path)

            # Initialize a dictionary to store folder names and their IDs
            folder_ids = {}
            folders_paths = {}

            # Get the base folder path from the "Folders" sheet
            base_folder_path = excel_handler.get_folder_path_from_releasenote(excel_data)
            logger.info(f"Base Folder Path: {base_folder_path}")
            folders_paths = {"Parent_Folder": base_folder_path}

            # Create or get the parent folder ID
            folder_ids['Parent'] = orchestrator.ensure_folder_path_exists(base_folder_path)
            logger.info(f"Parent folder ID: {folder_ids['Parent']}")

            # Ensure loader_count, worker_count, and handoff_count are not None
            loader_count = int(loader_count) if loader_count is not None else 0
            worker_count = int(worker_count) if worker_count is not None else 0
            handoff_count = int(handoff_count) if handoff_count is not None else 0

            # Check counts and create folders with appropriate suffixes
            if worker_count >= 1:
                worker_folder_name = f"{base_folder_path}/{base_folder_path.split('/')[-1]}_Worker"
                folder_ids['Worker'] = create_and_save_folder(orchestrator, worker_folder_name)
                folders_paths["Worker_Folder"] = worker_folder_name

            if loader_count >= 1:
                loader_folder_name = f"{base_folder_path}/{base_folder_path.split('/')[-1]}_Loader"
                folder_ids['Loader'] = create_and_save_folder(orchestrator, loader_folder_name)
                folders_paths["Loader_Folder"] = loader_folder_name

            if handoff_count >= 1:
                handoff_folder_name = f"{base_folder_path}/{base_folder_path.split('/')[-1]}_Handoff"
                folder_ids['Handoff'] = create_and_save_folder(orchestrator, handoff_folder_name)
                folders_paths["Handoff_Folder"] = handoff_folder_name

            logger.info(f"Folder creation results: {folder_ids}")

            # Create environment variables on GitHub
            github_handler.create_environment_variables(folders_paths, repo_name)

            lambda_value = {"with_lambda": with_lambda}
            github_handler.create_environment_variables(lambda_value, repo_name)



            ticketID = {"ticket_id": str(ticket_id)}
            github_handler.create_environment_variables(ticketID, repo_name)


            process_name = {"process_name": processName}
            github_handler.create_environment_variables(process_name, repo_name)

            loaderCount = {"loader": str(loader_count)}
            github_handler.create_environment_variables(loaderCount, repo_name)

            workerCount = {"worker": str(worker_count)}
            github_handler.create_environment_variables(workerCount, repo_name)


            handoffCount = {"handoff":str(handoff_count)}
            github_handler.create_environment_variables(handoffCount, repo_name)


            # Retrieve data from the 'Assets' sheet and create assets
            assets_data = excel_handler.get_assets_data(excel_data)
            logger.info(f"Assets Data: {assets_data}")
            orchestrator.create_assets(assets_data, folder_ids)
            logger.info("After Assets Creation")

            # Retrieve data from the 'Queue' sheet and create queues
            queue_data = excel_handler.get_queue_data(excel_data)
            logger.info(f"Queue Data: {queue_data}")
            orchestrator.create_queues(queue_data, folder_ids["Parent"])


            # Return Error and Warning list
            Error_List=orchestrator.return_Errorlists()
            Warning_List=orchestrator.return_Warninglists()



            print("ERROR List :: ")
            print(Error_List)
            print("Warning List :: ")
            print(Warning_List)

            if Error_List:
                # Send success message to SQS
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="Rejected",
                    comment=f"Deployment Failed:\n {Error_List}"
                )
                logger.info(f"Failed processed ticket {ticket_id}")
                return {"statusCode": 200, "body": json.dumps({"error": "Failed processed ticket"})}

            else:

                if Warning_List:
                    print("warning list:")        
                    print(Warning_List)

                print("I'm HERE 2. >> ")
                # Send success message to SQS
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="In Progress",
                    comment="Second Stage - Done With the Orchestrator Infrastructure Creation"
                )

                # Get Kibana URLs
                print("releasenote path: ", tmp_path)
                DashboardURL, DestinationSpaceURL = helper.get_kibana_urls(tmp_path)
                print("Kibana Source url: ",DashboardURL)
                print("Kibana Destination url: ",DestinationSpaceURL)

                
                if not DashboardURL or not DestinationSpaceURL:
                    logger.error("Kibana URLs are missing. Exiting process.")
                    message = {"IssueID": issue_id, "Status": "rejected", "Message": "Kibana URLs are missing in the release notes."}
                    sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                    return
                
                # Format Kibana URLs to send to SQS
                kibana_fields_to_send = [
                {
                    "name": "Destination Space URL",
                    "value": DestinationSpaceURL
                },
                {
                    "name": "Dashboard URL", 
                    "value": DashboardURL
                }
                ]

                # Send Kibana URLs to SQS
                sqs_handler.send_to_kibana_func_prod(ticket_id=ticket_id,custom_fields=kibana_fields_to_send)
                logger.info(f"Deployment completed successfully for ticket_id: {ticket_id}, repo_name: {repo_name}")

                # Send Merge Request to SQS
                sqs_handler.send_to_merge_request_func_prod(ticket_id=ticket_id, custom_fields=custom_fields)
                logger.info(f"Successfully processed ticket {ticket_id}")
                #return {"statusCode": 200, "body": json.dumps("Processing completed successfully.")}

                
                sqs_handler.send_to_merge_request_func_prod(ticket_id=ticket_id, custom_fields=custom_fields)
                logger.info(f"Successfully processed ticket {ticket_id}")
                return {"statusCode": 200, "body": json.dumps("Processing completed successfully.")} 

         

        except Exception as e:
            logger.error(f"Error processing ticket {ticket_id}: {e}")
            sqs_handler.send_results_to_closure_func(
                ticket_id=ticket_id,
                ticket_status="rejected",
                comment=f"An error occurred: {str(e)}"
            )
   


# Function to create folder and return its ID
def create_and_save_folder(orchestrator, folder_name):
    folder_id = orchestrator.ensure_folder_path_exists(folder_name)
    logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
    return folder_id


def get_custom_field_value(custom_fields, field_name):
    for field in custom_fields:
        if field['name'] == field_name:
            return field['value']
    return None
