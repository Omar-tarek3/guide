import json
import boto3
from botocore.exceptions import ClientError

class SQS:
    def __init__(self, logger):
        self.logger = logger
        session = boto3.session.Session()
        self.sqs = session.client(
            service_name='sqs',
            endpoint_url='https://sqs.eu-central-1.amazonaws.com/264313199387',
            #endpoint_url='https://sqs.eu-central-1.amazonaws.com/',
        )
        self.merge_request_queue_url = 'https://sqs.eu-central-1.amazonaws.com/264313199387/vdf-prodTest-01-rca-merge-request-CICD-Test-SQS'


        # self.sqs = boto3.client('sqs')
        # self.queue_url = 'https://sqs.eu-central-1.amazonaws.com/264313199387/vdf-prod-01-sqs-rca-automated-redmine-ticket-status' ##########3
        # self.sqs_client = boto3.client("sqs", region_name=region_name)
    
    def get_queue_url_by_name(self, name):
        try:
            queue = self.sqs.get_queue_url(QueueName=name)
            self.logger.info(f"Got queue {name} with URL={queue['QueueUrl']}")
            return queue['QueueUrl']
        except ClientError as error:
            self.logger.exception(f"Couldn't get queue named {name}.")
            raise error
    
    def send_message(self,queue_name, message_body, message_attributes=None):
        if not message_attributes:
            message_attributes = {}

        try:
            queue_url = self.get_queue_url_by_name(queue_name)
            response = self.sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageAttributes=message_attributes
            )
            print("entered sqs message")
            self.logger.info(f"Message Sent to Queue: {queue_name} and the message id: {response['MessageId']}")
            return response
        except ClientError as error:
            self.logger.exception("Send message failed: %s", message_body)
            raise error
    def send_results_to_p2_func_prod(self, ticket_id, custom_fields):
        try:
            # msg = {"id": ticket_id, "custom_fields": custom_fields}
            msg = {"id": ticket_id, "custom_fields": custom_fields}

            json_msg = json.dumps(msg, indent=4)

            response = self.sqs.send_message(QueueUrl=self.merge_request_queue_url, MessageBody=json_msg)

            self.logger.info(f'Message sent to the queue {self.merge_request_queue_url}.')
        except ClientError:
            self.logger.info(f'Could not send message to the queue - {self.merge_request_queue_url}.')
            raise
        else:
            self.logger.info(response)
            return response
        


    # def send_results_to_closure_func(self,ticket_id, ticket_status, comment):
    #     try:
    #         msg = {"IssueID": ticket_id, "Status": ticket_status, "Message": comment}
    #         json_msg = json.dumps(msg, indent=4)
    #         response = self.sqs_client.send_message(QueueUrl=self.queue_url, MessageBody=json_msg)
            
    #         logger.info(f'JSON MSG is {json_msg}')
    #         logger.info(f'queue_url is {self.queue_url}')

    #         self.loger.info(f'Message sent to the queue {self.queue_url}.')
    #     except ClientError:
    #         self.loger.exception(f'Could not send meessage to the - {self.queue_url}.')
    #         raise
    #     else:
    #         self.loger.info(response)
    #         return response
