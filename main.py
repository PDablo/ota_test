from machine import Pin, SPI
import framebuf
import time
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD
import ntptime
import urequests
from WIFI_CONFIG import BOT_TOKEN, CHAT_ID

# --- FUNCIONES DE REGISTRO Y NOTIFICACIÓN ---
def guardar_log_y_avisar(mensaje):
    try:
        # 1. Sincronizar hora de internet
        ntptime.settime()
        
        # 2. Ajustar a hora local (UTC-3)
        hora_local = time.time() - (3 * 3600)
        tm = time.localtime(hora_local)
        timestamp = f"{tm[0]:04d}-{tm[1]:02d}-{tm[2]:02d} {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
        
        # 3. Guardar en un archivo de texto interno (historial.txt)
        with open("historial.txt", "a") as f:
            f.write(f"[{timestamp}] {mensaje}\n")
        print(f"Log guardado: [{timestamp}] {mensaje}")
        
        # 4. Enviar notificación por Telegram
        mensaje_url = f"[{timestamp}] {mensaje}".replace(" ", "%20")
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje_url}"
        res = urequests.get(url)
        res.close()
        
    except Exception as e:
        print("Error en registro/Telegram:", e)
        
        
#----------INTERRUPTS--------
pinInterupt = Pin(5, Pin.IN, Pin.PULL_UP)

def callback(pinInterrupt):
    print("INT")
    
pinInterupt.irq(trigger=Pin.IRQ_RISING, handler=callback)

#Los pines de control deberian ser asignados aca
#mediante su numero logico GPIOn
sck = 10
mosi = 11
miso = 28
rst = 12
dc = 8
cs = 9
busy = 13
class EPD_4in2_V2:
    def __init__(self):
        # SPI1 configurado en los pines puenteados
        self.spi = SPI(1, baudrate=4000000, polarity=0, phase=0, sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self.reset_pin = Pin(rst, Pin.OUT)	#RST
        self.dc_pin = Pin(dc, Pin.OUT)	#DC
        self.cs_pin = Pin(cs, Pin.OUT)	#CS
        self.busy_pin = Pin(busy, Pin.IN, Pin.PULL_UP)	#BUSY
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
        print("Iniciando ciclo...")
        
        # Instanciar el actualizador
        ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "main.py")
        
        # Forzamos la conexión WiFi primero para poder mandar el mensaje de Telegram
        ota_updater.connect_wifi()
        try:
            ota_updater.download_and_install_update_if_available()
        except Exception as e:
            print("Fallo OTA:", e)
        # Disparamos el mensaje y el guardado local ANTES de actualizar
        guardar_log_y_avisar("Pico W: Consultando actualizaciones en GitHub...")
        # 1. APAGAR Wi-Fi para liberar el bus de alimentación y evitar brownout
        print("Apagando radio Wi-Fi para estabilizar alimentación...")
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.disconnect()
        wlan.active(False)
        
        # 2. Darle tiempo a los capacitores de la placa para recuperarse del pico del Wi-Fi
        time.sleep(2)
        print("Actualizando pantalla E-Paper...")
        try:
            epd = EPD_4in2_V2()
            epd.init()
            
            buf = bytearray(int(400 * 300 / 8))
            fb = framebuf.FrameBuffer(buf, 400, 300, framebuf.MONO_HLSB)
            
            fb.fill(0xFF)
            fb.rect(10, 10, 380, 280, 0x00)
            fb.text("Actualizacion OK v6", 120, 140, 0x00)
            fb.text("Sistema alimentado autonomo.", 80, 160, 0x00)
            
            epd.display(buf)
            epd.sleep()
        except Exception as e:
            print("Error en pantalla:", e)
            
            print("Esperando 1 hora para el próximo ciclo...")
            time.sleep(3600)
    
        except Exception as e:
            print("Error:", e)
    

# Iniciar el programa
if __name__ == '__main__':
    main()
