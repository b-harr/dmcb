import pandas as pd
import utils

def add_fantasy_stats(df, numeric_columns):
    """
    Process the DataFrame by cleaning, sorting, and adding fantasy basketball stats.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame containing basketball player data.
        numeric_columns (list): List of column names expected to contain numeric values.

    Returns:
        pd.DataFrame: Processed DataFrame with added fantasy stats.
    """
    # Remove rows for "League Average" and drop rows with missing "Player" values
    df = df[df["Player"] != "League Average"].dropna(subset=["Player"])
    
    # Generate a unique player key
    df["Player Key"] = df["Player"].apply(utils.make_player_key)
    
    # Sort the DataFrame by player key and team
    df = df.sort_values(by=["Player Key", "Team"])
    
    # Convert numeric columns to numeric types, handling errors
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    
    # Calculate fantasy basketball stats
    df["FP"] = (df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"] - df["TOV"] - df["PF"]).astype(int)
    df["FPPG"] = (df["FP"] / df["G"]).round(1)
    df["FPPM"] = (df["FP"] / df["MP"]).round(2)
    df["MPG"] = (df["MP"] / df["G"]).round(1)
    df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)
    
    return df
