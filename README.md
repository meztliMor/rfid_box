# rfid_box
A POC for using PN532 NFC reader/writer and LCD1602 (with I2C interface) with a Raspberry Pi (3 B+) running Raspbian.

# Python module dependencies:
* nfcpy
* RPi.GPIO
* gkeepapi
* smbus

# PN532 NFC
Raspberry Pi drives UARTPN532 using UART. The pins are connected as follows:
```
RPi                 PN532
PIN 8  (TXD) <----> SCL
PIN 10 (RXD) <----> SDA
```
# LCD1602 with I2C interface:
Raspberry Pi drives LCD1602 using I2C. The pins are connected as follows:
```
RPi                LCD1602
PIN 3 (SDA) <----> SDA
PIN 5 (SCL) <----> SCL
```
# Push button
It's connected to pin 16.

# Python module dependencies:
* nfcpy
* RPi.GPIO
* gkeepapi
* smbus
