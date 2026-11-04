
import serial
import time

PORT = "COM3"
BAUD_RATE = 9600

try:
    print(f"Connecting to Arduino on {PORT}...")
    with serial.Serial(PORT, BAUD_RATE, timeout=1) as arduino:
        time.sleep(2)
        print("Connected! Scan an RFID card or book tag.")
        
        while True:
            line = arduino.readline().decode(
                "utf-8", errors="ignore"
            ).strip()

            if line:
                print("Arduino:", line)

except KeyboardInterrupt:
    print("\nRFID test stopped.")

except serial.SerialException as error:
    print(f"Serial connection error: {error}")
