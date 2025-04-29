import os
import sys
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.append(PROJECT_ROOT)

import scripts as s

def main(match_id: str):

    # Get current matchrooms player info
    all_p_ids, all_g_ids, all_nicks, configured_time = s.lobby_info(match_id)


    avg_kd = []
    avg_kr = []
    session_performance = []
    lobby_ses_dat = []

    for idx in range(len(all_p_ids)):
        p_id = all_p_ids[idx]
        g_id = all_g_ids[idx]
        nick = all_nicks[idx]

        ses_dat = s.session(p_id, nick, configured_time)
        lobby_ses_dat.append(ses_dat)

    columns = ['K/D', 'K/R', '# Matches', '# Wins', 'Performance']
    lobby_ses_dat = np.array(lobby_ses_dat)
    data = pd.DataFrame(data=lobby_ses_dat, index=all_nicks, columns=columns)

if __name__ == '__main__':
    try:
        match_id = str(sys.argv[1])
    except IndexError:
        raise Exception('Please provide a match_id as a string when calling Main')
    
    try:
        main(match_id=match_id)
    except KeyError:
        raise Exception('Match id is invalid, please provide a valid Match id')