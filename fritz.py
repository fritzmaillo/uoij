import base64
import logging
import random
from typing import Optional, Tuple
from dataclasses import dataclass
import requests
from seleniumbase import SB

# Configurare sistem de logare
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class LocatieGeografica:
    """Reprezintă informații despre locația geografică și fusul orar."""
    latitudine: float
    longitudine: float
    fus_orar: str
    cod_tara: str


class AutomatizareBrowserStream:
    """Gestionează automatizarea browserului pentru interacțiuni cu platforma de streaming."""
    
    # Constante de configurare
    API_GEOLOCATIE = "http://ip-api.com/json/"
    CANAL_TINTA = "YnJ1dGFsbGVz"  # Nume canal codificat Base64
    SABLON_URL_TINTA = "https://www.twitch.tv/{}"
    TIMEOUT_CLICK = 4
    PAUZA_SCURTA = 2
    PAUZA_MEDIE = 10
    PAUZA_LUNGA_MIN = 400
    PAUZA_LUNGA_MAX = 900
    
    SELECTORI = {
        "buton_accept": 'button:contains("Accept")',
        "buton_start_vizionare": 'button:contains("Start Watching")',
        "stream_live": "#live-channel-stream-information",
    }
    
    def __init__(self):
        """Inițializează automatizarea browserului cu datele de geolocație."""
        self.locatie = self._obtine_geolocatia()
        self.url_tinta = self._construieste_url_tinta()
        self.durata_pauza_random = random.randint(
            self.PAUZA_LUNGA_MIN, 
            self.PAUZA_LUNGA_MAX
        )
    
    @staticmethod
    def _obtine_geolocatia() -> LocatieGeografica:
        """
        Obține informațiile de geolocație pe baza IP-ului.
        
        Returnează:
            LocatieGeografica: Obiect cu latitudine, longitudine, fus orar și cod țară.
            
        Ridică:
            requests.RequestException: Dacă apelul API eșuează.
        """
        try:
            raspuns = requests.get(AutomatizareBrowserStream.API_GEOLOCATIE, timeout=5)
            raspuns.raise_for_status()
            date = raspuns.json()
            
            return LocatieGeografica(
                latitudine=date["lat"],
                longitudine=date["lon"],
                fus_orar=date["timezone"],
                cod_tara=date["countryCode"].lower()
            )
        except requests.RequestException as eroare:
            logger.error(f"Eroare la obținerea geolocației: {eroare}")
            raise
    
    @staticmethod
    def _construieste_url_tinta() -> str:
        """
        Decodează numele canalului din Base64 și construiește URL-ul țintă.
        
        Returnează:
            str: URL complet către canalul de streaming.
        """
        nume_codat = AutomatizareBrowserStream.CANAL_TINTA
        nume_decodat = base64.b64decode(nume_codat).decode("utf-8")
        return AutomatizareBrowserStream.SABLON_URL_TINTA.format(nume_decodat)
    
    def _accepta_dialoguri(self, driver: SB) -> None:
        """
        Acceptă eventualele dialoguri de consimțământ/cookie-uri.
        
        Args:
            driver: Instanță SeleniumBase.
        """
        if driver.is_element_present(self.SELECTORI["buton_accept"]):
            driver.cdp.click(self.SELECTORI["buton_accept"], timeout=self.TIMEOUT_CLICK)
            driver.sleep(self.PAUZA_SCURTA)
    
    def _asteapta_incarcare_stream(self, driver: SB) -> None:
        """
        Așteaptă încărcarea streamului și gestionează butonul de pornire vizionare.
        
        Args:
            driver: Instanță SeleniumBase.
        """
        driver.sleep(self.PAUZA_MEDIE)
        if driver.is_element_present(self.SELECTORI["buton_start_vizionare"]):
            driver.cdp.click(self.SELECTORI["buton_start_vizionare"], timeout=self.TIMEOUT_CLICK)
            driver.sleep(self.PAUZA_MEDIE)
    
    def _initializeaza_driver(self, driver: SB, mod_nedetectabil: bool = False) -> SB:
        """
        Inițializează și configurează o instanță de driver.
        
        Args:
            driver: Instanță SeleniumBase.
            mod_nedetectabil: Activează modul nedetectabil dacă este True.
            
        Returnează:
            SB: Instanța de driver configurată.
        """
        driver.activate_cdp_mode(
            self.url_tinta,
            tzone=self.locatie.fus_orar,
            geoloc=(self.locatie.latitudine, self.locatie.longitudine)
        )
        driver.sleep(self.PAUZA_SCURTA)
        self._accepta_dialoguri(driver)
        return driver
    
    def _ruleaza_browser_secundar(self, driver_principal: SB) -> None:
        """
        Lansează și gestionează o instanță secundară de browser.
        
        Args:
            driver_principal: Instanța principală SeleniumBase.
        """
        try:
            driver_secundar = driver_principal.get_new_driver(undetectable=True)
            self._initializeaza_driver(driver_secundar, mod_nedetectabil=True)
            self._asteapta_incarcare_stream(driver_secundar)
            self._accepta_dialoguri(driver_secundar)
            driver_principal.sleep(self.durata_pauza_random)
        except Exception as eroare:
            logger.error(f"Eroare browser secundar: {eroare}")
        finally:
            # Curățare dacă este necesar
            pass
    
    def ruleaza(self) -> None:
        """
        Execută bucla principală de automatizare.
        
        Monitorizează continuu pagina de streaming și gestionează mai multe instanțe de browser.
        """
        while True:
            try:
                with SB(
                    uc=True, 
                    locale="en",
                    ad_block=True,
                    chromium_arg="--disable-webgl"
                ) as driver_principal:
                    self._initializeaza_driver(driver_principal)
                    self._asteapta_incarcare_stream(driver_principal)
                    self._accepta_dialoguri(driver_principal)
                    
                    # Verifică dacă streamul live este prezent
                    if driver_principal.is_element_present(self.SELECTORI["stream_live"]):
                        self._accepta_dialoguri(driver_principal)
                        self._ruleaza_browser_secundar(driver_principal)
                    else:
                        logger.info("Stream live negăsit, se oprește automatizarea")
                        break
            except Exception as eroare:
                logger.error(f"Automatizarea a eșuat: {eroare}")
                break


def principal():
    """Punctul de intrare în script."""
    automatizare = AutomatizareBrowserStream()
    automatizare.ruleaza()


if __name__ == "__main__":
    principal()
