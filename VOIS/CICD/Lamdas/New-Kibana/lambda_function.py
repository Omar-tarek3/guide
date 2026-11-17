#!/usr/bin/env python
# -*- coding: utf-8 -*-
import boto3
import ssl
import requests
import json
import os
from json import dumps as json_dumps, loads as json_loads
from json.decoder import JSONDecodeError
import botocore
from botocore.exceptions import ClientError
from Services.sqs import SQS
from Services.ssm import SSM
from Services.github import GitHub
from Services.helper import Helper
import logging
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Global variables
region_name = 'eu-central-1'

# Define Logger Object
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sqs_handler = SQS(logger)
ssm_handler = SSM(logger)
helper = Helper(logger)
closure_sqs_name = "vdf-prod-01-sqs-rca-automated-redmine-ticket-status"

# Retrieve API keys
key = ssm_handler.getparameter("/vdf-prod-01-params/kibana/api_key")
api_key = 'ApiKey ' + str(key)
key_dev = ssm_handler.getparameter("/vdf-dev-01-params/kibana/api_key")
api_key_dev = 'ApiKey ' + str(key_dev)

print(api_key)
print(api_key_dev)

Github_Token_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/GithubToken")
Github_OrgName_SSM = ssm_handler.getparameter("/vdf-prod-01-params/rca/Github/OrganizationName")

print("github token is ",Github_Token_SSM)
print("github org name is ",Github_OrgName_SSM)

proxies = {"https": "vpce-0974f7457e940e4bf-0s4t8nsz.vpce-svc-0ffc3575422275d21.eu-central-1.vpce.amazonaws.com:8081"}

# helper = Helper(logger)

def custom_fields_value(name, custom_fields):
    for item in custom_fields:
        if item['name'] == name:
            return item['value']

def extract_info_from_ndjson(ndjson_path):
    New_function = "kibana | selectFilter"
    deprecated_function = "filters"
    print("Reading exported ndjson")
    with open(ndjson_path, 'r', encoding='utf-8') as file:
        for line in file:
            data = json.loads(line)
            if 'type' in data and data['type'] == "index-pattern":
                print("index value extracting")
                index_value = data['attributes']['title'].lower()
                print("index title is " + index_value)
            if 'type' in data and data['type'] == "canvas-workpad":
                print("🔎 start extract canvas-workpad")
                canvasworkpadtitle = data['attributes']['name']
                print("canvas-workpad title is " + canvasworkpadtitle)
                if 'attributes' in data and 'pages' in data['attributes']:
                    for page in data["attributes"]["pages"]:
                        for element in page["elements"]:
                            expression = element.get("expression")
                            if expression and "filters" in expression:
                                element["expression"] = expression.replace(deprecated_function, New_function)
                if 'attributes' in data and 'variables' in data['attributes']:
                    for index, variables in enumerate(data['attributes']["variables"]):
                        if variables['name'] == "process_identifier":
                            processIdentifier = data['attributes']["variables"][index]["value"]
                            break
                print("processidentifier is " + processIdentifier)
                print("canvas-workpad extracted successfully ✅")
            if 'type' in data and data['type'] == "visualization":
                print("🔎 start extract visualization")
                visualizationtitle = data['attributes']['title']
                print("visualization title is " + visualizationtitle)
                for reference in data["references"]:
                    if "id" in reference:
                        if index_value.startswith('default'):
                            new_reference_id = 'aa52758b-a219-4810-bc1b-d52e255dc298'
                        else:
                            new_reference_id = 'ab269859-c04d-4cb9-86ac-9e02e888c081'
                        reference["id"] = new_reference_id
                print("visualization extracted successfully ✅")
            if 'type' in data:
                with open("/tmp/exported_" + data['type'] + ".ndjson", 'w', encoding='utf-8') as json_file:
                    json.dump(data, json_file)
    return canvasworkpadtitle, visualizationtitle, processIdentifier

def lambda_handler(event, context):
    issue_id = ""
    try:
        print("Starting ...")
        for record in event['Records']:
            data = json.loads(record['body'])
            logger.info(f"data {data}")  # Log the entire data dictionary
            # Extract ticket_id and repo_name
            ticket_id = data.get('custom_fields', {}).get('ticket_id', None)
            repo_name = data.get('custom_fields', {}).get('repo_name', None)
            issue_id=ticket_id

            # Print extracted details
            print(f"ticket_id is {ticket_id}")
            print(f"repo_name is {repo_name}")       
           


            # record_body_in_json = json.loads(record["body"])
            # issue_id = record_body_in_json["id"]
            # ticket_id = record_body_in_json["id"]
            # print(issue_id)
            # custom_fields = record_body_in_json["custom_fields"]



            # Initialize GitHub and Helper instances
            github = GitHub(
                    token=Github_Token_SSM,
                    repo_owner=Github_OrgName_SSM,
                    repo_name=repo_name
            )

            print("Github token is ", Github_Token_SSM)
            print("Github org name is ", Github_OrgName_SSM)


            # Define the directory and pattern for finding the releasenote file
            directory_path = "Attached-releases"
            file_pattern = "_releasenote.xlsx"

            #Step 1:Get file path
            repo_files = github.list_files_in_directory(repo_name, directory_path)  #List of file paths in the specified directory
            matching_files = [f for f in repo_files if f.endswith(file_pattern)]  #finds the file with the pattern (end with _releasenote.xlsx)

            if not matching_files:
                raise FileNotFoundError("No matching release note file found.")

            file_path = matching_files[0]  # Use the first matched file
            logger.info(f"Found file: {file_path}")


            # Step 2: Download Release Notes from GitHub
            releasenote_path = "/releasenote.xlsx"
            download_result = github.download_file(
                #file_path="Attached-releases/1234_LM_VOIS_DevOpsTestPipeLines_Worker_releasenote.xlsx",
                file_path=file_path,
                local_path="/tmp/releasenote.xlsx",
                branch="develop"
            )
            if download_result["statusCode"] != 200:
                logger.error("Failed to download the release notes file.")

                message = {"IssueID": issue_id, "Status": "Rejected", "Message":"Failed to download the release notes file."}
                sqs_handler.send_message(closure_sqs_name, json.dumps(message))

                return {"statusCode": 500, "body": "Failed to download the release notes file."}
            if download_result:
                # Step 3: Retrieve Kibana URLs from Release Notes
                kibana_source_url, kibana_destination_url = helper.get_kibana_urls(releasenote_path)
                print("Kibana Source url ",kibana_source_url)
                print("Kibana Destination url ",kibana_destination_url)

                
                if not kibana_source_url or not kibana_destination_url:
                    logger.error("Kibana URLs are missing. Exiting process.")
                    message = {"IssueID": issue_id, "Status": "rejected", "Message": "Kibana URLs are missing in the release notes."}
                    sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                    return
                
                print(f"Kibana Source URL: {kibana_source_url}")
                print(f"Kibana Destination URL: {kibana_destination_url}")
            else:
                logger.error("Failed to download release notes. Exiting process.")
                message = {"IssueID": issue_id, "Status": "rejected", "Message": "Failed to download release notes from GitHub."}
                sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                return

            Destination_url = kibana_destination_url
            dashboard_url = kibana_source_url
            export_space_id = dashboard_url.split('/')[4]
            object_id = dashboard_url.split('/')[8]
            import_space_id = Destination_url.split('/')[4]

        print("Setup Finished")

        # Export Dashboard with its references
        headers_dev = {'kbn-xsrf': 'true', 'Authorization': api_key_dev}
        export_url = f"https://kibana.iaprobotics-dev.vodafone.com/s/{export_space_id}/api/saved_objects/_export"
        
        try:
            export_data = {'objects': [{'type': 'canvas-workpad', 'id': object_id}], 'includeReferencesDeep': True}
            print("Starting Post Request ...")
            export_response = requests.post(url=export_url, headers=headers_dev, json=export_data, proxies=proxies, verify=False)
            print(" ✅ Post Request Finished")
        except Exception as e:
            logger.info(f"it's an exception {e}")
            message = {"IssueID": issue_id, "Status": "rejected", "Message": f"it failed to export , {e}"}
            sqs_handler.send_message(closure_sqs_name, json.dumps(message))
            return

        print(" ✅ Export Finished")

        # Write the response in a file
        f = open("/tmp/exported_data.ndjson", "w")
        f.write((export_response.content).decode('utf-8'))
        f.close()
        
        # Extract and validate the ndjson data
        dashboard_name, datatable_name, process_identifier = extract_info_from_ndjson("/tmp/exported_data.ndjson")
        
        if dashboard_name:
            dashboard_name = '_'.join(dashboard_name.rsplit('_', 1)[:-1])
            if (dashboard_name.lower().find(process_identifier.lower())) != -1:
                print(' ✅ Valid Dashboard Matching')
            else:
                print(' ⛔ Dashboard name not matched with process_identifier - Ticket Rejected')
                message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Dashboard name {dashboard_name} and Process Identifier Must match."}
                sqs_handler.send_message(closure_sqs_name, json.dumps(message))
                return

        # Final Kibana import step...
        mycanvasfile = {'file': open('/tmp/exported_canvas-workpad.ndjson', 'rb')}
        mydatatablefile = {'file': open('/tmp/exported_visualization.ndjson', 'rb')}
        # import_url = f"https://kibana.iaprobotics.vodafone.com/s/{import_space_id}/api/saved_objects/_import"
        import_url = f"https://kibana.iaprobotics-dev.vodafone.com/s/{import_space_id}/api/saved_objects/_import"
        import_params = {"overwrite": True}
        
        try:
            requests.post(url=import_url, headers=headers_dev, params=import_params, files=mycanvasfile, proxies=proxies, verify=False)
            requests.post(url=import_url, headers=headers_dev, params=import_params, files=mydatatablefile, proxies=proxies, verify=False)
            # requests.post(url=import_url, headers={'kbn-xsrf': 'true', 'Authorization': api_key}, params=import_params, files=mycanvasfile, verify=False)
            # requests.post(url=import_url, headers={'kbn-xsrf': 'true', 'Authorization': api_key}, params=import_params, files=mydatatablefile, verify=False)
            message = {"IssueID": issue_id, "Status": "In Progress", "Message": "Stage 3 - Kibana Objects Imported Successfully"}
            sqs_handler.send_message(closure_sqs_name, json.dumps(message))
            #sqs_handler.send_results_to_p2_func_prod(ticket_id=ticket_id, custom_fields=custom_fields)
        except Exception as e:
            logger.info(f"it's an exception {e}")
            message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Failed to import , {e}"}
            sqs_handler.send_message(closure_sqs_name, json.dumps(message))

    except Exception as e:
        logger.info(f"it's an exception {e}")
        message = {"IssueID": issue_id, "Status": "rejected", "Message": f"Failed to process , {e}"}
        sqs_handler.send_message(closure_sqs_name, json.dumps(message))

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
