import asyncio
import sys, os, json, time, random
from os.path import exists
from collections import deque

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from hdwallet import HDWallet
from hdwallet.mnemonics import BIP39Mnemonic
from hdwallet.cryptocurrencies import Tron as Cryptocurrency
from hdwallet.derivations import BIP44Derivation, CHANGES
from hdwallet.hds import BIP32HD

from tronpy import Tron
from tronpy.providers import HTTPProvider


console = Console()


class Scanner:
    def __init__(self, threads=10):
        self.sem = asyncio.Semaphore(threads)

        self.total = 0
        self.hit = 0
        self.start_time = time.time()

        self.logs = deque(maxlen=15)

        self.client = Tron(
            HTTPProvider(api_key="ed68c908-a4df-443d-9bea-1a747d3ec8be")
        )

        self.contract = self.client.get_contract(
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        )
        self.precision = self.contract.functions.decimals()

        self.table = Table(expand=True)
        self.table.add_column("Address", justify="center", style="cyan")
        self.table.add_column("TRX", justify="center", style="green")
        self.table.add_column("USDT", justify="center", style="magenta")
        self.table.add_column("Status", justify="center")

    def log(self, message, style="white"):
        self.logs.append(Text(message, style=style))

    async def seek(self, seed):
        async with self.sem:
            await asyncio.to_thread(self._process_seed, seed)

    def retry(self, func, *args, retries=5):
        for i in range(retries):
            try:
                return func(*args)
            except Exception as e:
                if "429" in str(e):
                    wait = (i + 1) * 2
                    self.log(f"[429] retry {wait}s", "yellow")
                    time.sleep(wait)
                else:
                    return 0
        return 0

    def _process_seed(self, seed):
        try:
            time.sleep(random.uniform(0.2, 0.5))

            hdwallet = HDWallet(
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

            self.total += 1

            if float(trx_balance or 0) > 0 or float(usdt_balance) > 0:
                self.hit += 1
                status = "[bold green]HIT[/]"

                with open("resul.txt", "a") as f:
                    f.write(f"{address}|{seed}|{priv}\n")

                self.log(f"[HIT] {address} | TRX:{trx_balance} USDT:{usdt_balance}", "green")

            else:
                status = "[red]EMPTY[/]"
                self.log(f"[SCAN] {address}", "dim")

            self.table.add_row(
                address,
                str(trx_balance),
                str(usdt_balance),
                status
            )

        except Exception as e:
            self.log(f"[ERROR] {e}", "red")

    def build_layout(self):
        layout = Layout()

        layout.split(
            Layout(name="top", size=12),
            Layout(name="bottom")
        )

        # top = table
        layout["top"].update(
            Panel(self.table, title="🔥 TRON SCANNER", border_style="cyan")
        )

        # bottom = logs + stats
        speed = self.total / (time.time() - self.start_time + 1)

        log_text = "\n".join([str(log) for log in self.logs])

        stats = f"""
[bold green]Total:[/] {self.total}
[bold cyan]Hit:[/] {self.hit}
[bold yellow]Speed:[/] {speed:.2f}/s
"""

        layout["bottom"].split_row(
            Layout(Panel(log_text, title="📜 Logs", border_style="magenta")),
            Layout(Panel(stats, title="📊 Stats", border_style="green"))
        )

        return layout

    async def run(self, input_file):
        with open(input_file, "r") as f:
            seeds = f.read().splitlines()

        tasks = [asyncio.create_task(self.seek(seed)) for seed in seeds if seed.strip()]

        with Live(self.build_layout(), refresh_per_second=5, console=console) as live:
            while not all(t.done() for t in tasks):
                live.update(self.build_layout())
                await asyncio.sleep(0.2)

            await asyncio.gather(*tasks)

        console.print(Panel(
            f"[bold green]DONE[/]\nTotal: {self.total}\nHit: {self.hit}",
            title="Result"
        ))


if __name__ == "__main__":
    console.print(Panel("🚀 [bold cyan]TRON SCANNER PRO MAX[/]"))

    input_file = input("List : ")
    threads = int(input("Thread (5-20): "))

    if not exists(input_file):
        console.print("[red]File not found[/]")
        exit()

    scanner = Scanner(threads)
    asyncio.run(scanner.run(input_file))