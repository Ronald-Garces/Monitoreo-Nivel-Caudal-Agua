#include <WiFi.h>
#include <PubSubClient.h>
#include "heltec.h"

const char* WIFI_SSID   = "FIBER_STORE_JOSHUA_2.4";
const char* WIFI_PASS   = "J@shua*57237";
const char* MQTT_BROKER = "192.168.100.5";      
const uint16_t MQTT_PORT = 1883;
const char* MQTT_TOPIC  = "analogico";            
// LoRa:
const long   LORA_FREQ  = 865E6;    
const uint8_t LORA_SYNC = 0x12;    

WiFiClient espClient;
PubSubClient mqtt(espClient);

void wifiConnect() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Heltec.display->clear();
  Heltec.display->drawString(0, 0, "Conectando WiFi...");
  Heltec.display->drawString(0, 12, WIFI_SSID);
  Heltec.display->display();

  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) {
    delay(300);
  }

  Heltec.display->clear();
  if (WiFi.status() == WL_CONNECTED) {
    Heltec.display->drawString(0, 0, "WiFi OK");
    Heltec.display->drawString(0, 12, WiFi.localIP().toString());
  } else {
    Heltec.display->drawString(0, 0, "WiFi FAIL");
  }
  Heltec.display->display();
}

void mqttConnect() {
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  String cid = "heltecRX-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  while (!mqtt.connected() && WiFi.status() == WL_CONNECTED) {
    mqtt.connect(cid.c_str());   
    if (!mqtt.connected()) delay(1000);
  }
  if (mqtt.connected()) {
    Heltec.display->clear();
    Heltec.display->drawString(0, 0, "MQTT conectado");
    Heltec.display->drawString(0, 12, MQTT_TOPIC);
    Heltec.display->display();
  }
}

void setup() {
  Serial.begin(115200);        
  delay(50);

  Heltec.begin(
    true,   // Display
    true,   // LoRa
    true,   // Serial
    true,   // PABOOST
    LORA_FREQ
  );
  LoRa.setSyncWord(LORA_SYNC);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.enableCrc();

  Serial.println("RX listo 115200");

  wifiConnect();
  if (WiFi.status() == WL_CONNECTED) mqttConnect();

  Heltec.display->clear();
  Heltec.display->drawString(0, 0, "RX Heltec LoRa");
  Heltec.display->drawString(0, 12, "Esperando...");
  Heltec.display->display();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected()) mqttConnect();
  if (mqtt.connected()) mqtt.loop();

  int p = LoRa.parsePacket();
  if (p) {
    String msg = "";
    while (LoRa.available()) msg += (char)LoRa.read();
    msg.trim();                      

    float nivel_f = msg.toFloat();   
    char buffer[16];
    dtostrf(nivel_f, 1, 2, buffer); 

    bool ok = false;
    if (mqtt.connected()) {
      ok = mqtt.publish(MQTT_TOPIC, buffer, true); 
    }

    Heltec.display->clear();
    Heltec.display->drawString(0, 0, "RX LoRa OK");
    Heltec.display->drawString(0, 12, "Nivel: " + String(buffer) + " m");
    Heltec.display->drawString(0, 24, "RSSI: " + String(LoRa.packetRssi()));
    Heltec.display->drawString(0, 36, ok ? "MQTT: OK" : "MQTT: FAIL");
    Heltec.display->display();

    Serial.print("Nivel RX: ");
    Serial.print(buffer);
    Serial.println(ok ? "  [MQTT OK]" : "  [MQTT FAIL]");
  }
}
