from machine import Pin, SPI
import framebuf
import time
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD

# ---------- INTERRUPTS --------
pinInterupt = Pin(5, Pin.IN, Pin.PULL_UP)

def callback(pinInterrupt):
    print("INT")

pinInterupt.irq(trigger=Pin.IRQ_RISING, handler=callback)

# ---------- PINES CONTROL --------
sck = 10
mosi = 11
miso = 28
rst = 12
dc = 8
cs = 9
busy = 13

class EPD_4in2_V2:
    def __init__(self):
        self.spi = SPI(1, baudrate=4000000, polarity=0, phase=0, sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self.reset_pin = Pin(rst, Pin.OUT)
        self.dc_pin = Pin(dc, Pin.OUT)
        self.cs_pin = Pin(cs, Pin.OUT)
        self.busy_pin = Pin(busy, Pin.IN, Pin.PULL_UP)
        self.width = 400
        self.height = 300

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def send_command(self, command):
        self.dc_pin.value(0)
        self.cs_pin.value(0)
        self.spi.write(bytearray([command]))
        self.cs_pin.value(1)

    def send_data(self, data):
        self.dc_pin.value(1)
        self.cs_pin.value(0)
        self.spi.write(bytearray([data]))
        self.cs_pin.value(1)
        
    def send_data_array(self, buf):
        self.dc_pin.value(1)
        self.cs_pin.value(0)
        self.spi.write(bytearray(buf))
        self.cs_pin.value(1)

    def ReadBusy(self):
        while(self.busy_pin.value() == 1):
            self.delay_ms(10)

    def reset(self):
        self.reset_pin.value(1)
        self.delay_ms(20)
        self.reset_pin.value(0)
        self.delay_ms(2)
        self.reset_pin.value(1)
        self.delay_ms(20)

    def init(self):
        self.reset()
        self.send_command(0x21)
        self.send_data(0x40)
        self.send_data(0x00)
        self.send_command(0x3C)
        self.send_data(0x05)
        self.send_command(0x11)
        self.send_data(0x03)
        self.ReadBusy()
        self.send_command(0x44)
        self.send_data(0x00)
        self.send_data(0x31)
        self.send_command(0x45)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x2B)
        self.send_data(0x01)
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)
        self.ReadBusy()

    def display(self, image_buffer):
        self.send_command(0x24)
        self.send_data_array(image_buffer)
        self.send_command(0x20)
        self.ReadBusy()

    def sleep(self):
        self.send_command(0x10)
        self.send_data(0x01)

# --- EJECUCIÓN PRINCIPAL ---
firmware_url = "https://github.com/PDablo/ota_test/"

def main():
    while True:
        print("Iniciando ciclo. Comprobando actualizaciones OTA...")
        try:
            ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "main.py")
            # Si hay actualización, el dispositivo se reiniciará automáticamente aquí.
            ota_updater.download_and_install_update_if_available()
        except Exception as e:
            print("Error durante la comprobación OTA:", e)
        
        print("Actualizando pantalla E-Paper...")
        try:
            epd = EPD_4in2_V2()
            epd.init()
            
            buf = bytearray(int(400 * 300 / 8))
            fb = framebuf.FrameBuffer(buf, 400, 300, framebuf.MONO_HLSB)
            
            fb.fill(0xFF)
            fb.rect(10, 10, 380, 280, 0x00)
            fb.text("¡Hola Mundo!", 110, 140, 0x00)
            fb.text("El hardware funciona perfecto.", 80, 160, 0x00)
            
            epd.display(buf)
            epd.sleep()
        except Exception as e:
            print("Error en pantalla:", e)
            
        print("Esperando 1 hora para el próximo ciclo...")
        time.sleep(3600) # Pausa de 3600 segundos (1 hora)

# Iniciar el programa
if __name__ == '__main__':
    main()
