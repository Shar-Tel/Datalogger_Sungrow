# Datalogger Sungrow / Sungrow Data Logger

## Español

### Descripción general
Este proyecto está diseñado para leer datos de inversores Sungrow a través de la red usando MODBUS/TCP sobre IP. El sistema consulta uno o varios inversores cada 15 minutos, almacena las lecturas en una base de datos SQLite local y publica los valores en formato JSON a través de MQTT a un broker externo.

Está pensado para monitorización energética, integración con plataformas de supervisión, dashboards, automatización o almacenamiento histórico. La lógica principal se encuentra en `mqttDataIPSungrow_BD.py`, mientras que la capa de lectura del protocolo MODBUS está implementada en `Sungrow_smartlogger.py`.

Este proyecto está basado en el trabajo de Robin Ostlund sobre lectura de inversores Sungrow por MODBUS.

### ¿Qué hace?
- Lee datos eléctricos de inversores Sungrow por IP.
- Permite configurar varios inversores y varias plantas.
- Recolecta medidas clave como:
  - Potencia activa AC (`PAC`)
  - Energía diaria (`KDY`)
  - Energía mensual (`KMT`)
  - Corrientes por fase (`IL1`, `IL2`, `IL3`)
  - Tensiones por fase (`UL1`, `UL2`, `UL3`)
  - Temperatura (`TKK`)
  - Corriente total y por fase (`IDC`, `IDC1`, `IDC2`, `IDC3`)
  - Tensión de CC (`UCC`)
  - Tensión a tierra (`UGD`)
- Guarda cada lectura en SQLite para evitar pérdida de datos si la conexión MQTT falla.
- Envía las lecturas pendientes desde la base de datos a MQTT cuando la conexión está disponible.
- También consulta alarmas del inversor y las publica en un topic específico.

### Arquitectura del proyecto
- `Sungrow_smartlogger.py`: lógica de acceso MODBUS a los inversores.
- `mqttDataIPSungrow_BD.py`: flujo principal, lectura de datos, publicación MQTT y gestión de SQLite.
- `config.cfg`: credenciales y configuración del broker MQTT.
- `configSungrow.xml`: configuración de los inversores y sus direcciones IP.
- `Lecturas.sqlite`: base de datos SQLite creada en ejecución para almacenar lecturas pendientes.

### Requisitos
- Python 3.x
- Librerías:
  - `pymodbus`
  - `paho-mqtt`
  - `pytz`
  - `sqlite3` (incluido en Python)

Se pueden instalar con:

```bash
pip install pymodbus paho-mqtt pytz
```

### Configuración

#### 1) Broker MQTT (`config.cfg`)
El archivo `config.cfg` debe contener los datos del broker MQTT, por ejemplo:

```ini
[MQTT]
broker_address = 192.168.1.10
port = 1883
user = usuario_mqtt
password = contraseña_mqtt
```

#### 2) Inversores a monitorizar (`configSungrow.xml`)
El archivo `configSungrow.xml` define la planta y los inversores que se van a consultar.

Ejemplo:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Inversores Nombre="MiPlanta">
    <Inverter>
        <Numero>1,2,3</Numero>
        <IP>192.168.1.50</IP>
        <Puerto>502</Puerto>
    </Inverter>
    <Inverter>
        <Numero>4</Numero>
        <IP>192.168.1.51</IP>
        <Puerto>502</Puerto>
    </Inverter>
</Inversores>
```

### Cómo funciona la lectura
El programa comprueba la hora y realiza la lectura en los minutos `:00`, `:15`, `:30` y `:45` de cada hora. También es posible forzar una lectura inmediata al arrancar pulsando cualquier tecla, según la lógica del script.

Cada ciclo:
1. Se conecta al broker MQTT.
2. Recorre cada inversor configurado.
3. Lee los registros MODBUS necesarios.
4. Convierte los valores a un JSON.
5. Guarda el dato en SQLite.
6. Intenta enviar los datos pendientes por MQTT.
7. Repite el proceso en el siguiente intervalo.

### Topics MQTT
El proyecto publica en estos topics:
- `General/datos`: lecturas de energía y estado del inversor.
- `General/alarmas`: alarmas generadas por el inversor.

### Base de datos local
El script crea y usa una base de datos SQLite llamada `Lecturas.sqlite`.

Cuando la conexión MQTT no está disponible, las lecturas se almacenan en la base de datos y se reintentan más tarde, evitando pérdidas de datos.

### Ejecución
Desde la carpeta del proyecto, ejecuta:

```bash
python mqttDataIPSungrow_BD.py
```

Para detener la ejecución, usa `Ctrl + C`.

### Notas importantes
- La dirección MODBUS del inversor suele ser el puerto `502`.
- La red debe permitir la comunicación TCP desde el equipo que ejecuta el script hasta cada inversor.
- Si el broker MQTT está caído, las lecturas se quedan en SQLite y se reenvían más tarde.
- El script asume que los inversores están en la misma red local o en una red con acceso IP disponible.

### Licencia y uso
Este proyecto está destinado a uso técnico y de monitorización de instalaciones con inversores Sungrow. Se recomienda revisar la compatibilidad de los registros MODBUS con el modelo concreto de inversor antes de desplegarlo en producción.

---

## English

### Overview
This project is designed to read data from Sungrow inverters over the network through MODBUS/TCP via IP. The system queries one or more inverters every 15 minutes, stores the readings in a local SQLite database, and publishes the values in JSON format to an MQTT broker.

It is intended for energy monitoring, integration with supervision platforms, dashboards, automation systems, or historical data storage. The main logic is located in `mqttDataIPSungrow_BD.py`, while the MODBUS communication layer is implemented in `Sungrow_smartlogger.py`.

This project is based on the work of Robin Ostlund on reading Sungrow inverters via MODBUS.

### What it does
- Reads inverter data by IP address.
- Supports multiple inverters and several plants.
- Collects key metrics such as:
  - Active AC power (`PAC`)
  - Daily energy (`KDY`)
  - Monthly energy (`KMT`)
  - Current per phase (`IL1`, `IL2`, `IL3`)
  - Voltage per phase (`UL1`, `UL2`, `UL3`)
  - Temperature (`TKK`)
  - Total and per-phase DC current (`IDC`, `IDC1`, `IDC2`, `IDC3`)
  - DC voltage (`UCC`)
  - Ground voltage (`UGD`)
- Stores each reading in SQLite to avoid data loss if MQTT is unavailable.
- Sends pending readings from the local database when the connection is restored.
- Polls inverter alarms and publishes them on a dedicated topic.

### Project structure
- `Sungrow_smartlogger.py`: MODBUS communication layer for Sungrow devices.
- `mqttDataIPSungrow_BD.py`: main data acquisition flow, MQTT publishing, and SQLite management.
- `config.cfg`: MQTT broker credentials and connection settings.
- `configSungrow.xml`: inverter configuration and IP address list.
- `Lecturas.sqlite`: local SQLite database created at runtime to queue readings.

### Requirements
- Python 3.x
- Libraries:
  - `pymodbus`
  - `paho-mqtt`
  - `pytz`
  - `sqlite3` (included with Python)

Install them with:

```bash
pip install pymodbus paho-mqtt pytz
```

### Configuration

#### 1) MQTT broker (`config.cfg`)
The file `config.cfg` must contain the MQTT broker details, for example:

```ini
[MQTT]
broker_address = 192.168.1.10
port = 1883
user = mqtt_user
password = mqtt_password
```

#### 2) Inverters to monitor (`configSungrow.xml`)
The file `configSungrow.xml` defines the plant name and the inverters to be queried.

Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Inversores Nombre="MyPlant">
    <Inverter>
        <Numero>1,2,3</Numero>
        <IP>192.168.1.50</IP>
        <Puerto>502</Puerto>
    </Inverter>
    <Inverter>
        <Numero>4</Numero>
        <IP>192.168.1.51</IP>
        <Puerto>502</Puerto>
    </Inverter>
</Inversores>
```

### How reading works
The program checks the time and performs the read at minutes `:00`, `:15`, `:30`, and `:45` of each hour. It can also trigger an immediate read at startup by pressing any key, depending on the script logic.

Each cycle:
1. Connects to the MQTT broker.
2. Loops through each configured inverter.
3. Reads the required MODBUS registers.
4. Converts the values into a JSON payload.
5. Saves the data to SQLite.
6. Tries to send pending readings to MQTT.
7. Repeats in the next interval.

### MQTT topics
The project publishes to the following topics:
- `General/datos`: inverter energy and status readings.
- `General/alarmas`: inverter alarms.

### Local database
The script creates and uses a SQLite database named `Lecturas.sqlite`.

If the MQTT connection is unavailable, readings are stored locally and retried later, preventing data loss.

### Execution
From the project folder, run:

```bash
python mqttDataIPSungrow_BD.py
```

To stop the process, use `Ctrl + C`.

### Important notes
- The inverter MODBUS port is usually `502`.
- The network must allow TCP communication from the machine running the script to each inverter.
- If the MQTT broker is down, the readings remain stored in SQLite and are resent later.
- The script assumes the inverters are on the same local network or on a network with IP reachability.

### License and usage
This project is intended for technical monitoring of Sungrow inverter installations. It is recommended to verify the compatibility of the MODBUS register map with the exact inverter model before deploying it in a production environment.

---

## Quick start / Inicio rápido

```bash
pip install pymodbus paho-mqtt pytz
python mqttDataIPSungrow_BD.py
```

Configure `config.cfg` and `configSungrow.xml` before launching the script.

## Contributing / Contribución
If you want to expand the project, you can add:
- support for more Sungrow registers,
- more advanced fault handling,
- dashboard integration,
- CSV export or database normalization,
- automatic service startup with systemd or Windows Task Scheduler.

Si quieres ampliar el proyecto, puedes añadir:
- soporte para más registros Sungrow,
- manejo de errores más avanzado,
- integración con dashboards,
- exportación CSV o normalización de bases de datos,
- inicio automático con systemd o Programador de tareas de Windows.


