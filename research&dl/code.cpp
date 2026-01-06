/*
 * IoT Health Monitoring Band - WOKWI SIMULATION (With Finger Detection)
 * Board: ESP32-S2 Mini
 * Pins: SDA=33, SCL=35, ECG=34, FINGER_SWITCH=1
 */

 #include <Wire.h>
 #include <Adafruit_GFX.h>
 #include <Adafruit_SSD1306.h>
 #include <Adafruit_MPU6050.h>
 #include <Adafruit_Sensor.h>
 
 // --- Configuration ---
 #define SCREEN_WIDTH 128
 #define SCREEN_HEIGHT 64
 #define OLED_RESET    -1 
 #define SCREEN_ADDRESS 0x3C 
 
 // ** PINS **
 #define I2C_SDA 33
 #define I2C_SCL 35
 #define ECG_PIN 34 
 #define FINGER_PIN 1  // The Switch acting as "Finger Sensor"
 
 // --- Objects ---
 Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
 Adafruit_MPU6050 mpu;
 
 // --- Variables ---
 int simulatedBPM = 0;
 long lastBPMUpdate = 0;
 String activityStatus = "Idle";
 bool fingerDetected = false;
 
 void setup() {
   Serial.begin(115200);
   
   Wire.begin(I2C_SDA, I2C_SCL);
 
   // 1. Initialize OLED
   if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
     Serial.println(F("SSD1306 allocation failed"));
     for(;;);
   }
   
   // 2. Initialize MPU6050
   if (!mpu.begin()) {
     Serial.println("Failed to find MPU6050 chip");
     while (1) delay(10);
   }
   mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
   mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
 
   // 3. Setup Pins
   pinMode(ECG_PIN, INPUT);
   pinMode(FINGER_PIN, INPUT); // Read the switch
 
   display.clearDisplay();
   display.setTextSize(1);
   display.setTextColor(SSD1306_WHITE);
   display.println("System Ready");
   display.display();
   delay(1000);
 }
 
 void loop() {
   // --- CHECK FINGER (READ SWITCH) ---
   // If Switch connects to 3.3V (HIGH), finger is "detected"
   if (digitalRead(FINGER_PIN) == HIGH) {
     fingerDetected = true;
   } else {
     fingerDetected = false;
   }
 
   // --- SIMULATE HEART RATE ---
   if (fingerDetected) {
     if (millis() - lastBPMUpdate > 2000) { 
       lastBPMUpdate = millis();
       simulatedBPM = random(68, 85); // Generate normal BPM
     }
   } else {
     simulatedBPM = 0; // Reset BPM if no finger
   }
 
   // --- READ MOTION (MPU6050) ---
   sensors_event_t a, g, temp;
   mpu.getEvent(&a, &g, &temp);
   float totalAccel = sqrt(sq(a.acceleration.x) + sq(a.acceleration.y) + sq(a.acceleration.z));
   
   if (totalAccel > 11.0) activityStatus = "Active";
   else if (totalAccel < 9.9 && totalAccel > 9.7) activityStatus = "Resting";
   else activityStatus = "Moving";
 
   // --- READ ECG ---
   int ecgValue = analogRead(ECG_PIN);
 
   // --- UPDATE DISPLAY ---
   display.clearDisplay();
   
   // Header
   display.setCursor(0, 0);
   display.println("HEALTH MONITOR");
   display.drawLine(0, 10, 128, 10, SSD1306_WHITE);
 
   if (fingerDetected) {
     // SHOW DATA
     display.setCursor(0, 15);
     display.print("BPM: ");
     display.print(simulatedBPM); 
 
     display.setCursor(0, 27);
     display.print("Status: ");
     display.print(activityStatus);
 
     display.setCursor(0, 39);
     display.print("ECG: ");
     display.print(ecgValue);
   } else {
     // SHOW WARNING
     display.setCursor(10, 25);
     display.setTextSize(1);
     display.println("NO FINGER");
     display.setCursor(10, 35);
     display.println("DETECTED");
   }
   
   display.display();
   delay(100); 
 }