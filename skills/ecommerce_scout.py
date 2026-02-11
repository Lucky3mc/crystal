import requests
import csv
import time
import os
from bs4 import BeautifulSoup
from skill_manager import Skill

class EcommerceScout(Skill):
    name = "E-Commerce Scout"
    description = "Tracks prices and alerts you to drops on your wishlist."
    keywords = ["scout", "track", "wishlist", "add to list"]
    supported_intents = ["ecommerce_scout"]
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.wishlist_file = "wishlist.csv"
        self.last_check_time = 0
        self.check_interval = 3600  # Check every 1 hour (3600 seconds)

    def _extract_price(self, url):
        """Scrapes the price from a given URL."""
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Simplified logic: look for common price containers
            price_tag = soup.find("span", class_="a-price-whole") or soup.find("div", class_="x-price-primary")
            if price_tag:
                # Remove symbols like $ or , to get a clean number
                return float(price_tag.text.replace("$", "").replace(",", "").strip())
            return None
        except:
            return None

    def price_monitor(self):
        """Called by the Brain's background loop."""
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return # Too early to check again

        print("📡 [SCOUT]: Running background wishlist check...")
        if not os.path.exists(self.wishlist_file): return

        updated_rows = []
        with open(self.wishlist_file, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                current_price = self._extract_price(row['url'])
                if current_price:
                    # 🔥 ALERT LOGIC: If price is lower than target, notify!
                    if current_price <= float(row['target_price']):
                        print(f"🔥 [ALERT]: {row['name']} dropped to ${current_price}!")
                    
                    row['last_price'] = current_price
                updated_rows.append(row)

        # Update the CSV with the latest prices
        with open(self.wishlist_file, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["name", "url", "target_price", "last_price"])
            writer.writeheader()
            writer.writerows(updated_rows)

        self.last_check_time = current_time

    def run(self, parameters: dict):
        text = parameters.get("user_input", "").lower()
        
        # Logic to add a new item: "track [URL] target [price]"
        if "track" in text:
            url = next((w for w in text.split() if "http" in w), None)
            target = text.split("target")[-1].strip() if "target" in text else "0"
            
            if url:
                with open(self.wishlist_file, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["New Product", url, target, "N/A"])
                return f"Target acquired, Lucky. I've added that URL to the wishlist with a ${target} goal."
        
        return "To track an item, say: 'track [link] target [price]'"