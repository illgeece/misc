#!/usr/bin/env python3
"""
DHT22 Temperature and Humidity Sensor Reader 
Reads temperature and humidity data using SPI communication and prints at intervals
Test for SPI connection 
"""

import time
import board
import digitalio
import adafruit_dht
from datetime import datetime

class DHT22SensorReader:
    def __init__(self, data_pin=board.D4, read_interval=2.0):

        self.data_pin = data_pin
        self.read_interval = read_interval
        self.dht = adafruit_dht.DHT22(data_pin)
        
    def read_sensor(self):

        try:
            temperature_c = self.dht.temperature
            humidity = self.dht.humidity
            
            if temperature_c is not None and humidity is not None:
                return temperature_c, humidity
            else:
                return None, None
                
        except RuntimeError as error:
            # DHT22 sensors can be finicky, handle common errors
            print(f"Sensor reading error: {error.args[0]}")
            return None, None
        except Exception as error:
            print(f"Unexpected error: {error}")
            return None, None
    
    def format_reading(self, temperature_c, humidity):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temperature_f = temperature_c * 9.0 / 5.0 + 32.0
        
        return (f"[{timestamp}] "
                f"Temperature: {temperature_c:.1f}°C ({temperature_f:.1f}°F) | "
                f"Humidity: {humidity:.1f}%")
    
    def run_continuous_reading(self):

        print("DHT22 Sensor Reader Starting...")
        print(f"Reading interval: {self.read_interval} seconds")
        print(f"Data pin: {self.data_pin}")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                temperature_c, humidity = self.read_sensor()
                
                if temperature_c is not None and humidity is not None:
                    reading = self.format_reading(temperature_c, humidity)
                    print(reading)
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] Failed to read sensor data")
                
                time.sleep(self.read_interval)
                
        except KeyboardInterrupt:
            print("\nSensor reading stopped by user")
        except Exception as error:
            print(f"Fatal error: {error}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        try:
            self.dht.exit()
        except:
            pass
        print("Sensor cleanup completed")


def main():
    """Main function to run the DHT22 sensor reader"""
    # Configuration
    DATA_PIN = board.D4  # GPIO pin 4 (physical pin 7)
    READ_INTERVAL = 3.0  # seconds between readings
    
    # Create and run sensor reader
    sensor_reader = DHT22SensorReader(
        data_pin=DATA_PIN,
        read_interval=READ_INTERVAL
    )
    
    sensor_reader.run_continuous_reading()


if __name__ == "__main__":
    main()
