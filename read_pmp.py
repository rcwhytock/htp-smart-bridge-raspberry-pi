from typing import Optional

import os
import json

key_types = {
    "stm32_temp": float,
    "bridge_temp": float,
    "bridge_hum": float,
    "bridge_hpa": int,
    "bridge_volt": int,
    "activation": str,
    "data": str,
}

def read_pmp() -> dict:
    print("Reading PMP serial info...")

    values = {}

    filepath = "serial.log"

    try:
        if not os.path.exists(filepath):
            return values

        with open(filepath) as fp:
            for line in fp:
                elements = line.split(":")
                if len(elements) == 2:
                    try:
                        key = elements[0].strip()
                        value = elements[1].strip()
                        if key in key_types:
                            values[key] = key_types[key](value)
                    except:
                        pass

        print("Read PMP serial info:", values)
    except Exception as e:
        print("Error reading PMP serial info", e)

    return values


if __name__ == '__main__':
    print(json.dumps(read_pmp()))
