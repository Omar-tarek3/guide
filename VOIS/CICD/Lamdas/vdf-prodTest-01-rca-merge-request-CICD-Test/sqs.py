import json
# import logging
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import boto3
from botocore.exceptions import ClientError


class SQS:
    def __init__(self, loger):
        self.loger = loger
        region_name = 'eu-central-1' 

        # define the sqs
        self.sqs = boto3.client('sqs')
        self.queue_url = 'https://sqs.eu-central-1.amazonaws.com/264313199387/vdf-prod-01-sqs-rca-automated-redmine-ticket-status' ##########3
        self.kibana_queue_url = "https://sqs.eu-central-1.amazonaws.com/264313199387/vdf-prod-01-sqs-rca-Import_Kibana_CICD"
        self.sqs_client = boto3.client("sqs", region_name=region_name)

    def send_results_to_closure_func(self,ticket_id, ticket_status, comment):
        try:
            msg = {"IssueID": ticket_id, "Status": ticket_status, "Message": comment}
            json_msg = json.dumps(msg, indent=4)
            response = self.sqs_client.send_message(QueueUrl=self.queue_url, MessageBody=json_msg)
            
            logger.info(f'JSON MSG is {json_msg}')
            logger.info(f'queue_url is {self.queue_url}')

            self.loger.info(f'Message sent to the queue {self.queue_url}.')
        except ClientError:
            self.loger.exception(f'Could not send meessage to the - {self.queue_url}.')
            raise
        else:
            self.loger.info(response)
            return response
            
            
    def send_results_to_p2_func_prod(self, ticket_id, custom_fields):
        try:
            msg = {"id": ticket_id, "custom_fields": custom_fields}
            json_msg = json.dumps(msg, indent=4)

            response = self.sqs_client.send_message(QueueUrl=self.kibana_queue_url, MessageBody=json_msg)

            self.loger.info(f'Message sent to the queue {self.kibana_queue_url}.')
        except ClientError:
            self.loger.info(f'Could not send message to the queue - {self.kibana_queue_url}.')
            raise
        else:
            self.loger.info(response)
            return response        
