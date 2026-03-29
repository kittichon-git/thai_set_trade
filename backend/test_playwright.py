import asyncio
import logging
from dw_scraper import scrape_dw_universe_playwright, DW_ALL_COLLECTED, DW_UNIVERSE

logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing Playwright Scraper...")
    await scrape_dw_universe_playwright()
    print(f"Total in ALL: {sum(len(v) for v in DW_ALL_COLLECTED.values())}")
    print(f"Total in UNIVERSE: {sum(len(v) for v in DW_UNIVERSE.values())}")
    
    # Check BLS
    all_dws = [dw for list_dw in DW_ALL_COLLECTED.values() for dw in list_dw]
    bls_count = len([dw for dw in all_dws if dw.issuer == "BLS"])
    print(f"Total BLS in ALL: {bls_count}")

    # Check WHA
    wha_all = DW_ALL_COLLECTED.get("WHA", [])
    print(f"WHA total: {len(wha_all)}")
    issuers = set(d.issuer for d in wha_all)
    print(f"WHA Issuers: {issuers}")
    wha_01 = [d.dw_code for d in wha_all if "01" in d.dw_code]
    print(f"WHA 01 codes: {wha_01}")

if __name__ == "__main__":
    asyncio.run(test())
