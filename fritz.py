import base64
import logging
import random
from dataclasses import dataclass
from typing import Tuple
import requests
from seleniumbase import SB


# ==============================
# CONFIGURARE GLOBALĂ
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("StreamAutomation")


@dataclass(frozen=True)
class ConfigAplicatie:
    api_geolocatie: str = "http://ip-api.com/json/"
    canal_codat_base64: str = "YnJ1dGFsbGVz"
    sablon_url: str = "https://www.twitch.tv/{}"
    timeout_click: int = 4
    pauza_scurta: int = 2
    pauza_medie: int = 10
    pauza_lunga_min: int = 400
    pauza_lunga_max: int = 900


@dataclass
class Locatie:
    latitudine: float
    longitudine: float
    fus_orar: str
    cod_tara: str


# ==============================
# SERVICIU GEOLOCAȚIE
# ==============================

class ServiciuGeolocatie:

    def __init__(self, config: ConfigAplicatie):
        self.config = config

    def obtine_locatie_curenta(self) -> Locatie:
        try:
            raspuns = requests.get(self.config.api_geolocatie, timeout=5)
            raspuns.raise_for_status()
            date = raspuns.json()

            return Locatie(
                latitudine=date["lat"],
                longitudine=date["lon"],
                fus_orar=date["timezone"],
                cod_tara=date["countryCode"].lower()
            )
        except requests.RequestException as eroare:
            logger.error("Eroare la obținerea geolocației: %s", eroare)
            raise


# ==============================
# MANAGER BROWSER
# ==============================

class ManagerBrowser:

    SELECTORI = {
        "accept_cookie": 'button:contains("Accept")',
        "start_vizionare": 'button:contains("Start Watching")',
        "indicator_live": "#live-channel-stream-information",
    }

    def __init__(self, config: ConfigAplicatie, locatie: Locatie):
        self.config = config
        self.locatie = locatie

    def construieste_url_canal(self) -> str:
        nume_decodat = base64.b64decode(
            self.config.canal_codat_base64
        ).decode("utf-8")

        return self.config.sablon_url.format(nume_decodat)

    def initializeaza_driver(self, driver: SB, url: str) -> None:
        driver.activate_cdp_mode(
            url,
            tzone=self.locatie.fus_orar,
            geoloc=(self.locatie.latitudine, self.locatie.longitudine)
        )
        driver.sleep(self.config.pauza_scurta)
        self.accepta_cookie(driver)

    def accepta_cookie(self, driver: SB) -> None:
        if driver.is_element_present(self.SELECTORI["accept_cookie"]):
            driver.cdp.click(
                self.SELECTORI["accept_cookie"],
                timeout=self.config.timeout_click
            )
            driver.sleep(self.config.pauza_scurta)

    def porneste_stream_daca_e_necesar(self, driver: SB) -> None:
        driver.sleep(self.config.pauza_medie)

        if driver.is_element_present(self.SELECTORI["start_vizionare"]):
            driver.cdp.click(
                self.SELECTORI["start_vizionare"],
                timeout=self.config.timeout_click
            )
            driver.sleep(self.config.pauza_medie)

    def stream_este_live(self, driver: SB) -> bool:
        return driver.is_element_present(
            self.SELECTORI["indicator_live"]
        )


# ==============================
# SERVICIU AUTOMATIZARE STREAM
# ==============================

class ServiciuAutomatizareStream:

    def __init__(self):
        self.config = ConfigAplicatie()
        self.serviciu_geo = ServiciuGeolocatie(self.config)
        self.locatie = self.serviciu_geo.obtine_locatie_curenta()
        self.manager_browser = ManagerBrowser(self.config, self.locatie)

        self.durata_random = random.randint(
            self.config.pauza_lunga_min,
            self.config.pauza_lunga_max
        )

    def ruleaza_browser_secundar(self, driver_principal: SB) -> None:
        try:
            driver_secundar = driver_principal.get_new_driver(
                undetectable=True
            )

            url = self.manager_browser.construieste_url_canal()

            self.manager_browser.initializeaza_driver(
                driver_secundar,
                url
            )

            self.manager_browser.porneste_stream_daca_e_necesar(
                driver_secundar
            )

            self.manager_browser.accepta_cookie(driver_secundar)

            driver_principal.sleep(self.durata_random)

        except Exception as eroare:
            logger.error("Eroare la browser secundar: %s", eroare)

    def ruleaza(self) -> None:
        url = self.manager_browser.construieste_url_canal()

        while True:
            try:
                with SB(
                    uc=True,
                    locale="en",
                    ad_block=True,
                    chromium_arg="--disable-webgl"
                ) as driver_principal:

                    self.manager_browser.initializeaza_driver(
                        driver_principal,
                        url
                    )

                    self.manager_browser.porneste_stream_daca_e_necesar(
                        driver_principal
                    )

                    self.manager_browser.accepta_cookie(driver_principal)

                    if self.manager_browser.stream_este_live(driver_principal):
                        logger.info("Stream live detectat.")
                        self.ruleaza_browser_secundar(driver_principal)
                    else:
                        logger.info("Stream live indisponibil. Oprire.")
                        break

            except Exception as eroare:
                logger.error("Automatizarea a eșuat: %s", eroare)
                break


# ==============================
# ENTRY POINT
# ==============================

def main():
    aplicatie = ServiciuAutomatizareStream()
    aplicatie.ruleaza()


if __name__ == "__main__":
    main()
