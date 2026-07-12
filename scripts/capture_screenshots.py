"""Capture Lappa IDE screenshots via headless Chrome + Selenium."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:8840"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=8) as r:
        return json.loads(r.read().decode())


def set_slider(driver, sid: str, value: float) -> None:
    driver.execute_script(
        """
        const el = document.getElementById(arguments[0]);
        el.value = arguments[1];
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        sid,
        str(value),
    )


def click_demo(driver, name: str) -> None:
    # open demos panel
    driver.find_element(By.CSS_SELECTOR, '.act[data-panel="demos"]').click()
    time.sleep(0.35)
    cards = driver.find_elements(By.CSS_SELECTOR, ".demo-card")
    for c in cards:
        if name in c.text:
            c.click()
            time.sleep(1.4)
            return
    raise RuntimeError(f"demo not found: {name}")


def open_explorer(driver) -> None:
    driver.find_element(By.CSS_SELECTOR, '.act[data-panel="explorer"]').click()
    time.sleep(0.25)


def open_sim_panel(driver) -> None:
    driver.find_element(By.CSS_SELECTOR, '.act[data-panel="sim"]').click()
    time.sleep(0.25)


def wait_boot(driver) -> None:
    wait = WebDriverWait(driver, 30)
    wait.until(
        lambda d: d.execute_script(
            "return document.getElementById('demo-list') "
            "&& document.getElementById('demo-list').children.length > 0"
        )
    )
    # monaco + first demo load
    time.sleep(2.8)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("health", get_json("/health"))

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1600,1000")
    opts.add_argument("--force-device-scale-factor=1")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.binary_location = CHROME

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(BASE + "/")
        wait_boot(driver)

        # 1) Overview — demos list visible
        driver.find_element(By.CSS_SELECTOR, '.act[data-panel="demos"]').click()
        time.sleep(0.5)
        driver.save_screenshot(str(OUT / "ide-overview.png"))
        print("saved ide-overview.png")

        # 2) Diff drive with motion
        click_demo(driver, "diff_drive_2w")
        open_sim_panel(driver)
        set_slider(driver, "lx", 0.55)
        set_slider(driver, "az", 0.55)
        time.sleep(2.8)  # trail builds
        open_explorer(driver)
        driver.save_screenshot(str(OUT / "sim-diff-drive.png"))
        print("saved sim-diff-drive.png")

        # 3) Omni 3w
        click_demo(driver, "omni_3w")
        open_sim_panel(driver)
        set_slider(driver, "lx", 0.25)
        set_slider(driver, "ly", 0.55)
        set_slider(driver, "az", 0.25)
        time.sleep(2.5)
        # leave demos panel open to show robot list
        driver.find_element(By.CSS_SELECTOR, '.act[data-panel="demos"]').click()
        time.sleep(0.3)
        driver.save_screenshot(str(OUT / "sim-omni-3w.png"))
        print("saved sim-omni-3w.png")

        # 4) Arm
        click_demo(driver, "simple_arm")
        open_sim_panel(driver)
        set_slider(driver, "lx", 0.5)
        set_slider(driver, "az", -0.4)
        time.sleep(2.2)
        open_explorer(driver)
        driver.save_screenshot(str(OUT / "sim-arm.png"))
        print("saved sim-arm.png")

        # 5) Ackermann + docker panel
        click_demo(driver, "ackermann_4w")
        open_sim_panel(driver)
        set_slider(driver, "lx", 0.5)
        set_slider(driver, "az", 0.35)
        time.sleep(2.0)
        driver.find_element(By.CSS_SELECTOR, '.act[data-panel="docker"]').click()
        time.sleep(0.35)
        try:
            driver.find_element(By.ID, "btn-docker-refresh").click()
            time.sleep(0.7)
        except Exception:
            pass
        driver.save_screenshot(str(OUT / "docker-panel.png"))
        print("saved docker-panel.png")

        # 6) Tricycle for variety
        click_demo(driver, "tricycle_3w")
        open_sim_panel(driver)
        set_slider(driver, "lx", 0.5)
        set_slider(driver, "az", 0.6)
        time.sleep(2.3)
        open_explorer(driver)
        driver.save_screenshot(str(OUT / "sim-tricycle.png"))
        print("saved sim-tricycle.png")

    finally:
        driver.quit()

    for p in sorted(OUT.glob("*.png")):
        print(f"  {p.name} {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
