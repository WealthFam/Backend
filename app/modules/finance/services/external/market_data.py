import asyncio
import logging
import httpx
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class MarketDataService:
    # Resolution for sparklines (40 points across the period)
    MARKET_INDEX_RESOLUTION = 40

    # Core indices for the dashpulse overview
    DASHBOARD_INDICES = [
        {"name": "NIFTY 50", "symbol": "^NSEI"},
        {"name": "SENSEX", "symbol": "^BSESN"},
        {"name": "NASDAQ", "symbol": "^IXIC"},
        {"name": "SMALLCAP 100", "symbol": "^CNXSC"},
        {"name": "GOLD", "symbol": "GOLDBEES.NS"},
        {"name": "USD / INR", "symbol": "USDINR=X"}
    ]

    @staticmethod
    async def get_market_indices(timeframe: str = "1d") -> List[Dict[str, Any]]:
        """
        Orchestrates fetching and formatting for all dashboard indices.
        Returns ready-to-render data for the frontend.
        """
        async def process_ticker(idx):
            try:
                data = await MarketDataService.fetch_ticker_data(idx['symbol'], timeframe)
                
                if not data["success"] or not data["points"]:
                    return {
                        "name": idx['name'],
                        "value": "Unavailable",
                        "change": "0.00",
                        "percent": "0.00%",
                        "isUp": True,
                        "sparkline": [],
                        "labels": []
                    }
                
                current_price = data["current_price"]
                previous_close = data["previous_close"]
                points = data["points"]
                
                valid_closes = [p['c'] for p in points]
                
                # Decimal calculations for financial precision
                current_dec = Decimal(str(current_price))
                if timeframe != "1d" and valid_closes:
                    initial_dec = Decimal(str(valid_closes[0]))
                    change_dec = current_dec - initial_dec
                    percent_dec = (change_dec / initial_dec) * 100 if initial_dec else Decimal('0')
                else:
                    prev_dec = Decimal(str(previous_close)) if previous_close else current_dec
                    change_dec = current_dec - prev_dec
                    percent_dec = (change_dec / prev_dec) * 100 if prev_dec else Decimal('0')
                    
                # Sparkline sampling
                step = max(1, len(points) // MarketDataService.MARKET_INDEX_RESOLUTION)
                sampled_points = points[::step] if len(points) > MarketDataService.MARKET_INDEX_RESOLUTION else points
                
                sparkline = [round(p['c'], 2) for p in sampled_points]
                
                # Time labels for tooltips
                labels = []
                for p in sampled_points:
                    dt = datetime.fromtimestamp(p['t'])
                    if timeframe == "1d":
                        labels.append(dt.strftime('%I:%M %p'))
                    else:
                        labels.append(dt.strftime('%b %d'))

                return {
                    "name": idx['name'],
                    "symbol": idx['symbol'],
                    "value": f"{current_price:,.2f}", 
                    "change": f"{change_dec:+.2f}",
                    "percent": f"{percent_dec:+.2f}%",
                    "isUp": change_dec >= 0,
                    "sparkline": sparkline,
                    "labels": labels
                }
            except Exception as e:
                logger.error(f"Error processing {idx['name']}: {e}")
                return {
                    "name": idx['name'],
                    "value": "Error",
                    "change": "0.00",
                    "percent": "0.00%",
                    "isUp": True,
                    "sparkline": [],
                    "labels": []
                }

        tasks = [process_ticker(idx) for idx in MarketDataService.DASHBOARD_INDICES]
        return await asyncio.gather(*tasks)

    @staticmethod
    async def fetch_ticker_data(symbol: str, timeframe: str = "1d") -> Dict[str, Any]:
        """
        Low-level fetch from Yahoo Finance with trend fallback.
        """
        try:
            # Map timeframe to Yahoo Finance params
            interval = "5m"
            if timeframe == "7d":
                interval = "15m"
            elif timeframe == "30d":
                interval = "1d"
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={timeframe}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
            
            # Fallback: If 1d is too sparse, try 5d trend
            if response.status_code == 200 and timeframe == "1d":
                temp_data = response.json()
                temp_res = temp_data['chart']['result'][0]
                temp_indicators = temp_res['indicators']['quote'][0]
                temp_closes = [c for c in temp_indicators.get('close', []) if c is not None]
                
                if len(temp_closes) < 10:
                    logger.info(f"Sparse 1d data for {symbol}, falling back to 5d trend")
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1h&range=5d"
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch {symbol}: {response.status_code}")
                return MarketDataService._empty_response()

            data = response.json()
            if not data.get('chart', {}).get('result'):
                return MarketDataService._empty_response()

            res = data['chart']['result'][0]
            meta = res['meta']
            indicators = res['indicators']['quote'][0]
            closes = indicators.get('close', [])
            timestamps = res.get('timestamp', [])
            
            points = []
            for i in range(min(len(closes), len(timestamps))):
                if closes[i] is not None:
                    points.append({"c": float(closes[i]), "t": int(timestamps[i])})
            
            return {
                "success": True,
                "symbol": symbol,
                "current_price": meta.get('regularMarketPrice'),
                "previous_close": meta.get('chartPreviousClose'),
                "points": points,
                "meta": meta
            }

        except Exception as e:
            logger.error(f"Error in MarketDataService for {symbol}: {e}")
            return MarketDataService._empty_response()

    @staticmethod
    def _empty_response() -> Dict[str, Any]:
        return {
            "success": False,
            "current_price": 0,
            "previous_close": 0,
            "points": [],
            "meta": {}
        }
