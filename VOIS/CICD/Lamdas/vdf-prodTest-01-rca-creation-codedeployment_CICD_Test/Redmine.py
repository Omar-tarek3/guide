import json
import requests
# import logging
import logging
import pandas as pd
from io import BytesIO
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Redmine:
    def __init__(self, logger):
        self.logger = logger
        self.proxies = {
            "https": "vpce-0974f7457e940e4bf-0s4t8nsz.vpce-svc-0ffc3575422275d21.eu-central-1.vpce.amazonaws.com:8081"
        }
        self.key = "376a6131b268e8324e76ce0c11bb63340f3aaf60"
        self.base_url = "https://redmine.iaprobotics-dev.vodafone.com"
    
    def get_status_obj_by_name(self, status_name):
        query = {
            "key": self.key
        }
        status_obj = {}
        try:
            response = requests.get(f"{self.base_url}/issue_statuses.json", params=query, proxies=self.proxies, verify=False);
            self.logger.info("Issue Statuses Retrieved")
            issue_statuses = response.json()['issue_statuses']
            for status in issue_statuses:
                if(status['name'].lower() == status_name.lower()):
                    self.logger.info(f"Status with name: {status_name} found")
                    status_obj = status
                    break
            
            return status_obj
        except requests.exceptions.RequestException as e:
            self.logger.exception("Error Occurred")
            self.logger.exception(e)
            raise e
        except Exception as e:
            self.logger.exception(f"Error {e.__class__} Occurred")
            raise e
            
            
     
    def get_issues_by_status_id(self,status_id):
        query = {
            "key": self.key,
            "status_id": status_id
        }
        try:
            self.logger.info("Retrieving Issues")
            response = requests.get(f"{self.base_url}/issues.json", params=query, proxies=self.proxies, verify=False);
            self.logger.info("Issues Retrieved")
            self.logger.info(f"Count of new issues: {len(response.json()['issues'])} ")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.exception("Error Occurred")
            self.logger.exception(e)
            raise e
        except Exception as e:
            self.logger.exception(f"Error {e.__class__} Occurred")
            raise e

    def get_issue_details(self, issue_id):
        query = {
            "key": self.key,
            # "issue_id": issue_id,
            "include": "attachments"
        }
        try:
            self.logger.info("---Retrieving issue details---")
            self.logger.info(f"{self.base_url}/issues/{issue_id}.json")
            response = requests.get(f"{self.base_url}/issues/{issue_id}.json", params=query, proxies=self.proxies,
                                    verify=False)
            self.logger.info(f"---Issue details retrieved--- {response}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.exception("Error Occurred")
            self.logger.exception(e)
            return False
        except Exception as e:
            self.logger.exception(f"Error {e.__class__} Occurred")
            return False
    
    # def get_issue_details(self,issue_id):
    #     query = {
    #         "key": self.key,
    #         # "issue_id": issue_id,
    #         "include": "attachments"
    #     }
    #     try:
    #         self.logger.info("Retrieving issue details")
    #         response = requests.get(f"{self.base_url}/issues/{issue_id}.json", params=query,  verify=False);
    #         self.logger.info("Issue details retrieved")
    #         return response.json()
    #     except requests.exceptions.RequestException as e:
    #         self.logger.exception("Error Occurred")
    #         self.logger.exception(e)
    #         raise e
    #     except Exception as e:
    #         self.logger.exception(f"Error {e.__class__} Occurred")
    #         raise e            
            

    def get_issues_by_tracker_id(self, tracker_id):
        query = {
            "key": self.key,
            "tracker_id": tracker_id
        }
        try:
            self.logger.info("Retrieving Issues")
            response = requests.get(f"{self.base_url}/issues.json", params=query, proxies=self.proxies, verify=False);
            self.logger.info("Issues Retrieved")
            self.logger.info(f"Count of new issues: {len(response.json()['issues'])} ")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.exception("Error Occurred")
            self.logger.exception(e)
            raise e
        except Exception as e:
            self.logger.exception(f"Error {e.__class__} Occurred")
            raise e

    def get_custom_fields(self):
        query = {
            "key": self.key
        }

        try:
            response = requests.get(f"{self.base_url}/custom_fields.json", params=query, proxies=self.proxies,
                                    verify=False);
            self.logger.info("Custom Fields Retrieved")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.exception("Error Occurred")
            self.logger.exception(e)
            raise e
        except Exception as e:
            self.logger.exception(f"Error {e.__class__} Occurred")
            raise e

    def set_issue_status(self, issue_id, status):
        query = {
            "key": self.key,
            
        }
        print(status)
        data = {
            "issue": {
                "status_id": status['id']
            }
        }
        
        try:
            print(f"Issue_id {issue_id}")
            response = requests.put(f"{self.base_url}/issues/{issue_id}.json", params=query, json=data, proxies=self.proxies, verify=False);
            print(response.content)
            self.logger.info("Issue Status Updated")
            return response
        except requests.exceptions.RequestException as e:
            self.logger.exception("Error Occurred")
            self.logger.exception(e)
            raise e
        except Exception as e:
            self.logger.exception(f"Error {e.__class__} Occurred")
            raise e

    def get_readmine_attachment(self, FileURL):
        query = {
            "key": self.key
        }
        try:
            response = requests.get(FileURL, params=query, proxies=self.proxies, verify=False)
            # print(response.text)
            return response.json()
        except Exception as e:
            return (e)
            
            
    def download_file_as_dataframe(self, content_url):
        try:
            query = {
                "key": self.key,
                # "issue_id": issue_id,
                "include": "attachments"
            }
            response = requests.get(content_url, params=query,proxies=self.proxies,verify=False)

            if response.status_code == 200:
                with open('/tmp/Parameters.xlsx', 'wb') as file:
                    file.write(response.content)
                    print("File 'Parameters.xlsx' downloaded and saved to /tmp/")

                # Read the downloaded file into a DataFrame
                df = pd.read_excel('/tmp/Parameters.xlsx')
                return df
            else:
                print(f"Failed to download the file. Status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"An error occurred during file download: {str(e)}")
            return None
            
    def download_file(self,filename, content_url):
        query = {
            "key": self.key,
            # "issue_id": issue_id,
            "include": "attachments"
        }
        r = requests.get(
            content_url,
            params=query,
            proxies=self.proxies,
            # proxies=self.proxies, # only for prod
            verify=False)
        open(f'/tmp/{filename}', 'wb').write(r.content)    
            

