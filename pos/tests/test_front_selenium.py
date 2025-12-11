"""
E2E front sin npm: usa Selenium con Chrome headless.
Requiere instalar: pip install selenium webdriver-manager
Si no están disponibles, se salta el test.
"""
import json
import unittest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except Exception:  # noqa: BLE001
    SELENIUM_AVAILABLE = False


class FrontSeleniumTestCase(StaticLiveServerTestCase):
    host = "127.0.0.1"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not SELENIUM_AVAILABLE:
            raise unittest.SkipTest("Selenium/webdriver-manager no instalados")
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1280,720")
            cls.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            cls.driver.set_page_load_timeout(15)
            cls.wait = WebDriverWait(cls.driver, 15)
        except Exception as e:  # noqa: BLE001
            raise unittest.SkipTest(f"No se pudo iniciar Chrome headless: {e}")

    @classmethod
    def tearDownClass(cls):
        if SELENIUM_AVAILABLE:
            try:
                cls.driver.quit()
            except Exception:
                pass
        super().tearDownClass()

    def test_login_apertura_y_venta(self):
        """Flujo básico: login, abrir caja (si procede), vender y ver ticket."""
        import os
        base = self.live_server_url
        USER = os.getenv("SELENIUM_USER", "admin")
        PIN = os.getenv("SELENIUM_PIN", "1234")

        d = self.driver
        d.get(base + "/")

        # Login
        d.find_element(By.NAME, "username").send_keys(USER)
        d.find_element(By.NAME, "pin").send_keys(PIN)
        d.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Si aparece modal de abrir caja
        try:
            monto_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="monto_inicial"]'))
            )
            monto_input.clear()
            monto_input.send_keys("100000")
            abrir_btn = d.find_element(By.XPATH, "//button[contains(., 'Abrir caja') or contains(., 'abrir caja')]")
            abrir_btn.click()
        except Exception:
            # No apareció modal de apertura
            pass

        # Ir a vender
        d.get(base + "/vender/")
        # Seleccionar primer producto visible
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card")))
        d.find_elements(By.CSS_SELECTOR, ".product-card")[0].click()

        # Procesar venta
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Procesar') or contains(., 'procesar')]"))).click()
        try:
            d.find_element(By.NAME, "monto_recibido").send_keys("200000")
        except Exception:
            pass
        # Botón confirmar
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirmar') or contains(., 'confirmar')]"))).click()

        # Confirmación de venta
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Venta #') or contains(text(), 'venta #')]")))

        # Intentar ver ticket
        try:
            d.find_element(By.XPATH, "//a[contains(., 'Ticket') or contains(., 'ticket')]").click()
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Total') or contains(text(), 'total')]")))
        except Exception:
            # Si no hay link de ticket, al menos ya confirmó la venta
            pass

