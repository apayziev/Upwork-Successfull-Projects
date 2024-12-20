import json
import os
import pandas as pd

folder_path = os.path.join(os.getcwd())

# Read the json file
with open(os.path.join(folder_path, 'leads.json'), encoding='utf-8') as f:
    data = json.load(f)

# upload data to excel file according to the json fields
df = pd.DataFrame(data)
df.to_excel(os.path.join(folder_path, 'leads.xlsx'), index=False)

# Read the excel file
df = pd.read_excel(os.path.join(folder_path, 'leads.xlsx'))
print(df)


# import json
# import os

# def read_json_data(filepath):
#     """
#     Reads data from a JSON file.

#     Args:
#         filepath (str): The path to the JSON file.

#     Returns:
#         list: A list of dictionaries representing the JSON data.
#     """
#     try:
#         with open(filepath, 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         return data
#     except FileNotFoundError:
#         print(f"Error: JSON file not found at: {filepath}")
#         return None


# # OR
# leads_data = read_json_data(os.path.join(os.getcwd(), 'leads.json'))

# if leads_data:
#     for lead in leads_data:
#         print(lead)  # Process each lead dictionary
