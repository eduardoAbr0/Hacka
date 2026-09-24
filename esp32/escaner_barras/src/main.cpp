#include <Arduino.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "FS.h"
#include "SD_MMC.h"

// --- PINES CÁMARA (Freenove ESP32-S3 WROOM CAM) ---
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM      4
#define SIOC_GPIO_NUM      5

#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       17
#define Y7_GPIO_NUM       18
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       10
#define Y4_GPIO_NUM        8
#define Y3_GPIO_NUM        9
#define Y2_GPIO_NUM       11
#define VSYNC_GPIO_NUM     6
#define HREF_GPIO_NUM      7
#define PCLK_GPIO_NUM     13

#define LED_PIN            2

// --- PINES SD MMC ---
#define SD_MMC_CMD        38
#define SD_MMC_CLK        39
#define SD_MMC_D0         40

// --- PINES SENSOR ULTRASÓNICO ---
#define TRIG_PIN           1
#define ECHO_PIN           3

// Funciones auxiliares
void parpadearError();
float obtenerDistanciaCM();
bool tomarYGuardarFoto();

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("Iniciando sistema de detección y captura...");

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Configurar pines del sensor de ultrasonido
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  // Verificación de PSRAM
  if (psramFound()) {
    Serial.printf("PSRAM detectada correctamente! Libre: %d bytes\n", ESP.getFreePsram());
  } else {
    Serial.println("ATENCIÓN: PSRAM NO detectada. La cámara usará DRAM.");
  }

  // Configuración de la Cámara
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;

  config.pixel_format = PIXFORMAT_GRAYSCALE; // GC0308 no soporta JPEG por hardware
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_LATEST;

  if (psramFound()) {
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.frame_size = FRAMESIZE_QVGA; // Reducir tamaño si no hay PSRAM
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Error al iniciar la cámara: 0x%x\n", err);
    parpadearError();
    return;
  }
  Serial.println("Cámara inicializada.");

  // Inicializar tarjeta SD en modo 1-bit
  SD_MMC.setPins(SD_MMC_CLK, SD_MMC_CMD, SD_MMC_D0);
  if (!SD_MMC.begin("/sdcard", true, false, SDMMC_FREQ_DEFAULT, 5)) {
    Serial.println("Error al montar la tarjeta SD");
    parpadearError();
    return;
  }
  Serial.println("Tarjeta SD lista. Esperando objeto a menos de 20 cm...");
}

void loop() {
  float distancia = obtenerDistanciaCM();

  if (distancia > 0 && distancia < 20.0) {
    Serial.printf("Objeto detectado a %.1f cm! Tomando foto...\n", distancia);
    
    if (tomarYGuardarFoto()) {
      Serial.println("Captura completada con éxito.");
    } else {
      Serial.println("Fallo al procesar o guardar la captura.");
    }

    // Tiempo de espera (3 segundos) para evitar guardar fotos infinitas del mismo objeto
    delay(3000);
    Serial.println("Reanudando monitoreo...");
  }

  delay(150); // Muestreo de distancia cada 150 ms
}

// Mide la distancia con el HC-SR04
float obtenerDistanciaCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 25000); // Timeout a 25ms (~4 metros máx)
  if (duracion == 0) return -1.0; // Fuera de rango o lectura fallida

  return (duracion * 0.0343) / 2.0;
}

// Captura, convierte a JPG y guarda en SD
bool tomarYGuardarFoto() {
  // Descartar primeros frames acumulados para actualizar la exposición/brillo del sensor
  for (int i = 0; i < 3; i++) {
    camera_fb_t * tmp = esp_camera_fb_get();
    if (tmp) esp_camera_fb_return(tmp);
    delay(40);
  }

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Error al obtener frame del buffer");
    return false;
  }

  uint8_t * jpg_buf = NULL;
  size_t jpg_len = 0;
  bool convertOk = frame2jpg(fb, 80, &jpg_buf, &jpg_len);
  esp_camera_fb_return(fb); // Liberar buffer de la cámara tan pronto como sea posible

  if (!convertOk) {
    Serial.println("Error al convertir frame a JPEG");
    return false;
  }

  // Nombre dinámico basado en tiempo de ejecución para evitar sobrescribir
  String path = "/foto_" + String(millis()) + ".jpg";
  File file = SD_MMC.open(path.c_str(), FILE_WRITE);
  
  if (!file) {
    Serial.println("Error al abrir/crear el archivo en la SD");
    free(jpg_buf);
    return false;
  }

  file.write(jpg_buf, jpg_len);
  file.close();
  free(jpg_buf);

  Serial.printf("Foto guardada en SD: %s (%u bytes)\n", path.c_str(), jpg_len);

  // Parpadeo de confirmación (LED enciende brevemente)
  digitalWrite(LED_PIN, HIGH);
  delay(300);
  digitalWrite(LED_PIN, LOW);

  return true;
}

void parpadearError() {
  for (int i = 0; i < 10; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);
    delay(150);
  }
}