import pandas as pd
import utils

def process_data(df, numeric_columns):
    df = df[df["Player"] != "League Average"].dropna(subset=["Player"])
    df["Player Key"] = df["Player"].apply(utils.make_player_key)
    df = df.sort_values(by=["Player Key", "Team"])
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    
    df["FP"] = (df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"] - df["TOV"] - df["PF"]).astype(int)
    df["FPPG"] = (df["FP"] / df["G"]).round(1)
    df["FPPM"] = (df["FP"] / df["MP"]).round(2)
    df["MPG"] = (df["MP"] / df["G"]).round(1)
    df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)
    
    return df
