import csv
import os
import logging

# Set up module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CSVHandler:
    """
    A utility class for handling CSV file operations.
    """

    @staticmethod
    def read_csv(file_path):
        """
        Reads a CSV file and returns its contents as a list of rows.
        Each row is represented as a list of values.
        
        Args:
            file_path (str): The path to the CSV file.

        Returns:
            list: A list of rows from the CSV file.
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
        
        Args:
            file_path (str): The path to the CSV file.
            data (list of lists): The data to write, where each sublist represents a row.
            headers (list, optional): Optional list of column headers.
        """
        try:
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

    @staticmethod
    def append_csv(file_path, data):
        """
        Appends data to an existing CSV file. Creates the file if it doesn't exist.
        
        Args:
            file_path (str): The path to the CSV file.
            data (list of lists): The data to append, where each sublist represents a row.
        """
        try:
            file_exists = os.path.exists(file_path)
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows(data)
                action = "Appended" if file_exists else "Created and wrote"
                logger.info(f"{action} {len(data)} rows to {file_path}.")
        except Exception as e:
            logger.error(f"Error appending to CSV file '{file_path}': {e}")
            raise

    @staticmethod
    def clear_csv(file_path):
        """
        Clears the contents of a CSV file.
        
        Args:
            file_path (str): The path to the CSV file.
        """
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                pass
            logger.info(f"Cleared contents of {file_path}.")
        except Exception as e:
            logger.error(f"Error clearing CSV file '{file_path}': {e}")
            raise


# Example usage
if __name__ == "__main__":
    # Set up logging for the module
    logging.basicConfig(level=logging.INFO)
    
    # Example file path
    example_file = "example.csv"
    
    # Example data
    headers = ["Name", "Age", "City"]
    data = [["Alice", 30, "New York"], ["Bob", 25, "San Francisco"]]
    
    # Write to CSV
    CSVHandler.write_csv(example_file, data, headers=headers)
    
    # Read from CSV
    read_data = CSVHandler.read_csv(example_file)
    print("Read data:", read_data)
    
    # Append to CSV
    additional_data = [["Charlie", 35, "Chicago"]]
    CSVHandler.append_csv(example_file, additional_data)
    
    # Read again to see appended data
    read_data = CSVHandler.read_csv(example_file)
    print("Updated data:", read_data)
    
    # Clear the CSV file
    CSVHandler.clear_csv(example_file)
