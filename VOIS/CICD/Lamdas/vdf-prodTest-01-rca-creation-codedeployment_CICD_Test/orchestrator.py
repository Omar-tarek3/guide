from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
import requests
import json
import boto3
import pandas as pd
# from datetime import datetime
import math
import datetime


disable_warnings(InsecureRequestWarning)
# def serialize_data(data):
#     for key, value in data.items():
#         print("KEYYYYYY" ,key)
#         if isinstance(value, datetime):
#             data[key] = value.isoformat()
#     return data
Error_List = []
Warning_List = []
def serialize_data(data):
    """Recursively serialize data to make it JSON serializable."""
    if isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: serialize_data(value) for key, value in data.items()}
    elif isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
        return data.isoformat()
    elif isinstance(data, (float, int)) and pd.isna(data):
        return None
    elif data is pd.NA or data is pd.NaT:
        return None
    # elif data is np.nan:
    #     return None
    else:
        return data


class Orchestrator:
    def __init__(self, logger):
        self.logger = logger
        ssm = boto3.client('ssm')
        parameter = ssm.get_parameter(Name='/vdf-prod-01-params/orchestrator/api', WithDecryption=True)
        self.auth = json.loads(parameter['Parameter']['Value'])
        orchestratorURL = ssm.get_parameter(Name='/vdf-prod-01-params/shared/uipath-orchestrator-url', WithDecryption=True)
        self.orchURL = str(orchestratorURL['Parameter']['Value'])

    def get_token(self):
        try:
            url = self.orchURL + "/api/account/authenticate"
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            response = requests.post(url, data=json.dumps(self.auth), headers=headers, verify=False)
            if response.status_code == 200:
                bearerToken = response.json().get('result')
                self.logger.info('Successful Authentication')
                return bearerToken
            else:
                self.logger.error(f'Authentication Unsuccessful, status code: {response.status_code}')
                return None
        except Exception as e:
            self.logger.error(f"Error occurred in get_token: {e.__class__} - {e}")
            return None
            
    def validate_folder_path(self, folderPath):
        """Validates if a folder path exists in the Orchestrator."""
        bearerToken = self.get_token()
        if not bearerToken:
            self.logger.error("Failed to retrieve bearer token for validation.")
            return False

        fullPathArr = folderPath.split("/")
        if len(fullPathArr) < 2:
            self.logger.info("Invalid folder path provided; folder path does not contain enough segments.")
            return False
        
        self.logger.info(f"Validating folder path: {folderPath}")
    
        headers = {
            'Content-type': 'application/json',
            'Accept': 'text/plain',
            'Authorization': f'Bearer {bearerToken}'
        }
        url = f"{self.orchURL}/api/FoldersNavigation/GetFoldersForCurrentUser?searchText={fullPathArr[1]}"
        self.logger.info(f"URL for fetching folders: {url}")
    
        try:
            grabFolders = requests.get(url, headers=headers, verify=False)
            folders = grabFolders.json()
            
            if folders.get('Count', 0) == 0:
                self.logger.info("No matching folders found.")
                return False
            else:
                for item in folders.get('PageItems', []):
                    if item['FullyQualifiedName'] == folderPath:
                        self.logger.info(f"Folder path matched: {item['FullyQualifiedName']}")
                        return True
                self.logger.info("Folder path not found in the list of folders.")
                return False
        except Exception as e:
            self.logger.error(f"Error occurred in validate_folder_path: {e}")
            return False

    def create_folder(self, data):
        """Creates a folder in Orchestrator."""
        bearerToken = self.get_token()
        if not bearerToken:
            self.logger.error("Failed to retrieve bearer token for folder creation.")
            return None

        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/json;odata.metadata=minimal;odata.streaming=true',
            'Authorization': f'Bearer {bearerToken}'
        }
        url = f"{self.orchURL}/odata/Folders"
        
        try:
            response = requests.post(url, json=data, headers=headers, verify=False)
            response_data = response.json()
            self.logger.info(f"Folder creation response: {response_data}")
            return response_data
        except Exception as e:
            self.logger.error(f"Error occurred in create_folder: {e}")
            Error_List.append(f"Error occurred in create_folder: {e}")
            return None

    def serialize_data(data):
        for key, value in data.items():
            print("KEYYYYYY" ,key)
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data        
    
  
    def ensure_folder_path_exists(self, folder_path):
        """
        Ensures that each folder in the given path exists in Orchestrator.
        Creates each level if it does not exist.
        Returns the ID of the final folder in the path.
        """
        folders = folder_path.split('/')
        parent_folder_id = self.get_folder_id(folders[0])  # Root folder ID
        
        if not parent_folder_id:
            self.logger.error(f"Root folder '{folders[0]}' does not exist, cannot create subfolders.")
            return None
        
        # Proceed with subfolders
        for i in range(1, len(folders)):  # Start from the second item (subfolder)
            current_folder_name = '/'.join(folders[:i + 1])  # Fully qualified name for the current subfolder
    
            if not self.validate_folder_path(current_folder_name):
                # Folder does not exist, create it
                data = {
                    "DisplayName": folders[i],
                    "Description": f"Folder for {folders[i]}",
                    "ParentId": parent_folder_id  # Set the parent folder ID for subfolders
                }
                folder_response = self.create_folder(data)
                folder_id = folder_response.get('Id') if folder_response else None
                
                if not folder_id:
                    self.logger.error(f"Failed to create folder: {current_folder_name}")
                    return None
                
                self.logger.info(f"Created folder '{folders[i]}' with ID {folder_id}")
                parent_folder_id = folder_id  # Update parent ID for next level
            else:
                # Folder exists, retrieve its ID to proceed to the next level
                parent_folder_id = self.get_folder_id(current_folder_name)
                self.logger.info(f"Folder '{current_folder_name}' already exists with ID {parent_folder_id}")
                
        return parent_folder_id


    def get_folder_id(self,FolderName):
        print('get_folder_boolean')
        bearerToken = self.get_token()
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Authorization': 'Bearer {}'.format(bearerToken)}
        url = self.orchURL  + "/odata/Folders"
        grabFolders = requests.get(url, headers=headers, verify = False)
        folders = grabFolders.json()
        Skipfile = 1000
        NumberOfitration = int(folders['@odata.count']) / 1000
        NumberOfitration = math.floor(int(NumberOfitration+1))
        id = 0
        FolderFound = 0
        #--------------Filter for specified Folder-------------#
        # print(FolderName)
        for i in range(0,NumberOfitration):
            for x in range(0,len(folders['value'])):
                #print(folders['value'][x]['FullyQualifiedName'])
                if (folders['value'][x]['FullyQualifiedName'] == FolderName):
                    print(folders['value'][x])
                    print(type(folders['value'][x]))
                    id = int(folders['value'][x]['Id'])
                    key = str(folders['value'][x]['Key'])
                    FolderFound = id
                    break
                else:
                    continue
            if FolderFound != 0:
                break
            url = self.orchURL + "/odata/Folders?%24skip="+ str(Skipfile)
            grabFolders = requests.get(url, headers=headers, verify = False)
            folders = grabFolders.json()
            Skipfile=int(Skipfile)+1000
            
        print("FolderFound")
        print(FolderFound)
        return FolderFound  

    def create_assets(self, assets_excel, folder_ids):
            """Creates assets in UiPath Orchestrator from the provided DataFrame."""
            
            # Convert to DataFrame if needed
            if isinstance(assets_excel, list):
                assets_excel = pd.DataFrame(assets_excel)

            bearerToken = self.get_token()
            asset_count = 0
            url_assets = f"{self.orchURL}/odata/Assets"
            folder_id =0
            
            for index, row in assets_excel.iterrows():
                # Determine folder ID based on AssetFolder value
                asset_folder = row["AssetFolder"]
                if asset_folder == "Global":
                    folder_id = folder_ids['Parent']
                elif asset_folder == "Loader":
                    folder_id = folder_ids['Loader']
                elif asset_folder == "Worker":
                    folder_id = folder_ids['Worker']
                elif asset_folder == "Handoff":
                    folder_id = folder_ids['Handoff']
                else:
                    self.logger.error(f"Unknown folder type: {asset_folder} for asset {row['Name']}")
                    continue
    
                headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'X-UIPATH-OrganizationUnitId': '{}'.format(folder_id), 'Authorization': 'Bearer {}'.format(bearerToken)}
                # headers['X-UIPATH-OrganizationUnitId'] = str(folder_id)
    
                # Set asset properties
                asset_name = row["Name"]
                asset_type = row["ValueType"]
                asset_value = row["Value"]
                asset_username = row["UserName"]
                print("USERNAME",asset_username)
                # password = row.get["Password",""]
                password = row["Password"]
                value_scope = "Global"
    
                # Prepare data based on asset type
                data = {
                    "Name": asset_name,
                    "ValueScope": value_scope,
                    "ValueType": asset_type
                }
    
                if asset_type == "Text":
                    data["StringValue"] = asset_value
                elif asset_type == "Bool":
                    data["BoolValue"] = asset_value
                elif asset_type == "Integer":
                    data["IntValue"] = asset_value
                elif asset_type == "Credential":
                    data["CredentialUsername"] = asset_username
                    data["CredentialPassword"] = password
                else:
                    self.logger.error(f"Unknown asset type: {asset_type} for asset {asset_name}")
                    continue
    

                # Convert datetime fields to strings
                data = serialize_data(data)
                response = requests.post(url_assets, data=json.dumps(data), headers=headers, verify=False)

    
                if response.status_code == 201:
                    asset_count += 1
                    self.logger.info(f"Created asset: {asset_name}")
                else:
                    self.logger.error(f"Failed to create asset {asset_name}. Status code: {response.status_code}, Response: {response.text}")
                    if response.text:  # Check if response.text is not empty
                        try:
                            # Parse response text as JSON to check for specific messages
                            response_message = json.loads(response.text)
                            if "message" in response_message:
                                message = response_message["message"]
                                if "must not be null" in message:
                                    Error_List.append(f"Failed to create asset {asset_name}: {message}")
                                elif "is already used" in message:
                                    Warning_List.append(f"Asset {asset_name} already exists: {message}")
                                else:
                                    Error_List.append(f"Failed to create asset {asset_name}: {message}")
                            else:
                                Error_List.append(f"Failed to create asset {asset_name}: {response.text}")
                        except json.JSONDecodeError:
                            # If response.text is not JSON, append it as is
                            Error_List.append(f"Failed to create asset {asset_name}: {response.text}")
                    else:
                        Error_List.append(f"Failed to create asset {asset_name}: Empty response text")

                print(f"Error List inside creating assets is {Error_List}")
                print(f"Warning_List inside creating assets is {Warning_List}")        

                self.logger.info(f"Created {asset_count} / {len(assets_excel)} Assets")

     

    def create_queues(self, queues_excel,parent_id):
        """Creates queues in UiPath Orchestrator from the provided DataFrame."""
        
        # Convert to DataFrame if needed
        if isinstance(queues_excel, list):
            queues_excel = pd.DataFrame(queues_excel)
    
        bearerToken = self.get_token()
        queue_count = 0
        url_queues = f"{self.orchURL}/odata/QueueDefinitions"
        
        for index, row in queues_excel.iterrows():
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'X-UIPATH-OrganizationUnitId': '{}'.format(parent_id), 'Authorization': 'Bearer {}'.format(bearerToken)}
           
            
            # Set queue properties
            queue_name = row["Queue Name"]
            queue_description = row["Queue Description"]
            enforce_unique_reference = bool(row["Enforce Unique Reference"])
            accept_auto_retries = bool(row["Accept Automatic Retries"])
            
            # Max retries validation
            max_retries = row.get("Max Number of Retries", 0)
            max_retries = int(max_retries) if pd.notna(max_retries) and max_retries != "" else 0
            
            data = {
                "Name": queue_name,
                "Description": queue_description,
                "MaxNumberOfRetries": max_retries,
                "AcceptAutomaticallyRetry": accept_auto_retries,
                "EnforceUniqueReference": enforce_unique_reference
            }
            
            # Create queue
            response = requests.post(url_queues, data=json.dumps(data), headers=headers, verify=False)
            
            if response.status_code == 201:
                queue_count += 1
                self.logger.info(f"Created queue: {queue_name}")
            else:
                self.logger.error(f"Failed to create queue {queue_name}. Status code: {response.status_code}, Response: {response.text}")
                if response.text:  # Check if response.text is not empty
                    try:
                        # Parse response text as JSON to check for specific messages
                        response_message = json.loads(response.text)
                        if "message" in response_message:
                            message = response_message["message"]
                            if "is already used" in message:
                                Warning_List.append(f"Failed to create queue {queue_name} already exists: {message}")
                            else:
                                Error_List.append(f"Failed to create queue {queue_name}: {message}")
                        else:
                            Error_List.append(f"Failed to create queue {queue_name}: {response.text}")
                    except json.JSONDecodeError:
                        # If response.text is not JSON, append it as is
                        Error_List.append(f"Failed to create queue {queue_name}: {response.text}")
                else:
                    Error_List.append(f"Failed to create queue {queue_name}: Empty response text")
        
        self.logger.info(f"Created {queue_count} / {len(queues_excel)} Queues")

    def return_Errorlists(self):
        return Error_List
    def return_Warninglists(self):
        return Warning_List
    def serialize_data(data):
        for key, value in data.items():
            print("KEYYYYYY" ,key)
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    