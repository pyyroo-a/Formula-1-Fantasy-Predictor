import pandas as pd

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Status"] == "Finished"].copy()

    df = df.sort_values(by=["Abbreviation", "Year", "RoundNumber"])

    df["PreviousPosition"] = (
        df.groupby("Abbreviation")["Position"]
        .shift(1)
    )

    df["Rolling3Average"] = (
        df.groupby("Abbreviation")["Position"]
        .rolling(window=3)
        .mean()
        .reset_index(0 ,drop=True)
    )

    df = df.dropna(subset=["PreviousPosition","Rolling3Average"])

    return df

def add_position_change(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["PositionChange"] = df["GridPosition"] - df["Position"]

    df["AveragePositionChange"] = (
        df.groupby("Abbreviation")["PositionChange"]
        .transform(lambda x: x.rolling(window=3).mean())
    )

    df["AveragePositionChange"] = df["AveragePositionChange"].fillna(0) # just a check incase there isnt any history

    return df

def add_consistency(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Consistency"] = (
        df.groupby("Abbreviation")["PositionChange"]
        .transform(lambda x: x.rolling(window=3).std()) # the lower the std the better because it shows the driver is consistenc
    )

    df["Consistency"] = df["Consistency"].fillna(0)

    return df

def add_grid_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["GridvsForm"] = df["GridPosition"] - df["Position"]

    df["FormTrend"] = df["Rolling3Average"] - df["PreviousPosition"]

    return df

def add_results_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Top10Finish"] = (df["Position"] <= 10).astype(int)
    df["Top5Finish"] = (df["Position"] <= 5).astype(int)
    df["DNF"] = (df["Status"] != "Finished").astype(int)

    return df

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_rolling_features(df)
    df = add_position_change(df)
    df = add_consistency(df)
    df = add_grid_features(df)
    df = add_results_flags(df)

    return df