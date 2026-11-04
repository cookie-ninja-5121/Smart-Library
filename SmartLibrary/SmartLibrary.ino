#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define SS_PIN     10
#define RST_PIN    7
#define BUZZER_PIN 8

MFRC522 rfid(SS_PIN, RST_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2);

bool scanningEnabled = false;
unsigned long lcdMessageUntil = 0;

void showMessage(const String& line1, const String& line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1.substring(0, 16));
  lcd.setCursor(0, 1);
  lcd.print(line2.substring(0, 16));
}

void showIdleScreen() {
  if (scanningEnabled) {
    showMessage("TAP RFID", "");
  } else {
    showMessage("SMART LIBRARY", "");
  }
}

void readHostCommands() {
  while (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "MODE:SCAN") {
      scanningEnabled = true;
      lcdMessageUntil = 0;
      showIdleScreen();
    } else if (command == "MODE:IDLE") {
      scanningEnabled = false;
      lcdMessageUntil = 0;
      showIdleScreen();
    } else if (command.startsWith("LCD:")) {
      int separator = command.indexOf('|', 4);
      if (separator >= 0) {
        String heading = command.substring(4, separator);
        String detail = command.substring(separator + 1);
        showMessage(heading, detail);
        lcdMessageUntil = millis() + 2500;
      }
    }
  }
}

String readUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      uid += "0";
    }
    uid += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) {
      uid += " ";
    }
  }
  uid.toUpperCase();
  return uid;
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(20);

  SPI.begin();
  rfid.PCD_Init();

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, HIGH);

  lcd.init();
  lcd.backlight();
  showIdleScreen();
}

void loop() {
  readHostCommands();

  if (!scanningEnabled) {
    return;
  }

  if (lcdMessageUntil != 0 &&
      (long)(millis() - lcdMessageUntil) >= 0) {
    lcdMessageUntil = 0;
    showIdleScreen();
  }

  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = readUID();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  Serial.print("Tag UID: ");
  Serial.println(uid);

  digitalWrite(BUZZER_PIN, LOW);
  delay(80);
  digitalWrite(BUZZER_PIN, HIGH);
}
