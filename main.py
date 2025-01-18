from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import os
import time
import threading

app = Flask(__name__)

@dataclass
class Business:
    """holds business data"""
    
    name: str = None  # Nome do negócio
    address: str = None  # Endereço completo
    website: str = None  # URL do site oficial
    phone_number: str = None  # Número de telefone
    category: str = None  # Categoria do negócio (ex.: restaurante, loja)
    opening_hours: dict = None  # Horário de funcionamento, ex.: {"Segunda": "08:00-18:00", ...}
    reviews_count: int = None  # Número total de avaliações
    reviews_average: float = None  # Média das avaliações (0.0 a 5.0)
    latitude: float = None  # Latitude do local
    longitude: float = None  # Longitude do local
    price_level: int = None  # Nível de preço (1 = barato, 5 = caro)

@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """

    business_list: list[Business] = field(default_factory=list)
    save_at = "output"

    def dataframe(self):
        """transform business_list to pandas dataframe"""
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"output/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"output/{filename}.csv", index=False)


def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""
    coordinates = url.split("/@")[-1].split("/")[0]
    return float(coordinates.split(",")[0]), float(coordinates.split(",")[1])


def scrape_data(search_list):
    """Main scraping logic"""
    business_list = BusinessList()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.wait_for_timeout(5000)

        for search_for in search_list:
            print(f"-----\nSearching for: {search_for}")

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            # scrolling to load more businesses
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            previously_counted = 0
            while True:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)

                # Check if the number of listings increased, continue if true
                current_count = page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).count()
                
                if current_count == previously_counted:
                    print("Reached all available listings.")
                    break
                else:
                    previously_counted = current_count
                    print(f"Currently Scraped: {current_count}")

            # Scraping the business details
            listings = page.locator(
                '//a[contains(@href, "https://www.google.com/maps/place")]'
            ).all()

            for listing in listings:
                try:
                    listing.click()
                    page.wait_for_timeout(15000)

                    # Select the elements to scrape
                    business = Business()
                    business.name = page.locator('//h1[@class="DUwDvf lfPIob"]').inner_text() if page.locator('//h1[@class="DUwDvf lfPIob"]').count() > 0 else ""
                    business.address = page.locator('//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]').inner_text() if page.locator('//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]').count() > 0 else ""
                    business.website = page.locator("//a[contains(@aria-label, 'Website')]").get_attribute('href') if page.locator("//a[contains(@aria-label, 'Website')]").count() > 0 else "Not Given"
                    business.phone_number = page.locator('//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]').inner_text() if page.locator('//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]').count() > 0 else ""
                    business.reviews_count = int(page.locator("//div[2]/span[2]/span/span").get_attribute('aria-label').split()[0].replace(",", "")) if page.locator("//div[2]/span[2]/span/span").count() > 0 else 0
                    business.reviews_average = float(page.locator('//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]').get_attribute('aria-label').split()[0].replace(",", ".")) if page.locator('//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]').count() > 0 else 0
                    business.category = page.locator('//div[contains(@class, "fontBodyMedium")]//button[contains(@class, "DkEaL")]').inner_text() if page.locator('//div[contains(@class, "fontBodyMedium")]//button[contains(@class, "DkEaL")]').count() > 0 else ""
                    business.latitude, business.longitude = extract_coordinates_from_url(page.url)

                    business_list.business_list.append(business)

                except Exception as e:
                    print(f"Error: {e}")
            
            print(f"Finished scraping {search_for}")
            
        browser.close()

    return business_list


@app.route('/scrape', methods=['POST'])
def scrape():
    """API endpoint to trigger the scraping process"""
    search_terms = request.json.get('search', [])
    
    if not search_terms:
        return jsonify({"error": "No search terms provided"}), 400
    
    print("Starting scraping process...")
    
    # Scrape data in a separate thread to avoid blocking the server
    threading.Thread(target=scrape_data, args=(search_terms,)).start()
    
    return jsonify({"message": "Scraping started successfully!"}), 200


@app.route('/status', methods=['GET'])
def status():
    """API endpoint to check if the scraping is finished"""
    return jsonify({"status": "scraping in progress"}), 200


if __name__ == '__main__':
    app.run(debug=True)
