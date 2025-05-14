import threading
import time
from paramiko import SSHClient, AutoAddPolicy

import tkinter as tk

from power_in_tone import power_in_tone
import datetime as dt
import pandas as pd
import xlsxwriter
import json
from tkinter import ttk

import socket

tension = None
HOST = '192.2.1.60'
PORT = 8888

params = ["fc",
          "gain",
          "frec0_ini",
          "frec0_fin",
          "step_frec",
          "frec_ini",
          "frec_fin",
          "step_gain",
          "gain_ini",
          "gain_fin"]

default_params = [2400,  # fc
                  90,  # gain
                  0,  # frec0_ini
                  0,  # frec0_fin
                  100,  # step_frec
                  2400,  # frec_ini
                  2400,  # frec_fin
                  1,  # step_gain
                  90,  # gain_ini
                  90]  # gain_fin

entries = []
string_vars = []


def start_sequence(entradas):
    print(entradas)
    print("Secuencia iniciada.")


class SSHClienteInteractivo:
    def __init__(self, hostname, username, password=None, key_filename=None, port=22):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.client = None
        self.channel = None
        self.stop = False
        self.prueba = {'Prueba': 0, 'Frecuencias': [], 'Potencia': [], 'Ganancia': []}
        self.status = ""
        self.executing = False
        self.voltage = None

    def conectar(self, label):
        if self.client is None or not self.client.get_transport().is_active():
            self.client = SSHClient()
            self.client.set_missing_host_key_policy(AutoAddPolicy())

            try:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    key_filename=self.key_filename
                )
                self.status = "Comunicación iniciada con Conjunto ADRV."
                label.config(text=self.status)
                label.update_idletasks()
            except Exception as e:
                print(f"Ocurrió un error: {e}")
                self.status = "Conjunto ADRV o Analizador no conectado."
                label.config(text=self.status, fg="red")
                label.update_idletasks()
                self.client.close()

    def ejecutar_interactivo(self, comando, label, duracion=5):
        self.conectar(label)
        self.channel = self.client.invoke_shell()
        time.sleep(1)

        self.channel.send(f"{comando}\n")
        time.sleep(duracion)

        self.channel.send('\x03')  # CTRL+C
        time.sleep(1)

        output = ""
        while self.channel.recv_ready():
            output += self.channel.recv(1024).decode()

        self.cerrar(label, True)
        return output

    def ejecutar_iterativo(self, frec_ini, frec_fin, step, label, duracion=5):
        frec_actual = frec_ini
        step = int(step)

        self.conectar(label)
        self.channel = self.client.invoke_shell()
        # time.sleep(1)
        while frec_actual <= frec_fin:
            comando = 'cd /PARMS/tx_nbandas/;./tx_nbandas --freq {} --ampl {} --gain {}'.format(str(frec_actual * 1e6),
                                                                                                str(0.9), str(90))
            self.channel.send(f"{comando}\n")
            time.sleep(duracion)

            self.channel.send('\x03')  # CTRL+C
            frec_actual += step
            time.sleep(1)

        output = ""
        while self.channel.recv_ready():
            output += self.channel.recv(1024).decode()

        self.cerrar(label, True)
        return output

    def prueba4(self, label, sn, user):

        output = ""
        if not self.executing:

            value = self.prueba.pop('Voltage', None)

            serial_number = sn.get()
            usuario = user.get()

            sn.config(state="disabled")
            sn.update_idletasks()

            user.config(state="disabled")
            user.update_idletasks()

            self.executing = True
            frec_actual = 100
            step = 100
            frec_fin = 6000
            preset = False

            self.prueba['Prueba'] = 4
            self.prueba['Ganancia'].clear()
            self.prueba['Frecuencias'].clear()
            self.prueba['Potencia'].clear()

            self.conectar(label)
            self.channel = self.client.invoke_shell()

            self.status = "Iniciado prueba 4..."
            label.config(text=self.status)
            label.update_idletasks()

            medida = 0
            medidas = int((frec_fin-frec_actual)/step)
            # time.sleep(1)
            while frec_actual <= frec_fin:
                comando = 'cd /PARMS/tx_nbandas/;./tx_nbandas --freq {} --ampl {} --gain {}'.format(
                    str(frec_actual*1e6), str(0.9), str(90))
                self.channel.send(f"{comando}\n")
                time.sleep(1)
                # AQUI IRIA POWER IN TONE
                result = power_in_tone(fc=frec_actual, span=1, points=1001, preset=preset)

                result = json.loads(result)
                if result["ERROR/WARNINGS"] == "-ERROR 001: Device not connected or not found.-":
                    self.status = "Prueba 4: Analizador no conectado.".format(medida, medidas)
                    label.config(text=self.status, fg="red")
                    label.update_idletasks()
                    break

                self.channel.send('\x03')  # CTRL+C

                self.status = "Prueba 4: Medida {} de {}...".format(medida, medidas)
                label.config(text=self.status)
                label.update_idletasks()
                # print(self.status)


                self.prueba['Ganancia'].append(90)
                self.prueba['Frecuencias'].append(frec_actual)
                self.prueba['Potencia'].append(result['power_result'])
                # print(f"{frec_actual}: {result['power_result']}")

                if not preset:
                    preset = True

                frec_actual += step
                medida += 1
                time.sleep(1)
                if self.stop:
                    self.stop = False
                    break

            output = ""
            while self.channel.recv_ready():
                output += self.channel.recv(1024).decode()

            self.status = "Creando excel de resultados..."
            label.config(text=self.status)
            label.update_idletasks()

            # df = pd.DataFrame(self.prueba)
            # now = dt.datetime.now()
            # formatted_now = now.strftime("%Y-%m-%d %H-%M-%S-%f")
            # df.to_excel('prueba_{}_{}_{}_{}.xlsx'.format(self.prueba['Prueba'],
            # formatted_now, serial_number, usuario), index=False)
            t1 = threading.Thread(target=self.results_to_excel, args=(serial_number, usuario))
            t1.start()

            self.status = "Prueba 4 finalizada."
            label.config(text=self.status)
            label.update_idletasks()
            # self.cerrar()

            self.executing = False
            sn.config(state="normal")
            sn.update_idletasks()

            user.config(state="normal")
            user.update_idletasks()

        return output

    def prueba5(self, label, sn, user):

        output = ""
        if not self.executing:

            value = self.prueba.pop('Voltage', None)

            serial_number = sn.get()
            usuario = user.get()

            sn.config(state="disabled")
            sn.update_idletasks()

            user.config(state="disabled")
            user.update_idletasks()

            self.executing = True

            gain_actual = 90
            step = 1
            gain_final = 40

            frec_actual = 433

            self.prueba['Prueba'] = 5
            self.prueba['Ganancia'].clear()
            self.prueba['Frecuencias'].clear()
            self.prueba['Potencia'].clear()

            self.conectar(label)
            self.channel = self.client.invoke_shell()
            preset = False

            medida = 0
            medidas = int((gain_actual - gain_final) / step)

            self.status = "Iniciado prueba 5..."
            label.config(text=self.status)
            label.update_idletasks()
            # time.sleep(1)
            while gain_actual >= gain_final:  # PARA 433MHZ

                comando = 'cd /PARMS/tx_nbandas/;./tx_nbandas --freq {} --ampl {} --gain {}'.format(
                    str(frec_actual*1e6), str(0.9), str(gain_actual))
                self.channel.send(f"{comando}\n")
                # AQUI IRIA POWER IN TONE
                time.sleep(1)
                result = power_in_tone(fc=frec_actual,
                                       span=1,
                                       points=1001,
                                       preset=preset,
                                       rlevel=20 if gain_actual >= 65 else -25)
                result = json.loads(result)
                if result["ERROR/WARNINGS"] == "-ERROR 001: Device not connected or not found.-":
                    self.status = "Prueba 5: Analizador no conectado.".format(medida, medidas)
                    label.config(text=self.status, fg="red")
                    label.update_idletasks()
                    break

                self.channel.send('\x03')  # CTRL+C

                self.status = "Prueba 5: Medida {} de {} en {}MHz...".format(medida, medidas, frec_actual)
                label.config(text=self.status)
                label.update_idletasks()

                self.prueba['Ganancia'].append(gain_actual)
                self.prueba['Frecuencias'].append(frec_actual)
                self.prueba['Potencia'].append(result["power_result"])

                if not preset:
                    preset = True

                gain_actual -= step
                medida += 1

                if gain_actual < gain_final and frec_actual == 433:
                    gain_actual = 90
                    frec_actual = 5800
                    medida = 0
                if self.stop:
                    self.stop = False
                    break
                time.sleep(1)

            while self.channel.recv_ready():
                output += self.channel.recv(1024).decode()

            self.status = "Creando excel de resultados..."
            label.config(text=self.status)
            label.update_idletasks()

            # df = pd.DataFrame(self.prueba)
            # now = dt.datetime.now()
            # formatted_now = now.strftime("%Y-%m-%d %H-%M-%S-%f")
            # df.to_excel('prueba_{}_{}_{}_{}.xlsx'.format(self.prueba['Prueba'],formatted_now,
            # serial_number, usuario), index=False)
            t1 = threading.Thread(target=self.results_to_excel, args=(serial_number, usuario))
            t1.start()
            # self.results_to_excel(serial_number, usuario)

            self.status = "Prueba 5 finalizada."
            label.config(text=self.status)
            label.update_idletasks()
            # self.cerrar()

            self.executing = False
            sn.config(state="normal")
            sn.update_idletasks()

            user.config(state="normal")
            user.update_idletasks()

        return output

    def listen_for_data(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))

        while True:
            data, addr = sock.recvfrom(1024)
            self.voltage = data.decode('utf-8')

    def get_voltage(self):
        return self.voltage

    def advanced_test(self, label, entry1="", entry2=""):

        output = ""
        entries_to_dict = {}
        for i, param in enumerate(params):
            entries_to_dict = {
                param: default_params[i] if entries[i].get() == "" else entries[i].get()
            }

        if not self.executing:

            listen_thread = threading.Thread(target=self.listen_for_data, daemon=True)
            listen_thread.start()
            for entry in entries:
                entry.config(state="disabled")
                entry.update_idletasks()

            self.executing = True

            self.prueba['Prueba'] = 0
            self.prueba['Ganancia'].clear()
            self.prueba['Frecuencias'].clear()
            self.prueba['Potencia'].clear()
            self.prueba['Voltage'] = []

            self.conectar(label)
            self.channel = self.client.invoke_shell()
            preset = False

            medida = 0
            medidas = (abs(int((entries_to_dict['gain_ini'] - entries_to_dict['gain_fin']) / entries_to_dict['step'])) +
                       abs(int((entries_to_dict['frec_ini']-entries_to_dict['frec_fin'])/entries_to_dict['step'])))

            gain_actual = entries_to_dict['gain_ini']
            gain_final = entries_to_dict['gain_fin']

            frec_actual = entries_to_dict['frec_ini']
            frec_final = entries_to_dict['frec_fin']

            orden_frec = "Ascendente"
            orden_gain = "Ascendente"

            if gain_actual >= gain_final:
                orden_gain = "Descendente"
            elif gain_final >= gain_actual:
                orden_gain = "Ascendente"

            if frec_actual >= frec_final:
                orden_frec = "Descendente"
            elif frec_final >= frec_actual:
                orden_frec = "Ascendente"

            self.status = "Iniciado prueba..."
            label.config(text=self.status)
            label.update_idletasks()
            # time.sleep(1)
            while ((gain_actual >= gain_final and orden_gain == "Descendente") or
                   (gain_final >= gain_actual and orden_gain == "Ascendente") or
                   (frec_actual >= frec_final and orden_frec == "Descendente") or
                   (frec_final >= frec_actual and orden_frec == "Ascendente")):

                comando = 'cd /PARMS/tx_nbandas/;./tx_nbandas --freq {} --ampl {} --gain {} --frec0_ini {} --frec0_fin {}'.format(
                    str(float(frec_actual)*1e6), str(0.9), str(float(gain_actual)),
                    str(float(entries_to_dict['frec0_ini'])*1e6), str(float(entries_to_dict['frec0_fin'])*1e6))
                self.channel.send(f"{comando}\n")
                # AQUI IRIA POWER IN TONE
                time.sleep(1)
                result = power_in_tone(fc=frec_actual,
                                       span=1,
                                       points=1001,
                                       preset=preset,
                                       rlevel=20 if gain_actual >= 65 else -25)
                result = json.loads(result)
                voltage = self.get_voltage()

                if result["ERROR/WARNINGS"] == "-ERROR 001: Device not connected or not found.-":
                    self.status = "Prueba: Analizador no conectado.".format(medida, medidas)
                    label.config(text=self.status, fg="red")
                    label.update_idletasks()
                    break

                self.channel.send('\x03')  # CTRL+C

                self.status = "Prueba: Medida {} de {} en {}MHz...".format(medida, medidas, frec_actual)
                label.config(text=self.status)
                label.update_idletasks()

                self.prueba['Ganancia'].append(gain_actual)
                self.prueba['Frecuencias'].append(frec_actual)
                self.prueba['Potencia'].append(result["power_result"])
                self.prueba['Voltage'].append(voltage)

                if not preset:
                    preset = True

                if orden_gain == "Ascendente":
                    gain_actual += entries_to_dict['gain_step']
                elif orden_gain == 'Descendente':
                    gain_actual -= entries_to_dict['gain_step']

                medida += 1

                if gain_actual < gain_final and frec_actual == 433:
                    gain_actual = 90
                    if orden_frec == "Ascendente":
                        frec_actual += entries_to_dict['frec_step']
                    elif orden_frec == 'Descendente':
                        frec_actual -= entries_to_dict['frec_step']

                if self.stop:
                    self.stop = False
                    break
                time.sleep(1)

            while self.channel.recv_ready():
                output += self.channel.recv(1024).decode()

            self.status = "Creando excel de resultados..."
            label.config(text=self.status)
            label.update_idletasks()

            # df = pd.DataFrame(self.prueba)
            # now = dt.datetime.now()
            # formatted_now = now.strftime("%Y-%m-%d %H-%M-%S-%f")
            # df.to_excel('prueba_{}_{}_{}_{}.xlsx'.format(self.prueba['Prueba'],formatted_now,
            # serial_number, usuario), index=False)
            t1 = threading.Thread(target=self.results_to_excel, args=("serial_number", "usuario"))
            t1.start()
            # self.results_to_excel(serial_number, usuario)

            self.status = "Prueba finalizada."
            label.config(text=self.status)
            label.update_idletasks()
            # self.cerrar()

            for entry in entries:
                entry.config(state="normal")
                entry.update_idletasks()
            listen_thread.join()
            self.executing = False

        return output

    def cerrar(self, label, window):
        if not window:
            self.stop = True
            self.status = "Cerrando aplicación..."
            label.config(text=self.status)
            label.update_idletasks()
            time.sleep(2.0)
        else:
            self.stop = False
            time.sleep(2.0)
        if self.channel:
            self.channel.close()
        if self.client:
            self.client.close()

    def stop_sequence(self):
        if self.executing:
            self.stop = True

    def results_to_excel(self, serial_number, usuario):
        df = pd.DataFrame(self.prueba)

        df['Umbral inferior'] = df.apply(retrieve_low_threshold, axis=1)
        df['Umbral superior'] = df.apply(retrieve_upper_threshold, axis=1)

        now = dt.datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H-%M-%S-%f")
        # df.to_excel('prueba_{}_{}_{}_{}.xlsx'.format(self.prueba['Prueba'], formatted_now,
        # serial_number, usuario), index=False)

        with pd.ExcelWriter('prueba_{}_{}_{}_{}.xlsx'.format(df['Prueba'].loc[df.index[0]],
                                                             formatted_now,
                                                             serial_number,
                                                             usuario), engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Resultados")

            workbook = writer.book
            worksheet = writer.sheets["Resultados"]

            # worksheet["G1"] = "Fecha"
            worksheet.write('I1', 'Fecha')
            # worksheet["H1"] = formatted_now
            worksheet.write('J1', formatted_now)
            # worksheet["G2"] = "Usuario"
            worksheet.write('I2', 'Usuario')
            # worksheet["H2"] = usuario
            worksheet.write('J2', usuario)
            # worksheet["G3"] = "Numero de serie"
            worksheet.write('I3', 'Numero de serie')
            # worksheet["H3"] = serial_number
            worksheet.write('J3', serial_number)

            format1 = workbook.add_format({'bg_color': 'red'})

            for i in range(len(df)):

                potencia_cell = f'C{i+2}'
                umbral_inferior = df.loc[i, 'Umbral inferior']
                umbral_superior = df.loc[i, 'Umbral superior']

                worksheet.conditional_format(potencia_cell, {'type': 'cell',
                                                             'criteria': '<',
                                                             'value': umbral_inferior,
                                                             'format': format1})
                worksheet.conditional_format(potencia_cell, {'type': 'cell',
                                                             'criteria': '>',
                                                             'value': umbral_superior,
                                                             'format': format1})
            # workbook.close()


def retrieve_low_threshold(test_result):
    threshold = 0

    if test_result['Prueba'] == 4:
        coef = [1.64787379e-49, -7.15110565e-45, 1.38278895e-40, -1.56921975e-36,
                1.15782084e-32, -5.80731732e-29,  2.00645134e-25, -4.71037957e-22,
                7.11628673e-19, -5.81318223e-16, 3.12902131e-14, 4.03512743e-10,
                -3.27868527e-07,  6.26310085e-05, 2.67035704e-02, -1.23328799e+00]
        for i in range(15, -1, -1):
            threshold += coef[i] * test_result['Frecuencias'] ** i
        threshold -= 2

    elif test_result['Prueba'] == 5:

        if test_result['Frecuencias'] == 433:
            threshold = (1.01115725*test_result['Ganancia']-83.6506)-2.5
        if test_result['Frecuencias'] == 5800:
            threshold = (0.98222965*test_result['Ganancia']-93.2764)-2.5

    return threshold


def retrieve_upper_threshold(test_result):
    threshold = 0

    if test_result['Prueba'] == 4:

        coef = [1.64787379e-49, -7.15110565e-45, 1.38278895e-40, -1.56921975e-36,
                1.15782084e-32, -5.80731732e-29, 2.00645134e-25, -4.71037957e-22,
                7.11628673e-19, -5.81318223e-16, 3.12902131e-14, 4.03512743e-10,
                -3.27868527e-07, 6.26310085e-05, 2.67035704e-02, -1.23328799e+00]
        for i in range(15, -1, -1):
            threshold += coef[i] * test_result['Frecuencias'] ** i
        threshold += 2

    elif test_result['Prueba'] == 5:

        if test_result['Frecuencias'] == 433:
            threshold = (1.01115725*test_result['Ganancia']-83.6506)+2.5
        if test_result['Frecuencias'] == 5800:
            threshold = (0.98222965*test_result['Ganancia']-93.2764)+2.5

    return threshold


def exec_tx_nbandas(freq, gain, ibw):
    client = SSHClient()
    client.load_system_host_keys()

    client.set_missing_host_key_policy(AutoAddPolicy())
    print("Abro canal SSH.")
    client.connect("192.2.1.11", username="root", password="analog")
    print("Estoy ejecutando tx_nbandas con los siguientes parametros:\n"
          "Frecuencia central (fc): {}\n"
          "Ganancia (gain): {}\n"
          "IBW (ibw): {}".format(freq, gain, ibw))
    client.exec_command('cd /PARMS/tx_nbandas/;./tx_nbandas --freq {} --ampl {} --gain {}'.format(
        str(freq*1e6), str(gain), str(ibw)))
    client.close()
    print("Closing channel...")


def close(root_ui, ssh_client, label, window):
    ssh_client.cerrar(label, window)
    root_ui.quit()


def thread_handler(func, label, entry1, entry2):
    t1 = threading.Thread(target=func, args=(label, entry1, entry2))
    t1.start()


def advanced_options_entries(frame):

    for i, param in enumerate(params):

        label = tk.Label(frame, text=param)
        label.grid(row=i, column=0, padx=10, pady=5, sticky="e")

        string_var = tk.StringVar()

        entry = tk.Entry(frame, textvariable=string_var)
        entry.grid(row=i, column=1, padx=10, pady=5, sticky="w")

        default_label = tk.Label(frame, text=default_params[i])
        default_label.grid(row=i, column=2, padx=10, pady=5, sticky="e")

        entries.append(entry)
        string_vars.append(string_var)


if __name__ == '__main__':

    ssh = SSHClienteInteractivo("192.2.1.11", "root", password="analog")
    status = ("Estado:\n"
              "Esperando a confirmar que tenemos comunicación con el CONJUNTO ADRV y el analizador de espectros...")

    # salida = ssh.ejecutar_interactivo('cd /PARMS/tx_nbandas/;./tx_nbandas --freq {} --ampl {} --gain {}'.format(
    # str(2400*1e6), str(0.9), str(90)), duracion=1)
    # salida = ssh.ejecutar_iterativo(frec_ini=100, frec_fin=6000, step=100, duracion=4)

    root = tk.Tk()
    root.title("ADRV set Tester")
    root.geometry("600x400")

    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, expand=True)
    test_window = ttk.Frame(notebook)
    notebook.add(test_window, text="Test de validación Conjunto de ADRV")

    entry_frame = tk.Frame(test_window, bg="grey")
    entry_frame.pack(side=tk.TOP, fill="x", expand=True)

    sn_label = tk.Label(entry_frame, text="Nº Serie", anchor='w')
    sn_label.pack(side=tk.LEFT, padx=5, pady=5)
    sn_var = tk.StringVar()
    entry_SN = tk.Entry(entry_frame, textvariable=sn_var)
    entry_SN.pack(side=tk.LEFT)

    user_label = tk.Label(entry_frame, text="Usuario", anchor='w')
    user_label.pack(side=tk.LEFT, padx=5, pady=5)
    user_var = tk.StringVar()
    entry_user = tk.Entry(entry_frame, textvariable=user_var)
    entry_user.pack(side=tk.LEFT)

    button_frame = tk.Frame(test_window, bg="grey")
    button_frame.pack(side=tk.TOP, fill="both", expand=True)

    test4_button = tk.Button(button_frame, text="PRUEBA 4\nBARRIDO EN FRECUENCIA",
                             command=lambda: thread_handler(ssh.prueba4, status_label, entry_SN, entry_user),
                             height=5, width=10)
    test4_button.pack(side=tk.LEFT, fill="both", expand=True)

    test5_button = tk.Button(button_frame, text="PRUEBA 5\nBARRIDO EN GANANCIA",
                             command=lambda: thread_handler(ssh.prueba5, status_label, entry_SN, entry_user),
                             height=5, width=10)
    test5_button.pack(side=tk.LEFT, fill="both", expand=True)

    status_frame = tk.Frame(test_window)
    status_frame.pack(side=tk.BOTTOM, fill="x", expand=True)
    status_label = tk.Label(status_frame, text=status, anchor='w')
    status_label.pack(side=tk.BOTTOM, padx=5, pady=5)

    stop_button_frame = tk.Frame(test_window)
    stop_button_frame.pack(side=tk.TOP, fill="x", expand=True)
    stop_button = tk.Button(stop_button_frame, text="STOP", command=ssh.stop_sequence, height=5)
    stop_button.pack(side=tk.BOTTOM, fill="both")

    quit_button_frame = tk.Frame(test_window)
    quit_button_frame.pack(side=tk.TOP, fill="x", expand=True)
    quit_button = tk.Button(quit_button_frame, text="CERRAR APLICACION",
                            command=lambda: close(root, ssh, status_label, False), height=5)
    quit_button.pack(side=tk.BOTTOM, fill="both")

    root.protocol("WM_DELETE_WINDOW", close(root, ssh, status_label, True))

    advanced_options = ttk.Frame(notebook)
    notebook.add(advanced_options, text="Opciones avanzadas")

    advanced_options_entries(advanced_options)

    advanced_options.grid_columnconfigure(0, weight=1, uniform="equal")
    advanced_options.grid_columnconfigure(1, weight=2, uniform="equal")

    status_label_advanced = tk.Label(advanced_options, text=status, anchor='w')
    status_label_advanced.grid(row=len(params)+1, columnspan=3, column=0, padx=10, pady=5, sticky="w")

    run_test = tk.Button(advanced_options, text="RUN",
                         command=lambda: thread_handler(ssh.advanced_test, status_label_advanced, "", ""))
    run_test.grid(row=len(params), column=0, padx=10, pady=5, sticky="w")

    stop_test = tk.Button(advanced_options, text="STOP", command=ssh.stop_sequence)
    stop_test.grid(row=len(params), column=1, padx=10, pady=5, sticky="w")

    root.mainloop()
