import os

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define data folder path relative to the base directory
data_dir = os.path.join(base_dir, 'data')

# Now you can define paths to specific CSV files here
spotrac_contracts_path = os.path.join(data_dir, 'spotrac_contracts.csv')
bbref_stats_path = os.path.join(data_dir, 'bbref_stats.csv')

# And any other paths you need
