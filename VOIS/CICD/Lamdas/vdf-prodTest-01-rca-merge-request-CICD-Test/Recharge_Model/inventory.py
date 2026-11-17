from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
#from datetime import datetime

disable_warnings(InsecureRequestWarning)
# from services.orchestrator import orchestrator
import Recharge_Model.S3 as S3

# from services.helper import uploadfile
from botocore.config import Config
from services import Redmine
from dateutil.tz import tzutc
import openpyxl
from datetime import datetime, timezone
import logging
import requests
import boto3
import json
import time


# configure API Calls retries
config = Config(retries={"max_attempts": 2, "mode": "standard"})

# Configure Services
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# orch_handler = orchestrator(logger)
redmine_handler = Redmine.Redmine(logger)

# Time formating
today = datetime.now()
current_year = datetime.now().year
month = today.strftime("%b")



# def call_recharge_lambda():
#     # Replace this with your Lambda function URL
#     lambda_function_url = "https://ktnrbimuahk3eldxxtbjuqv6fa0nkgzf.lambda-url.eu-central-1.on.aws/"
    
#     # Data to send to the Lambda function
#     payload = {
#         "key1": "value1",
#         "key2": "value2"
#     }
    
#     # Convert payload to JSON
#     json_payload = json.dumps(payload)
    
#     # Make the POST request to the Lambda function URL
#     response = requests.post(lambda_function_url, data=json_payload)
    
#     # Check the response status code
#     if response.status_code == 200:
#         print("Lambda function triggered successfully")
#         # print("Response:", response.json())
#         return response.json()
#     else:
#         print("Failed to trigger Lambda function")
#         print("Status code:", response.status_code)
#         # print("Response:", response.text)
#         return response.text



def write_data_exist(wb, sheet_name, data, row_index):
    """
    Write data to an Excel sheet.

    Args:
        wb (openpyxl.Workbook): The workbook to write the data to.
        sheet_name (str): The name of the sheet to write the data to.
        data (list): The data to write to the sheet.
    """
    try:
        sheet = wb[sheet_name]
    except KeyError:
        sheet = wb.create_sheet(sheet_name)

    # row = sheet.max_row + 1
    # print("----------", row)
    for col, item in enumerate(data, start=1):
        sheet.cell(row=row_index, column=col, value=item)
        
        
def write_data(wb, sheet_name, data):
    """
    Write data to an Excel sheet.

    Args:
        wb (openpyxl.Workbook): The workbook to write the data to.
        sheet_name (str): The name of the sheet to write the data to.
        data (list): The data to write to the sheet.
    """
    try:
        sheet = wb[sheet_name]
    except KeyError:
        sheet = wb.create_sheet(sheet_name)

    row = sheet.max_row + 1
    print("----------", row)
    for col, item in enumerate(data, start=1):
        sheet.cell(row=row, column=col, value=item)

def uploadfile_custom(name, file_path):
    # fileN = name + "_for(" + str(month) + str(current_year) + ").xlsx"
    fileN = name + ".xlsx"
    S3.upload_file(file_path, "prod-audit-iap-automation", f"vdf-prod-IAP-Rcharge-Model/{fileN}")
    print("File Uploaded Scussesfully")
    
def downloadfile_custom(fileN):
    S3.download_file("prod-audit-iap-automation", f"vdf-prod-IAP-Rcharge-Model/{fileN}.xlsx", f"/tmp/{fileN}.xlsx")



def redmine_details(ticket_id):
    
    output_file = "/tmp/Robot_licence_inventory.xlsx"
    downloadfile_custom("Robot_licence_inventory")
    wb = openpyxl.load_workbook(output_file)
    sheet = wb["RPA_Inventory"]
    max_row = sheet.max_row

    
    Title = ""
    Location = "AWS - Frankfurt"
    Process_Status = ""
    Technology = "RPA"
    Technology_Product = "UIPath"
    Technology_Categorization = "RPA Ui Path"
    Release_Date_HC = ""
    BAU_Date = ""
    Function = ""
    Project = ""
    Business_Area = ""
    Local_Market = ""
    Support_Model = "In HC with Delivery"
    Bots_Count = "0"
    Process_Count = "0"
    Decommission_Date = ""
    Re_Assigning_Date = ""
    Comments = "The Process is New and in HC"
    Recharge_Group = ""
    DWE_Approach = ""
    DWE_Count = ""
    DWE_Actual = ""
    Volume_PM = ""
    AHT	= ""
    PPMID = ""
    
    # Main Match Value
    AWS_Package_name = ""
    
    Delivery_Manager = ""
    Business_Spoc = ""
    Detailed_process_description = ""
    Frequency = ""
    Business_Unit = ""
    Business_Leads = ""
    Item_Type = "Item"
    Path = "sites/RPAAOServiceHub/Lists/Master Process Data"
    Process_Short_Code = ""
    Hours_Per_Month	= "0"
    Percentage_per_Month = "0"	
    VM_Tier	= ""
    Auto_Scaling_Max = ""
    HC_Ticket = ""
    BAU_Ticket = ""
    
    loader = 0
    worker = 0
    handoff = 0
    
    worker_pkg = ""
    loader_pkg = ""
    handoff_pkg = ""
    
    
    automation_approved_status = redmine_handler.get_issue_details(ticket_id)
    print(automation_approved_status)
    custom_fields = automation_approved_status["issue"]["custom_fields"]
    print(custom_fields)
    ticket_type = automation_approved_status["issue"]["tracker"]["name"]
    # print(ticket_type)
    # attachments_array = automation_approved_status["issue"]["attachments"]
    
    # if ticket_type == 'Auto: HC CodeDeployment':
    Process_Status = "Ramp-up / Hypercare"
    Release_Date_HC = automation_approved_status["issue"]['closed_on']
    HC_Ticket = automation_approved_status["issue"]["id"]
        
    # elif ticket_type == 'Auto: BAU Deployment':
    #     Process_Status = "BAU"
    #     BAU_Date = automation_approved_status["issue"]['closed_on']
    #     BAU_Ticket = automation_approved_status["issue"]["id"]
    
    try:
        for item in custom_fields:
            if item['name'] == 'Process name' and item['value'] != '':
                Title = item['value']
                
            elif item['name'] == 'Squad Name' and item['value'] != '':
                Function = item['value']
                
            elif item['name'] == 'Project Name' and item['value'] != '':
                Project = item['value']
                
            elif item['name'] == 'Business Area (VSS/LM/Group)' and item['value'] != '':
                Business_Area = item['value']
                
            elif item['name'] == 'Local Market' and item['value'] != '':
                Local_Market = item['value']
                
            # elif item['name'] == 'Loader Max Count' and item['value'] != '':
            #     Bots_Count += int(item['value'])
            
            elif item['name'] == 'Bots Count' and item['value'] != '':
                Bots_Count = item['value']
                
            elif item['name'] == 'Robot License Count' and item['value'] != '':
                Process_Count = item['value']
                
            elif item['name'] == 'Monthly Volume' and item['value'] != '':
                Volume_PM = item['value']
                
            elif item['name'] == 'Human AHT' and item['value'] != '':
                AHT = item['value']
                
            elif item['name'] == 'PPM ID' and item['value'] != '':
                PPMID = item['value']
             
            elif item['name'] == 'Process Script Name in UiPath' and item['value'] != '':
                AWS_Package_name = item['value']
              
            elif item['name'] == 'Volume Frequency' and item['value'] != '':
                Frequency = item['value']
                
            elif item['name'] == 'Business SPOC Email ID' and item['value'] != '':
                Business_Spoc = item['value']
             
            elif item['name'] == 'Detailed Process Description' and item['value'] != '':
                Detailed_process_description = item['value']  
            
            elif item['name'] == 'Planned deploy date as per PI' and item['value'] != '':
                BAU_Date = item['value']  
                
            elif item['name'] == 'Benefit Approach' and item['value'] != '':
                DWE_Approach = item['value']
                
            elif item['name'] == 'FTE/DWE ' and item['value'] != '':
                DWE_Count = item['value']
             
            elif item['name'] == 'Squad Lead/ Delivery Lead' and item['value'] != '':
                Delivery_Manager = item['value']
            
# pkg names
            elif item['name'] == 'worker_package' and item['value'] != '':
                worker_pkg = str(item['value']).split(".")[0]
                
            elif item['name'] == 'loader_package' and item['value'] != '':
                loader_pkg = str(item['value']).split(".")[0]
                
            elif item['name'] == 'handoff_package' and item['value'] != '':
                handoff_pkg = str(item['value']).split(".")[0]
                
# Count
            elif item['name'] == 'Loader Max  Count' and item['value'] != '':
                loader = item['value']
                print("loader: ", loader)
                
            elif item['name'] == 'Worker Max Count' and item['value'] != '':
                worker = item['value']
                print("Worker: ", worker)
                
            elif item['name'] == 'HandOff Max Count' and item['value'] != '':
                handoff = item['value']
                print("HandOff: ", handoff)
                
         
        
        if Business_Area == "":
            Recharge_Group = str(Function) + str(Local_Market)
        else:
            Recharge_Group = str(Function) + str(Business_Area)
            
        pkgs = {loader_pkg: loader, worker_pkg: worker, handoff_pkg: handoff}
        print(pkgs)
        
        tech = loader + worker + handoff
        if tech == 0:
            Technology = "RPA - Lambda"
            
        print("max_row: ", max_row)
        for pkg in pkgs:
            print("write in progress ..")
            
            if pkg != '' and pkgs[pkg] != 0:
                
                for row_index in range(2, max_row + 1):
                    # sheet_title = sheet.cell(row=row_index, column=1).value
                    pkg_name = sheet.cell(row=row_index, column=26).value
                    
                    if str(pkg) == str(pkg_name):
                        print("Exist")
                        write_data_exist(wb, "RPA_Inventory", 
                            [
                                Title,
                                Location,
                                Process_Status,
                                Technology,
                                Technology_Product,
                                Technology_Categorization,
                                Release_Date_HC,
                                BAU_Date,
                                Function,
                                Project,
                                Business_Area,
                                Local_Market,
                                Support_Model,
                                Bots_Count,
                                Process_Count,
                                Decommission_Date,
                                Re_Assigning_Date,
                                Comments,
                                Recharge_Group,
                                DWE_Approach,
                                DWE_Count,
                                DWE_Actual,
                                Volume_PM,
                                AHT,
                                PPMID,
                                pkg,
                                Delivery_Manager,
                                Business_Spoc,
                                Detailed_process_description,
                                Frequency,
                                Business_Unit,
                                Business_Leads,
                                Item_Type,
                                Path,
                                Process_Short_Code,
                                Hours_Per_Month,
                                Percentage_per_Month,	
                                VM_Tier,
                                Auto_Scaling_Max,
                                "",
                                "",
                                "",
                                HC_Ticket,
                                BAU_Ticket,
                                pkgs[pkg]
                            ],
                            row_index
                        )
                        
                        # max_row = max_row + 1
                    #  HC
                    else:
                        print("New")
                        write_data_exist(wb, "RPA_Inventory", 
                            [
                                Title,
                                Location,
                                Process_Status,
                                Technology,
                                Technology_Product,
                                Technology_Categorization,
                                Release_Date_HC,
                                BAU_Date,
                                Function,
                                Project,
                                Business_Area,
                                Local_Market,
                                Support_Model,
                                Bots_Count,
                                Process_Count,
                                Decommission_Date,
                                Re_Assigning_Date,
                                Comments,
                                Recharge_Group,
                                DWE_Approach,
                                DWE_Count,
                                DWE_Actual,
                                Volume_PM,
                                AHT,
                                PPMID,
                                pkg,
                                Delivery_Manager,
                                Business_Spoc,
                                Detailed_process_description,
                                Frequency,
                                Business_Unit,
                                Business_Leads,
                                Item_Type,
                                Path,
                                Process_Short_Code,
                                Hours_Per_Month,
                                Percentage_per_Month,	
                                VM_Tier,
                                Auto_Scaling_Max,
                                "",
                                "",
                                "",
                                HC_Ticket,
                                BAU_Ticket,
                                pkgs[pkg]
                            ],
                            max_row + 1
                        )
                        
                        max_row = max_row + 1
                        break
                
        wb.save(output_file)
        wb.close()
        uploadfile_custom("Robot_licence_inventory", output_file)

    except Exception as e:
        print("Error :", e)