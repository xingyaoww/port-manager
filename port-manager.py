import streamlit as st
import pandas as pd
import subprocess

from st_aggrid import AgGrid, GridOptionsBuilder
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

st.set_page_config(layout="wide")

# https://blog.streamlit.io/auto-generate-a-dataframe-filtering-ui-in-streamlit-with-filter_dataframe/
def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns
    Args:
        df (pd.DataFrame): Original dataframe
    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters", key="-".join(df.columns))

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df


def get_netstat_df():
    output = subprocess.run(["sudo", "netstat", "-tupln"], capture_output=True)

    # Skip 1st line ("Active Internet connections (only servers)")
    # and 2nd line ("Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name")
    netstat_outputs = output.stdout.decode().split("\n")[2:-1]
    netstat_col_names = ["Protocol", "Recv-Q", "Send-Q", "Local Address", "Foreign Address", "State", "PID/Program name"]
    netstat_df = pd.DataFrame(list(map(lambda x: x.strip().split(maxsplit=6), netstat_outputs)), columns=netstat_col_names)

    # Seperately Visualize TCP & UDP
    _udp = netstat_df["Protocol"].str.startswith("udp")
    # fix UDP column alignment issue
    netstat_df.loc[_udp, "PID/Program name"] = netstat_df.loc[_udp, "State"]
    netstat_df.loc[_udp, "State"] = None

    netstat_df["Port Number"] = netstat_df["Local Address"].str.split(":").str[-1].apply(int)
    netstat_df.fillna("-", inplace=True)
    return netstat_df.sort_values(by="Port Number")

def get_process_info():
    output = subprocess.run(["sudo", "ps", "aux"], capture_output=True)
    ps_outputs = output.stdout.decode().split("\n")
    ps_outputs = list(map(lambda x: x.split(maxsplit=10), ps_outputs))
    ps_colnames, ps_outputs = ps_outputs[0], ps_outputs[1:]
    return pd.DataFrame(ps_outputs, columns=ps_colnames)

netstat_df = get_netstat_df()
process_info = get_process_info()
process_info.set_index("PID", inplace=True)

st.header("Port Manager")
netstat_df["PID"] = netstat_df["PID/Program name"].apply(
    lambda x: x.split("/")[0] if x != "-" else "-"
)
netstat_df["Program Command"] = netstat_df["PID"].apply(
    lambda pid: process_info.loc[pid, "COMMAND"] if pid != "-" else "-"
)
netstat_df["User"] = netstat_df["PID"].apply(
    lambda pid: process_info.loc[pid, "USER"] if pid != "-" else "-"
)

netstat_df["Application"] = "EDITABLE - FILL THIS LATER"
# Filter Keys for Port Manager
netstat_df = netstat_df[[
    "Protocol",
    "Port Number",
    "Local Address",
    "State",
    "PID",
    "User", 
    "Program Command",
    "Application"
]]

options_builder = GridOptionsBuilder.from_dataframe(netstat_df)
options_builder.configure_column("Application", editable=True)
# options_builder.configure_column("Program Command", initialWidth=200)

AgGrid(
    filter_dataframe(netstat_df),
    gridOptions=options_builder.build(),
    height=800,
    theme="streamlit",
    # fit_columns_on_grid_load=True
)
