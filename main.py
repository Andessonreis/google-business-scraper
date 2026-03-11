from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import os
import re
import time
import random

# ==============================
# MODELS
# ==============================


@dataclass
class Business:
    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    category: str = None
    opening_hours: dict = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: float = None
    longitude: float = None
    price_level: int = None


@dataclass
class BusinessList:
    business_list: list[Business] = field(default_factory=list)

    def dataframe(self):
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )


# ==============================
# HELPERS
# ==============================


def slugify(text):
    return (
        text.lower()
        .replace(" ", "_")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def read_search_terms(file_path="input.txt"):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def extract_coordinates_from_url(url: str):
    coordinates = url.split("/@")[-1].split("/")[0]
    lat, lon = coordinates.split(",")[:2]
    return float(lat), float(lon)


# ==============================
# 🔢 PARSERS
# ==============================


def parse_int(text: str) -> int:
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else 0


def parse_float(text: str) -> float:
    match = re.search(r"[\d.,]+", text)
    if not match:
        return 0.0

    value = match.group(0)

    if "," in value and value.count(",") == 1:
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", "")

    return float(value)


# ==============================
# VALIDATION, DEDUP & FILTERING
# ==============================


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def validate_search_terms(terms: list[str]) -> list[str]:
    """Remove termos vazios e duplicados"""
    cleaned = []
    seen = set()

    for term in terms:
        term = normalize_text(term)
        if not term:
            continue
        if term in seen:
            continue
        seen.add(term)
        cleaned.append(term)

    return cleaned


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove registros inválidos"""
    if df.empty:
        return df

    df = df[df["name"].notna() & (df["name"] != "")]
    df = df[df["latitude"].notna() & df["longitude"].notna()]

    return df


def deduplicate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicados por coordenada"""
    if df.empty:
        return df

    return df.drop_duplicates(subset=["latitude", "longitude"], keep="first")


def filter_only_cellphones(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra o DataFrame para manter apenas linhas com números de celular."""
    if df.empty or "phone_number" not in df.columns:
        return df

    # Regex para celular brasileiro: (XX) 9XXXX-XXXX ou similar
    celular_pattern = r"\(?\d{2}\)?\s*9\d{4}-?\d{4}"

    # Aplica o filtro
    df = df[df["phone_number"].str.contains(celular_pattern, na=False, regex=True)]

    return df


# ==============================
# SCRAPER (INTACTO)
# ==============================


def scrape_data(search_term):
    business_list = BusinessList()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.get_by_label("Pesquise no Google Maps").wait_for()

        print(f"\n🔎 Searching for: {search_term}")

        search_box = page.get_by_label("Pesquise no Google Maps")
        search_box.fill(search_term)

        page.get_by_role("button", name="Pesquisar").click()

        # === INÍCIO DA CORREÇÃO ===
        try:
            # Espera até 10 segundos para ver se a lista de resultados aparece
            page.locator(
                '//a[contains(@href, "https://www.google.com/maps/place")]'
            ).first.wait_for(timeout=10000)
        except Exception:
            print(
                f"⚠️ Nenhum resultado encontrado ou lista não carregada para: {search_term}. Pulando..."
            )
            browser.close()
            return business_list  # Retorna a lista vazia e o pipeline segue o jogo

        # Se passou do try, significa que tem lista, então podemos fazer o hover
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
        # === FIM DA CORREÇÃO ===

        previously_counted = 0
        while True:
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(3000)

            current_count = page.locator(
                '//a[contains(@href, "https://www.google.com/maps/place")]'
            ).count()

            if current_count == previously_counted:
                print("Reached all available listings.")
                break
            else:
                previously_counted = current_count
                print(f"Currently Scraped: {current_count}")

        listings = page.locator(
            '//a[contains(@href, "https://www.google.com/maps/place")]'
        ).all()

        for listing in listings:
            try:
                listing.click()
                page.wait_for_timeout(8000)

                business = Business()

                business.name = (
                    page.locator("//h1").last.inner_text()
                    if page.locator("//h1").count() > 0
                    else ""
                )

                business.address = (
                    page.locator(
                        '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    ).inner_text()
                    if page.locator(
                        '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    ).count()
                    > 0
                    else ""
                )

                business.website = (
                    page.locator("//a[contains(@aria-label, 'Website')]").get_attribute(
                        "href"
                    )
                    if page.locator("//a[contains(@aria-label, 'Website')]").count() > 0
                    else ""
                )

                business.phone_number = (
                    page.locator(
                        '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                    ).inner_text()
                    if page.locator(
                        '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                    ).count()
                    > 0
                    else ""
                )

                if page.locator("//div[2]/span[2]/span/span").count() > 0:
                    text = page.locator("//div[2]/span[2]/span/span").get_attribute(
                        "aria-label"
                    )
                    business.reviews_count = parse_int(text)

                star_locator = page.locator(
                    '//div[@role="img" and contains(@aria-label, "estrelas")]'
                )

                if star_locator.count() > 0:
                    text = star_locator.first.get_attribute("aria-label")
                    business.reviews_average = parse_float(text)

                business.category = (
                    page.locator(
                        '//div[contains(@class, "fontBodyMedium")]//button[contains(@class, "DkEaL")]'
                    ).inner_text()
                    if page.locator(
                        '//div[contains(@class, "fontBodyMedium")]//button[contains(@class, "DkEaL")]'
                    ).count()
                    > 0
                    else ""
                )

                business.latitude, business.longitude = extract_coordinates_from_url(
                    page.url
                )

                business_list.business_list.append(business)

            except Exception as e:
                print(f"Error scraping a specific listing: {e}")

        print(f"Finished scraping {search_term}")
        browser.close()

    return business_list


# ==============================
# PIPELINE
# ==============================

if __name__ == "__main__":
    search_terms = validate_search_terms(read_search_terms("input.txt"))

    all_dataframes = []

    for index, term in enumerate(search_terms):
        # Evita delay na PRIMEIRA busca, mas aplica em todas as subsequentes
        if index > 0:
            delay = random.uniform(
                15.0, 30.0
            )  # Sorteia um número entre 15 e 30 segundos
            print(
                f"\n⏳ Aguardando {delay:.2f} segundos para evitar bloqueios do Google..."
            )
            time.sleep(delay)

        print(f"\n===== PROCESSANDO ({index + 1}/{len(search_terms)}): {term} =====")

        result = scrape_data(term)
        df = result.dataframe()

        # validação e dedup (safe)
        df = validate_dataframe(df)
        df = deduplicate_dataframe(df)

        # Filtra logo aqui para não salvar lixo nas pastas individuais
        df = filter_only_cellphones(df)

        if not df.empty:
            all_dataframes.append(df)

            term_folder = f"output/por_termo/{slugify(term)}"
            os.makedirs(term_folder, exist_ok=True)

            df.to_csv(f"{term_folder}/dados_celular.csv", index=False)
            df.to_excel(f"{term_folder}/dados_celular.xlsx", index=False)
        else:
            print(f"Nenhum celular encontrado para o termo: {term}")

    os.makedirs("output/consolidado", exist_ok=True)

    if all_dataframes:
        df_all = pd.concat(all_dataframes, ignore_index=True)

        # deduplicação global
        df_all = deduplicate_dataframe(df_all)

        # Salva a única planilha final com todos os celulares
        df_all.to_csv("output/consolidado/todos_os_contadores_celular.csv", index=False)
        df_all.to_excel(
            "output/consolidado/todos_os_contadores_celular.xlsx", index=False
        )

        print(
            f"\n🔥 Pipeline finalizado! {len(df_all)} contadores com celular encontrados."
        )
    else:
        print(
            "\n❌ Nenhum dado com número de celular foi encontrado em todas as buscas."
        )
