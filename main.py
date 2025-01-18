from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import os
import sys
import time

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
    #sobre_content: str = None  # Descrição fornecida pelo proprietário ou extraída

@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """

    business_list: list[Business] = field(default_factory=list)
    save_at = "output"

    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """

        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"output/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file

        Args:
            filename (str): filename
        """

        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"output/{filename}.csv", index=False)


def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""

    coordinates = url.split("/@")[-1].split("/")[0]
    # return latitude, longitude
    return float(coordinates.split(",")[0]), float(coordinates.split(",")[1])


def main():
    ########
    # input
    ########

    # read search from arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    args = parser.parse_args()

    if args.search:
        search_list = [args.search]

    if args.total:
        total = args.total
    else:
        # if no total is passed, we set the value to random big number
        total = 1_000_000

    if not args.search:
        search_list = []
        # read search from input.txt file
        input_file_name = "input.txt"
        # Get the absolute path of the file in the current working directory
        input_file_path = os.path.join(os.getcwd(), input_file_name)
        # Check if the file exists
        if os.path.exists(input_file_path):
            # Open the file in read mode
            with open(input_file_path, "r") as file:
                # Read all lines into a list
                search_list = file.readlines()

        if len(search_list) == 0:
            print(
                "Error occured: You must either pass the -s search argument, or add searches to input.txt"
            )
            sys.exit()

    ###########
    # scraping
    ###########
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        # wait is added for dev phase. can remove it in production
        page.wait_for_timeout(5000)

        for search_for_index, search_for in enumerate(search_list):
            print(f"-----\n{search_for_index} - {search_for}".strip())

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            # scrolling
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            # this variable is used to detect if the bot
            # scraped the same number of listings in the previous iteration
            previously_counted = 0
            while True:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)

                if (
                    page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    >= total
                ):
                    listings = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()[:total]
                    listings = [listing.locator("xpath=..") for listing in listings]
                    print(f"Total Scraped: {len(listings)}")
                    break
                else:
                    # logic to break from loop to not run infinitely
                    # in case arrived at all available listings
                    if (
                        page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count()
                        == previously_counted
                    ):
                        listings = page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).all()
                        print(
                            f"Arrived at all available\nTotal Scraped: {len(listings)}"
                        )
                        break
                    else:
                        previously_counted = page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count()
                        print(
                            f"Currently Scraped: ",
                            page.locator(
                                '//a[contains(@href, "https://www.google.com/maps/place")]'
                            ).count(),
                        )

            business_list = BusinessList()

            # scraping
            for listing in listings:
                try:
                    listing.click()
                    page.wait_for_timeout(15000)

                    name_attribute = "aria-label"
                    business_name_xpath = '//h1[@class="DUwDvf lfPIob"]'
                    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    website_xpath = "//a[contains(@aria-label, 'Website') and contains(@href, 'http')]"

                    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                    review_count_xpath = "//div[2]/span[2]/span/span"
                    reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'
                    book_a_table = "//div[2]/div[5]/div/a/div"
                    category_xpath = '//div[contains(@class, "fontBodyMedium")]//button[contains(@class, "DkEaL")]'
                    opening_hours_xpath = "//td[@class='mxowUb']//li[@class='G8aQO']"
                    price_level_xpath = '//span[@class="mgr77e"]'
                    #description_xpath = '//div[@data-attrid="description"]//span//text()'

                    # Check for the presence of "book a table"
                    if page.locator(book_a_table).count() > 0:
                        print("Skipping business with 'Book a Table' option")
                        continue

                    business = Business()
                        
                    # Business Name       
                    if page.locator(business_name_xpath).count() > 0:
                        business.name = page.locator(business_name_xpath).inner_text()
                        print(f"Extracted name: {business.name}")  # DEBUGGING
                    else:
                        print("Business name not found")
                        business.name = ""
                        
                    # Address
                    if page.locator(address_xpath).count() > 0:
                        business.address = (
                            page.locator(address_xpath).all()[0].inner_text()
                        )
                    else:
                        business.address = ""
                        
                    # Website
                    if page.locator(website_xpath).count() > 0:
                        temp = page.locator(website_xpath)
                        href_value = temp.get_attribute('href')
                        business.website = href_value if href_value else "Not Given" 
                    else:
                        business.website = "Not Given"
                        
                    # Phone Number
                    if page.locator(phone_number_xpath).count() > 0:
                        business.phone_number = (
                            page.locator(phone_number_xpath).all()[0].inner_text()
                        )
                    else:
                        business.phone_number = ""
                        
                    # Review Count 
                    if page.locator(review_count_xpath).count() > 0:
                        business.reviews_count = int(
                            page.locator(review_count_xpath)
                            .get_attribute(name_attribute)
                            .split()[0]
                            .replace(",", "")
                            .strip()
                        )
                    else:
                        business.reviews_count = ""
                        
                    # Review Average
                    if page.locator(reviews_average_xpath).count() > 0:
                        business.reviews_average = float(
                            page.locator(reviews_average_xpath)
                            .get_attribute(name_attribute)
                            .split()[0]
                            .replace(",", ".")
                            .strip()
                        )
                    else:
                        business.reviews_average = ""
                        
                    # Category
                    if page.locator(category_xpath).count() > 0:
                        business.category = page.locator(category_xpath).inner_text()
                    else:
                        business.category = ""
                    
                    # Opening Hours
                    opening_hours_elements = page.locator(opening_hours_xpath)

                    # Verificar se há elementos encontrados
                    if opening_hours_elements.count() > 0:
                        # Garantir que o loop não exceda 7 dias
                        business.opening_hours = {
                            f"Dia {i+1}": opening_hours_elements.nth(i).inner_text()
                            for i in range(min(opening_hours_elements.count(), 7))
                        }
                    else:
                        business.opening_hours = {}
                                                                
                    # Latitude and Longitude
                    business.latitude, business.longitude = (
                        extract_coordinates_from_url(page.url)
                    )

                    business_list.business_list.append(business)
                except Exception as e:
                    print(f"Error occured: {e}")

            #########
            # output
            #########
            business_list.save_to_excel(
                f"google_maps_data_{search_for}".replace(" ", "_")
            )
            business_list.save_to_csv(
                f"google_maps_data_{search_for}".replace(" ", "_")
            )
            #########
            # Adicionar um delay de 5 minutos antes da próxima pesquisa
            #########
            print(f"Aguardando 5 minutos antes de iniciar a próxima pesquisa...")
            time.sleep(300)  # Aguarda 300 segundos (5 minutos)


        browser.close()


if __name__ == "__main__":
    main()