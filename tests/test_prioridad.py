"""
tests/test_prioridad.py
Pruebas unitarias para el motor de priorización multicriterio (IP).
"""
import unittest
from app.prioridad.services import calcular_ip


class TestMotorPrioridad(unittest.TestCase):

    def test_ip_minimo(self):
        """Reporte con todos los factores en cero debe dar IP = 0.0."""
        reporte = {
            "tipo_gravedad": 0,
            "zona_poblacion": 0,
            "horas_sin_atencion": 0,
            "recurrencia": 0
        }
        ip = calcular_ip(reporte)
        self.assertEqual(ip, 0.0)

    def test_ip_maximo_saturado(self):
        """Reporte con valores máximos debe dar IP = 100.0 sin excederlo."""
        reporte = {
            "tipo_gravedad": 10.0,
            "zona_poblacion": 25000,      # > 10000 (satura a 10)
            "horas_sin_atencion": 200,    # > 168 (satura a 10)
            "recurrencia": 15             # > 10 (satura a 10)
        }
        ip = calcular_ip(reporte)
        self.assertEqual(ip, 100.0)

    def test_ip_acotamiento_recurrencia(self):
        """Valores extremos de recurrencia no deben superar el 100 de IP."""
        reporte = {
            "tipo_gravedad": 10.0,
            "zona_poblacion": 10000,
            "horas_sin_atencion": 168,
            "recurrencia": 500  # Valor desproporcionado
        }
        ip = calcular_ip(reporte)
        self.assertLessEqual(ip, 100.0)
        self.assertEqual(ip, 100.0)

    def test_ip_caso_tipico_fuga_maestra(self):
        """Caso típico: Fuga en tubería maestra en zona poblada con 12h de espera."""
        reporte = {
            "tipo_gravedad": 10.0,        # G = 10
            "zona_poblacion": 8000,       # D = 8.0
            "horas_sin_atencion": 12,     # T ~ 4.99
            "recurrencia": 2              # R = 2.0
        }
        ip = calcular_ip(reporte)
        # IP = 10 * ((10 * 0.35) + (8 * 0.25) + (4.99 * 0.25) + (2 * 0.15))
        #    = 10 * (3.5 + 2.0 + 1.25 + 0.3) = 70.5 aprox
        self.assertGreater(ip, 65.0)
        self.assertLess(ip, 85.0)

    def test_clasificacion_urgencia(self):
        """Comprobar los rangos de urgencia establecidos en el diseño."""
        def clasificar(ip):
            if ip >= 80:
                return "critica"
            elif ip >= 60:
                return "alta"
            elif ip >= 40:
                return "media"
            return "baja"

        self.assertEqual(clasificar(85.0), "critica")
        self.assertEqual(clasificar(70.0), "alta")
        self.assertEqual(clasificar(45.0), "media")
        self.assertEqual(clasificar(20.0), "baja")


if __name__ == "__main__":
    unittest.main()
