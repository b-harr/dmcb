import os

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define data folder path relative to the base directory
data_dir = os.path.join(base_dir, 'data')

# Now you can define paths to specific CSV files here
spotrac_contracts_path = os.path.join(data_dir, 'spotrac_contracts.csv')
bbref_stats_path = os.path.join(data_dir, 'bbref_stats.csv')
sportsws_positions_path = os.path.join(data_dir, 'sportsws_positions.csv')
contract_types_path = os.path.join(data_dir, 'contract_types.csv')

google_sheets_url = "https://docs.google.com/spreadsheets/d/1NgAl7GSl3jfehz4Sb3SmR_k1-QtQFm55fBPb3QOGYYw"
service_account_email = "gchelp@dmcb-442123.iam.gserviceaccount.com"
