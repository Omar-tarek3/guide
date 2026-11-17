import boto3
import botocore
from botocore.exceptions import ClientError

class SSM:
    def __init__(self, logger):
        self.logger = logger
        region_name = 'eu-central-1'
        self.client= boto3.client('ssm')

        session = boto3.Session()
        self.s3session = session.client(
            'ssm',
            region_name=region_name
        )
        
    def getparameter (self, parametername):
        try:
            response = self.client.get_parameter( Name=parametername,WithDecryption=True)
            parameter= response["Parameter"]
            for key in parameter:
                if key == "Value":
                    return parameter[key]
           
        except ClientError as error:
            self.logger.exception(error)
            raise error
        except Exception as e:
            raise e
        