"""
Run this ONCE before airline_reservation.py.

  python setup_database.py          -> creates the tables and loads the sample flights
  python setup_database.py --csv    -> only writes flights_data.csv (no database needed)

It is safe to run again: flights that already exist (same flight number) are skipped,
and your existing bookings are never touched.
"""
import csv
import sys

DB_CONFIG = {'host': 'localhost', 'user': 'root', 'passwd': '1234', 'port': 3306}
DATABASE = 'csproject'

# (airline, flight no, departure, destination, schedule, duration, baggage, fare in $, gate)
FLIGHTS = [
    # ---------------- your original flights (from Bahrain) ----------------
    ('Air France', 'AF123', 'Bahrain', 'Paris', '08:00-15:00', '7h', '30-40kg', 750, 'B4'),
    ('Air France', 'AF789', 'Bahrain', 'Lyon', '22:00-05:00', '7h', '30-40kg', 850, 'B6'),
    ('British Airways', 'BA001', 'Bahrain', 'London', '09:00-14:00', '5h', '20-25kg', 750, 'C19'),
    ('British Airways', 'BA002', 'Bahrain', 'Manchester', '15:00-20:00', '5h', '25-35kg', 800, 'A2'),
    ('Emirates', 'EK202', 'Bahrain', 'Dubai', '08:00-10:00', '2h', '20-30kg', 300, 'A4'),
    ('Emirates', 'EK305', 'Bahrain', 'London', '15:00-20:00', '5h', '25-35kg', 700, 'B13'),
    ('Emirates', 'EK407', 'Bahrain', 'Paris', '22:00-05:00', '7h', '30-40kg', 800, 'B2'),
    ('Etihad Airways', 'EY101', 'Bahrain', 'Abu Dhabi', '05:00-07:00', '2h', '20-30kg', 300, 'C3'),
    ('Etihad Airways', 'EY202', 'Bahrain', 'London', '09:00-14:00', '5h', '25-35kg', 700, 'A24'),
    ('Etihad Airways', 'EY303', 'Bahrain', 'New York', '22:00-08:00', '10h', '40-50kg', 1200, 'B20'),
    ('Coorgairline', 'GF123', 'Bahrain', 'Dubai', '05:00-15:00', '6h', '20-30kg', 600, 'A5'),
    ('Gulf Air', 'GF202', 'Bahrain', 'Mumbai', '10:00-15:00', '5h', '30-40kg', 500, 'D9'),
    ('Gulf Air', 'GF303', 'Bahrain', 'Delhi', '12:00-17:00', '5h', '40-50kg', 550, 'D1'),
    ('Gulf Air', 'GF404', 'Bahrain', 'Dubai', '06:00-07:30', '1.5h', '20-30kg', 200, 'D14'),
    ('Gulf Air', 'GF505', 'Bahrain', 'New York', '23:00-09:00', '10h', '40-50kg', 1600, 'D10'),
    ('Gulf Air', 'GF606', 'Bahrain', 'Bangalore', '14:00-19:00', '5h', '30-40kg', 600, 'D11'),
    ('Gulf Air', 'GF707', 'Bahrain', 'Sydney', '23:00-10:00', '12h', '30-40kg', 1700, 'D3'),
    ('Indian Airlines', 'IA101', 'Bahrain', 'Mumbai', '07:00-12:00', '5h', '40-50kg', 600, 'A20'),
    ('Indian Airlines', 'IA202', 'Bahrain', 'Delhi', '08:00-13:00', '5h', '25-35kg', 500, 'C29'),
    ('Indian Airlines', 'IA303', 'Bahrain', 'Bangalore', '14:00-19:00', '5h', '30-40kg', 550, 'D4'),
    ('Lufthansa', 'LH101', 'Bahrain', 'Frankfurt', '07:00-11:00', '4h', '30-40kg', 600, 'A15'),
    ('Lufthansa', 'LH202', 'Bahrain', 'Munich', '13:00-17:00', '4h', '30-40kg', 650, 'C4'),
    ('Lufthansa', 'LH303', 'Bahrain', 'Berlin', '19:00-23:00', '4h', '40-50kg', 700, 'C21'),
    ('Qatar Airways', 'QR123', 'Bahrain', 'Doha', '06:00-07:30', '1.5h', '20-25kg', 200, 'C10'),
    ('Qatar Airways', 'QR456', 'Bahrain', 'New York', '09:00-18:00', '9h', '40-50kg', 1000, 'C2'),
    ('Qatar Airways', 'QR789', 'Bahrain', 'Sydney', '20:00-08:00', '12h', '35-45kg', 1500, 'A12'),
    ('Singapore Airlines', 'SQ001', 'Bahrain', 'Singapore', '07:00-17:00', '10h', '30-40kg', 1000, 'B9'),
    ('Singapore Airlines', 'SQ002', 'Bahrain', 'Tokyo', '12:00-22:00', '10h', '30-40kg', 1200, 'B10'),
    ('Singapore Airlines', 'SQ003', 'Bahrain', 'Sydney', '18:00-06:00', '12h', '30-40kg', 1500, 'C1'),
    ('Turkish Airlines', 'TK011', 'Bahrain', 'Istanbul', '08:00-12:00', '4h', '20-25kg', 400, 'A8'),
    ('Turkish Airlines', 'TK022', 'Bahrain', 'Ankara', '17:00-21:00', '4h', '40-50kg', 450, 'B21'),

    # ---------------- NEW: more destinations from Bahrain ----------------
    ('Kuwait Airways', 'KU201', 'Bahrain', 'Kuwait City', '09:00-10:00', '1h', '20-30kg', 150, 'A6'),
    ('Saudia', 'SV501', 'Bahrain', 'Riyadh', '11:00-12:30', '1.5h', '20-30kg', 180, 'B7'),
    ('Saudia', 'SV620', 'Bahrain', 'Jeddah', '14:00-16:30', '2.5h', '25-35kg', 260, 'B8'),
    ('EgyptAir', 'MS610', 'Bahrain', 'Cairo', '13:00-16:00', '3h', '30-40kg', 380, 'C12'),
    ('Pakistan International', 'PK182', 'Bahrain', 'Karachi', '06:30-09:30', '3h', '30-40kg', 350, 'C13'),
    ('SriLankan Airlines', 'UL264', 'Bahrain', 'Colombo', '03:00-08:00', '5h', '30-40kg', 520, 'A9'),
    ('Air India', 'AI941', 'Bahrain', 'Kochi', '04:00-09:00', '5h', '25-35kg', 520, 'A10'),
    ('Air India', 'AI942', 'Bahrain', 'Chennai', '10:30-15:30', '5h', '25-35kg', 540, 'A11'),
    ('Air India Express', 'IX474', 'Bahrain', 'Kozhikode', '23:00-04:00', '5h', '20-30kg', 430, 'A13'),
    ('IndiGo', '6E1302', 'Bahrain', 'Hyderabad', '16:00-21:00', '5h', '20-25kg', 480, 'D6'),
    ('Thai Airways', 'TG338', 'Bahrain', 'Bangkok', '22:00-05:00', '7h', '30-40kg', 900, 'B14'),
    ('Malaysia Airlines', 'MH163', 'Bahrain', 'Kuala Lumpur', '21:00-05:00', '8h', '35-45kg', 950, 'B15'),
    ('Cathay Pacific', 'CX746', 'Bahrain', 'Hong Kong', '22:00-08:00', '10h', '30-40kg', 1250, 'B16'),
    ('KLM', 'KL428', 'Bahrain', 'Amsterdam', '07:30-13:30', '6h', '30-40kg', 900, 'C6'),
    ('Swiss', 'LX243', 'Bahrain', 'Zurich', '10:00-16:00', '6h', '30-40kg', 950, 'C7'),
    ('ITA Airways', 'AZ821', 'Bahrain', 'Rome', '12:00-18:00', '6h', '30-40kg', 880, 'C8'),
    ('Iberia', 'IB316', 'Bahrain', 'Madrid', '08:00-15:00', '7h', '30-40kg', 920, 'C9'),
    ('Air Canada', 'AC771', 'Bahrain', 'Toronto', '23:30-11:30', '12h', '40-50kg', 1750, 'D12'),
    ('United Airlines', 'UA991', 'Bahrain', 'Los Angeles', '21:00-13:00', '16h', '40-50kg', 1900, 'D13'),
    ('Ethiopian Airlines', 'ET645', 'Bahrain', 'Johannesburg', '20:00-05:00', '9h', '30-40kg', 1100, 'D15'),

    # ---------------- NEW: flights from Dubai ----------------
    ('Emirates', 'EK500', 'Dubai', 'Mumbai', '08:00-11:00', '3h', '25-35kg', 280, 'A1'),
    ('Emirates', 'EK512', 'Dubai', 'Delhi', '10:00-14:00', '4h', '25-35kg', 320, 'A3'),
    ('Emirates', 'EK001', 'Dubai', 'London', '07:30-14:30', '7h', '30-40kg', 780, 'B1'),
    ('Emirates', 'EK201', 'Dubai', 'New York', '10:30-22:30', '12h', '40-50kg', 1450, 'B3'),
    ('Emirates', 'EK404', 'Dubai', 'Singapore', '09:00-17:00', '8h', '35-45kg', 850, 'B5'),
    ('Qatar Airways', 'QR101', 'Dubai', 'Doha', '12:00-13:30', '1.5h', '20-25kg', 210, 'C11'),
    ('Air India Express', 'IX434', 'Dubai', 'Kozhikode', '20:00-00:00', '4h', '20-30kg', 290, 'A16'),
    ('Air India', 'AI934', 'Dubai', 'Kochi', '11:00-15:00', '4h', '25-35kg', 330, 'A14'),

    # ---------------- NEW: flights from Mumbai ----------------
    ('Air India', 'AI131', 'Mumbai', 'London', '13:00-22:00', '9h', '30-40kg', 900, 'A7'),
    ('Air India', 'AI144', 'Mumbai', 'New York', '01:00-15:00', '14h', '40-50kg', 1500, 'A17'),
    ('IndiGo', '6E1401', 'Mumbai', 'Delhi', '06:00-08:00', '2h', '15-20kg', 120, 'B11'),
    ('IndiGo', '6E1405', 'Mumbai', 'Bangalore', '09:00-10:30', '1.5h', '15-20kg', 90, 'B12'),
    ('IndiGo', '6E1409', 'Mumbai', 'Kochi', '12:00-14:00', '2h', '15-20kg', 110, 'B17'),
    ('Emirates', 'EK501', 'Mumbai', 'Dubai', '04:00-07:00', '3h', '20-30kg', 270, 'C14'),
    ('Singapore Airlines', 'SQ425', 'Mumbai', 'Singapore', '20:00-02:00', '6h', '30-40kg', 600, 'C15'),
    ('Gulf Air', 'GF211', 'Mumbai', 'Bahrain', '05:00-10:00', '5h', '30-40kg', 500, 'D16'),

    # ---------------- NEW: flights from Delhi ----------------
    ('Air India', 'AI111', 'Delhi', 'London', '14:00-23:00', '9h', '30-40kg', 800, 'D2'),
    ('Air India', 'AI101', 'Delhi', 'New York', '02:00-17:00', '15h', '40-50kg', 1450, 'D5'),
    ('IndiGo', '6E2001', 'Delhi', 'Mumbai', '07:00-09:00', '2h', '15-20kg', 110, 'A18'),
    ('IndiGo', '6E2005', 'Delhi', 'Kochi', '10:00-13:30', '3.5h', '15-20kg', 190, 'A19'),
    ('Emirates', 'EK511', 'Delhi', 'Dubai', '04:30-08:30', '4h', '25-35kg', 280, 'C16'),

    # ---------------- NEW: flights from Kochi (Kerala) ----------------
    ('Air India Express', 'IX451', 'Kochi', 'Dubai', '03:30-07:00', '3.5h', '20-30kg', 300, 'B24'),
    ('Air India', 'AI944', 'Kochi', 'Bahrain', '06:00-11:00', '5h', '25-35kg', 520, 'B25'),
    ('IndiGo', '6E5311', 'Kochi', 'Delhi', '08:00-11:00', '3h', '15-20kg', 170, 'A22'),
    ('IndiGo', '6E5312', 'Kochi', 'Mumbai', '15:00-17:00', '2h', '15-20kg', 105, 'A23'),

    # ---------------- NEW: flights from London ----------------
    ('British Airways', 'BA117', 'London', 'New York', '10:30-18:30', '8h', '23-32kg', 700, 'A21'),
    ('British Airways', 'BA106', 'London', 'Paris', '08:00-09:00', '1h', '20-25kg', 130, 'B18'),
    ('Virgin Atlantic', 'VS003', 'London', 'Los Angeles', '11:00-22:00', '11h', '40-50kg', 900, 'B22'),
    ('Lufthansa', 'LH901', 'London', 'Frankfurt', '07:00-09:00', '2h', '20-30kg', 150, 'C17'),
    ('Emirates', 'EK002', 'London', 'Dubai', '14:00-22:00', '8h', '30-40kg', 800, 'D7'),

    # ---------------- NEW: flights from New York and Singapore ----------------
    ('Delta', 'DL100', 'New York', 'London', '19:00-02:00', '7h', '23-32kg', 720, 'D8'),
    ('American Airlines', 'AA100', 'New York', 'Los Angeles', '08:00-14:00', '6h', '25-35kg', 320, 'C18'),
    ('Singapore Airlines', 'SQ321', 'Singapore', 'Tokyo', '09:00-16:00', '7h', '30-40kg', 600, 'C19'),
    ('Singapore Airlines', 'SQ231', 'Singapore', 'Sydney', '07:00-15:00', '8h', '30-40kg', 720, 'B23'),
]

DELAYED = {'BA002', 'GF707', 'EK201'}   # a few flights start as "Delayed" so the status feature shows up


def report_for(flight):
    """Makes the extra details (status, aircraft, seats, terminal, bags) for a flight."""
    airline, number, departure, destination, _, duration, _, _, gate = flight
    hours = float(duration.rstrip('h'))
    if hours <= 2.5:
        model, capacity, bags = 'Airbus A320', 180, 1
    elif hours <= 6:
        model, capacity, bags = 'Boeing 737-800', 189, 2
    elif hours <= 10:
        model, capacity, bags = 'Boeing 787-9', 290, 2
    else:
        model, capacity, bags = 'Airbus A350-900', 325, 3
    terminal = {'A': 1, 'B': 2, 'C': 3, 'D': 4}.get(gate[0].upper(), 1)
    status = 'Delayed' if number in DELAYED else 'On Time'
    return (airline, number, departure, destination, status, model, capacity, terminal, bags)


def write_csv(path='flights_data.csv'):
    with open(path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['airlinename', 'flightno', 'departure', 'destination', 'flightschedule',
                         'duration', 'baggage', 'fare', 'gate'])
        for flight in FLIGHTS:
            writer.writerow(list(flight[:7]) + [float(flight[7]), flight[8]])
    print(f'Wrote {len(FLIGHTS)} flights to {path}')


def setup_database():
    import mysql.connector as sql
    conn = sql.connect(**DB_CONFIG)
    cur = conn.cursor(buffered=True)
    cur.execute(f'CREATE DATABASE IF NOT EXISTS {DATABASE}')
    cur.execute(f'USE {DATABASE}')

    cur.execute("""CREATE TABLE IF NOT EXISTS flights (
        airlinename VARCHAR(50), flightno VARCHAR(10) PRIMARY KEY, departure VARCHAR(40),
        destination VARCHAR(40), flightschedule VARCHAR(20), duration VARCHAR(10),
        baggage VARCHAR(15), fare DECIMAL(10,2), gate VARCHAR(5))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS flightreports (
        airlinename VARCHAR(50), flightno VARCHAR(10) PRIMARY KEY, departure VARCHAR(40),
        destination VARCHAR(40), status VARCHAR(20), model VARCHAR(40), capacity INT,
        terminal INT, no_of_baggage INT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS user_table (
        booking_no VARCHAR(10) PRIMARY KEY, first_name VARCHAR(30), last_name VARCHAR(30),
        email VARCHAR(100), phone_no VARCHAR(20), departure VARCHAR(40), arrival VARCHAR(40),
        `class` VARCHAR(20), seat_no VARCHAR(5), gate_no VARCHAR(5), terminal INT,
        flight_no VARCHAR(10), dates DATE, fare DECIMAL(10,2),
        checked_in TINYINT(1) NOT NULL DEFAULT 0,
        username VARCHAR(30) DEFAULT NULL,
        trip_type VARCHAR(10) DEFAULT 'one_way',
        return_booking_no VARCHAR(10) DEFAULT NULL,
        meal_choice VARCHAR(200) DEFAULT NULL,
        extra_bags INT DEFAULT 0)""")

    # ---- NEW TABLES for the enhanced features ----

    # User accounts (login with hashed passwords)
    cur.execute("""CREATE TABLE IF NOT EXISTS accounts (
        username VARCHAR(30) PRIMARY KEY,
        password_hash VARCHAR(128) NOT NULL,
        salt VARCHAR(32) NOT NULL,
        first_name VARCHAR(30),
        last_name VARCHAR(30),
        email VARCHAR(100),
        phone VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

    # Waiting list (join when a flight is full)
    cur.execute("""CREATE TABLE IF NOT EXISTS waiting_list (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(30) DEFAULT NULL,
        flight_no VARCHAR(10),
        dates DATE,
        travel_class VARCHAR(20),
        num_passengers INT DEFAULT 1,
        first_name VARCHAR(30),
        last_name VARCHAR(30),
        email VARCHAR(100),
        phone VARCHAR(20),
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

    # remove the test row that was in the old CSV files, if it was imported
    cur.execute("DELETE FROM flights WHERE flightno = '23333333333333333'")
    cur.execute("DELETE FROM flightreports WHERE flightno = '23333333333333333'")

    added = 0
    for flight in FLIGHTS:
        cur.execute('SELECT 1 FROM flights WHERE flightno = %s', (flight[1],))
        if not cur.fetchone():
            cur.execute("INSERT INTO flights VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", flight)
            added += 1
        cur.execute('SELECT 1 FROM flightreports WHERE flightno = %s', (flight[1],))
        if not cur.fetchone():
            cur.execute("INSERT INTO flightreports VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", report_for(flight))
    conn.commit()
    conn.close()
    print(f'Done. {added} new flight(s) added, {len(FLIGHTS) - added} already existed.')


if __name__ == '__main__':
    numbers = [f[1] for f in FLIGHTS]
    assert len(numbers) == len(set(numbers)), 'Duplicate flight numbers in FLIGHTS!'
    if '--csv' in sys.argv:
        write_csv()
    else:
        setup_database()