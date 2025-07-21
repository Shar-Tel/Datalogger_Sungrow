#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqttClient
import sqlite3 as lite
import json
import select
from datetime import datetime
from Sungrow_smartlogger import Sungrow
import configparser as ConfigParser 
import select
import termios
import tty



IDC = "IDC"	  # Corriente Icc
UL1 = "UL1"	  # Tensión Uco L1
UL2 = "UL2"	  # Tensión Uco L2
UL3 = "UL3"	  # Tensión Uco L3
TKK = "TKK"	  # Temp. unidad potencia 1
IL0 = "IL0"	  # Corriente Ico total
IL1 = "IL1"	  # Corriente Ico L1
IL2 = "IL2"	  # Corriente Ico L2
IL3 = "IL3"	  # Corriente Ico L3
SYS = "SYS"	  # 4E28 = 17128
TNF = "TNF"	  # generated frequency (Hz)
UDC = "UDC"	  # Tensión Ucc
PAC = "PAC"	  # Potencia AC
PDC = "PDC"	  # Potencia DC
PRL = "PRL"	  # relative output (%)
KT0 = "KT0"	  # total yield (kWh)
KDY = "KDY"	  # Energía diaria
KMT = "KMT"   # Energia mensual
SAL = "SAL"   # Alarma de sistema
UGD = "UGD"	  # Tensión Ugnd

		


def convert_data(PAC,KDY,IL1,IL2,IL3,UL1,UL2,UL3,KMT,TKK,IDC,UCC,UGD,inverter):
	"""Convierte los datos leídos del inversor Sungrow a un diccionario para enviar por MQTT"""
	global planta
	# metemos los datos en un diccionario
	ev=[]
	ev.insert(0,['Planta',planta])
	ev.insert(1,['Inverter',int(inverter)])
	ev.insert(2,['PAC',PAC])
	ev.insert(3,['KDY',KDY])
	ev.insert(4,['IL1',IL1])
	ev.insert(5,['IL2',IL2])
	ev.insert(6,['IL3',IL3])
	ev.insert(7,['UL1',UL1])
	ev.insert(8,['UL2',UL2])
	ev.insert(9,['UL3',UL3])
	ev.insert(10,['KMT',KMT])
	ev.insert(11,['TKK',TKK])
	ev.insert(12,['IDC',IDC])
	ev.insert(13,['UDC',UCC])
	ev.insert(14,['UGD',UGD])
	#Tengo que pasar la fecha de la lectura
	now=datetime.now()
	fecha_ahora=now.strftime("%Y-%m-%d %H:%M:%S")
	ev.insert(15,['Fecha',fecha_ahora])
	return (dict(ev))
	
	
def convert_alarm(alarm,inverter):
	"""Convierte la alarma leída del inversor Sungrow a un diccionario para enviar por MQTT"""
	global planta,inverter_linea
	# metemos los datos en un diccionario
	ev=[]
	ev.insert(0,['Planta',planta])
	ev.insert(1,['Inverter',inverter])
	ev.insert(2,['alarma',alarm])
	ev.insert(3,['tipo',2])#Tipo Sungrow
	return (dict(ev))    
			

#region CONECTA MQTT					
def conectar(user, password, broker_address, port):
	#Conecta con el servidor MQTT
	global client
	try:
		client = mqttClient.Client(mqttClient.CallbackAPIVersion.VERSION2, planta+"_LeeSungrowIP")               #create new instance
		client.username_pw_set(user, password=password)    #poner usuario y contraseña
		client.on_connect= on_connect                      #unir función callback
		client.connect(broker_address, port=port)          #conectar al broker
		client.loop_start()        #start the loop
	except Exception as e:
		print(e)



def on_connect(client, userdata, flags, rc, properties=None):
	if rc == 0:
		global Connected                #Use global variable
		Connected = True                #Signal connection 
	else:
		print("Connection failed")

#endregion

#region BD

def guardaBD(datos):
	"""Guarda en la SQLite los datos que se le pasan"""
	con = lite.connect('Lecturas.sqlite')
	with con:
			cur = con.cursor()
			cur.execute("INSERT INTO Lecturas_guardadas_inverters_Sungrow (dato) VALUES (?)",[datos])
			con.commit()
	con.close()


def enviadeBD():
	"""Envía los datos que hay en BD"""
	#Conecto al MQTT cada vez que envío por si se ha perdido internet o lo que sea
	if Connected==True:
		#Lee las lecturas de la BD
		try:
		#Leo el KDY guardado para ese inverter este día
			con = lite.connect('Lecturas.sqlite') 
			with con:
				con.row_factory = lite.Row
				cur = con.cursor()    
				cur.execute("SELECT * FROM Lecturas_guardadas_inverters_Sungrow")
				rows = cur.fetchall()
			#Si devuelve lecturas, las trato una a una
			for row in rows:
				id=row["id"]
				dato=row["dato"]
				print("Envío dato de BD")
				print(dato)
				#Intento enviar el dato a MQTT
				resultado=client.publish("General/datos",dato,2)
				#Si la envía con éxito, la borra de la BD
				if (resultado[0]==0 or resultado[0]==4):
					borraDatoBD(id)
				else:
					print("Fallo al enviar, ¿no hay internet?") 
				time.sleep(1)	
		except Exception as e:
			print(e) 
		finally:       
			con.close()   
   




def borraDatoBD(id):
	"""Borra de la BD el dato con la id pasada"""
	con = lite.connect('Lecturas.sqlite') 
	with con:
		con.row_factory = lite.Row
		cur = con.cursor()    
		cur.execute("DELETE FROM Lecturas_guardadas_inverters_Sungrow WHERE id="+str(id))
		print("Borrada linea de BD con id="+str(id))

#endregion

#region PRESIONAR TECLA
# Función para verificar si se ha presionado una tecla
def tecla_presionada():
	dr, dw, de = select.select([sys.stdin], [], [], 0)
	return dr

# Configuración para habilitar la detección sin bloquear el input
def config_teclado():
	fd = sys.stdin.fileno()
	old_settings = termios.tcgetattr(fd)
	tty.setcbreak(sys.stdin.fileno())
	return old_settings

# Restaurar configuración original del teclado
def restaurar_teclado(old_settings):
	termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)

# Función para esperar la pulsación de una tecla o continuar después de 10 segundos
def esperar_tecla():
	print("Presione cualquier tecla en los próximos 10 segundos para leer ya...",end='')
	old_settings = config_teclado()
	start_time = time.time()

	while time.time() - start_time < 10:
		print('.',end='')
		sys.stdout.flush()
		if tecla_presionada():
			tecla = sys.stdin.read(1)  # Lee un carácter
			restaurar_teclado(old_settings)
			#print(f"Se presionó la tecla: {tecla}")
			return True
		time.sleep(0.1)  # Pequeña pausa para no consumir demasiado CPU
	
	restaurar_teclado(old_settings)
	print("La primera lectura será al siguiente cuarto.")
	return False
#endregion

def deboLeer():
	"""Devuelve True si es un minuto de los de leer y todavía no ha leído"""
	global leido
	now=datetime.now()
	minutos=now.strftime("%M")
	#Sólo se tiene que hacer a los cuartos
	print(minutos,end=',')
	sys.stdout.flush()
	if int(minutos) in [0,15,30,45]:
		#Sólo lo hago si no lo he leido ya este minuto
		if not leido:
			leido=True #Marco que ha leído este minuto
			return True
	else:
		leido=False
		return False

def esHoraCero():
	"""Devuelve True si la hora actual está entre las 00:00 y las 00:59"""
	now = datetime.now()
	hora = now.strftime("%H")
	return hora == "00"

#region MAIN
def main():
	global planta,Connected,user,password,broker_address,port,leido
	#Saco datos del xml
	root = ET.parse('configSungrow.xml').getroot()
	planta=root.attrib['Nombre']
	datos_inverters=[]
	for child in root:
		temp=[]
		temp.append(child.find("Numero").text.split(","))
		temp.append(child.find("IP").text)
		temp.append(child.find("Puerto").text)
		datos_inverters.append(temp)

	#Leo la configuración desde el archivo config.cfg
	cfg = ConfigParser.ConfigParser()
	if not cfg.read("config.cfg"):
		print("No existe el archivo de configuracion")
		sys.exit(0)
	Connected = False   #global variable for the state of the connection
	broker_address= cfg.get("MQTT", "broker_address")
	port = cfg.getint("MQTT", "port")
	user = cfg.get("MQTT", "user")
	password = cfg.get("MQTT", "password")



	leido=False    

	#Miro si se pulsa una tecla para leer al instante
	if esperar_tecla():
		#Se debe leer ya
		leerYa=True
	else:
		leerYa=False	

	try:    
		while True:
			#Es un minuto de los de leer o le han dado a una tecla al arrancar
			if deboLeer() or leerYa:
				leerYa=False #Ya no debo leer más sin tener en cuenta la hora
				conectar(user, password, broker_address, port)
				veces=0
				#Espero a conexión MQTT o hasta 50 veces
				while Connected != True and veces<50:   
					time.sleep(0.1)
					print("espero reconexión")
					veces+=1
				#Recorro los inverters y pido datos
				for inverter in datos_inverters:
					inverter_ip = inverter[1]
					inverter_puerto=inverter[2]
					inverterMODBUS=Sungrow(inverter_ip, inverter_puerto)
					for inverter_numero in inverter[0]:
						print("miro inverter "+inverter_numero)
						try:
							result=inverterMODBUS.get(int(inverter_numero),"PAC")
							PAC=result.value
							print("PAC "+inverter_numero+" "+str(result.value))
							#Si son las 00 pongo a cero la energía diaria porque puede salir la lectura del día anterior
							if esHoraCero():
								KDY=0
							else:	
								result=inverterMODBUS.get(int(inverter_numero),"KDY")
								print("KDY "+inverter_numero+" "+str(result.value))
								KDY=result.value
							result=inverterMODBUS.get(int(inverter_numero),"IL1")
							print("IL1 "+inverter_numero+" "+str(result.value))
							IL1=result.value
							result=inverterMODBUS.get(int(inverter_numero),"IL2")
							print("IL2 "+inverter_numero+" "+str(result.value))
							IL2=result.value
							result=inverterMODBUS.get(int(inverter_numero),"IL3")
							print("IL3 "+inverter_numero+" "+str(result.value))
							IL3=result.value
							result=inverterMODBUS.get(int(inverter_numero),"UL1")
							print("UL1 "+inverter_numero+" "+str(result.value))
							UL1=result.value
							result=inverterMODBUS.get(int(inverter_numero),"UL2")
							print("UL2 "+inverter_numero+" "+str(result.value))
							UL2=result.value
							result=inverterMODBUS.get(int(inverter_numero),"UL3")
							print("UL3 "+inverter_numero+" "+str(result.value))
							UL3=result.value
							result=inverterMODBUS.get(int(inverter_numero),"KMT")
							print("KMT "+inverter_numero+" "+str(result.value))
							KMT=result.value
							result=inverterMODBUS.get(int(inverter_numero),"TKK")
							print("TKK "+inverter_numero+" "+str(result.value))
							TKK=result.value
							result=inverterMODBUS.get(int(inverter_numero),"IDC1")
							print("IDC1 "+inverter_numero+" "+str(result.value))
							IDC1=result.value
							result=inverterMODBUS.get(int(inverter_numero),"IDC2")
							print("IDC2 "+inverter_numero+" "+str(result.value))
							IDC2=result.value
							result=inverterMODBUS.get(int(inverter_numero),"IDC3")
							print("IDC3 "+inverter_numero+" "+str(result.value))
							IDC3=result.value
							IDC=round(IDC1+IDC2+IDC3,2)
							print("IDC "+inverter_numero+" "+str(IDC))
							result=inverterMODBUS.get(int(inverter_numero),"UGD")
							print("UGD "+inverter_numero+" "+str(result.value))
							UGD=result.value
							result=inverterMODBUS.get(int(inverter_numero),"UCC")
							print("UCC "+inverter_numero+" "+str(result.value))
							UCC=result.value


							try:
								data = convert_data(PAC,KDY,IL1,IL2,IL3,UL1,UL2,UL3,KMT,TKK,IDC,UCC,UGD,inverter_numero)
								print(data)
								#Guardo los datos en BD
								guardaBD(json.dumps(data))
							except:
								pass
						except:
							pass
						time.sleep(1)

						#Pido alarmas	
						try:
							if Connected==True:
								print("miro alarmas")
								result=inverterMODBUS.get(int(inverter_numero),"ALM")
								if (result !=None):
									print(result)	  
									try:
										data = convert_alarm(int(result.value),inverter_numero)
										print(data)
										print("envio a mqtt inverter "+inverter_linea+"."+inverter_numero)
										client.publish("General/alarmas",json.dumps(data),2)
									except Exception as e: 
										print(e)
						except Exception as e: 
							print(e)

						time.sleep(1)
					inverterMODBUS.close_connection()
				#Intento enviar los datos de la BD
				enviadeBD()	
				time.sleep(10)	
				#Desconecto del servidor MQTT
				if Connected==True:
					client.disconnect()
					client.loop_stop()
					Connected=False

			else:
				time.sleep(10)
				
	except KeyboardInterrupt:
	#   f.close()
		client.disconnect()
		client.loop_stop()

#endregion
if __name__ == "__main__":
	main()
