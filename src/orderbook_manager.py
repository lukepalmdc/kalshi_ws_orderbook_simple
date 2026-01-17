from collections import defaultdict
import threading



class OrderbookManager:
    def __init__(self):
        # Store orderbooks by market_ticker
        # Structure: {market_ticker: {'yes': {price: quantity}, 'no': {price: quantity}}}
        self.orderbooks = defaultdict(lambda: {'yes': {}, 'no': {}})
        self.market_ids = {}  # Track market_ticker -> market_id mapping
        self._lock = threading.Lock()  # Thread-safe access
        self.message_count = 0
        self.dropped_messages = 0
    
    def handle_snapshot(self, msg):
        """Process orderbook_snapshot message"""
        market_ticker = msg['market_ticker']
        market_id = msg['market_id']
        
        with self._lock:
            # Store market ID mapping
            self.market_ids[market_ticker] = market_id
            
            # Initialize orderbook with snapshot data
            orderbook = {'yes': {}, 'no': {}}
            
            # Process yes side
            for price, quantity in msg['yes']:
                orderbook['yes'][price] = quantity
            
            # Process no side
            for price, quantity in msg['no']:
                orderbook['no'][price] = quantity
            
            self.orderbooks[market_ticker] = orderbook
        
        print(f"[Orderbook] Snapshot loaded for {market_ticker}")
    
    def handle_delta(self, msg):
        """Process orderbook_delta message - FAST, lock-free when possible"""
        market_ticker = msg['market_ticker']
        price = msg['price']
        delta = msg['delta']
        side = msg['side']
        
        # Quick check without lock first
        if market_ticker not in self.orderbooks:
            print(f"[Orderbook] Warning: Received delta for unknown market {market_ticker}")
            return
        
        with self._lock:
            orderbook = self.orderbooks[market_ticker]
            
            # Get current quantity at this price level
            current_qty = orderbook[side].get(price, 0)
            new_qty = current_qty + delta
            
            if new_qty <= 0:
                # Remove price level if quantity is 0 or negative
                if price in orderbook[side]:
                    del orderbook[side][price]
            else:
                # Update quantity
                orderbook[side][price] = new_qty
            
            self.message_count += 1
    
    def get_orderbook(self, market_ticker):
        """Thread-safe method to get orderbook snapshot"""
        with self._lock:
            if market_ticker not in self.orderbooks:
                return None
            # Return a deep copy to avoid race conditions
            return {
                'yes': dict(self.orderbooks[market_ticker]['yes']),
                'no': dict(self.orderbooks[market_ticker]['no'])
            }
    
    def get_best_prices(self, market_ticker):
        """Get best bid/ask for each side"""
        with self._lock:
            if market_ticker not in self.orderbooks:
                return None
            
            orderbook = self.orderbooks[market_ticker]
            
            result = {}
            if orderbook['yes']:
                result['best_yes'] = max(orderbook['yes'].keys())
                result['best_yes_qty'] = orderbook['yes'][result['best_yes']]
            
            if orderbook['no']:
                result['best_no'] = max(orderbook['no'].keys())
                result['best_no_qty'] = orderbook['no'][result['best_no']]
            
            return result
    
    def get_depth(self, market_ticker, side, max_levels=10):
        """Get top N levels of orderbook for a side"""
        with self._lock:
            if market_ticker not in self.orderbooks:
                return []
            
            orderbook = self.orderbooks[market_ticker]
            sorted_levels = sorted(orderbook[side].items(), reverse=True)
            return sorted_levels[:max_levels]

    def calculate_liquidity_in_range(self, ticker, side, price_delta_cents):
        """
        Calculate total liquidity from best price to best_price + delta
        
        Args:
            ticker: Market ticker
            side: 'yes' or 'no'
            price_delta_cents: How many cents from best price to include (e.g., 5 for 5 cents)
        
        Returns:
            dict with liquidity stats or None if no data
        """
        orderbook = self.get_orderbook(ticker)
        best = self.get_best_prices(ticker)
        
        if not orderbook or not best:
            return None
        
        side_lower = side.lower()
        if side_lower == 'yes':
            best_price_key = 'best_no'
        else:
            best_price_key = 'best_yes'
        
        if best_price_key not in best:
            return None

        if side_lower == 'yes':
            asks_side = 'no' 
        else:
            asks_side = 'yes'

        
        best_price = (100 - best[best_price_key])
        min_price = best_price
        max_price = best_price + price_delta_cents
        
        # Sum liquidity in the range
        total_liquidity = 0
        levels_included = 0
        total_notional = 0
        total_price = 0

        for price, qty in orderbook[asks_side].items():
            price = (100 - price)
            if min_price <= price <= max_price:
                total_liquidity += qty
                levels_included += 1
                total_notional += (price) * qty
                total_price += ((price/100) * qty) / qty
                

        return {
            'ticker': ticker,
            'side': side_lower,
            'best_price': best_price,
            'max_price': max_price,
            'price_range': (min_price, max_price),
            'price_delta_cents': price_delta_cents,
            'total_liquidity': total_liquidity,
            'levels_included': levels_included,
            'total_notional': total_notional,
            'total_price': total_price
        }
    
    def get_all_markets(self):
        """Get list of all tracked market tickers"""
        with self._lock:
            return list(self.orderbooks.keys())
    
    def get_stats(self):
        """Get orderbook statistics"""
        return {
            'messages_processed': self.message_count,
            'messages_dropped': self.dropped_messages,
            'markets_tracked': len(self.orderbooks),
            'queue_size': message_queue.qsize(),
            'queue_max': message_queue.maxsize
        }
    
    def print_orderbook(self, market_ticker, max_levels=10):
        """Print current orderbook state"""
        orderbook = self.get_orderbook(market_ticker)
        if not orderbook:
            print(f"No orderbook for {market_ticker}")
            return
        
        print(f"\n=== Orderbook for {market_ticker} ===")
        
        # Sort and display yes side
        yes_sorted = sorted(orderbook['yes'].items(), reverse=True)[:max_levels]
        print(f"YES side ({len(orderbook['yes'])} levels):")
        for price, qty in yes_sorted:
            print(f"  {price:3d} ({price/100:.2f}): {qty:,}")
        
        # Sort and display no side
        no_sorted = sorted(orderbook['no'].items(), reverse=True)[:max_levels]
        print(f"NO side ({len(orderbook['no'])} levels):")
        for price, qty in no_sorted:
            print(f"  {price:3d} ({price/100:.2f}): {qty:,}")
        print()


    def print_orderbook_asks(self, market_ticker, max_levels=10):
        """Print orderbook showing explicit bids (asks implicit via 100-price)"""
        orderbook = self.get_orderbook(market_ticker)
        if not orderbook:
            print(f"No orderbook for {market_ticker}")
            return

        # YES bids (explicit)
        yes_sorted = sorted(orderbook["yes"].items(), reverse=True)[:max_levels]
 
        for price, qty in yes_sorted:
            implied_no_ask = 100 - price
        
        # NO bids (explicit)
        no_sorted = sorted(orderbook["no"].items(), reverse=True)[:max_levels]

        for price, qty in no_sorted:
            implied_yes_ask = 100 - price