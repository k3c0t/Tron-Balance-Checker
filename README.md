
# 🚀 TRON Async Scanner Termux - Nethunter 

Scanner wallet TRON berbasis mnemonic (seed phrase) menggunakan **asyncio** untuk performa tinggi + anti rate limit.


## Penting
- Jangan Set Thread lebih dari 5 Karena Akan Limit
- ini api key gratisan jadi terbatas 


## ✨ Features

- ⚡ Async scanning (lebih cepat dari threading biasa)
- 🧠 Smart rate limit handling (anti 429)
- 🔁 Auto retry + exponential backoff
- 🎯 Detect TRX & USDT balance
- 💾 Save result ke file
- 🔒 Stable & optimized

---

## 📦 Requirements

- Python 3.9+
- rich
- hdwallet>=3.0.0
- tronpy>=0.4.0
- requests>=2.31.0
