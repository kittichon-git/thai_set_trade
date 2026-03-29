import asyncio
import logging
from dw_scraper import _scrape_bls, DW_ALL_COLLECTED

logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing BLS Scraper...")
    bls_data = await _scrape_bls()
    print(f"BLS items found: {sum(len(v) for v in bls_data.values())}")
    
    # Check WHA
    wha_bls = bls_data.get("WHA", [])
    print(f"WHA BLS total: {len(wha_bls)}")
    for d in wha_bls:
        print(f"  {d.dw_code} (Gearing: {d.gearing}, Expiry: {d.expiry_date})")

if __name__ == "__main__":
    asyncio.run(test())
