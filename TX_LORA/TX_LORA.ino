#include "heltec.h"

static const long LORA_FREQ = 865E6;
static const uint8_t LORA_SYNC = 0x12;

bool isNumericLine(const String& s) {
  if (s.length() == 0) return false;
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (!((c >= '0' && c <= '9') || c == '.' || c == '-' || c == '+')) return false;
  }
  return true;
}

void setup() {
  Heltec.begin(true, true, true, true, LORA_FREQ);
  LoRa.setSyncWord(LORA_SYNC);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.enableCrc();

  Serial.println("TX listo");

  Heltec.display->clear();
  Heltec.display->drawString(0, 0, "TX Heltec LoRa");
  Heltec.display->drawString(0, 12, "Freq: 865 MHz");
  Heltec.display->display();
}

void loop() {
  if (Serial.available()) {
    String linea = Serial.readStringUntil('\n');
    linea.trim();
    if (isNumericLine(linea)) {
      // Enviar por LoRa
      LoRa.beginPacket();
      LoRa.print(linea);          
      LoRa.endPacket();

      Heltec.display->clear();
      Heltec.display->drawString(0, 0, "TX LoRa \xE2\x86\x92"); 
      Heltec.display->drawString(0, 12, "Nivel: " + linea + " cm");
      Heltec.display->display();

      Serial.println(String("[TX] Enviado: ") + linea);
    }
  }
}
