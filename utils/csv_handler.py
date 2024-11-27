import csv
import os
import logging

# Set up module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CSVHandler:
    @staticmethod
    def ensure_folder_exists(folder_path):
        """
        Ensures the specified folder exists. Creates it if it doesn't.
        """
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logger.info(f"Created missing directory: {folder_path}")

    @staticmethod
    def read_csv(file_path):
        """
        Reads a CSV file and returns its contents as a list of rows.
        Each row is represented as a list of values.
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File does not exist: {file_path}")
                return []
            
            with open(file_path, mode="r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                data = [row for row in reader]
                logger.info(f"Read {len(data)} rows from {file_path}.")
                return data
        except Exception as e:
            logger.error(f"Error reading CSV file '{file_path}': {e}")
            raise

    @staticmethod
    def write_csv(file_path, data, headers=None):
        """
        Writes data to a CSV file. Overwrites the file if it already exists.
        """
        try:
            CSVHandler.ensure_folder_exists(os.path.dirname(file_path))
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if headers:
                    writer.writerow(headers)
                    logger.info(f"Wrote headers to {file_path}: {headers}")
                writer.writerows(data)
                logger.info(f"Wrote {len(data)} rows to {file_path}.")
        except Exception as e:
            logger.error(f"Error writing to CSV file '{file_path}': {e}")
            raise

# Example Usage
if __name__ == "__main__":
    # Get the project base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Construct a path to the 'data/' folder
    data_dir = os.path.join(base_dir, "data")
    example_file = os.path.join(data_dir, "example.csv")

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Example data
    headers = ["Name", "Age", "City"]
    data = [["Alice", 30, "New York"], ["Bob", 25, "San Francisco"]]

    # Write to CSV
    CSVHandler.write_csv(example_file, data, headers=headers)

    # Read from CSV
    read_data = CSVHandler.read_csv(example_file)
    print("Read data:", read_data)
