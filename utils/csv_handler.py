import csv
import logging

# Set up module-level logging to track operations
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CSVHandler:
    """
    A utility class for handling CSV file operations.
    
    This class provides methods to:
    - Read from a CSV file
    - Write to a CSV file (overwriting existing content)
    - Append data to an existing CSV file
    - Clear the contents of a CSV file
    """

    @staticmethod
    def read_csv(file_path):
        """
        Reads a CSV file and returns its contents as a list of rows.
        
        Args:
            file_path (str): The path to the CSV file.
        
        Returns:
            list: A list of rows from the CSV file, each row being a list of values.
        
        If the file doesn't exist, it logs a warning and returns an empty list.
        """
        try:
            with open(file_path, mode="r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)  # Create a CSV reader object
                data = [row for row in reader]  # Read all rows into a list
                logger.info(f"Read {len(data)} rows from {file_path}.")  # Log how many rows were read
                return data
        except Exception as e:
            logger.error(f"Error reading CSV file '{file_path}': {e}")  # Log any errors that occur
            raise  # Re-raise the exception so the caller is aware of the error

    @staticmethod
    def write_csv(file_path, data, headers=None):
        """
        Writes data to a CSV file, overwriting the file if it already exists.
        
        Args:
            file_path (str): The path to the CSV file.
            data (list of lists): The data to write to the file, where each sublist represents a row.
            headers (list, optional): Optional list of column headers to write at the top of the file.
        
        Writes the headers (if provided) first, followed by the data rows.
        """
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)  # Create a CSV writer object
                if headers:  # If headers are provided, write them first
                    writer.writerow(headers)
                    logger.info(f"Wrote headers to {file_path}: {headers}")  # Log the headers written
                writer.writerows(data)  # Write the data rows
                logger.info(f"Wrote {len(data)} rows to {file_path}.")  # Log the number of rows written
        except Exception as e:
            logger.error(f"Error writing to CSV file '{file_path}': {e}")  # Log any errors
            raise  # Re-raise the exception to alert the caller

    @staticmethod
    def append_csv(file_path, data):
        """
        Appends data to an existing CSV file. Creates the file if it doesn't exist.
        
        Args:
            file_path (str): The path to the CSV file.
            data (list of lists): The data to append, where each sublist represents a row.
        
        Appends data to the CSV file if it exists, or creates a new file and writes the data if it doesn't.
        """
        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)  # Create a CSV writer object
                writer.writerows(data)  # Append the data rows
                logger.info(f"Appended {len(data)} rows to {file_path}.")  # Log the number of rows appended
        except Exception as e:
            logger.error(f"Error appending to CSV file '{file_path}': {e}")  # Log any errors
            raise  # Re-raise the exception to alert the caller

    @staticmethod
    def clear_csv(file_path):
        """
        Clears the contents of a CSV file, effectively deleting all its data.
        
        Args:
            file_path (str): The path to the CSV file.
        
        This method will leave the file empty, but the file itself remains.
        """
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                # Opening the file in write mode and not writing anything clears its content
                pass
            logger.info(f"Cleared contents of {file_path}.")  # Log that the file has been cleared
        except Exception as e:
            logger.error(f"Error clearing CSV file '{file_path}': {e}")  # Log any errors
            raise  # Re-raise the exception to alert the caller


# Example usage (not part of the class definition, but included for testing the module)
if __name__ == "__main__":
    # Set up logging for the module
    logging.basicConfig(level=logging.INFO)
    
    # Example file path
    example_file = "example.csv"
    
    # Example data to write or append
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
