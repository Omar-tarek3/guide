import pandas as pd  # For handling Excel files

class ExcelHandler:
    def __init__(self, logger):
        self.logger = logger

    def save_to_temp(self, file_content, tmp_path="/tmp/new.xlsx"):
        try:
            with open(tmp_path, "wb") as file:
                file.write(file_content)
                self.logger.info(f"File saved to {tmp_path}")
            return tmp_path
        except Exception as e:
            self.logger.error(f"Error saving file: {e}")
            raise

    def read_excel(self, tmp_path):
        try:
            excel_data = pd.read_excel(tmp_path, sheet_name=None, engine="openpyxl")
            self.logger.info("Excel data loaded successfully.")
            return excel_data
        except ValueError as e:
            self.logger.error(f"Error reading Excel file: {e}")
            raise

    
    def get_folder_path_from_releasenote(self, excel_data, sheet_name="Folders"):
        """Retrieve the first row of the specified sheet, formatting it as Folder/Subfolder with custom separators."""
        if sheet_name in excel_data:
            first_row = excel_data[sheet_name].iloc[0]  # Get the first row
    
            # Filter out NaN values and strip spaces
            non_nan_cells = [str(cell).strip() for cell in first_row if pd.notna(cell)]
            
            # Create formatted path: the first cell as folder, then add _ between the next cells
            if non_nan_cells:
                formatted_path = f"{non_nan_cells[0]}/{'_'.join(non_nan_cells[1:])}".strip()
            else:
                formatted_path = ""
    
            self.logger.info(f"Formatted folder path from '{sheet_name}': {formatted_path}")
            return formatted_path
        else:
            self.logger.warning(f"'{sheet_name}' sheet not found in the Excel file.")
            raise ValueError(f"'{sheet_name}' sheet not found.")
            
            
    def get_assets_data(self, excel_data, sheet_name="Assets"):
        """Retrieve all rows in the specified sheet and return them as a list of dictionaries."""
        if sheet_name in excel_data:
            assets_sheet = excel_data[sheet_name]
            assets_data = assets_sheet.to_dict(orient="records")  # Convert rows to list of dictionaries
            self.logger.info(f"Retrieved data from '{sheet_name}' sheet: {assets_data}")
            return assets_data
        else:
            self.logger.warning(f"'{sheet_name}' sheet not found in the Excel file.")
            raise ValueError(f"'{sheet_name}' sheet not found.")        

    def get_queue_data(self, excel_data, sheet_name="Queues"):
        """Retrieve all rows in the specified sheet and return them as a list of dictionaries."""
        if sheet_name in excel_data:
            queue_sheet = excel_data[sheet_name]
            queue_data = queue_sheet.to_dict(orient="records")  # Convert rows to list of dictionaries
            self.logger.info(f"Retrieved data from '{sheet_name}' sheet: {queue_data}")
            return queue_data
        else:
            self.logger.warning(f"'{sheet_name}' sheet not found in the Excel file.")
            raise ValueError(f"'{sheet_name}' sheet not found.")