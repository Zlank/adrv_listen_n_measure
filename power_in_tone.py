import time
import pyvisa as visa
import time as t

import json

# Argumentos
import argparse


def power_in_tone(fc, span, points=1001, test_name="None", device_IP="192.2.1.50", rlevel=20, rpos=1, sleep_time=2, preset=False):

    result = {
        "function": "tone_test",
        "test_name": test_name,
        "timestamp": int(t.time()),
        "device_IP": device_IP,
        "idn": "Unknown",
        "central_frequency": fc,
        "span": span,
        "ibw": "None",
        "points": points,
        "rlevel": rlevel,
        "rpos": rpos,
        "fstart": (fc - span) / 2,
        "fend": (fc - span) / 2,
        "power_result": 0,
        "frec_result": 0,
        "step": "NONE",
        "trace": [],
        "ERROR/WARNINGS":"NONE",
        "preset": preset
    }

    try:
        rm = visa.ResourceManager()
        # Creamos el objeto con la IP del dispositivo y registramos el IDN (identificador).
        device = rm.open_resource("TCPIP0::" + device_IP + "::inst0::INSTR")  # 192.168.113.206

    except visa.errors.VisaIOError:
        print("ERROR 001: Printing to JSON.")
        result["ERROR/WARNINGS"] = "-ERROR 001: Device not connected or not found.-"
        return result

    idn = device.query('*IDN?')
    result["idn"] = idn

    if fc < 0:
        print("ERROR 002: Printing to JSON.")
        result["ERROR/WARNINGS"] = "-ERROR 002: Central frequency must be above 0.-"
        return result
    if span < 0:
        print("ERROR 003: Printing to JSON.")
        result["ERROR/WARNINGS"] = "-ERROR 003: Span frequency must be above 0.-"
        return result
    if result["fstart"] < 0:
        print("ERROR 004: Printing to JSON.")
        result["ERROR/WARNINGS"]= "-ERROR 004: Frequency Span out of Scope.-"
        return result

    points_options = [101, 201, 401, 601, 801, 1001]
    if points not in points_options:
        points = min(points_options, key=lambda x: abs(x - points))
        print("WARNING 001: Printing to JSON.")
        result["ERROR/WARNINGS"] = "-WARNING 001: Points must be one of the options below:\n[101, 201, 401, 601, 801, 1001]\n\nChanging to"+str(points)+"."
        result["points"] = points

    if not result["preset"]:
        # Realizamos un Preset del analizador
        device.write("SYST:PRES")

        # Configuramos el analizador para que nos analice el espectro de frecuencia segun los parametros que queremos
        device.write("INST:SEL 'SA'")
        time.sleep(3.0)

    device.write("SENS:FREQ:CENT {}".format(fc*1e6))
    device.write("FREQ:SPAN {}".format(span*1e6))

    device.write("SENS:SWE:POIN {}".format(points)) # parametro
    device.write("DISP:WIND:TRAC1:Y:RLEV {}".format(rlevel)) # parametro
    device.write("DISP:WIND:TRAC1:Y:RPOS {}".format(rpos)) # parametro

    # Para obtener una medida limpia y sin fluctuaciones de los datos de la traza, se realiza un MAX HOLD
    # (se congela la traza para mostrar los valores máximos en cada frecuencia)
    device.write(':TRACe:TYPE %s' % ('MAXH'))
    # print(str(sleep_time))
    t.sleep(sleep_time)

    # Generamos un marker y lo situamos sobre el máximo valor de la banda medida
    device.write("CALC:MARK1:ACT")
    # device.write("CALC:MARK1:X {}".format(fc*1e6))
    device.write('CALC:MARK:FUNC:MAX')

    # Hallamos el valor en frecuencia del primer armonico
    device.write("CALC:MARK1:X?")
    mark1_frec = (float(device.read()))
    # Hallamos el valor en potencia del marker
    device.write("CALC:MARK1:Y?")
    mark1_pot = (float(device.read()))  # Transformo str a float

    temp_values = device.query_ascii_values(':TRACe1:DATA?')
    result["trace"] = temp_values

    pow_in_mark = temp_values[len(temp_values)//2]
    result["power_result"] = mark1_pot
    result["frec_result"] = mark1_frec

    # Para borrar la traza en cada periodo de tiempo utilizaremos
    device.write(':TRACe:TYPE %s' % ('CLRW'))

    device.close()
    rm.close()

    result = json.dumps(result)

    return result


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Power in Tone, it returns a JSON with all the data that the Spectrum Analyzer gives.")

    parser.add_argument('--fc', type=float, required=True, help="Central Frequency (float)")
    parser.add_argument('--span', type=float, required=True, help="Frequency Span (float)")

    parser.add_argument('-TN', '--test_name', type=str, required=False, default="None", help="Test Name (string)")
    parser.add_argument('-dIP', '--device_IP', type=str, required=False, default="192.2.1.50", help="Device IP (string)")
    parser.add_argument('--points', type=int, required=False, default=1001, help="Points (integer)")
    parser.add_argument('-rlevel', '--ref_level', type=float, required=False, default=20, help="Reference Level (float)")
    parser.add_argument('-rpos', '--ref_pos', type=float, required=False, default=1, help="Reference Position (float)")
    parser.add_argument('-sT', '--sleep_time', type=float, required=False, default=1, help="Time for sleep and drink coffe")
    parser.add_argument('-prst', '--preset', type=bool, required=False, default=False, help="Bool var to avoid recursive presets in the SA.")

    # Parsear los argumentos
    args = parser.parse_args()

    print(power_in_tone(args.fc, args.span, args.points, args.test_name, args.device_IP, args.ref_level, args.ref_pos , args.sleep_time, args.preset))
