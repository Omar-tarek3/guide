from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

disable_warnings(InsecureRequestWarning)
import requests
import json
import boto3

class orchestrator:
    def __init__(self,logger):
        self.logger=logger
        ssm = boto3.client('ssm')
        parameter = ssm.get_parameter(Name='/vdf-prod-01-params/orchestrator/api', WithDecryption=True)
        self.auth = (json.loads(parameter['Parameter']['Value']))
        accountName = str(self.auth['usernameOrEmailAddress'])
        orchestratorURL = ssm.get_parameter(Name='/vdf-prod-01-params/shared/uipath-orchestrator-url',
                                            WithDecryption=True)
        self.orchURL = str(orchestratorURL['Parameter']['Value'])
    def get_token(self):
        try:
            #-------------------------Grabbing bearer token---------------------------#
            url = self.orchURL + "/api/account/authenticate"
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            response = requests.post(url, data=json.dumps(self.auth),headers=headers,verify = False)
            getToken = response.json()
            bearerToken = str(getToken['result'])
            #Printing Status Code
            if (response.status_code == 200):
                self.logger.info('Successful Authentication')
                return bearerToken
            else:
                self.logger.info('Authentication Unsuccessful', response.status_code)
                return
            # ADMIN TO ALLOW SCRIPT TO EDIT / CREATE VALUES

        except Exception as e:
            self.logger.info(json.dumps({
                'statusCode': 400,
                'body': f"Error Happened with \n orchestrator validate_folder_path : {e.__class__} \nDetails: {e}"
            }))
            return False
    def validate_folder_path(self,folderPath):
        # ----------------------------------------------- Grab Folders -----------------------------------------------------------#
        bearerToken=self.get_token()
        fullPathArr = folderPath.split("/")
        
        print("fullPathArr")
        print(fullPathArr)
        
        print("Here in validate_folder_path Orchestrator ")
        print(folderPath)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Authorization': 'Bearer {}'.format(bearerToken)}
        url = self.orchURL + "/api/FoldersNavigation/GetFoldersForCurrentUser?searchText=" + fullPathArr[1]
        print(f"url is {url}")
        grabFolders = requests.get(url, headers=headers, verify = False)
        folders = grabFolders.json()
        self.logger.info(f"{folders}")
        self.logger.info("Folder Count")
        self.logger.info(f"{folders['Count']}")

        if (folders['Count'] == 0):
            return False
        else:
            for item in folders['PageItems']:
                if item['FullyQualifiedName'] == folderPath:
                    self.logger.info("FolderIsMatched")
                    self.logger.info(item['FullyQualifiedName'])
                    self.logger.info(folderPath)
                    return True
                else:
                    return False


    def get_library(self,lib_name):
        bearerToken = self.get_token()
        headers = {'Accept': 'application/json',
                   'Authorization': 'Bearer {}'.format(bearerToken)}
        url = self.orchURL + f"/odata/Libraries?searchTerm={lib_name}"
        response = requests.get(url, headers=headers, verify=False)
        return response.json()

    def upload_nupkg(self, nupkg, type):

        if type == 'package':
            subpkg = 'Processes'
        else:
            subpkg = 'Libraries'
        def get_nupkg(self, nupkg):
            bearerToken = self.get_token()
            headers = {"Accept": "*/*", "Authorization": "Bearer {}".format(bearerToken)}
            url = ( self.orchURL + f'/odata/{subpkg}?searchTerm=' + (nupkg.split('.')[0]) )
            try:
                # Send GET request
                response = requests.get(url, headers = headers, verify = False)
                # response.raise_for_status()  # Raise an exception for unsuccessful status codes

                # Parse JSON response
                Processes = response.json()
                self.logger.info(f"OutProcesses : {Processes}")
                ProcessInfo = {'Id' : 0 , 'ProcessKey' : '', 'ProcessVersion' : ''}
                if(int(Processes['@odata.count']) > 0):
                    for i in range(int(Processes['@odata.count'])):
                        ProcessInfo['Id'] = Processes['value'][i]['Id']
                        ProcessInfo['ProcessKey'] = Processes['value'][i]['Key']
                        ProcessInfo['ProcessVersion'] = Processes['value'][i]['Version']
                    return ProcessInfo
                else:
                    self.logger.info("There's no processes found in this folder")
                    return ProcessInfo 

            except requests.exceptions.RequestException as e:
                print(f"Error retrieving package details: {e}")
                return False
        
        # upload nupkg
        bearerToken = self.get_token()
        self.logger.info(f'bearerToken {bearerToken}') 
        headers = {'Accept': '*/*','Authorization': 'Bearer {}'.format(bearerToken)}
        url = self.orchURL + f"/odata/{subpkg}/UiPath.Server.Configuration.OData.UploadPackage"
        self.logger.info(f'url: {url}')
        files = {f'{nupkg}': open(f'/tmp/{nupkg}.nupkg', 'rb')}
        self.logger.info(f"files_Data {files}")
        upload_nupkg = requests.post(url=url, headers=headers, files=files,verify=False)
        uploaded_nupkg_status = upload_nupkg.json()
        self.logger.info(f"upload_result {uploaded_nupkg_status}")
        
        if upload_nupkg:
            uploaded_nupkg_status = get_nupkg(self, nupkg)
            print("uploaded_nupkg_status ", uploaded_nupkg_status)
            return uploaded_nupkg_status
            
        elif uploaded_nupkg_status["errorCode"] == 1004 or 'already' in uploaded_nupkg_status['message']:
            self.logger.info(f"the package  {nupkg} already uploaded")
            uploaded_nupkg_status = get_nupkg(self, nupkg)
            print("uploaded_nupkg_status ", uploaded_nupkg_status)
            return uploaded_nupkg_status
            
        else:
            self.logger.info(f"the package  {nupkg} didn't successfully uploaded")
            return False

