from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize WebDriver
g_driver = webdriver.Chrome()

def enter_password(driver, password):
    """Enter password and proceed if the password field is visible."""
    try:
        # Wait until the password field is visible
        password_field = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "reauthenticate-form_pc_input_0"))
        )
        print("Password field found!")
        driver.execute_script("arguments[0].scrollIntoView();", password_field)
        password_field.send_keys(password)
        print("Password entered successfully!")

        # Click OK button to proceed
        ok_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "reauthenticate-form_pc_button_0"))
        )
        ok_button.click()
        print("Continue button clicked!")
    except Exception as e:
        print(f"Error entering password: {e}")

def reload_page_invalid_error(driver):
    """Case 1: Reload unlink page if invalid error occurs."""
    try:
        # Check for the error message by its class name
        error_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "my-0 ErrorScreen_error-screen-message_teJOl"))
        )
        # If the error is found, reload the page
        print("Session invalid error found. Reloading the page...")
        driver.get("https://ec.nintendo.com/my/devices/unlink")
        return True  # Indicate that a reload occurred
    except Exception:
        print("No session invalid error found. Proceeding to next case.")
        return False

def deregister_account_disabled_button_case(driver):
    """Case 2: Stop automation if Deregister button is disabled."""
    try:
        # Wait for Deregister button to appear
        deregister_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "group"))
        )

        # Check if Deregister button is disabled
        if not deregister_button.is_enabled():
            print("Deregister button is disabled. Automation stopped.")
            return True  # Indicate that automation should stop
    except Exception as e:
        print(f"Error in disabled button case: {e}")
    return False  # Indicate that automation should continue

def deregister_account_enabled_button_case(driver):
    """Case 3: Handle deregistration process if Deregister button is enabled."""
    try:
        # Wait for Deregister button to appear and click if enabled
        deregister_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "group"))
        )
        if deregister_button.is_enabled():
            deregister_button.click()
            print("Deregister button clicked!")

            # Confirm de-registration
            confirm_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.bg-nintendo-red"))
            )
            confirm_button.click()
            print("Confirm button clicked")

            # Final de-registration confirmation
            final_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.bg-nintendo-red"))
            )
            final_button.click()
            print("Account has been de-registered")
            return True
    except Exception as e:
        print(f"Error in enabled button case: {e}")
    return False

try:
    # Open the page
    g_driver.get("https://ec.nintendo.com/my/devices/unlink")

    # Step 1: Enter password to proceed if the page asks for it
    enter_password(g_driver, "kd256958")

    # Step 2: Sequentially handle cases based on the new requirements
    # Check for the 'session invalid' error and reload the page if found
    if reload_page_invalid_error(g_driver):
        enter_password(g_driver, "kd256958")
        if reload_page_invalid_error(g_driver):
            print("Error persists after reloading. Stopping automation.")
        elif deregister_account_disabled_button_case(g_driver):
            print("Automation stopped due to disabled button.")
        else:
            deregister_account_enabled_button_case(g_driver)
    # Check if Deregister button is disabled and stop if so
    elif deregister_account_disabled_button_case(g_driver):
        print("Automation stopped due to disabled button.")
    # Proceed with deregistration if the button is enabled
    else:
        deregister_account_enabled_button_case(g_driver)

except Exception as error:
    print(f"Unexpected error encountered: {error}")

finally:
    # Close the browser
    g_driver.quit()
