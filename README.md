Programa que lee cada cuarto inversores Sungrow por IP mediante MODBUS, guarda las lecturas en una SQLite local y las envía como JSON mediante MQTT a un broker.
Basado en el código de Robin Ostlund sungrow_modbus.
En config,cfg hay que poner los datos del broker de MQTT
En configSungrow.xml se deben poner una o mas IP desde donde leer los inversores, así como las direcciones MODBUS de los inversores asociados a cada IP.
