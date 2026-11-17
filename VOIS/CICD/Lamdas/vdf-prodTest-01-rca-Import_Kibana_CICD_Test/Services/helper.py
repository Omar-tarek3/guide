import pandas as pd
import openpyxl
import requests
import logging

# logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from Services.orchestrator import orchestrator
orch_handler = orchestrator(logger)

class Helper:
    def __init__(self, logger):
        self.logger = logger
        self.proxies = {
            "https": "vpce-0974f7457e940e4bf-0s4t8nsz.vpce-svc-0ffc3575422275d21.eu-central-1.vpce.amazonaws.com:8081"
        }
        self.key = "376a6131b268e8324e76ce0c11bb63340f3aaf60"
        self.base_url = "https://redmine.iaprobotics-dev.vodafone.com"

    # Function to get Kibana Source URL and Destination URL from kibana sheet
    def get_kibana_urls(self, releasenote):
        try:
            error_list = []
            sheets_dict = pd.read_excel(f'/tmp/{releasenote}', sheet_name=None)
            self.logger.info(f'print releasenote in helper {sheets_dict}')
            max = 0
            flag = 0
            worker = 0
            loader = 0
            # 1- check for the sheet names and arrange it
            all_sheets = []
            for name, sheet in sheets_dict.items():
                sheet['sheet'] = name
                all_sheets.append(name)
            self.logger.info(all_sheets)
            Validate_sheets = ['Index', 'Folders', 'Assets', 'Queues', 'Libraries', 'Kibana']

            if all_sheets[0] == 'Index':
                for i in range(len(Validate_sheets)):
                    max = 0
                    if Validate_sheets[i] not in all_sheets:
                        self.logger.info(f"{Validate_sheets[i]} Not found")
                        for j in range(len(all_sheets)):
                            x = ''.join(set(Validate_sheets[i]).intersection(all_sheets[j]))
                            if len(x) > max:
                                max = len(x)
                                flag = j
                        self.logger.info(f"{all_sheets[flag]} should be replaced with {Validate_sheets[flag]}")
                        error_list.append(f"{all_sheets[flag]} should be replaced with {Validate_sheets[flag]}")

            else:
                self.logger.info("Index must be the first sheet")
                error_list.append("Index must be the first sheet")

            # Initialize Kibana URLs
            source_url = None
            destination_url = None

            #CHECK KIBAANNAAAAA SHEEEETT
            Kibana_col_list = ['Name', 'Value']
            Kibana_sheet = sheets_dict["Kibana"]
            df = pd.DataFrame(Kibana_sheet)
            column_names = list(sheets_dict["Kibana"].columns.values)
            print("COLS NAME" , column_names)
            missing = []
            print("INSIDE KIBANA" , df)

            # Check for Kibana URLs in the 'Kibana' sheet
            if 'Kibana' in sheets_dict:
                kibana_sheet = sheets_dict['Kibana']
                for i, row in kibana_sheet.iterrows():
                    self.logger.info(f"Row: {row}")
                    if row['Name'] == 'Kibana Source URL':
                        source_url = row['Value']
                    elif row['Name'] == 'Kibana Destination URL':
                        destination_url = row['Value']

                # Log missing URLs if any
                if not source_url or not destination_url:
                    if not source_url:
                        self.logger.error("Kibana Source URL is missing in the Kibana sheet.")
                    if not destination_url:
                        self.logger.error("Kibana Destination URL is missing in the Kibana sheet.")
                    return None, None

            else:
                self.logger.error("Kibana sheet is missing in the release notes.")
                return None, None

            return source_url, destination_url

        except Exception as e:
            self.logger.error(f"Error while retrieving Kibana URLs: {e}")
            return None, None

    # Other existing methods...

    def get_releasenote(self, arr):
        filename = ""
        content_url = ""
        counter = 0
        for i in arr:
            self.logger.info(i)
            suffixes = ('xlsx', "xls")
            if ("releasenote" in i['filename'].lower()) and i['filename'].endswith(suffixes):
                filename = i['filename']
                content_url = i['content_url']
                self.logger.info(f"filename in : {i['filename']}")
                counter += 1
        if counter == 1:
            self._download_file(filename, content_url)
            return {"filename": filename, "content_url": content_url}
        else:
            self.logger.info(f"counter {counter}")
            return False

    # Add the remaining methods from your original code...
