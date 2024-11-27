import csv
import logging

# Set up module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CSVHandler:
    @staticmethod
    def read_csv(file_path):
        try:
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
        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows(data)
                logger.info(f"Appended {len(data)} rows to {file_path}.")
        except Exception as e:
            logger.error(f"Error appending to CSV file '{file_path}': {e}")
            raise
