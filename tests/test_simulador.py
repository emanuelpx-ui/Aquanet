"""
tests/test_simulador.py
Pruebas unitarias para la lógica topológica del simulador de red hídrica.
"""
import unittest
import networkx as nx


class TestSimuladorRed(unittest.TestCase):

    def setUp(self):
        """
        Crea un grafo sintético de distribución hídrica:
        Depósito (1) -> Nodo Distribución (2) -> Colonias (3 y 4)
        """
        self.G = nx.DiGraph()
        self.G.add_node(1, nombre="Depósito Principal", tipo="deposito")
        self.G.add_node(2, nombre="Tanque Regulador", tipo="distribucion")
        self.G.add_node(3, nombre="Colonia Centro", tipo="colonia")
        self.G.add_node(4, nombre="Colonia Sur", tipo="colonia")

        self.G.add_edge(1, 2, id=101, capacidad=5000)
        self.G.add_edge(2, 3, id=102, capacidad=2500)
        self.G.add_edge(2, 4, id=103, capacidad=2500)

    def test_alcance_inicial(self):
        """Todos los nodos deben ser alcanzables desde el depósito inicialmente."""
        alcanzables = nx.descendants(self.G, 1) | {1}
        self.assertEqual(alcanzables, {1, 2, 3, 4})

    def test_corte_nodo_intermedio(self):
        """La falla del nodo de distribución (2) debe dejar sin servicio a las colonias 3 y 4."""
        g_falla = self.G.copy()
        g_falla.remove_node(2)

        alcanzables_despues = nx.descendants(g_falla, 1) | {1}
        afectados = (nx.descendants(self.G, 1) | {1}) - alcanzables_despues - {2}

        self.assertEqual(afectados, {3, 4})

    def test_corte_arista(self):
        """La falla de la tubería 2 -> 3 solo debe afectar a la colonia 3."""
        g_falla = self.G.copy()
        g_falla.remove_edge(2, 3)

        alcanzables_despues = nx.descendants(g_falla, 1) | {1}
        afectados = (nx.descendants(self.G, 1) | {1}) - alcanzables_despues

        self.assertEqual(afectados, {3})


if __name__ == "__main__":
    unittest.main()
