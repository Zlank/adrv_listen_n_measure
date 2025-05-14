import numpy as np
import matplotlib.pyplot as plt

# Datos proporcionados
frecuencias = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000,
                        2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800,
                        3900, 4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400, 5500, 5600,
                        5700, 5800, 5900, 6000])

potencia = np.array([1.898138, 4.134663, 7.014313, 8.076028, 7.590801, 7.498612, 7.74281, 6.780979, 7.615199, 7.627787, 6.867665,
                     6.788922, 6.54277, 5.56542, 6.061428, 6.485725, 5.550255, 5.104291, 4.327911, 5.923291, 3.987109, 4.072296,
                     4.586446, 4.662449, 4.587702, 4.698763, 4.884107, 4.93048, 3.552698, 3.161169, 3.556376, 3.633381, 4.162486,
                     4.589858, 2.485558, 2.62718, 4.684071, 4.334551, 4.131106, 4.303038, 2.596086, 2.428624, 3.3514, 2.483991,
                     1.930336, 2.430294, 3.459064, 1.249839, 1.383866, 3.114718, 2.382377, 1.418405, -0.1989645, -0.2249452, -1.208909,
                     -1.69348, -1.96627, -1.862275, -2.754931, -3.757201])

# Ajuste polinómico de grado 3 (puedes cambiar el grado del polinomio)
grado = 15
coeficientes = np.polyfit(frecuencias, potencia, grado)

# Crear una función polinómica a partir de los coeficientes obtenidos
polinomio = np.poly1d(coeficientes)

# Crear puntos de frecuencia para graficar el ajuste
frecuencias_ajuste = np.linspace(100, 6000, 100)
potencia_ajuste = polinomio(frecuencias_ajuste)

# Graficar los datos originales y el ajuste polinómico
plt.figure(figsize=(10, 6))
plt.plot(frecuencias, potencia, 'o', label='Datos originales')
plt.plot(frecuencias_ajuste, potencia_ajuste, '-', label='Ajuste polinómico (grado {})'.format(grado), color='red')
plt.xlabel('Frecuencia (Hz)')
plt.ylabel('Potencia')
plt.title('Ajuste Polinómico de Potencia en función de la Frecuencia')
plt.legend()
plt.grid(True)
plt.show()

# Mostrar los coeficientes del polinomio
print("Coeficientes del polinomio ajustado:", coeficientes)