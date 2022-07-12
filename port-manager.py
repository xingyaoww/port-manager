import streamlit as st
import pandas as pd
import subprocess

def get_netstat_df():
    output = subprocess.run(["netstat", "-tupln"], capture_output=True)

    # Skip 1st line ("Active Internet connections (only servers)")
    # and 2nd line ("Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name")
    netstat_outputs = output.stdout.decode().split("\n")[2:-1]
    netstat_col_names = ["Protocol", "Recv-Q", "Send-Q", "Local Address", "Foreign Address", "State", "PID/Program name"]
    netstat_df = pd.DataFrame(list(map(lambda x: x.split(), netstat_outputs[1:])), columns=netstat_col_names)

    # Seperately Visualize TCP & UDP
    _udp = netstat_df["Protocol"].str.startswith("udp")
    netstat_tcp_df = netstat_df[~_udp]
    netstat_udp_df = netstat_df[_udp]
    # fix UDP column alignment issue
    netstat_udp_df.loc[:, "PID/Program name"] = netstat_udp_df.loc[:, "State"]
    netstat_udp_df.loc[:, "State"] = None
    return netstat_tcp_df, netstat_udp_df

netstat_tcp_df, netstat_udp_df = get_netstat_df()


st.header("TCP Ports")
st.table(netstat_tcp_df)
st.header("UDP Ports")
st.table(netstat_udp_df)
