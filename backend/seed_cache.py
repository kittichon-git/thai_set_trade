"""
seed_cache.py — ดึงข้อมูล DW จาก thaidw.com โดยใช้ Chrome profile ของคุณ
(browser จะโหลด cached data ที่มีอยู่แล้ว แม้ตลาดจะปิด)

วิธีใช้:
    python seed_cache.py

ผล: สร้างไฟล์ dw_cache.json ในโฟลเดอร์เดียวกัน
"""
from __future__ import annotations

import json
import os
import time

# ── Chrome user profile path (แก้ถ้า profile ของคุณอยู่ที่อื่น) ──────────
CHROME_PROFILE = os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data"
)
THAIDW_URL = (
    "https://thaidw.com/tools/dwsearch/"
    "?underlying=all&maturity=all&expiry=all&type=all"
    "&effectiveGearing=all&indicator=all&moneyness=all"
    "&moneynessPercent=all&issuer=all"
)
CACHE_FILE = os.path.join(os.path.dirname(__file__), "dw_cache.json")


def main() -> None:
    from playwright.sync_api import sync_playwright

    result: list = []

    def on_response(res) -> None:
        nonlocal result
        if "ScreenerJSONServlet" in res.url and "init=1" not in res.url:
            try:
                body = res.body()
                if len(body) > 20:
                    d = json.loads(body)
                    items = d.get("data") or d.get("dwlist") or []
                    if items:
                        result = items
                        print(f"✓ Intercepted {len(items)} items from {res.url[:80]}")
            except Exception as ex:
                print(f"  parse error: {ex}")

    print(f"Chrome profile: {CHROME_PROFILE}")
    print("เปิด browser... (อย่าปิด Chrome อื่นที่เปิดอยู่ก่อน)")

    with sync_playwright() as p:
        # ใช้ Chrome จริงของผู้ใช้ (มี cache/session)
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE,
            headless=False,           # เปิดหน้าต่างจริง
            channel="chrome",         # ใช้ Chrome ไม่ใช่ Chromium
            args=["--no-first-run", "--no-default-browser-check"],
        )
        page = ctx.new_page()
        page.on("response", on_response)

        print(f"กำลังโหลด {THAIDW_URL[:60]}...")
        try:
            page.goto(THAIDW_URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception:
            pass

        # รอ 15 วิให้ React load + API call
        for i in range(15, 0, -1):
            print(f"\r  รอ {i:2d} วิ... items={len(result)}", end="", flush=True)
            time.sleep(1)
        print()

        ctx.close()

    if result:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"saved_at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": result}, f)
        print(f"\n✓ บันทึก {len(result)} items → {CACHE_FILE}")
    else:
        print("\n✗ ไม่พบข้อมูล — ลองปิด Chrome ทั้งหมดก่อนแล้วรันใหม่")


if __name__ == "__main__":
    main()
