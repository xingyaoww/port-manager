import streamlit as st
import pandas as pd
import subprocess

from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout="wide")

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
    netstat_df,
    gridOptions=options_builder.build(),
    height=800,
    theme="streamlit",
    # fit_columns_on_grid_load=True
)
