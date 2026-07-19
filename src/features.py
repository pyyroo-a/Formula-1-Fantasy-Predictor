import pandas as pd

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Status"].isin(["Finished", "Lapped"])].copy()

    df = df.sort_values(by=["Abbreviation", "Year", "RoundNumber"])

    df["PreviousPosition"] = (
        df.groupby("Abbreviation")["Position"]
        .shift(1)
    )

    df["Rolling3Average"] = (
        df.groupby("Abbreviation")["Position"]
        .transform(lambda x: x.ewm(span=3, adjust=False).mean())
    )

    df = df.dropna(subset=["PreviousPosition"])

    return df

def add_position_change(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["PositionChange"] = df["GridPosition"] - df["Position"]

    df["AveragePositionChange"] = (
        df.groupby("Abbreviation")["PositionChange"]
        .transform(lambda x: x.ewm(span=3, adjust=False).mean())
    )

    df["AveragePositionChange"] = df["AveragePositionChange"].fillna(0)

    return df

def add_consistency(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Consistency"] = (
        df.groupby("Abbreviation")["PositionChange"]
        .transform(lambda x: x.ewm(span=3, adjust=False).std())
    )

    df["Consistency"] = df["Consistency"].fillna(0)

    return df

def add_grid_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["GridvsForm"] = df["GridPosition"] - df["Rolling3Average"]

    df["FormTrend"] = df["Rolling3Average"] - df["PreviousPosition"]

    return df

def add_results_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Top10Finish"] = (df["Position"] <= 10).astype(int)
    df["Top5Finish"] = (df["Position"] <= 5).astype(int)
    df["DNF"] = (df["Status"] != "Finished").astype(int)

    return df

def add_driver_dominance(df: pd.DataFrame) -> pd.DataFrame:
    """Win rate and podium rate over last 5 races — captures in-season dominance like Antonelli."""
    df = df.copy()

    df["Win"] = (df["Position"] == 1).astype(int)
    df["Podium"] = (df["Position"] <= 3).astype(int)

    df["WinRate"] = (
        df.groupby("Abbreviation")["Win"]
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
        .fillna(0)
    )

    df["PodiumRate"] = (
        df.groupby("Abbreviation")["Podium"]
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
        .fillna(0)
    )

    return df

def add_team_form(df: pd.DataFrame) -> pd.DataFrame:
    """Team's average finishing position over the last 3 races — penalises consistently poor teams."""
    df = df.copy()

    team_race_avg = (
        df.groupby(["TeamName", "Year", "RoundNumber"])["Position"]
        .mean()
        .reset_index()
        .rename(columns={"Position": "_TeamRaceAvg"})
        .sort_values(["TeamName", "Year", "RoundNumber"])
    )

    team_race_avg["TeamAvgPosition"] = (
        team_race_avg.groupby("TeamName")["_TeamRaceAvg"]
        .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    )

    df = df.merge(
        team_race_avg[["TeamName", "Year", "RoundNumber", "TeamAvgPosition"]],
        on=["TeamName", "Year", "RoundNumber"],
        how="left",
    )
    df["TeamAvgPosition"] = df["TeamAvgPosition"].fillna(10.0)

    return df

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_rolling_features(df)
    df = add_position_change(df)
    df = add_consistency(df)
    df = add_grid_features(df)
    df = add_results_flags(df)
    df = add_driver_dominance(df)
    df = add_team_form(df)

    return df