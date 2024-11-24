import json
import time
from seleniumwire import webdriver
# from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from .models import Order
from .email_utils import send_pin_email
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import random

# separte method for browser initialization and return the driver object


def bot_automation(order_id,driver):
   
    four_digit_code = None  # Initialize four_digit_code
    password = None

    try:
        print("Running bot automation...")

        # Retrieve order details from the database
        order = Order.query.filter_by(order_id=order_id).first()

        if not order or not order.big_link or not order.password:
            print("Order not found or missing big_link/password")
            return

        big_link = order.big_link
        password = order.password
        
            

        # Retrieve access code from the customer record
        access_order = Order.query.filter_by(order_id=order_id).first()
        if not access_order or not access_order.access_code:
            print("Customer order not found or missing access_code")
            return

        access_code = access_order.access_code
        email = access_order.email if access_order else None

        if not email:
            print("Customer email not found")
            return

        print(f"Order ID: {order_id}")
        print(f"Customer Email: {email}")

       
        try:
            cookies = json.loads(big_link)

            print("\nLoaded Cookies: ", cookies)
            

            for cookie in cookies:
                expiration = int(cookie['expirationDate'])
                cookie_dict = {
                    "domain": cookie['domain'],
                    "name": cookie['name'],
                    "value": cookie['value'],
                    "path": cookie['path'],
                    "secure": cookie['secure'],
                    "httpOnly": cookie['httpOnly'],
                    "expiry": expiration,
                }
                
            try:
                driver.add_cookie(cookie_dict)
                print("\nCookie added successfully.")
            except Exception as e:
                print(f"Failed to add cookie: {e}")

            # Refresh to apply cookies
            driver.refresh()


            ### At this point the user should be logged in automatically ###

                
            print(f"Navigating using access code: {access_code}")
            # Navigate to the target URL
            target_url = f"https://accounts.nintendo.com/login/device?access_key={access_code}"
            driver.get(target_url)
            print("Navigated successfully")
            time.sleep(1)

            # Check if the page says You need to sign in again. Please restart the process from the beginning.
            if "restart the process from the beginning" in driver.page_source:
                # throw an exception to exit the automation
                raise Exception("You need to sign in again. Please restart the process from the beginning.")

            # The access code may have expired. Please try again later.
            if "The access code may have expired. Please try again later." in driver.page_source:
                # throw an exception to exit the automation
                raise Exception("The access code may have expired. Please try again later.")
        
            
            if "expired" in driver.page_source:
                print("Access code has expired. Exiting automation...")
                return

            try:
                # Wait until the password field is present and visible
                password_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "reauthenticate-form_pc_input_0"))
                )
                print("First Password field found!")

                # if field with that id is not found then search for reauthenticate-form_pc_input_0
                if not password_field:
                    password_field = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "reauthenticate-form_pc_input_0"))
                    )
                    print("Second Password field found!")

                # Enter password
                password_field.send_keys(password)
                print("Password entered successfully!")
                
            except Exception as error:
                raise Exception(f"Failed to enter password: {error}")

            # Check for expired access code in page source
            if "expired" in driver.page_source:
                print("Access code has expired. Exiting automation...")
                return

            try:
                # Wait until the continue button is clickable and then click it
                continue_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "reauthenticate-form_pc_button_0"))
                )
                continue_button.click()
                print("Continue button clicked!")
                
            except Exception as error:
                raise Exception(f"Failed to click the continue button: {error}")

            # Check for the "Select this account" button and click it if found
            try:
                # throw an exception to exit the automation
                if "This page cannot be displayed" in driver.page_source:
                    raise Exception("Error after entering access code. This page cannot be displayed.")
                select_account_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "choose-connect-button"))
                )
                select_account_button.click()
                print("Select this account button clicked!")
                
            except Exception as error:
                raise Exception(f"Select this account button not found: {error}")

            # Wait for the 5-digit code to appear
            try:
                print("Waiting for the 5-digit code to appear...")
                code_element = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".DeviceLoginPincodeShow_pincode_data"))
                )
                time.sleep(2)
                four_digit_code = code_element.text
                print(f"5-digit code is: {four_digit_code}")

            except Exception as error:
                print("5-digit code not found.")

        except Exception as error:
            print(f"Error during WebDriver or automation process - {error}")

    finally:
        # clear cookies and navigate to accounts.nintendo.com/logout
        driver.delete_all_cookies()
        driver.quit()
        print("Cookies deleted and driver quit successfully!")
        # driver.get("https://accounts.nintendo.com")
        # driver.quit()
        return four_digit_code,password

