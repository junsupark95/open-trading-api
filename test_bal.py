import sys
import asyncio

sys.path.extend(['.', 'examples_user', 'examples_user/domestic_stock', 'examples_user/auth'])

import kis_auth as ka
from domestic_stock_functions import inquire_balance

async def main():
    ka.auth(svr="vps", product="01")
    trenv = ka.getTREnv()
    df1, df2 = inquire_balance(env_dv="demo", cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod, afhr_flpr_yn="N", inqr_dvsn="01", unpr_dvsn="01", fund_sttl_icld_yn="N", fncg_amt_auto_rdpt_yn="N", prcs_dvsn="00")
    if not df2.empty:
        print("Columns in df2:", df2.columns.tolist())
    else:
        print("df2 is empty")

asyncio.run(main())
