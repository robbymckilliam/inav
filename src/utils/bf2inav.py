#!/usr/bin/python3
# Betaflight unified config to INAV target converter
#
# This script can be used to Generate a basic working target from a Betaflight Configuration.
# The idea is that this target can be used as a starting point for full INAV target.
#
# The generated target will not include any servo assignments or fixed wing features.
#
# TODO: ADC DMA info
# BF build API:
# target lists
# https://build.betaflight.com/api/targets
# target release info:
# https://build.betaflight.com/api/targets/{TARGET}
# load target:
# Unified targets are deprecated, replaced by https://github.com/betaflight/config


import sys
import os
import io
import getopt
import re
import json
import random
import string

version = '0.1'

def translateFunctionName(bffunction, index):
    return bffunction + '_' + index

def translatePin(bfpin):
    pin = re.sub("^([A-Z])0*(\d+)$", r'P\1\2', bfpin)
    return pin

def mcu2target(mcu):
#mcu STM32F405
    if mcu['type'] == 'STM32F405':
        return 'target_stm32f405xg'

#mcu STM32F411
    if mcu['type'] == 'STM32F411':
        return 'target_stm32f411xe'
    
#mcu STM32F7X2
    if mcu['type'] == 'STM32F7X2':
        return 'target_stm32f722xe'
    
#mcu STM32F745
    if mcu['type'] == 'STM32F745':
        return 'target_stm32f745xg'

#mcu STM32H743
    if mcu['type'] == 'STM32H743':
        return 'target_stm32h743xi'
    
    print("Unknown MCU: %s" % (mcu))
    sys.exit(-1)

def getPortConfig(map):
    mcu = map['mcu']
#mcu STM32F405
    if mcu['type'] == 'STM32F405':
        return """
#define TARGET_IO_PORTA         0xffff
#define TARGET_IO_PORTB         0xffff
#define TARGET_IO_PORTC         0xffff
#define TARGET_IO_PORTD         (BIT(2))
"""

#mcu STM32F411
    if mcu['type'] == 'STM32F411':
        return """
#define TARGET_IO_PORTA         0xffff
#define TARGET_IO_PORTB         0xffff
#define TARGET_IO_PORTC         0xffff
#define TARGET_IO_PORTD         (BIT(2))
"""
    
#mcu STM32F7X2
    if mcu['type'] == 'STM32F7X2':
        return """
#define TARGET_IO_PORTA         0xffff
#define TARGET_IO_PORTB         0xffff
#define TARGET_IO_PORTC         0xffff
#define TARGET_IO_PORTD         0xffff
"""
    
#mcu STM32F745
    if mcu['type'] == 'STM32F745':
        return """
#define TARGET_IO_PORTA 0xffff
#define TARGET_IO_PORTB 0xffff
#define TARGET_IO_PORTC 0xffff
#define TARGET_IO_PORTD 0xffff
#define TARGET_IO_PORTE 0xffff
"""

#mcu STM32H743
    if mcu['type'] == 'STM32H743':
        return """
#define TARGET_IO_PORTA 0xffff
#define TARGET_IO_PORTB 0xffff
#define TARGET_IO_PORTC 0xffff
#define TARGET_IO_PORTD 0xffff
#define TARGET_IO_PORTE 0xffff
"""
    
    print("Unknown MCU: %s" % (mcu))
    sys.exit(-1)

def writeCmakeLists(outputFolder, map):
    file = open(outputFolder + '/CMakeLists.txt', "w+")

    t = mcu2target(map['mcu'])

    file.write("%s(%s SKIP_RELEASES)\n" % (t, map['board_name']))

    return


def findPinsByFunction(function, map):
    result = []
    for pin in map['pins']:
        pattern = "^%s_" % (function)
        if map['pins'][pin].get('function') and re.search(pattern, map['pins'][pin]['function']):
            result.append(pin)
    
    return result

def findPinByFunction(function, map):
    for pin in map['pins']:
        if map['pins'][pin].get('function') and map['pins'][pin]['function'] == function:
            return pin
    
    return None


def getPwmOutputCount(map):
    motors = findPinsByFunction("MOTOR", map)
    servos = findPinsByFunction("SERVO", map)

    return len(motors) + len(servos)

def getGyroAlign(map):
    bfalign = map['variables']['gyro_1_sensor_align']
    m = re.search("^CW(\d+)(FLIP)?$", bfalign)
    if m:
        deg = m.group(1)
        flip = m.group(2)
        if flip:
            return "CW%s_DEG_FLIP" % (deg)
        else:
            return "CW%s_DEG" % (deg)

def getSerialByFunction(map, function):
    for serial in map.get("serial"):
        if map['serial'][serial].get('FUNCTION') == function:
            return serial

    return None

def getSerialMspDisplayPort(map):
    return getSerialByFunction(map, "131072")

def getSerialRx(map):
    rx = getSerialByFunction(map, "64")
    if(rx != None):
        return int(rx) + 1
    return None

def writeTargetH(folder, map):
    file = open(folder + '/target.h', "w+")

    file.write("""/*
 * This file is part of INAV.
 *
 * INAV is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * INAV is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with INAV.  If not, see <http://www.gnu.org/licenses/>.
 *
 * This target has been autgenerated by bf2inav.py
 */

#pragma once

//#define USE_TARGET_CONFIG

#define DEFAULT_FEATURES        (FEATURE_OSD | FEATURE_CURRENT_METER | FEATURE_VBAT | FEATURE_TELEMETRY  )


 \n"""
 )
    board_id = ''.join(random.choice(string.ascii_uppercase) for i in range(4))
    file.write("#define TARGET_BOARD_IDENTIFIER \"%s\"\n" % (board_id))
    file.write("#define USBD_PRODUCT_STRING \"%s\"\n" % (map['board_name']))

    # beeper
    file.write("// Beeper\n")
    pin = findPinByFunction('BEEPER_1', map)
    if pin:
        file.write("#define USE_BEEPER\n")
        file.write("#define BEEPER %s\n" % (pin))
        if map['variables'].get('beeper_inversion', 'OFF') == 'ON':
            file.write("#define BEEPER_INVERTED\n")
    
    # Leds
    file.write("// Leds\n")
    pin = findPinByFunction('LED_STRIP_1', map)
    if pin:
        file.write('#define USE_LED_STRIP\n')
        file.write("#define WS2811_PIN %s\n" % (pin))

    for i in range(1, 9):
        pin = findPinByFunction("LED_%i" % (i), map)
        if pin:
            file.write("#define LED%i %s\n" % (i-1, pin))

    # Serial ports and usb
    file.write("// UARTs\n")
    file.write("#define USB_IO\n")
    file.write("#define USB_VCP\n")
    serial_count = 0 
    pin = findPinByFunction('USB_DETECT_1', map)
    if pin:
        file.write("#define USE_USB_DETECT\n")
        file.write("#define USB_DETECT_PIN %s\n" % (pin))
        #file.write("#define VBUS_SENSING_ENABLED\n");  
        serial_count += 1
 
    for i in range(1, 9):
        txpin = findPinByFunction("SERIAL_TX_%i" % (i), map)
        rxpin = findPinByFunction("SERIAL_RX_%i" % (i), map)
        if txpin or rxpin:
            file.write("#define USE_UART%i\n" % (i))
            serial_count+=1
        else:
            continue

        if rxpin:
            file.write("#define UART%i_RX_PIN %s\n" % (i, rxpin))
        if txpin:
            file.write("#define UART%i_TX_PIN %s\n" % (i, txpin))
        else:
            file.write("#define UART%i_TX_PIN %s\n" % (i, rxpin))

    # soft serial
    for i in range(11, 19):
        txpin = findPinByFunction("SERIAL_TX_%i" % (i), map)
        rxpin = findPinByFunction("SERIAL_RX_%i" % (i), map)
        idx = i - 10
        if txpin != None or rxpin != None:
            file.write("#define USE_SOFTSERIAL%i\n" % (idx))
            serial_count+=1
        else:
            continue

        if txpin != None:
            file.write("#define SOFTSERIAL_%i_TX_PIN %s\n" % (idx, txpin))
        else:
            file.write("#define SOFTSERIAL_%i_TX_PIN %s\n" % (idx, rxpin))
    
        if rxpin != None:
            file.write("#define SOFTSERIAL_%i_RX_PIN %s\n" % (idx, rxpin))
        else:
            file.write("#define SOFTSERIAL_%i_RX_PIN %s\n" % (idx, txpin))
   
    file.write("#define SERIAL_PORT_COUNT %i\n" % (serial_count))

    serial_rx = getSerialRx(map)

    if serial_rx != None:
        file.write("#define DEFAULT_RX_TYPE RX_TYPE_SERIAL\n")
        file.write("#define SERIALRX_PROVIDER SERIALRX_CRSF\n")
        file.write("#define SERIALRX_UART SERIAL_PORT_USART%s\n" % (serial_rx))

    file.write("// SPI\n")
    use_spi_defined = False
    for i in range(1, 9):
        sckpin = findPinByFunction("SPI_SCK_%i" % (i), map)
        misopin = findPinByFunction("SPI_MISO_%i" % (i), map)
        mosipin = findPinByFunction("SPI_MOSI_%i" % (i), map)
        if (sckpin or misopin or mosipin):
            if (not use_spi_defined):
                use_spi_defined = True
                file.write("#define USE_SPI\n")
            file.write("#define USE_SPI_DEVICE_%i\n" % (i))
        
        if sckpin:
            file.write("#define SPI%i_SCK_PIN %s\n" % (i, sckpin))
        if misopin:
            file.write("#define SPI%i_MISO_PIN %s\n" % (i, misopin))
        if mosipin:
            file.write("#define SPI%i_MOSI_PIN %s\n" % (i, mosipin))

    file.write("// I2C\n")
    use_i2c_defined = False
    for i in range(1, 9):
        sclpin = findPinByFunction("I2C_SCL_%i" % (i), map)
        sdapin = findPinByFunction("I2C_SDA_%i" % (i), map)
        if (sclpin or sdapin):
            if (not use_i2c_defined):
                use_i2c_defined = True
                file.write("#define USE_I2C\n")
            file.write("#define USE_I2C_DEVICE_%i\n" % (i))
        
        if sclpin:
            file.write("#define I2C%i_SCL %s\n" % (i, sclpin))
        if sdapin:
            file.write("#define I2C%i_SDA %s\n" % (i, sdapin))

    file.write("// ADC\n")


    # ADC_BATT ch1
    use_adc = False
    pin = findPinByFunction('ADC_BATT_1', map)
    if pin:
        use_adc = True
        file.write("#define ADC_CHANNEL_1_PIN %s\n" % (pin))
        file.write("#define VBAT_ADC_CHANNEL ADC_CHN_1\n");
    
    # ADC_CURR ch2
    pin = findPinByFunction('ADC_CURR_1', map)
    if pin:
        use_adc = True
        file.write("#define ADC_CHANNEL_2_PIN %s\n" % (pin))
        file.write("#define CURRENT_METER_ADC_CHANNEL ADC_CHN_2\n");
    # ADC_RSSI ch3
    pin = findPinByFunction('ADC_RSSI_1', map)
    if pin:
        use_adc = True
        file.write("#define ADC_CHANNEL_3_PIN %s\n" % (pin))
        file.write("#define RSSI_ADC_CHANNEL ADC_CHN_3\n");

    # ADC_EXT  ch4 (airspeed?)
    pin = findPinByFunction('ADC_EXT_1', map)
    if pin:
        use_adc = True
        file.write("#define ADC_CHANNEL_4_PIN %s\n" % (pin))
        file.write("#define AIRSPEED_ADC_CHANNEL ADC_CHN_4\n");

    if use_adc:
        file.write("#define USE_ADC\n")
        file.write("#define ADC_INSTANCE ADC1\n")
    # TODO:
    #define ADC1_DMA_STREAM             DMA2_Stream4

    file.write("// Gyro & ACC\n")
    for supportedgyro in ['BMI160', 'BMI270', 'ICM20689', 'ICM42605', 'MPU6000', 'MPU6500', 'MPU9250']:
        found = False
        for var in ['USE_ACCGYRO_', 'USE_ACC_', 'USE_ACC_SPI', 'USE_GYRO_', 'USE_GYRO_SPI_']:
                val = var + supportedgyro
                if val in map['defines']:
                    found = True
                    break
        
        if found:
            file.write("#define USE_IMU_%s\n" % (supportedgyro))
            file.write("#define %s_CS_PIN       %s\n" % (supportedgyro, findPinByFunction('GYRO_CS_1', map)))
            file.write("#define %s_SPI_BUS BUS_SPI%s\n" % (supportedgyro, map['variables']['gyro_1_spibus']))
            file.write("#define IMU_%s_ALIGN    %s\n" % (supportedgyro, getGyroAlign(map)))


    # TODO
    file.write("// OSD\n")
    osd_spi_bus = map['variables'].get('max7456_spi_bus')
    if osd_spi_bus:
        file.write("#define USE_MAX7456\n")
        pin = findPinByFunction('OSD_CS_1', map)
        file.write("#define MAX7456_CS_PIN %s\n" % (pin))
        file.write("#define MAX7456_SPI_BUS BUS_SPI%s\n" % (osd_spi_bus))
    file.write("// Blackbox\n")
    # Flash:
    spiflash_bus = map['variables'].get('flash_spi_bus')
    if spiflash_bus:
        for i in range(1, 9):
            cs = findPinByFunction("FLASH_CS_%i" % (i), map)
            if cs:
                file.write("#define USE_FLASHFS\n")
                file.write("#define ENABLE_BLACKBOX_LOGGING_ON_SPIFLASH_BY_DEFAULT\n")
                file.write("#define USE_FLASH_M25P16\n")
                file.write("#define USE_FLASH_W25N01G\n")
                file.write("#define M25P16_SPI_BUS BUS_SPI%s\n" % (spiflash_bus))
                file.write("#define M25P16_CS_PIN %s\n" % (cs))
                file.write("#define W25N01G_SPI_BUS BUS_SPI%s\n" % (spiflash_bus))
                file.write("#define W25N01G_CS_PIN %s\n" % (cs))
                break

    # SD Card:
    use_sdcard = False
    for i in range(1, 9):
        sdio_cmd = findPinByFunction("SDIO_CMD_%i" % (i), map)

        if sdio_cmd:
            if not use_sdcard:
                file.write("#define USE_SDCARD\n")
                file.write("#define USE_SDCARD_SDIO\n")
                file.write("#define ENABLE_BLACKBOX_LOGGING_ON_SDCARD_BY_DEFAULT\n")
                use_sdcard = True
            file.write("#define SDCARD_SDIO_4BIT\n")
            file.write("#define SDCARD_SDIO_DEVICE SDIODEV_%i\n" % (i))

    file.write("\n// Otehrs\n\n")

    pwm_outputs = getPwmOutputCount(map)
    file.write("#define MAX_PWM_OUTPUT_PORTS %i\n" % (pwm_outputs))
    file.write("#define USE_SERIAL_4WAY_BLHELI_INTERFACE\n")

    file.write("#define USE_DSHOT\n");
    file.write("#define USE_ESC_SENSOR\n");

    port_config = getPortConfig(map)

    file.write(port_config)

    file.close()
    return

def writeTargetC(folder, map):
    file = open(folder + '/target.c', "w+")

    file.write("""/*
 * This file is part of INAV.
 *
 * INAV is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * INAV is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with INAV.  If not, see <http://www.gnu.org/licenses/>.
 *
 * This target has been autgenerated by bf2inav.py
 */

#include <stdint.h>

#include "platform.h"

#include "drivers/bus.h"
#include "drivers/io.h"
#include "drivers/pwm_mapping.h"
#include "drivers/timer.h"
#include "drivers/pinio.h"
//#include "drivers/sensor.h"

""")

    for supportedgyro in ['BMI160', 'BMI270', 'ICM20689', 'ICM42605', 'MPU6000', 'MPU6500', 'MPU9250']:
        found = False
        for var in ['USE_ACCGYRO_', 'USE_ACC_', 'USE_ACC_SPI', 'USE_GYRO_', 'USE_GYRO_SPI_']:
                val = var + supportedgyro
                if val in map['defines']:
                    found = True
                    break
        
        if found:
            file.write("//BUSDEV_REGISTER_SPI_TAG(busdev_%s,  DEVHW_%s,  %s_SPI_BUS,   %s_CS_PIN,   NONE,   0,  DEVFLAGS_NONE,  IMU_%s_ALIGN);\n" % (supportedgyro.lower(), supportedgyro, supportedgyro, supportedgyro, supportedgyro))


    file.write("\ntimerHardware_t timerHardware[] = {\n")

    motors = findPinsByFunction("MOTOR", map)
    if motors:
        for motor in motors:
            timer = map['pins'][motor]['TIM']
            channel = map['pins'][motor]['CH']
            dma = map['dmas'].get(motor, {}).get("DMA", "0")
            file.write("    DEF_TIM(%s, %s, %s, TIM_USE_MC_MOTOR, 0, %s),\n" % (timer, channel, motor, dma))

    servos = findPinsByFunction("SERVO", map)
    if servos:
        for servo in servos:
            timer = map['pins'][servo]['TIM']
            channel = map['pins'][servo]['CH']
            dma = map['dmas'].get(servo, {}).get("DMA", "0")
            file.write("    DEF_TIM(%s, %s, %s, TIM_USE_MC_SERVO, 0, %s),\n" % (timer, channel, servo, dma))

    beeper = findPinByFunction("BEEPER_1", map)
    if beeper:
        timer = map['pins'].get(beeper, {}).get('TIM')
        channel = map['pins'].get(beeper, {}).get('CH')
        dma = map['dmas'].get(beeper, {}).get("DMA", "0")
        if timer and channel:
            file.write("    DEF_TIM(%s, %s, %s, TIM_USE_BEEPER, 0, %s),\n" % (timer, channel, beeper, dma))

    led = findPinByFunction("LED_STRIP_1", map)
    if led:
        timer = map['pins'].get(led, {}).get('TIM')
        channel = map['pins'].get(led, {}).get('CH')
        dma = map['dmas'].get(led, {}).get("DMA", "0")
        if timer and channel:
            file.write("    DEF_TIM(%s, %s, %s, TIM_USE_LED, 0, %s),\n" % (timer, channel, led, dma))


    file.write("""
};

const int timerHardwareCount = sizeof(timerHardware) / sizeof(timerHardware[0]);
""")

    file.close()
    return

def writeConfigC(folder, map):
    file = open(folder + '/config.c', "w+")

    file.write("""/*
 * This file is part of INAV.
 *
 * INAV is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * INAV is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with INAV.  If not, see <http://www.gnu.org/licenses/>.
 *
 * This target has been autgenerated by bf2inav.py
 */

#include <stdint.h>

#include "platform.h"

#include "fc/fc_msp_box.h"
#include "fc/config.h"

#include "io/piniobox.h"

void targetConfiguration(void)
{
""")
    #//pinioBoxConfigMutable()->permanentId[0] = BOX_PERMANENT_ID_USER1;
    #//pinioBoxConfigMutable()->permanentId[1] = BOX_PERMANENT_ID_USER2;
    #//beeperConfigMutable()->pwmMode = true;
    file.write("""
}

""")

    file.close()
    return

def writeTarget(outputFolder, map):
    writeCmakeLists(outputFolder, map)
    writeTargetH(outputFolder, map)
    writeTargetC(outputFolder, map)
    writeConfigC(outputFolder, map)

    return

def buildMap(inputFile):
    map = { 'defines': [], 'features': [], 'pins': {}, 'dmas': {}, 'serial': {}, 'variables': {}}

    f = open(inputFile, 'r')
    while True:
        l = f.readline()
        if not l:
            break
        m = re.search(r'^#mcu\s+([0-9A-Za-z]+)$', l)
        if m:
            map['mcu'] = {'type': m.group(1)}

        m = re.search(r'^#\s+Betaflight\s+/\s+(STM32\w+)\s+\(\w+\).+$', l)
        if m:
            map['mcu'] = {'type': m.group(1)}

        m = re.search(r'^board_name\s+(\w+)$', l)
        if m:
            map['board_name'] = m.group(1)

        m = re.search(r'^manufacturer_id\s+(\w+)$', l)
        if m:
            map['manufacturer_id'] = m.group(1)
        
        m = re.search(r'^#define\s+(\w+)$', l)
        if m:
            map['defines'].append(m.group(1))

        m = re.search(r'^feature\s+(-?\w+)$', l)
        if m:
            map['features'].append(m.group(1))

        m = re.search(r'^resource\s+(-?\w+)\s+(\d+)\s+(\w+)$', l)
        if m:
            resource_type = m.group(1)
            resource_index = m.group(2)
            pin = translatePin(m.group(3))
            if not map['pins'].get(pin):
                map['pins'][pin] = {}

            map['pins'][pin]['function'] = translateFunctionName(resource_type, resource_index)

        m = re.search(r'^timer\s+(\w+)\s+AF(\d+)$', l)
        if m:
            pin = translatePin(m.group(1))
            if not map['pins'].get(pin):
                map['pins'][pin] = {}
            
            map['pins'][pin]['AF'] = m.group(2)

        m = re.search(r'^#\s*pin\s+(\w+):\s*(TIM\d+)\s+(CH\d+).+$', l)
        if m:
            pin = translatePin(m.group(1))
            if not map['pins'].get(pin):
                map['pins'][pin] = {}
            
            map['pins'][pin]['TIM'] = m.group(2)
            map['pins'][pin]['CH'] = m.group(3)
        
        m = re.search(r'^dma\s+([A-Za-z0-9]+)\s+([A-Za-z0-9]+)\s+(\d+).*$', l)
        if m:

            if(m.group(1) == 'ADC'):
                pin = 'ADC' + m.group(2)
            else:
                pin = translatePin(m.group(2))
            if not map['dmas'].get(pin):
                map['dmas'][pin] = {}
            
            map['dmas'][pin]['DMA'] = m.group(3)

#      1     2         3         4
# pin B04: DMA1 Stream 4 Channel 5
    
        m = re.search(r'^#\s+pin\s+(\w+):\s+(DMA\d+)\s+Stream\s+(\d+)\s+Channel\s+(\d+)\s*$', l)
        if m:
            pin = translatePin(m.group(1))
            if not map['pins'].get(pin):
                map['pins'][pin] = {}
            
            map['pins'][pin]['DMA_STREAM'] = m.group(3)
            map['pins'][pin]['DMA_CHANNEL'] = m.group(4)
        
        m = re.search(r'^#\s+ADC\s+(\d+):\s+(DMA\d+)\s+Stream\s+(\d+)\s+Channel\s+(\d+)\s*$', l)
        if m:
            pin = 'ADC' + m.group(1)
            if not map['dmas'].get(pin):
                map['dmas'][pin] = {}
            
            map['dmas'][pin]['DMA_STREAM'] = m.group(3)
            map['dmas'][pin]['DMA_CHANNEL'] = m.group(4)

        m = re.search(r'^#\s+TIMUP\s+(\d+):\s+(DMA\d+)\s+Stream\s+(\d+)\s+Channel\s+(\d+)\s*$', l)
        if m:
            pin = 'TIMUP' + m.group(1)
            if not map['dmas'].get(pin):
                map['dmas'][pin] = {}
            
            map['dmas'][pin]['DMA_STREAM'] = m.group(3)
            map['dmas'][pin]['DMA_CHANNEL'] = m.group(4)

        m = re.search(r'^#\s+ADC\s+(\d+):\s+(DMA\d+)\s+Stream\s+(\d+)\s+Request\s+(\d+)\s*$', l)
        if m:
            pin = 'ADC' + m.group(1)
            if not map['dmas'].get(pin):
                map['dmas'][pin] = {}
            
            map['dmas'][pin]['DMA_STREAM'] = m.group(3)
            map['dmas'][pin]['DMA_REQUEST'] = m.group(4)

        m = re.search(r'^#\s+TIMUP\s+(\d+):\s+(DMA\d+)\s+Stream\s+(\d+)\s+Channel\s+(\d+)\s*$', l)
        if m:
            pin = 'TIMUP' + m.group(1)
            if not map['dmas'].get(pin):
                map['dmas'][pin] = {}
            
            map['dmas'][pin]['DMA_STREAM'] = m.group(3)
            map['dmas'][pin]['DMA_CHANNEL'] = m.group(4)

        m = re.search(r'^#\s+TIMUP\s+(\d+):\s+(DMA\d+)\s+Stream\s+(\d+)\s+Request\s+(\d+)\s*$', l)
        if m:
            pin = 'TIMUP' + m.group(1)
            if not map['dmas'].get(pin):
                map['dmas'][pin] = {}
            
            map['dmas'][pin]['DMA_STREAM'] = m.group(3)
            map['dmas'][pin]['DMA_REQUEST'] = m.group(4)
 
        m = re.search(r'^serial\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$', l)
        if m:
            idx = m.group(1)
            if not map['serial'].get(idx):
                map['serial'][idx] = {}
            
            map['serial'][idx]['FUNCTION'] = m.group(2)
            map['serial'][idx]['MSP_BAUD'] = m.group(3)
            map['serial'][idx]['GPS_BAUD'] = m.group(4)
            map['serial'][idx]['TELEMETRY_BAUD'] = m.group(5)
            map['serial'][idx]['BLACKBOX_BAUD'] = m.group(6)

        m = re.search(r'^set\s+(\w+)\s*=\s*(\w+)$', l)
        if m:
            map['variables'][m.group(1)] = m.group(2)
 

    return map

def printHelp():
    print ("%s -i bf-target.config -o output-directory" % (sys.argv[0]))
    print ("    -i | --input-config=<file>     -- print this help")
    print ("    -o | --output-dir=<targetdir>  -- print this help")
    print ("    -h | --help                    -- print this help")
    print ("    -v | --version                 -- print version")
    return

def main(argv):
    inputfile = ''
    outputdir = '.'
    global version

    try:
        opts, args = getopt.getopt(argv,"hvi:o:", ["input-config=", "output-dir=", 'version', 'help'])
    except getopt.GeoptError:
        printHelp()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            printHelp()
            sys.exit(1)
        elif opt in ('-i', '--input-config'):
            inputfile = arg
        elif opt in ('-o', '--output-dir'):
            outputdir = arg
        elif opt in ('-v', '--version'):
            print ("%s: %s" % (sys.argv[0], version))
            sys.exit(0)

    if (os.path.exists(inputfile) and os.path.isdir(outputdir)):
        targetDefinition = buildMap(inputfile)
    else:
        printHelp()
        sys.exit(2)


    map = buildMap(inputfile)

    print (json.dumps(map, indent=4))

    writeTarget(outputdir, map)

    sys.exit(0)


if( __name__ == "__main__"):
    main(sys.argv[1:])


