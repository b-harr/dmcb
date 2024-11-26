import os
import pandas as pd

def read_file(input_dir, input_file):
    os.makedirs(input_dir, exist_ok=True)
    input_csv = os.path.join(input_dir, input_file)
    dataframe = pd.read_csv(input_csv)
    return dataframe

def write_file(dataframe, output_dir, output_file):
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, output_file)
    pd.DataFrame(dataframe).to_csv(output_csv, index=False, encoding="utf-8")
