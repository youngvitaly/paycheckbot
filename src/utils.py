# src/utils.py
import random
import datetime

def format_date_es(date_input):
    # input example: "28.11.2025,19:07"
    dt = datetime.datetime.strptime(date_input, "%d.%m.%Y,%H:%M")
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{days[dt.weekday()]}, {dt.day} de {months[dt.month-1]} de {dt.year} a las {dt.strftime('%H:%M')} hs", dt

def generate_sum(min_val=4500000, max_val=5500000):
    val = random.randint(min_val, max_val)
    return "$ {:,}".format(val).replace(",", ".")

def generate_client_name():
    first = ["José", "Juan", "Luis", "Carlos", "Miguel", "Andrés", "Pedro", "Fernando", "Ricardo", "Alberto"]
    middle = ["Antonio", "Manuel", "Francisco", "Alejandro", "Javier", "Roberto", "Eduardo", "Hernán", "Diego", "Santiago"]
    last = ["González", "Rodríguez", "Martínez", "López", "Hernández", "Pérez", "García", "Ramírez", "Torres", "Contreras"]
    return f"{random.choice(first)} {random.choice(middle)} {random.choice(last)} {random.choice(last)}"
