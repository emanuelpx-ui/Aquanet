"""
app/simulador/models.py
Grafo hídrico G(V,E,W) con NetworkX.
"""
import networkx as nx
from app.database import query_all, execute_returning


def construir_grafo() -> nx.DiGraph:
    """
    Construye el grafo dirigido desde la BD.
    Nodos = nodos_red, Aristas = aristas_red activas.
    """
    G = nx.DiGraph()

    nodos = query_all("""
        SELECT id, nombre, tipo, latitud, longitud,
               capacidad, demanda, id_zona
        FROM nodos_red WHERE activo = TRUE
    """)
    for n in nodos:
        G.add_node(n["id"], **dict(n))

    aristas = query_all("""
        SELECT id, id_nodo_origen, id_nodo_destino, capacidad
        FROM aristas_red WHERE estado = 'activa'
    """)
    for a in aristas:
        G.add_edge(
            a["id_nodo_origen"],
            a["id_nodo_destino"],
            id=a["id"],
            capacidad=float(a["capacidad"] or 0)
        )

    return G


def simular_falla_nodo(nodo_id: int) -> dict:
    """
    Simula la falla de un nodo y calcula qué nodos
    pierden conectividad con los depósitos.
    """
    G = construir_grafo()

    if nodo_id not in G:
        return {"error": "Nodo no encontrado en el grafo."}

    # Nodos depósito (fuentes de agua)
    depositos = [
        n for n, d in G.nodes(data=True)
        if d.get("tipo") == "deposito"
    ]

    # Nodos alcanzables antes de la falla
    alcanzables_antes = set()
    for dep in depositos:
        alcanzables_antes |= nx.descendants(G, dep)
    alcanzables_antes |= set(depositos)

    # Remover el nodo fallido
    G_falla = G.copy()
    G_falla.remove_node(nodo_id)

    # Nodos alcanzables después de la falla
    alcanzables_despues = set()
    for dep in depositos:
        if dep in G_falla:
            alcanzables_despues |= nx.descendants(G_falla, dep)
    alcanzables_despues |= set(depositos)

    # Nodos afectados = los que perdieron conectividad
    afectados_ids = alcanzables_antes - alcanzables_despues - {nodo_id}

    afectados = []
    for nid in afectados_ids:
        datos = G.nodes[nid]
        # Buscar rutas alternativas
        rutas_alt = []
        for dep in depositos:
            if dep in G_falla and nid in G_falla:
                try:
                    ruta = nx.shortest_path(G_falla, dep, nid)
                    rutas_alt.append(ruta)
                    break
                except nx.NetworkXNoPath:
                    pass

        afectados.append({
            "id_nodo":            nid,
            "nombre":             datos.get("nombre", ""),
            "tipo":               datos.get("tipo", ""),
            "impacto":            "sin_servicio" if not rutas_alt else "servicio_reducido",
            "rutas_alternativas": rutas_alt,
        })

    return {
        "nodo_falla":       nodo_id,
        "total_afectados":  len(afectados),
        "nodos_afectados":  afectados,
    }


def simular_falla_arista(arista_id: int) -> dict:
    """
    Simula la falla de una tubería (arista).
    """
    G = construir_grafo()

    # Buscar la arista por su ID de BD
    arista_data = None
    for u, v, d in G.edges(data=True):
        if d.get("id") == arista_id:
            arista_data = (u, v)
            break

    if not arista_data:
        return {"error": "Tubería no encontrada en el grafo."}

    depositos = [
        n for n, d in G.nodes(data=True)
        if d.get("tipo") == "deposito"
    ]

    alcanzables_antes = set()
    for dep in depositos:
        alcanzables_antes |= nx.descendants(G, dep)

    G_falla = G.copy()
    G_falla.remove_edge(*arista_data)

    alcanzables_despues = set()
    for dep in depositos:
        if dep in G_falla:
            alcanzables_despues |= nx.descendants(G_falla, dep)

    afectados_ids = alcanzables_antes - alcanzables_despues

    afectados = []
    for nid in afectados_ids:
        datos = G.nodes[nid]
        afectados.append({
            "id_nodo": nid,
            "nombre":  datos.get("nombre", ""),
            "tipo":    datos.get("tipo", ""),
            "impacto": "sin_servicio",
        })

    return {
        "arista_falla":     arista_id,
        "origen":           arista_data[0],
        "destino":          arista_data[1],
        "total_afectados":  len(afectados),
        "nodos_afectados":  afectados,
    }


def guardar_simulacion(resultado: dict, ejecutada_por: int) -> dict:
    """Persiste el resultado en la tabla simulaciones."""
    import json
    return execute_returning("""
        INSERT INTO simulaciones
            (id_nodo_falla, id_arista_falla, nodos_afectados,
             resultado_resumen, ejecutada_por)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (
        resultado.get("nodo_falla"),
        resultado.get("arista_falla"),
        json.dumps(resultado.get("nodos_afectados", [])),
        f"{resultado.get('total_afectados', 0)} nodos afectados",
        ejecutada_por
    ))