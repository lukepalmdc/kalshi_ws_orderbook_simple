# Kalshi Simple WebSocket Orderbook

**High-performance Python library for consuming live Kalshi orderbook data** with async + threaded support.  

This library allows you to track markets, process snapshots and deltas, and query the orderbook safely from synchronous code.

---

## Features

- Async-first orderbook feed
- Thread-safe `OrderbookManager`
- Background thread support for synchronous applications
- Calculates best prices, liquidity, and top N levels
- Lightweight and dependency-minimal
- Designed for live trading and backtesting

---

## Installation

```bash
pip install kalshi-simple-ws-orderbook
```


## Setup

You will need:

1. API Key ID
2. API Key file, (I use a .pem file)



Log in to your Kalshi account (demo or production)
Navigate to Account & security → API Keys
Click Create Key
Save both:
    Private Key: Downloaded as a .key file
    API Key ID: Displayed on screen


https://docs.kalshi.com/getting_started/quick_start_authenticated_requests


## Usage

See demo.py for examples on using the library, aside form getting the most recent orderbook there are several function to measure liquidity and get the current best price. Currentlyt the example is using market ticker "KXPRESPERSON-28-JVAN" which is the market ticker for jd vance presidential odds.

## Orderbook Notes

Kalshi order book is refreshed on subscription, and then updated with orderbook delta messages, if there is too much backpressure resubscribing can get current status, adding as a feature to next version

