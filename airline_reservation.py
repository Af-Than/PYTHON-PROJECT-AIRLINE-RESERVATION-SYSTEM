"""
COORG AIRLINE RESERVATION SERVICES
----------------------------------
1. Run setup_database.py once (creates the tables and loads the sample flights).
2. Run this file.
Tip: type  back  at any question to cancel and return to the previous menu.
"""
import getpass
import math
import random
import re
import time
from collections import Counter
from datetime import date, datetime, timedelta

import mysql.connector as sql
from tabulate import tabulate

DB_CONFIG = {'host': 'localhost', 'user': 'root', 'passwd': '1234',
             'port': 3306, 'database': 'csproject'}
ADMIN_PASSWORD = '1234'

WIDTH = 100               # width of the lines/headers on screen
DEFAULT_CAPACITY = 180    # used if a flight has no capacity saved
MAX_PASSENGERS = 9        # per booking
EXTRA_BAG_RATE = 5        # $ per kg above the baggage limit
MAX_BAG_WEIGHT = 50       # kg, heaviest bag we accept
STATUSES = ['On Time', 'Delayed', 'Boarding', 'Cancelled']


class GoBack(Exception):
    """Raised when the user types 'back' to cancel the current action."""


# ---------------------------------------------------------------------------
# PRICING / CLASS SYSTEM
# ---------------------------------------------------------------------------
class Pricing:
    # class name: (price multiplier of the base fare, perks)
    CLASSES = {
        'Economy': (1.0, 'Standard seat'),
        'Premium Economy': (1.25, 'Extra legroom + priority check-in'),
        'Business': (1.5, 'Lounge access + priority boarding + premium meal'),
        'First': (2.0, 'Private suite + lounge + premium meal'),
    }

    @staticmethod
    def normalise(name):
        for class_name in Pricing.CLASSES:
            if class_name.lower() == str(name).strip().lower():
                return class_name
        return 'Economy'

    @staticmethod
    def price(base_fare, travel_class):
        multiplier = Pricing.CLASSES[Pricing.normalise(travel_class)][0]
        return round(base_fare * multiplier, 2)

    @staticmethod
    def choose_class(base_fare, current=None):

        names = [n for n in Pricing.CLASSES if n != current]
        rows = []
        for number, name in enumerate(names, 1):
            price = Pricing.price(base_fare, name)
            row = [number, name, f'${price:.2f}']
            if current:
                diff = price - Pricing.price(base_fare, current)
                row.append(f'+${diff:.2f}' if diff >= 0 else f'-${-diff:.2f}')
            row.append(Pricing.CLASSES[name][1])
            rows.append(row)
        headers = ['No', 'Class', 'Price'] + (['Difference'] if current else []) + ['Perks']
        print(tabulate(rows, headers=headers, tablefmt='fancy_grid'))
        return Validator.choice('Select class (number or name): ', names)


# ---------------------------------------------------------------------------
# SCREEN HELPERS
# ---------------------------------------------------------------------------
class Display:
    @staticmethod
    def line(char='-'):
        print(char * WIDTH)

    @staticmethod
    def header(title, char='='):
        print(char * WIDTH)
        print(f'# {title} #'.center(WIDTH))
        print(char * WIDTH)

    @staticmethod
    def slow(text, delay=0.03):
        for letter in text:
            time.sleep(delay)
            print(letter, end='', flush=True)

    @staticmethod
    def loading(message):
        print(message, end=' ', flush=True)
        Display.slow('.....', 0.12)
        print()

    @staticmethod
    def exit_menu():
        print('EXITING THE CURRENT MENU', end=' ', flush=True)
        Display.slow('.....', 0.12)
        print()

    @staticmethod
    def table(rows, headers, fmt='pretty', empty='No records found.'):
        if not rows:
            print(empty)
        else:
            print(tabulate(rows, headers=headers, tablefmt=fmt))

    @staticmethod
    def ticket(b):
        name = f"{b['first_name']} {b['last_name']}"
        print()
        print('*' * 95)
        print(b['airlinename'].upper().center(95))
        print('-' * 95)
        print(f"BOOKING NO: {b['booking_no']:<12} DATE: {b['dates']}     SCHEDULE: {b['flightschedule']}")
        print()
        print(f"NAME: {name:<24} FLIGHT NO: {b['flight_no']:<10} CLASS: {Pricing.normalise(b['travel_class']).upper()}")
        print()
        print(f"FROM: {b['departure'].upper():<24} TO: {b['arrival'].upper()}")
        print()
        print(f"SEAT: {b['seat_no']:<8} GATE: {b['gate_no']:<8} TERMINAL: {b['terminal']}")
        if b.get('checked_in'):
            print('\nSTATUS: CHECKED IN')
        print('*' * 95)
        print()


# ---------------------------------------------------------------------------
# INPUT VALIDATION  (every question in the program goes through here)
# ---------------------------------------------------------------------------
class Validator:
    @staticmethod
    def ask(prompt):
        """Ask until the user types something that is not blank. 'back' cancels."""
        while True:
            value = ' '.join(input(prompt).split())      # trims and removes double spaces
            if value.lower() == 'back':
                raise GoBack()
            if value:
                return value
            print('  ! This cannot be empty or only spaces. Please try again.')

    @staticmethod
    def secret(prompt, pattern=None, error='Invalid input.'):
        """Like ask() but hides what is typed (used for passwords and CVV)."""
        while True:
            value = getpass.getpass(prompt).strip()
            if value.lower() == 'back':
                raise GoBack()
            if value and (pattern is None or re.fullmatch(pattern, value)):
                return value
            print('  ! ' + (error if value else 'This cannot be empty.'))

    @staticmethod
    def text(prompt, pattern=None, error='Invalid input.'):
        while True:
            value = Validator.ask(prompt)
            if pattern is None or re.fullmatch(pattern, value):
                return value
            print('  ! ' + error)

    @staticmethod
    def name(prompt):
        value = Validator.text(prompt, r"[A-Za-z][A-Za-z .'-]{0,29}",
                               'Use letters only (maximum 30 characters).')
        return value.title()

    @staticmethod
    def place(prompt):
        value = Validator.text(prompt, r"[A-Za-z][A-Za-z .'-]{1,29}",
                               'Use letters only (2 to 30 characters).')
        return value.title()

    @staticmethod
    def email(prompt):
        value = Validator.text(prompt, r"[\w.+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+",
                               'Enter a valid email address, e.g. name@gmail.com')
        return value.lower()

    @staticmethod
    def phone(prompt):
        while True:
            value = re.sub(r'[\s-]', '', Validator.ask(prompt))
            if re.fullmatch(r'\+?\d{7,15}', value):
                return value
            print('  ! Enter a valid phone number (7 to 15 digits).')

    @staticmethod
    def flight_no(prompt):
        while True:
            value = Validator.ask(prompt).upper()
            if re.fullmatch(r'[A-Z0-9]{3,8}', value):
                return value
            print('  ! A flight number has 3 to 8 letters/digits, e.g. AF123.')

    @staticmethod
    def integer(prompt, low=0, high=10 ** 6):
        while True:
            value = Validator.ask(prompt)
            if not re.fullmatch(r'\d+', value):
                print('  ! Please enter a whole number.')
                continue
            number = int(value)
            if number < low or number > high:
                if high >= 10 ** 6:
                    print(f'  ! The number must be at least {low}.')
                else:
                    print(f'  ! Please enter a number between {low} and {high}.')
                continue
            return number

    @staticmethod
    def amount(prompt, low=1, high=100000):
        while True:
            value = Validator.ask(prompt)
            if re.fullmatch(r'\d+(\.\d{1,2})?', value) and low <= float(value) <= high:
                return float(value)
            print(f'  ! Enter an amount between {low} and {high} (up to 2 decimals).')

    @staticmethod
    def yes_no(prompt):
        while True:
            value = Validator.ask(prompt + ' (yes/no): ').lower()
            if value in ('y', 'yes'):
                return True
            if value in ('n', 'no'):
                return False
            print('  ! Please type yes or no.')

    @staticmethod
    def choice(prompt, options):
        """The user can type the list number or the option name."""
        while True:
            value = Validator.ask(prompt)
            if value.isdigit() and 1 <= int(value) <= len(options):
                return options[int(value) - 1]
            for option in options:
                if option.lower() == value.lower():
                    return option
            print('  ! Please pick a number from the list (or type the name exactly).')

    @staticmethod
    def to_date(value):
        """Convert whatever the database returns into a date object."""
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()

    @staticmethod
    def travel_date(prompt, max_days=365):
        today = date.today()
        example = today + timedelta(days=7)
        while True:
            value = Validator.ask(prompt)
            try:
                chosen = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                print(f'  ! Use the format YYYY-MM-DD, for example {example}.')
                continue
            if chosen < today:
                print('  ! That date has already passed.')
            elif chosen > today + timedelta(days=max_days):
                print(f'  ! Bookings open only up to {max_days} days in advance.')
            else:
                return chosen


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------
class Database:
    def __init__(self, **config):
        try:
            self.conn = sql.connect(**config)
        except sql.Error as err:
            print(f'\n  ! Could not connect to MySQL: {err}')
            print('  Make sure MySQL is running, the details in DB_CONFIG are right,')
            print('  and that you have run setup_database.py once.')
            raise SystemExit(1)

    def _cursor(self, as_dict=False):
        self.conn.ping(reconnect=True, attempts=2, delay=1)
        return self.conn.cursor(dictionary=as_dict, buffered=True)

    def fetch_all(self, query, params=(), as_dict=False):
        cursor = self._cursor(as_dict)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetch_one(self, query, params=(), as_dict=False):
        cursor = self._cursor(as_dict)
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def execute(self, query, params=(), commit=True):
        cursor = self._cursor()
        try:
            cursor.execute(query, params)
            count = cursor.rowcount
        finally:
            cursor.close()
        if commit:
            self.conn.commit()
        return count

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def ensure_schema(self):
        """Adds the 'checked_in' column (so nobody can check in twice) if it is missing."""
        if not self.fetch_one("SHOW COLUMNS FROM flightreports LIKE 'airlinename'"):
            if self.fetch_one("SHOW COLUMNS FROM flightreports LIKE 'Airline'"):
                self.execute('ALTER TABLE flightreports CHANGE COLUMN Airline airlinename VARCHAR(50)')
        if not self.fetch_one("SHOW COLUMNS FROM user_table LIKE 'checked_in'"):
            self.execute('ALTER TABLE user_table ADD COLUMN checked_in TINYINT(1) NOT NULL DEFAULT 0')


# ---------------------------------------------------------------------------
# PAYMENT
# ---------------------------------------------------------------------------
class Payment:
    BANKS = ['HDFC', 'ICICI', 'SBI', 'Canara Bank', 'Axis Bank']
    CARD_BRANDS = {'3': 'Amex', '4': 'Visa', '5': 'Mastercard', '6': 'RuPay'}

    def process(self, amount, purpose='Payment'):
        """Returns the transaction id if the payment succeeded, otherwise None."""
        print()
        Display.header('PAYMENT', '-')
        print(f'Amount to pay for {purpose}: ${amount:.2f}\n')
        while True:
            print('ENTER 1: DEBIT/CREDIT CARD')
            print('ENTER 2: UPI')
            print('ENTER 3: NET BANKING')
            print('ENTER 4: CANCEL PAYMENT')
            method = Validator.integer('Choose a payment method: ', 1, 4)
            if method == 4:
                print('Payment cancelled.')
                return None
            if method == 1:
                label = self.card()
            elif method == 2:
                label = self.upi()
            else:
                label = self.net_banking()
            if self.verify_otp():
                return self.finish(amount, label)
            if not Validator.yes_no('Payment failed. Try another method?'):
                print('Payment cancelled.')
                return None

    def card(self):
        print('\n--- CARD PAYMENT ---')
        Validator.name('Card holder name: ')
        while True:
            number = re.sub(r'[\s-]', '', Validator.ask('Card number (16 digits): '))
            if re.fullmatch(r'\d{16}', number):
                break
            print('  ! A card number must be exactly 16 digits.')
        while True:
            expiry = Validator.ask('Expiry date (MM/YY): ')
            if self.valid_expiry(expiry):
                break
            print('  ! Invalid or expired date. Use MM/YY, for example 08/29.')
        Validator.secret('CVV (3 digits): ', r'\d{3}', 'The CVV must be exactly 3 digits.')
        brand = self.CARD_BRANDS.get(number[0], 'Card')
        return f'{brand} card ending {number[-4:]}'

    @staticmethod
    def valid_expiry(text):
        match = re.fullmatch(r'(0[1-9]|1[0-2])/(\d{2})', text)
        if not match:
            return False
        today = date.today()
        return (2000 + int(match.group(2)), int(match.group(1))) >= (today.year, today.month)

    def upi(self):
        print('\n--- UPI PAYMENT ---')
        upi_id = Validator.text('Enter UPI ID (e.g. name@okbank): ', r'[\w.-]{2,}@[A-Za-z]{2,}',
                                'A UPI ID looks like name@bank.')
        return f'UPI ({upi_id})'

    def net_banking(self):
        print('\n--- NET BANKING ---')
        for number, bank in enumerate(self.BANKS, 1):
            print(f'  {number}: {bank}')
        bank = Validator.choice('Select bank (number or name): ', self.BANKS)
        Validator.text('Enter User ID: ', r'\S{4,30}', 'The User ID needs 4 to 30 characters, no spaces.')
        Validator.secret('Enter Password: ', r'\S{4,30}', 'The password needs 4 to 30 characters, no spaces.')
        return f'Net banking ({bank})'

    @staticmethod
    def verify_otp():
        otp = str(random.randint(100000, 999999))
        print(f'\nAn OTP has been sent to your registered mobile number.  (Demo OTP: {otp})')
        for left in (2, 1, 0):
            if Validator.ask('Enter the 6-digit OTP: ') == otp:
                return True
            print(f'  ! Wrong OTP. {left} attempt(s) left.')
        return False

    @staticmethod
    def finish(amount, label):
        Display.loading('Payment in process')
        transaction = 'TXN' + ''.join(random.choices('0123456789', k=8))
        print('PAYMENT CONFIRMED!')
        print('-' * 40)
        print(f'Transaction ID : {transaction}')
        print(f'Paid by        : {label}')
        print(f'Amount         : ${amount:.2f}')
        print(f'Time           : {datetime.now():%Y-%m-%d %H:%M}')
        print('-' * 40)
        return transaction


# ---------------------------------------------------------------------------
# FLIGHTS
# ---------------------------------------------------------------------------
class FlightManager:
    COLUMNS = ("f.airlinename, f.flightno, f.departure, f.destination, f.flightschedule, "
               "f.duration, f.baggage, f.fare, f.gate, COALESCE(r.status, 'On Time')")
    HEADERS = ['Airline', 'Flight No', 'Departure', 'Destination', 'Schedule',
               'Duration', 'Baggage', 'Fare ($)', 'Gate', 'Status']
    SOURCE = "FROM flights f LEFT JOIN flightreports r ON f.flightno = r.flightno"

    @staticmethod
    def duration_from_schedule(schedule):
        start_text, end_text = schedule.split('-')
        start = datetime.strptime(start_text, '%H:%M')
        end = datetime.strptime(end_text, '%H:%M')
        minutes = int((end - start).total_seconds() // 60) % (24 * 60)
        if minutes == 0:
            minutes = 24 * 60
        return f'{minutes / 60:g}h'

    def __init__(self, db):
        self.db = db

    def get(self, flightno):
        row = self.db.fetch_one(
            """SELECT f.airlinename, f.flightno, f.departure, f.destination, f.flightschedule,
                      f.duration, f.baggage, f.fare, f.gate,
                      COALESCE(r.status, 'On Time') AS status, r.model, r.capacity,
                      r.terminal, r.no_of_baggage
               FROM flights f LEFT JOIN flightreports r ON f.flightno = r.flightno
               WHERE f.flightno = %s""", (flightno,), as_dict=True)
        if row:
            row['fare'] = float(row['fare'])
        return row

    # ---- choosing a flight while booking: departure -> destination -> flight ----
    def choose_flight(self):
        departures = [r[0] for r in self.db.fetch_all(
            'SELECT DISTINCT departure FROM flights ORDER BY departure')]
        if not departures:
            print('NO FLIGHTS ARE AVAILABLE AT THE MOMENT')
            return None
        print('STEP 1: CHOOSE WHERE YOU ARE FLYING FROM')
        for number, city in enumerate(departures, 1):
            print(f'  {number}: {city}')
        departure = Validator.choice('Select departure (number or name): ', departures)

        rows = self.db.fetch_all(
            """SELECT destination, COUNT(*), MIN(fare) FROM flights
               WHERE departure = %s GROUP BY destination ORDER BY destination""", (departure,))
        destinations = [r[0] for r in rows]
        print(f'\nSTEP 2: CHOOSE YOUR DESTINATION (from {departure})')
        table = [[i, r[0], r[1], f'${float(r[2]):.2f}'] for i, r in enumerate(rows, 1)]
        print(tabulate(table, headers=['No', 'Destination', 'Flights', 'Fares from'], tablefmt='pretty'))
        destination = Validator.choice('Select destination (number or name): ', destinations)

        flights = self.db.fetch_all(
            f"SELECT {self.COLUMNS} {self.SOURCE} WHERE f.departure = %s AND f.destination = %s "
            "ORDER BY f.flightschedule", (departure, destination))
        print(f'\nSTEP 3: AVAILABLE FLIGHTS  {departure.upper()} -> {destination.upper()}')
        print(tabulate(flights, headers=self.HEADERS, tablefmt='pretty'))
        valid = {row[1] for row in flights}
        while True:
            number = Validator.ask('Enter the FLIGHT NUMBER you want: ').upper()
            if number in valid:
                return self.get(number)
            print('  ! That flight number is not in the list above.')

    # ---- searching ----
    def search(self):
        print('ENTER 1: SEARCH BY AIRLINE NAME')
        print('ENTER 2: SEARCH BY FLIGHT NUMBER')
        print('ENTER 3: SEARCH BY DESTINATION')
        option = Validator.integer('Enter your option: ', 1, 3)
        if option == 2:
            flight = self.get(Validator.flight_no('Enter flight number: '))
            if not flight:
                print('NO FLIGHT FOUND WITH THAT NUMBER')
                return
            row = [flight['airlinename'], flight['flightno'], flight['model'], flight['capacity'],
                   flight['departure'], flight['destination'], flight['flightschedule'],
                   flight['status'], flight['terminal'], flight['gate']]
            print('\nFlight details:')
            print(tabulate([row], headers=['Airline', 'Flight No', 'Model', 'Capacity', 'Departure',
                                           'Destination', 'Schedule', 'Status', 'Terminal', 'Gate'],
                           tablefmt='grid'))
            return
        term = Validator.ask('Enter airline name: ' if option == 1 else 'Enter destination: ')
        column = 'f.airlinename' if option == 1 else 'f.destination'
        rows = self.db.fetch_all(f"SELECT {self.COLUMNS} {self.SOURCE} WHERE {column} LIKE %s "
                                 "ORDER BY f.destination, f.flightschedule", (f'%{term}%',))
        print(f'\nRESULTS FOR "{term}"')
        Display.table(rows, self.HEADERS, empty='NO FLIGHTS MATCHED YOUR SEARCH')

    # ---- admin: add / edit / delete ----
    def add_flight(self):
        Display.header('ADD A FLIGHT', '-')
        print("(Type 'back' at any question to cancel)\n")
        airline = Validator.text('Airline name: ', r"[A-Za-z][A-Za-z0-9 .&'-]{1,39}",
                                 'Use 2 to 40 letters/numbers.')
        while True:
            flightno = Validator.flight_no('Flight number: ')
            if not self.get(flightno):
                break
            print('  ! A flight with this number already exists.')
        departure = Validator.place('Departure airport/city: ')
        while True:
            destination = Validator.place('Destination: ')
            if destination.lower() != departure.lower():
                break
            print('  ! Destination cannot be the same as the departure.')
        schedule = Validator.text('Flight schedule (e.g. 05:00-15:00): ',
                                  r'(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d',
                                  'Use the 24-hour format HH:MM-HH:MM, e.g. 05:00-15:00.')
        duration = self.duration_from_schedule(schedule)
        print(f'Calculated duration: {duration}')
        while True:
            baggage = Validator.text('Baggage allowance per bag (e.g. 20-30kg): ', r'\d{1,2}-\d{1,2}kg',
                                     'Use the format 20-30kg.')
            low, high = (int(n) for n in re.findall(r'\d+', baggage))
            if low < high:
                break
            print('  ! The second number must be larger than the first.')
        fare = Validator.amount('Base (Economy) fare in $: ', 1, 100000)
        gate = Validator.text('Gate (e.g. B4): ', r'[A-Za-z0-9]{1,4}', 'Use up to 4 letters/digits.').upper()
        print('Status options:', ', '.join(f'{i}: {s}' for i, s in enumerate(STATUSES, 1)))
        status = Validator.choice('Status (number or name): ', STATUSES)
        model = Validator.text('Aircraft model (e.g. Boeing 737-800): ', r"[A-Za-z0-9 .-]{2,40}",
                               'Use 2 to 40 letters/numbers.')
        capacity = Validator.integer('Seat capacity: ', 1, 900)
        terminal = Validator.integer('Terminal number: ', 1, 9)
        bags = Validator.integer('Check-in bags allowed per person: ', 1, 5)

        print()
        print(tabulate([[airline, flightno, departure, destination, schedule, duration, baggage,
                         fare, gate, status]], headers=self.HEADERS[:9] + ['Status'], tablefmt='pretty'))
        if not Validator.yes_no('Add this flight?'):
            print('FLIGHT NOT ADDED')
            return
        self.db.execute(
            "INSERT INTO flights (airlinename, flightno, departure, destination, flightschedule, "
            "duration, baggage, fare, gate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (airline, flightno, departure, destination, schedule, duration, baggage, fare, gate),
            commit=False)
        self.db.execute(
            "INSERT INTO flightreports (airlinename, flightno, departure, destination, status, model, "
            "capacity, terminal, no_of_baggage) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (airline, flightno, departure, destination, status, model, capacity, terminal, bags),
            commit=False)
        self.db.commit()
        print('*' * 50)
        print('FLIGHT ADDED SUCCESSFULLY')
        print('*' * 50)

    def ask_existing_flight(self):
        flight = self.get(Validator.flight_no('Enter flight number: '))
        if not flight:
            print('NO RECORD FOUND FOR THE PROVIDED FLIGHT NUMBER')
        return flight

    def edit_flight(self):
        Display.header('MODIFY A FLIGHT', '-')
        flight = self.ask_existing_flight()
        if not flight:
            return
        print(f"\n{flight['airlinename']} {flight['flightno']}: {flight['departure']} -> "
              f"{flight['destination']} | Fare ${flight['fare']:.2f} | Gate {flight['gate']} | "
              f"Status {flight['status']}\n")
        print('ENTER 1: CHANGE THE STATUS')
        print('ENTER 2: CHANGE THE FARE')
        print('ENTER 3: CHANGE THE GATE')
        print('ENTER 4: GO BACK')
        option = Validator.integer('Enter your option: ', 1, 4)
        if option == 1:
            print('Status options:', ', '.join(f'{i}: {s}' for i, s in enumerate(STATUSES, 1)))
            status = Validator.choice('New status (number or name): ', STATUSES)
            self.db.execute('UPDATE flightreports SET status = %s WHERE flightno = %s',
                            (status, flight['flightno']))
        elif option == 2:
            fare = Validator.amount('New fare in $: ', 1, 100000)
            self.db.execute('UPDATE flights SET fare = %s WHERE flightno = %s', (fare, flight['flightno']))
        elif option == 3:
            gate = Validator.text('New gate (e.g. B4): ', r'[A-Za-z0-9]{1,4}',
                                  'Use up to 4 letters/digits.').upper()
            self.db.execute('UPDATE flights SET gate = %s WHERE flightno = %s', (gate, flight['flightno']))
        else:
            return
        print('INFORMATION UPDATED SUCCESSFULLY')

    def delete_flight(self):
        Display.header('DELETE A FLIGHT', '-')
        flight = self.ask_existing_flight()
        if not flight:
            return
        booked = self.db.fetch_one('SELECT COUNT(*) FROM user_table WHERE flight_no = %s',
                                   (flight['flightno'],))[0]
        if booked:
            print(f'THIS FLIGHT HAS {booked} BOOKING(S), SO IT CANNOT BE DELETED.')
            print('Tip: set its status to "Cancelled" instead (Modify a flight > Change the status).')
            return
        if not Validator.yes_no(f"Delete flight {flight['flightno']} ({flight['departure']} -> "
                                f"{flight['destination']})?"):
            print('DELETE CANCELLED')
            return
        self.db.execute('DELETE FROM flights WHERE flightno = %s', (flight['flightno'],), commit=False)
        self.db.execute('DELETE FROM flightreports WHERE flightno = %s', (flight['flightno'],), commit=False)
        self.db.commit()
        print('FLIGHT DELETED SUCCESSFULLY')


# ---------------------------------------------------------------------------
# PASSENGER
# ---------------------------------------------------------------------------
class Passenger:
    def __init__(self, first_name, last_name, email, phone, travel_class):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.travel_class = travel_class

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @staticmethod
    def ask(number, total, base_fare, first=None):
        print()
        Display.line()
        print(f'PASSENGER {number} OF {total}')
        first_name = Validator.name('First name: ')
        last_name = Validator.name('Last name: ')
        if first and Validator.yes_no(f'Use the same email and phone as {first.full_name}?'):
            email, phone = first.email, first.phone
        else:
            email = Validator.email('Email address: ')
            phone = Validator.phone('Phone number: ')
        print('\nCHOOSE A TRAVEL CLASS:')
        travel_class = Pricing.choose_class(base_fare)
        return Passenger(first_name, last_name, email, phone, travel_class)


# ---------------------------------------------------------------------------
# BOOKINGS
# ---------------------------------------------------------------------------
class BookingManager:
    SELECT = """SELECT u.booking_no, u.first_name, u.last_name, u.email, u.phone_no, u.departure,
                       u.arrival, u.`class` AS travel_class, u.seat_no, u.gate_no, u.terminal,
                       u.flight_no, u.dates, u.fare, u.checked_in,
                       f.airlinename, f.flightschedule, f.fare AS base_fare, f.baggage
                FROM user_table u JOIN flights f ON u.flight_no = f.flightno
                WHERE """

    def __init__(self, db, flights, payment):
        self.db = db
        self.flights = flights
        self.payment = payment

    # ---- helpers ----
    def seats_taken(self, flightno, travel_date):
        rows = self.db.fetch_all('SELECT seat_no FROM user_table WHERE flight_no = %s AND dates = %s',
                                 (flightno, travel_date))
        return {r[0] for r in rows}

    def capacity_of(self, flight):
        return flight['capacity'] or DEFAULT_CAPACITY

    def seats_left(self, flight, travel_date):
        return self.capacity_of(flight) - len(self.seats_taken(flight['flightno'], travel_date))

    def free_seat(self, flight, travel_date, also_taken=()):
        taken = self.seats_taken(flight['flightno'], travel_date) | set(also_taken)
        rows = math.ceil(self.capacity_of(flight) / 6)
        free = [f'{n}{letter}' for n in range(1, rows + 1) for letter in 'ABCDEF'
                if f'{n}{letter}' not in taken]
        return random.choice(free) if free else None

    def new_booking_no(self, used):
        while True:
            number = ''.join(random.choices('ABCDEF', k=3)) + ''.join(random.choices('123456789', k=3))
            if number not in used and not self.db.fetch_one(
                    'SELECT 1 FROM user_table WHERE booking_no = %s', (number,)):
                return number

    @staticmethod
    def is_past(booking):
        return Validator.to_date(booking['dates']) < date.today()

    def show_details(self, b):
        row = [b['booking_no'], f"{b['first_name']} {b['last_name']}", b['email'], b['phone_no'],
               b['departure'], b['arrival'], Pricing.normalise(b['travel_class']), b['dates'],
               b['flight_no'], b['airlinename'], f"${float(b['fare']):.2f}"]
        print('\nYOUR CURRENT DETAILS ARE:')
        print(tabulate([row], headers=['Booking No', 'Name', 'Email', 'Phone', 'Departure', 'Destination',
                                       'Class', 'Date', 'Flight No', 'Airline', 'Amount Paid'],
                       tablefmt='pretty'))

    def pick_booking(self, allow_name=True):
        """Find a booking by booking number (or last name). Returns a dict or None."""
        if allow_name:
            print('ENTER 1: USE YOUR BOOKING NUMBER')
            print('ENTER 2: USE YOUR LAST NAME')
            mode = Validator.integer('Enter your option: ', 1, 2)
        else:
            mode = 1
        if mode == 1:
            number = Validator.ask('Enter your booking number: ').upper()
            rows = self.db.fetch_all(self.SELECT + 'u.booking_no = %s', (number,), as_dict=True)
        else:
            last_name = Validator.name('Enter the passenger last name: ')
            rows = self.db.fetch_all(self.SELECT + 'u.last_name = %s ORDER BY u.dates',
                                     (last_name,), as_dict=True)
        if not rows:
            print('NO BOOKING WAS FOUND FOR THE DETAILS PROVIDED.')
            return None
        if len(rows) == 1:
            return rows[0]
        table = [[i, r['booking_no'], f"{r['first_name']} {r['last_name']}", r['flight_no'],
                  f"{r['departure']} -> {r['arrival']}", r['dates'], Pricing.normalise(r['travel_class'])]
                 for i, r in enumerate(rows, 1)]
        print('\nMULTIPLE BOOKINGS FOUND:')
        print(tabulate(table, headers=['No', 'Booking No', 'Name', 'Flight', 'Route', 'Date', 'Class'],
                       tablefmt='fancy_grid'))
        return rows[Validator.integer(f'Select a booking (1-{len(rows)}): ', 1, len(rows)) - 1]

    # ---- booking a flight ----
    def book(self):
        Display.header('BOOKING', '-')
        print("(Type 'back' at any question to cancel)\n")
        flight = self.flights.choose_flight()
        if not flight:
            return
        if flight['status'].lower() == 'cancelled':
            print('SORRY, THIS FLIGHT HAS BEEN CANCELLED. PLEASE CHOOSE ANOTHER FLIGHT.')
            return
        print()
        travel_date = Validator.travel_date('Enter date of travel (YYYY-MM-DD): ')
        left = self.seats_left(flight, travel_date)
        if left <= 0:
            print('SORRY, THIS FLIGHT IS FULL ON THAT DATE.')
            return
        most = min(MAX_PASSENGERS, left)
        count = Validator.integer(f'Number of passengers (1-{most}): ', 1, most)

        passengers = []
        for number in range(1, count + 1):
            passengers.append(Passenger.ask(number, count, flight['fare'],
                                            passengers[0] if passengers else None))
        total = self.print_bill(flight, passengers, travel_date)
        if not Validator.yes_no('Proceed to payment?'):
            print('TRANSACTION CANCELLED')
            Display.exit_menu()
            return
        transaction = self.payment.process(total, 'your flight booking')
        if not transaction:
            print('BOOKING NOT COMPLETED - YOU HAVE NOT BEEN CHARGED.')
            return
        self.save_bookings(flight, passengers, travel_date, transaction)

    def print_bill(self, flight, passengers, travel_date):
        print()
        Display.header('BILL', '-')
        print(f"{flight['airlinename']} {flight['flightno']}: {flight['departure']} -> "
              f"{flight['destination']} on {travel_date}")
        rows, total = [], 0
        for number, p in enumerate(passengers, 1):
            price = Pricing.price(flight['fare'], p.travel_class)
            total += price
            rows.append([number, p.full_name, p.travel_class, f'${price:.2f}'])
        rows.append(['', '', 'TOTAL', f'${total:.2f}'])
        print(tabulate(rows, headers=['No', 'Passenger', 'Class', 'Price'], tablefmt='fancy_grid'))
        return round(total, 2)

    def save_bookings(self, flight, passengers, travel_date, transaction):
        used, seats, saved = set(), set(), []
        try:
            for p in passengers:
                booking_no = self.new_booking_no(used)
                used.add(booking_no)
                seat = self.free_seat(flight, travel_date, seats)
                if seat is None:
                    raise RuntimeError('the flight became full')
                seats.add(seat)
                price = Pricing.price(flight['fare'], p.travel_class)
                self.db.execute(
                    "INSERT INTO user_table (booking_no, first_name, last_name, email, phone_no, "
                    "departure, arrival, `class`, seat_no, gate_no, terminal, flight_no, dates, fare) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (booking_no, p.first_name, p.last_name, p.email, p.phone, flight['departure'],
                     flight['destination'], p.travel_class, seat, flight['gate'],
                     flight['terminal'] or 1, flight['flightno'], travel_date, price),
                    commit=False)
                saved.append([booking_no, p.full_name, p.travel_class, seat])
            self.db.commit()
        except (sql.Error, RuntimeError) as err:
            self.db.rollback()
            print(f'\n  ! Booking could not be saved ({err}).')
            print(f'  Your payment {transaction} will be refunded.')
            return
        print('\nBOOKING SUCCESSFUL!')
        print(tabulate(saved, headers=['Booking No', 'Passenger', 'Class', 'Seat'], tablefmt='fancy_grid'))
        print('Please note down your booking numbers - you need them to view, modify or cancel.')
        print(f'Contact email on record: {passengers[0].email}')
        print('Use "VIEW TICKET" from the menu to see your ticket.')

    # ---- view / modify / cancel ----
    def view_ticket(self):
        Display.header('VIEW YOUR TICKET', '-')
        booking = self.pick_booking()
        if booking:
            Display.ticket(booking)

    def modify(self):
        Display.header('MODIFY BOOKING', '-')
        booking = self.pick_booking()
        if not booking:
            return
        if self.is_past(booking):
            print('THIS FLIGHT HAS ALREADY DEPARTED, SO THE BOOKING CANNOT BE CHANGED.')
            return
        self.show_details(booking)
        print('\nENTER 1: CHANGE THE DATE OF TRAVEL')
        print('ENTER 2: UPGRADE / CHANGE THE CLASS')
        print('ENTER 3: UPDATE EMAIL AND PHONE')
        print('ENTER 4: GO BACK')
        option = Validator.integer('What would you like to do? ', 1, 4)
        if option == 1:
            self.change_date(booking)
        elif option == 2:
            self.change_class(booking)
        elif option == 3:
            self.change_contact(booking)

    def change_date(self, b):
        if b['checked_in']:
            print('YOU HAVE ALREADY CHECKED IN, SO THE DATE CANNOT BE CHANGED.')
            return
        old_date = Validator.to_date(b['dates'])
        new_date = Validator.travel_date('Enter the NEW date of travel (YYYY-MM-DD): ')
        if new_date == old_date:
            print('That is already your travel date. No changes made.')
            return
        flight = self.flights.get(b['flight_no'])
        if self.seats_left(flight, new_date) <= 0:
            print('SORRY, THE FLIGHT IS FULL ON THAT DATE.')
            return
        seat = b['seat_no']
        if seat in self.seats_taken(flight['flightno'], new_date):
            seat = self.free_seat(flight, new_date)
        if not Validator.yes_no(f'Change the date from {old_date} to {new_date}?'):
            print('No changes made.')
            return
        self.db.execute('UPDATE user_table SET dates = %s, seat_no = %s WHERE booking_no = %s',
                        (new_date, seat, b['booking_no']))
        print('Date updated successfully!')
        if seat != b['seat_no']:
            print(f"Your old seat was taken on the new date. Your new seat is {seat}.")

    def change_class(self, b):
        current = Pricing.normalise(b['travel_class'])
        base = float(b['base_fare'])
        print(f'\nYour current class: {current}\n')
        new_class = Pricing.choose_class(base, current=current)
        diff = round(Pricing.price(base, new_class) - Pricing.price(base, current), 2)
        if diff > 0:
            print(f'\nUPGRADE TO {new_class.upper()}: you pay the difference of ${diff:.2f}.')
            if not Validator.yes_no('Continue to payment?'):
                print('No changes made.')
                return
            if not self.payment.process(diff, 'your class upgrade'):
                print('UPGRADE NOT COMPLETED - YOU HAVE NOT BEEN CHARGED.')
                return
        else:
            print(f'\nCHANGE TO {new_class.upper()}: you get a refund of ${-diff:.2f}.')
            if not Validator.yes_no('Confirm the change?'):
                print('No changes made.')
                return
        new_fare = round(float(b['fare']) + diff, 2)
        self.db.execute('UPDATE user_table SET `class` = %s, fare = %s WHERE booking_no = %s',
                        (new_class, new_fare, b['booking_no']))
        print(f'Class changed to {new_class}. Total paid for this booking is now ${new_fare:.2f}.')

    def change_contact(self, b):
        email = Validator.email('New email address: ')
        phone = Validator.phone('New phone number: ')
        self.db.execute('UPDATE user_table SET email = %s, phone_no = %s WHERE booking_no = %s',
                        (email, phone, b['booking_no']))
        print('Contact details updated successfully!')

    def cancel(self):
        Display.header('CANCEL TICKET', '-')
        booking = self.pick_booking(allow_name=False)
        if not booking:
            return
        if self.is_past(booking):
            print('THIS FLIGHT HAS ALREADY DEPARTED, SO IT CANNOT BE CANCELLED.')
            return
        refund = float(booking['fare'])
        print(f"\nBooking {booking['booking_no']}: {booking['first_name']} {booking['last_name']}, "
              f"{booking['departure']} -> {booking['arrival']} on {booking['dates']}")
        print(f'You will be refunded ${refund:.2f}.')
        if not Validator.yes_no('Confirm ticket cancellation?'):
            print('CANCELLATION ABORTED')
            return
        if not self.payment.verify_otp():
            print('REFUND CANCELLED - OTP VERIFICATION FAILED.')
            return
        self.db.execute('DELETE FROM user_table WHERE booking_no = %s', (booking['booking_no'],))
        Display.loading('Processing refund')
        print('TICKET CANCELLED')
        print(f'AMOUNT REFUNDED: ${refund:.2f}')

    # ---- search passengers ----
    def search_passenger(self):
        print('ENTER 1: SEARCH BY THE PASSENGER\'S LAST NAME')
        print('ENTER 2: SEARCH BY THE BOOKING NUMBER')
        option = Validator.integer('Enter your option: ', 1, 2)
        if option == 1:
            term = Validator.name('Enter the last name: ')
            where, params = 'last_name = %s', (term,)
        else:
            term = Validator.ask('Enter the booking number: ').upper()
            where, params = 'booking_no = %s', (term,)
        rows = self.db.fetch_all(
            "SELECT booking_no, first_name, last_name, email, phone_no, departure, arrival, `class`, "
            "seat_no, gate_no, terminal, flight_no, dates, fare FROM user_table WHERE " + where, params)
        print(f'\nBOOKINGS FOUND FOR "{term}"')
        Display.table(rows, ['Booking No', 'First Name', 'Last Name', 'Email', 'Phone No', 'Departure',
                             'Arrival', 'Class', 'Seat No', 'Gate No', 'Terminal', 'Flight No',
                             'Date of Travel', 'Money Spent'], empty='NO MATCHING PASSENGERS')


# ---------------------------------------------------------------------------
# OTHER SERVICES: ONLINE CHECK-IN AND FOOD
# ---------------------------------------------------------------------------
class Services:
    MENU = {1: ('Chicken Sandwich', 10), 2: ('Vegetable Sandwich', 8), 3: ('Water', 3),
            4: ('Soft Drink (Pepsi/Coca-Cola)', 5), 5: ('Fruit Platter', 15), 6: ('Caesar Salad', 15),
            7: ('Chicken Pasta', 20), 8: ('Veg Pasta', 15), 9: ('Chocolate Cake', 10), 10: ('Coffee', 5)}

    def __init__(self, db, bookings, flights, payment):
        self.db = db
        self.bookings = bookings
        self.flights = flights
        self.payment = payment

    @staticmethod
    def bag_limit(baggage_text):
        """'20-30kg' -> 30 (the heaviest weight allowed free per bag)."""
        numbers = re.findall(r'\d+', baggage_text or '')
        return int(max(numbers, key=int)) if numbers else 20

    def check_in(self):
        Display.header('ONLINE CHECK-IN', '-')
        booking = self.bookings.pick_booking(allow_name=False)
        if not booking:
            return
        if self.bookings.is_past(booking):
            print('THIS FLIGHT HAS ALREADY DEPARTED.')
            return
        if booking['checked_in']:
            print('YOU HAVE ALREADY CHECKED IN FOR THIS BOOKING.')
            Display.ticket(booking)
            return
        flight = self.flights.get(booking['flight_no'])
        allowed = flight['no_of_baggage'] or 2
        limit = self.bag_limit(booking['baggage'])
        print('\nBAGGAGE INFORMATION')
        print('-' * 40)
        print(f"{booking['airlinename']} allows {allowed} check-in bag(s) per person")
        print(f"Free weight limit per bag : {limit} kg")
        print(f'Extra cost per extra kg   : ${EXTRA_BAG_RATE}')
        print(f'Heaviest bag accepted     : {MAX_BAG_WEIGHT} kg')
        print('-' * 40)
        bags = Validator.integer(f'Number of bags to check in (0-{allowed}): ', 0, allowed)
        cost = 0
        for number in range(1, bags + 1):
            weight = Validator.integer(f'Weight of bag {number} in kg (1-{MAX_BAG_WEIGHT}): ', 1, MAX_BAG_WEIGHT)
            if weight > limit:
                extra = (weight - limit) * EXTRA_BAG_RATE
                print(f'  Bag {number} is {weight - limit} kg over the limit: ${extra}')
                cost += extra
        if cost:
            print(f'\nTOTAL EXTRA BAGGAGE COST: ${cost:.2f}')
            if not Validator.yes_no('Do you wish to pay and continue?'):
                print('PAYMENT CANCELLED - CHECK-IN NOT COMPLETED.')
                return
            if not self.payment.process(cost, 'excess baggage'):
                print('CHECK-IN NOT COMPLETED - YOU HAVE NOT BEEN CHARGED.')
                return
        self.db.execute('UPDATE user_table SET fare = fare + %s, checked_in = 1 WHERE booking_no = %s',
                        (cost, booking['booking_no']))
        Display.loading('Checking you in')
        print('CHECKED IN SUCCESSFULLY!')
        print(f"Seat {booking['seat_no']} | Gate {booking['gate_no']} | Terminal {booking['terminal']}")

    def food_order(self):
        Display.header('FOOD ORDER', '-')
        booking = self.bookings.pick_booking(allow_name=False)
        if not booking:
            print('Please book a ticket before ordering food.')
            return
        if self.bookings.is_past(booking):
            print('THIS FLIGHT HAS ALREADY DEPARTED.')
            return
        print('\n' + booking['airlinename'].upper().center(WIDTH // 2))
        table = [[n, name, f'${price}'] for n, (name, price) in self.MENU.items()]
        print(tabulate(table, headers=['No', 'Food/Drink', 'Price'], tablefmt='fancy_grid'))

        while True:
            raw = Validator.ask('\nEnter item numbers separated by commas '
                                '(e.g. 1,1,3 = two of item 1 and one of item 3): ')
            parts = [p.strip() for p in raw.split(',') if p.strip()]
            if parts and len(parts) <= 20 and all(p.isdigit() and int(p) in self.MENU for p in parts):
                break
            print(f'  ! Use only item numbers 1-{len(self.MENU)}, separated by commas (maximum 20 items).')
        counts = Counter(int(p) for p in parts)
        rows, total = [], 0
        for number in sorted(counts):
            name, price = self.MENU[number]
            rows.append([name, counts[number], f'${price}', f'${price * counts[number]}'])
            total += price * counts[number]
        rows.append(['TOTAL', '', '', f'${total}'])
        print('\n*BILL*')
        print(tabulate(rows, headers=['Item', 'Qty', 'Price', 'Subtotal'], tablefmt='fancy_grid'))
        if not Validator.yes_no('Confirm and pay for these items?'):
            print('FOOD ORDER CANCELLED')
            return
        if not self.payment.process(total, 'your food order'):
            print('FOOD ORDER NOT COMPLETED - YOU HAVE NOT BEEN CHARGED.')
            return
        self.db.execute('UPDATE user_table SET fare = fare + %s WHERE booking_no = %s',
                        (total, booking['booking_no']))
        print('Your food order has been placed successfully!')


# ---------------------------------------------------------------------------
# REPORTS (admin)
# ---------------------------------------------------------------------------
class Reports:
    def __init__(self, db):
        self.db = db

    def show(self):
        Display.header('REPORTS', '-')
        print('ENTER 1: FLIGHT REPORT')
        print('ENTER 2: PASSENGER REPORT')
        print('ENTER 3: GO BACK')
        option = Validator.integer('Enter your option: ', 1, 3)
        print()
        if option == 1:
            rows = self.db.fetch_all(
                """SELECT f.airlinename, f.flightno, f.departure, f.destination,
                          COALESCE(r.status, 'On Time'), r.model, f.flightschedule, f.duration, f.fare,
                          (SELECT COUNT(*) FROM user_table u WHERE u.flight_no = f.flightno)
                   FROM flights f LEFT JOIN flightreports r ON f.flightno = r.flightno
                   ORDER BY f.departure, f.destination""")
            print('FLIGHT REPORTS')
            Display.table(rows, ['Airline', 'Flight No', 'Departure', 'Destination', 'Status', 'Model',
                                 'Schedule', 'Duration', 'Fare (In $)', 'Bookings'], fmt='grid')
        elif option == 2:
            rows = self.db.fetch_all(
                """SELECT u.booking_no, u.first_name, u.last_name, u.email, u.phone_no, u.flight_no,
                          f.airlinename, u.departure, u.arrival, u.`class`, u.dates, u.fare
                   FROM user_table u JOIN flights f ON u.flight_no = f.flightno
                   ORDER BY u.dates, u.booking_no""")
            print('PASSENGER REPORTS')
            Display.table(rows, ['Booking No', 'First Name', 'Last Name', 'Email', 'Phone No', 'Flight No',
                                 'Airline', 'Departure', 'Destination', 'Class', 'Date', 'Booking Amount'])
            count, revenue = self.db.fetch_one('SELECT COUNT(*), COALESCE(SUM(fare), 0) FROM user_table')
            print(f'\nTotal bookings: {count}   |   Total revenue: ${float(revenue):.2f}')
        print()


# ---------------------------------------------------------------------------
# THE PROGRAM (menus)
# ---------------------------------------------------------------------------
class App:
    def __init__(self):
        self.db = Database(**DB_CONFIG)
        try:
            self.db.ensure_schema()
        except sql.Error as err:
            print(f'\n  ! The tables are not ready ({err}). Please run setup_database.py first.')
            raise SystemExit(1)
        self.flights = FlightManager(self.db)
        self.payment = Payment()
        self.bookings = BookingManager(self.db, self.flights, self.payment)
        self.services = Services(self.db, self.bookings, self.flights, self.payment)
        self.reports = Reports(self.db)

    def run_safely(self, action):
        """Runs a menu action; 'back' or a database problem returns to the menu instead of crashing."""
        try:
            action()
        except GoBack:
            print('\nCancelled.')
            Display.exit_menu()
        except sql.Error as err:
            self.db.rollback()
            print(f'\n  ! Database problem: {err}\n  Nothing was changed. Please try again.')

    @staticmethod
    def pick(high):
        """Menu choice. Typing 'back' picks the last option (return/exit)."""
        try:
            return Validator.integer('Enter your choice: ', 1, high)
        except GoBack:
            return high

    def run(self):
        while True:
            print()
            Display.header('WELCOME TO COORG AIRLINE RESERVATION SERVICES')
            print('\nENTER 1: ENTER AS ADMIN')
            print('ENTER 2: ENTER AS USER')
            print('ENTER 3: TO EXIT\n')
            choice = self.pick(3)
            if choice == 1:
                self.run_safely(self.admin)
            elif choice == 2:
                self.user()
            else:
                self.goodbye()
                break

    def user(self):
        while True:
            print()
            Display.header('AIRLINE RESERVATION', '-')
            print('ENTER 1: BOOK A FLIGHT')
            print('ENTER 2: SEARCH')
            print('ENTER 3: VIEW TICKET')
            print('ENTER 4: MODIFY BOOKING / UPGRADE CLASS')
            print('ENTER 5: FOOD SERVICES / ONLINE CHECK-IN')
            print('ENTER 6: CANCEL TICKET')
            print('ENTER 7: RETURN TO MENU\n')
            choice = self.pick(7)
            if choice == 1:
                self.run_safely(self.bookings.book)
            elif choice == 2:
                self.search()
            elif choice == 3:
                self.run_safely(self.bookings.view_ticket)
            elif choice == 4:
                self.run_safely(self.bookings.modify)
            elif choice == 5:
                self.other_services()
            elif choice == 6:
                self.run_safely(self.bookings.cancel)
            else:
                break

    def search(self):
        while True:
            print()
            Display.header('SEARCH', '-')
            print('ENTER 1: SEARCH THE FLIGHTS')
            print('ENTER 2: SEARCH THE PASSENGERS')
            print('ENTER 3: RETURN TO MENU\n')
            choice = self.pick(3)
            if choice == 1:
                self.run_safely(self.flights.search)
            elif choice == 2:
                self.run_safely(self.bookings.search_passenger)
            else:
                break

    def other_services(self):
        while True:
            print()
            Display.header('OTHER SERVICES')
            print('ENTER 1: ONLINE CHECK-IN')
            print('ENTER 2: FOOD SERVICES')
            print('ENTER 3: RETURN TO MENU\n')
            choice = self.pick(3)
            if choice == 1:
                self.run_safely(self.services.check_in)
            elif choice == 2:
                self.run_safely(self.services.food_order)
            else:
                break

    def admin(self):
        for left in (2, 1, 0):
            if Validator.secret('Enter ACCESS PASSWORD: ') == ADMIN_PASSWORD:
                break
            print(f'  ! Incorrect password. {left} attempt(s) left.')
        else:
            print('TOO MANY WRONG ATTEMPTS. RETURNING TO THE MAIN MENU.')
            return
        while True:
            print()
            Display.header('ADMIN MENU')
            print('ENTER 1: ADD A FLIGHT')
            print('ENTER 2: MODIFY A FLIGHT')
            print('ENTER 3: DELETE A FLIGHT')
            print('ENTER 4: REPORTS')
            print('ENTER 5: RETURN TO MENU\n')
            choice = self.pick(5)
            if choice == 1:
                self.run_safely(self.flights.add_flight)
            elif choice == 2:
                self.run_safely(self.flights.edit_flight)
            elif choice == 3:
                self.run_safely(self.flights.delete_flight)
            elif choice == 4:
                self.run_safely(self.reports.show)
            else:
                break

    @staticmethod
    def goodbye():
        print()
        print('*' * WIDTH)
        print('THANK YOU FOR CHOOSING COORG AIRLINE RESERVATION SERVICES'.center(WIDTH))
        print()
        print('For any queries, email us at coorgiflights@gmail.com.')
        print('Fax : 1000210        Tel.no : 1700032122')
        print('*' * WIDTH)


if __name__ == '__main__':
    try:
        App().run()
    except KeyboardInterrupt:
        print('\n\nProgram closed. Goodbye!')
