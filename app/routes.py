from pickle import FALSE

from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import Order
from .email_utils import send_admin_email, send_pin_email, send_order_email
from .automation import bot_automation
from . import db
from seleniumwire import webdriver
# from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import random
import atexit
from flask import copy_current_request_context
import threading
from time import sleep
from sqlalchemy.orm import scoped_session, sessionmaker

main_bp = Blueprint('main', __name__)

def browser_init():
    try:
        proxy_username = "9fa3c330655cbd7ee012"
        proxy_password = "3607b7d7a975d149"
        proxy_address = "gw.dataimpulse.com"
        proxy_port = "16000"

        # formulate the proxy url with authentication for dataimpulse
        proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_address}:{proxy_port}"

        # Set proxy options for SeleniumWire
        proxy_options = {
            "proxy": {
                "http": proxy_url,
                "https": proxy_url
            }
        }
        # Set Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        
        # local environment
        # g_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options,seleniumwire_options=proxy_options)

        # Heroku environment
        chromedriver_path = "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"
        g_driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options,seleniumwire_options=proxy_options)
        

        g_driver.get('https://accounts.nintendo.com')

        print('Chrome started successfully!')

        return g_driver
    except Exception as error:
        print(f"Error during WebDriver or automation process - {error}")
        return None
        




@main_bp.route('/admin')
def index():
    return render_template('index.html')

@main_bp.route('/save', methods=['POST'])
def save():
    order_id = request.form['order_id']
    password = request.form['password']
    big_link = request.form['big_link']
    email = request.form.get('email', '')

    updated_rows = Order.query.filter_by(order_id=order_id).update({
        'password': password,
        'big_link': big_link,
        'email': email,
        'role': 'admin'
    })

    if updated_rows:
        # Commit the update to the database
        db.session.commit()
        # flash(f"Order ID {order_id} exists. Data has been updated.", 'info')
    else:
        # Create a new order if no existing order was found
        new_order = Order(order_id=order_id, password=password, big_link=big_link, email=email, role='admin',
                          pin_code='')
        db.session.add(new_order)
        db.session.commit()
        # flash('Order saved successfully!', 'success')

    # Add the new order to the session and commit to the database

    return render_template('index.html', order_id=order_id, password=password, big_link=big_link, email=email, show_email_popup=FALSE)



@main_bp.route('/view_db')
def view_db():
    orders = Order.query.all()
    return render_template('view_db.html', orders=orders)

@main_bp.route('/', methods=['GET', 'POST'])
@main_bp.route('/customer', methods=['GET', 'POST'])
def customer():
    try:
        if request.method == 'POST':
            order_id = request.form['order_id']
            access_code = request.form.get('access_code')
            email = request.form['email']

            # Ensure that access_code is provided
            if not access_code:
                flash("Access code is required!", "error")
                return redirect(url_for('main.customer'))

            # Check if order_id exists
            existing_order = Order.query.filter_by(order_id=order_id).first()
            if not existing_order:
                flash("Order ID not found. Please check your details and try again.", "error")
                return redirect(url_for('main.customer'))

            # Update access_code and email
            existing_order.access_code = access_code
            existing_order.email = email
            db.session.commit()

            # If already logged in, show credentials
            if existing_order.pin_code:
                flash(f"Already Login! Your 5-digit pin code is: {existing_order.pin_code} and password is: {existing_order.password}", "success")
                return redirect(url_for('main.customer'))

            # Thread for the automation process
            @copy_current_request_context
            def run_automation():
                try:
                    webdriver = browser_init()
                    four_digit_code, password = bot_automation(order_id, webdriver)

                    print(f"Received pin_code: {four_digit_code} and password: {password}")
                    if four_digit_code:                      
                        try:
                            # generate a new database session for this thread
                            Session = sessionmaker(bind=db.engine)
                            session = Session()
                            order = session.query(Order).filter_by(order_id=order_id).first()
                            order.pin_code = four_digit_code
                            order.password = password
                            session.commit()
                            print("Order updated successfully!")
                        except Exception as e:
                            print(f"Error updating order: {e}")
                        finally:
                            session.close()



                except Exception as e:
                    print(f"Automation failed: {e}")

            # Start threads
            threading.Thread(target=run_automation).start()
            
            # sleep for 10 seconds
            sleep(10)
            flash("Process has started. You can resubmit the form to get pin code.", "notification")

            return redirect(url_for('main.customer'))

        return render_template('customer.html')

    except Exception as e:
        print(f"Error in processing: {e}")
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for('main.customer'))


@main_bp.route('/print_orders')
def print_orders():
    all_orders = Order.query.all()

    # Format the result as a string
    orders_data = ""
    for order in all_orders:
        orders_data += f"ID: {order.id}, Order ID: {order.order_id}, Password: {order.password}, "
        orders_data += f"Big Link: {order.big_link}, Email: {order.email},  Access Code: {order.access_code}\n"

    return f"<pre>{orders_data}</pre>"
