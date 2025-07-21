"""
Lee inversores Sungrow con MODBUS sobre TCP. Basado en el código de Robin Ostlund
"""
import logging
import time
from collections import namedtuple
from datetime import datetime

import pytz
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException as ModbusConnectionException

LOGGER = logging.getLogger(__name__)

RegisterDefinitions = namedtuple(
    "RegisterDefinitions", "type unit gain register length"
)
GridCode = namedtuple("GridCode", "standard country")
Result = namedtuple("Result", "value unit")
Alarm = namedtuple("Alarm", "name id level")


class Sungrow:
    """Interfaz al inversor Sungrow"""

    def __init__(self, host, port="502", timeout=5, wait=2):
        self.client = ModbusTcpClient(host=host, port=port, timeout=timeout)
        self._time_offset = None
        self.connected = False 
        self.wait = wait

    def get(self, modbus, name):
        """get named register from device"""
        reg = REGISTERS[name] 
        registro=reg.register-1 #Las direcciones tienen 1 de más
        response = self.read_register(registro, reg.length, modbus)

        if reg.type == "str":
            result = response.decode("utf-8").strip("\0")


        elif reg.type == "u32" and reg.unit == "epoch":
            tmp = int.from_bytes(response, byteorder="big")
            if self._time_offset is None:
                self._time_offset = self.get("time_zone").value
            tmp2 = datetime.utcfromtimestamp(tmp - 60 * self._time_offset)
            result = pytz.utc.normalize(pytz.utc.localize(tmp2, is_dst=True))

        elif reg.type == "u16":
            tmp = int.from_bytes(response, byteorder="big")
            if reg.gain == 1:
                result = tmp
            else:
                result = tmp / reg.gain

    
        elif reg.type == "u32":
            #Aquí hay que cambiar el orden de las words leídas antes de pasarlo a int
            fin=response[:2]
            principio=response[-2:]
            response=principio+fin
            tmp = int.from_bytes(response, byteorder="big")
            if reg.gain == 1:
                result = tmp
            else:
                result = tmp / reg.gain
            

        elif reg.type == "u64":
            tmp = int.from_bytes(response, byteorder="big")
            if reg.gain == 1:
                result = tmp
            else:
                result = tmp / reg.gain

        elif reg.type == "i16":
            tmp = int.from_bytes(response, byteorder="big")
            if (tmp & 0x8000) == 0x8000:
                # el resultado es negativo
                tmp = -((tmp ^ 0xFFFF) + 1)
            if reg.gain == 1:
                result = tmp
            else:
                result = tmp / reg.gain

        elif reg.type == "i32":
            tmp = int.from_bytes(response, byteorder="big")
            if (tmp & 0x80000000) == 0x80000000:
                # el resultado es negativo
                tmp = -((tmp ^ 0xFFFFFFFF) + 1)
            if reg.gain == 1:
                result = tmp
            else:
                result = tmp / reg.gain


        elif reg.type == "state_opt_bitfield32":
            result = []
            result.append(int.from_bytes(response[0:2],byteorder="big"))

        else:
            result = int.from_bytes(response, byteorder="big")

        return Result(result, reg.unit)

    def close_connection(self):
        self.client.close()
        self.connected = False

    def read_register(self, register, length, modbus):
        """
        Ejecutar un read register en el inversor Sungrow.
        Si no se puede leer, intenta reconectar hasta 5 veces.
        Si no se puede leer, lanza una excepción.
        """
        i = 0
        if not self.connected:
            self.client.connect()
            self.connected = True
            time.sleep(self.wait)
        while i < 5:
            try:
                response = self.client.read_input_registers(register, length, unit=modbus)
            except ModbusConnectionException as ex:
                LOGGER.exception("failed to connect to device, is the host correct?")
              #  raise ConnectionException(ex)
            if not response.isError():
                break
            self.client.close()
            self.client.connect()
            time.sleep(self.wait)

            LOGGER.debug("Failed reading register %s time(s)", i)
            i = i + 1
        else:
            message = (
                "could not read register value, is an other device already connected?"
            )
            LOGGER.error(message)
#             raise ReadException(message)
        return response.encode()[1:]



class ConnectionException(Exception):
    """Exception connecting to device"""


class ReadException(Exception):
    """Exception reading register from device"""

#Los registros que se pueden leer del inversor Sungrow
REGISTERS = {
    "PAC": RegisterDefinitions("u32", None, 1, 5031, 2),
    "KDY": RegisterDefinitions("u16", None, 10, 5003 , 1),
    "KMT": RegisterDefinitions("u32", None, 10, 5128 , 2),
    "IL1": RegisterDefinitions("u16", None, 10, 5022, 1),
    "IL2": RegisterDefinitions("u16", None, 10, 5023, 1),
    "IL3": RegisterDefinitions("u16", None, 10, 5024, 1),
    "UL1": RegisterDefinitions("u16", None, 10, 5019, 1),
    "UL2": RegisterDefinitions("u16", None, 10, 5020, 1),
    "UL3": RegisterDefinitions("u16", None, 10, 5021, 1),
    "IDC1": RegisterDefinitions("u16", None, 10, 5012, 1), #Los 3 IDCx sumados darán el IDC
    "IDC2": RegisterDefinitions("u16", None, 10, 5014, 1),
    "IDC3": RegisterDefinitions("u16", None, 10, 5016, 1),
    "UGD": RegisterDefinitions("i16", None, 10, 5146, 1),
    "UCC": RegisterDefinitions("u16", None, 10, 5147, 1),
    "TKK": RegisterDefinitions("i16", None, 10, 5008, 1),
    "ALM":RegisterDefinitions("u16", None, 10, 5045, 1),
}
  