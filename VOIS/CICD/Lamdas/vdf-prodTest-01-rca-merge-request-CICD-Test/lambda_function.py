import json
import logging
from github import GitHubOrganization
from sqs import SQS  # Assuming `SQS` is the class for handling SQS operations

# Set up logger
logger = logging.getLogger("GitHubOrganizationLogger")
logger.setLevel(logging.INFO)

# Initialize SQS handler
sqs_handler = SQS(logger)

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    base_branch = "hc-deployment"
    head_branch = "develop"
    title = "Auto-generated Pull Request"
    body = "This is an automated pull request created by Lambda."

    # Instantiate the GitHubOrganization class
    github_org = GitHubOrganization(logger)

    for record in event['Records']:
        try:
            # Parse the SQS message
            data = json.loads(record['body'])
            print(data)
            logger.info(f"Processing data: {data}")

            # Extract ticket information
            ticket_id = data.get('id')
            custom_fields = data.get('custom_fields', [])
            logger.info(f"Ticket ID: {ticket_id}, Custom Fields: {custom_fields}")



            with_lambda=get_custom_field_value(custom_fields,"with_lambda")
            print(f"with_lambda is : {with_lambda}")

            
            github_repo_name=get_custom_field_value(custom_fields,"Github Repo Name")

            # github_repo_name = next(
            #     (field.get('value') for field in custom_fields if field.get('name') == 'Github Repo Name'),
            #     None
            # )
            print("Github Repo Name : ",github_repo_name)


            pr_number = get_custom_field_value(custom_fields, "Pull Request Number")
            print(f"Pull Request Number : ",pr_number)
            # pr_number = next(
            #     (field.get('value') for field in custom_fields if field.get('name') == 'Pull Request Number'),
            #     None
            # )     



            target_team = "devops"
            target_comment = "approved"
            result=github_org.check_comments_and_approve_pr(github_repo_name, pr_number, target_team, target_comment)


            # target_users = ["salma-elmosalamy_voda", "hager-aboshady_voda", "mohamed-attiaabdelgelil_voda","nourhan-ali6_voda"] # => replace with users of insd
            # target_comment = "approved"
            # result=github_org.check_comments_and_approve_pr(github_repo_name, pr_number, target_users, target_comment)
            print("result is : ", result)
            
            
            if result:
                logger.info(f"Pull request #{pr_number} processed successfully (created, approved, and merged).")
                if with_lambda=="0":
                    # Send success message to SQS
                    sqs_handler.send_results_to_closure_func(
                        ticket_id=ticket_id,
                        ticket_status="resolved",
                        comment="The pull request has been created and approved successfully. The GitHub pipeline for building and deploying the package is now running."
                    )
                else:
                    sqs_handler.send_results_to_closure_func(
                        ticket_id=ticket_id,
                        ticket_status="in progress",
                        comment="The pull request has been successfully created and approved, initiating the pipeline execution in GitHub, including the creation of parameters for the Lambda function."
                    )                    


            else: 
                            
                # Send failure message to SQS
                sqs_handler.send_results_to_closure_func(
                    ticket_id=ticket_id,
                    ticket_status="rejected",
                    comment=f"An error occurred in approve and merge request "
                )   
            
        except Exception as e:
            logger.error(f"Error processing ticket ==> lambda_handler ==> {ticket_id}: {e}")
            
            # Send failure message to SQS
            sqs_handler.send_results_to_closure_func(
                ticket_id=ticket_id,
                ticket_status="rejected",
                comment=f"An error occurred: {str(e)}"
            )

def get_custom_field_value(custom_fields, field_name):
    for field in custom_fields:
        if field['name'] == field_name:
            return field['value']
    return None
    