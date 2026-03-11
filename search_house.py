import undetected_chromedriver as uc
import os
import shutil
import time
import datetime
import pandas as pd
import requests
import math


# Al enviar a Telegram, usa las variables de entorno que definimos en el YAML
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
home_latitude = float(os.getenv('LATITUDE'))
home_longitude = float(os.getenv('LONGITUDE'))
id_distrito = "51119516" # Villa El Salvador
name_distrito = "villa-el-salvador"
distance_home = 1500 # metros


def iniciar_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 1. User-Agent de un Chrome real (Windows)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    # 2. Ocultar que es un bot a nivel de protocolo
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    chrome_path = shutil.which("google-chrome") or shutil.which("chrome")
    driver = uc.Chrome(
        options=options,
        browser_executable_path=chrome_path,
        version_main=145 
    )
    
    # 3. Eliminar el rastro de 'navigator.webdriver'
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver
def obtener_puntos_mapa_urbania():
    # options = uc.ChromeOptions()
    driver = iniciar_driver()
    # driver = uc.Chrome(options=options)
    
    query_params = {
    "q": None,
    "direccion": None,
    "moneda": "",
    "preciomin": None,
    "preciomax": None,
    "services": "",
    "general": "",
    "searchbykeyword": "",
    "amenidades": "",
    "caracteristicasprop": None,
    "comodidades": "",
    "disposicion": None,
    "roomType": "",
    "outside": "",
    "areaPrivativa": "",
    "areaComun": "",
    "multipleRets": "",
    "tipoDePropiedad": "",
    "subtipoDePropiedad": None,
    "tipoDeOperacion": None,
    "garages": None,
    "antiguedad": None,
    "expensasminimo": None,
    "expensasmaximo": None,
    "withoutguarantor": None,
    "habitacionesminimo": 0,
    "habitacionesmaximo": 0,
    "ambientesminimo": 0,
    "ambientesmaximo": 0,
    "banos": None,
    "superficieCubierta": 1,
    "idunidaddemedida": 1,
    "metroscuadradomin": None,
    "metroscuadradomax": None,
    "tipoAnunciante": "ALL",
    "grupoTipoDeMultimedia": "",
    "publicacion": None,
    "sort": "relevance",
    "etapaDeDesarrollo": "",
    "auctions": None,
    "polygonApplied": None,
    "idInmobiliaria": None,
    "excludePostingContacted": "",
    "banks": "",
    "places": "",
    "condominio": "",
    "preTipoDeOperacion": "",
    "city": None,
    "province": None,
    "zone": id_distrito,
    "valueZone": None,
    "subZone": None,
    "coordenates": None
    }

    try:
        driver.get(f"https://urbania.pe/mapas/propiedades-en-{name_distrito}--lima--lima")
        print("Esperando validación de seguridad y cargando cookies...")
        
        # Simular una pequeña espera y scroll para "activar" la sesión humana
        time.sleep(15) 
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)

        script_fetch = """
        var callback = arguments[arguments.length - 1];
        fetch("https://urbania.pe/rplis-api/map/postings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(arguments[0])
        })
        .then(res => res.json())
        .then(data => callback(data))
        .catch(err => callback({error: err.message}));
        """

        print("Extrayendo puntos del mapa...")
        resultados = driver.execute_async_script(script_fetch, query_params)

        if 'error' in resultados:
            raise Exception(f"Error en la petición: {resultados['error']}")

        url_data_specified = 'https://urbania.pe/rpfic-api/posting-map/'

        results_specified = []

        for posting in resultados.get('mapPostings', []):
            posting_id = posting.get('postingId')
            if posting_id:
                url_specified = f"{url_data_specified}{posting_id}"
                resultados_specified = driver.execute_async_script("""
                var callback = arguments[arguments.length - 1];
                fetch(arguments[0], {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json"
                    }
                })
                .then(res => res.json())
                .then(data => callback(data))
                .catch(err => callback({error: err.message}));
                """, url_specified)
                if 'error' in resultados_specified:
                    print(f"Error al obtener detalles para el posting {posting_id}: {resultados_specified['error']}")
                else:
                    results_specified.append(resultados_specified)
        
        results = resultados, results_specified
        return results

    finally:
        driver.quit()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance



def enviar_notificaciones_vivienda(df_filtrado):
    if df_filtrado.empty:
        print("No hay ofertas que cumplan el criterio de distancia.")
        return

    print(f"Enviando {len(df_filtrado)} notificaciones...")

    for index, fila in df_filtrado.iterrows():
        mensaje = (
            f"🏠 *¡Oferta detectada cerca a ti!*\n\n"
            f"💰 *Precio:* {fila['price']}\n"
            f"📍 *A solo:* {fila['distance_to_home']:.2f} km de ti\n"
            f"🔗 [Abrir en Urbania]({fila['url']})"
        )
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        
        try:
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                print(f"Notificación {index} enviada con éxito.")
            else:
                print(f"Error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"Error de conexión: {e}")

resultados_urbania, resultados_specified_urbania = obtener_puntos_mapa_urbania()

result_by_df = []
for i in resultados_urbania['mapPostings']:
    row = {}
    row['id_app'] = i['postingId']
    row['description'] = i['title']
    row['x'] = i['geolocation']['geolocation'].get('longitude')
    row['y'] = i['geolocation']['geolocation'].get('latitude')
    row['operation'] = i['price'].get('operationType', {}).get('name')
    if i['price'].get('prices', {}):
        row['price'] = i['price'].get('prices', {})[0].get('amount')
        row['price_label'] = i['price'].get('prices', {})[0].get('formattedAmount')
        row['isoCode'] = i['price'].get('prices', {})[0].get('isoCode')
    else:
        row['price'] = None
    row['source'] = 'urbania'
    row['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row['distance_to_home'] = haversine(home_latitude, home_longitude, row['y'], row['x'])
    # detail = resultados_specified_urbania.find(lambda x: x['postingMap']['postingId'] == row['id_app'])
    detail = next((d for d in resultados_specified_urbania if d['postingMap']['postingId'] == row['id_app']), None)
    row['url'] = f"https://urbania.pe{detail['postingMap']['url']}?n_src=Listado&n_pos=1"
    result_by_df.append(row)

df = pd.DataFrame(result_by_df)
df.sort_values(by='distance_to_home', inplace=True)
df.reset_index(drop=True, inplace=True)
enviar_notificaciones_vivienda(df[df['distance_to_home'] <= distance_home])
