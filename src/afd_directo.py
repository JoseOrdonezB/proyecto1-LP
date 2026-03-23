from collections import deque
from src.regex import es_simbolo


class Nodo:
    def __init__(self, valor, izquierdo=None, derecho=None, posicion=None):
        self.valor = valor
        self.izquierdo = izquierdo
        self.derecho = derecho
        self.posicion = posicion

        self.nullable = False
        self.firstpos = set()
        self.lastpos = set()


def regex_a_postfijo(regex):

    precedencia = {
        '|': 1,
        '.': 2,
        '*': 3,
        '+': 3,
        '?': 3
    }

    salida = []
    pila = []

    for c in regex:

        if es_simbolo(c) or c == 'ε' or c == '#':
            salida.append(c)

        elif c == '(':
            pila.append(c)

        elif c == ')':
            while pila and pila[-1] != '(':
                salida.append(pila.pop())
            if not pila:
                raise ValueError("Paréntesis desbalanceados")
            pila.pop()

        else:
            while pila and pila[-1] != '(' and precedencia.get(pila[-1], 0) >= precedencia.get(c, 0):
                salida.append(pila.pop())
            pila.append(c)

    while pila:
        if pila[-1] == '(':
            raise ValueError("Paréntesis desbalanceados")
        salida.append(pila.pop())

    return ''.join(salida)

def construir_arbol(postfijo):

    pila = []
    pos = 1
    simbolo_por_pos = {}

    for c in postfijo:

        if c == 'ε':
            nodo = Nodo(c)
            nodo.nullable = True
            pila.append(nodo)

        elif es_simbolo(c) or c == '#':
            nodo = Nodo(c, posicion=pos)
            pila.append(nodo)
            simbolo_por_pos[pos] = c
            pos += 1

        elif c in ['*', '+', '?']:
            if not pila:
                raise ValueError("Error en regex: operador sin operando")
            hijo = pila.pop()
            pila.append(Nodo(c, hijo))

        elif c in ['.', '|']:
            if len(pila) < 2:
                raise ValueError("Error en regex: falta operando")
            der = pila.pop()
            izq = pila.pop()
            pila.append(Nodo(c, izq, der))

    if len(pila) != 1:
        raise ValueError("Regex inválida")

    return pila.pop(), simbolo_por_pos

def calcular_propiedades(nodo, followpos):

    if nodo is None:
        return

    calcular_propiedades(nodo.izquierdo, followpos)
    calcular_propiedades(nodo.derecho, followpos)

    if nodo.posicion is not None:

        nodo.nullable = False
        nodo.firstpos = {nodo.posicion}
        nodo.lastpos = {nodo.posicion}
        return

    if nodo.valor == '|':

        nodo.nullable = nodo.izquierdo.nullable or nodo.derecho.nullable
        nodo.firstpos = nodo.izquierdo.firstpos | nodo.derecho.firstpos
        nodo.lastpos = nodo.izquierdo.lastpos | nodo.derecho.lastpos

    elif nodo.valor == '.':

        nodo.nullable = nodo.izquierdo.nullable and nodo.derecho.nullable

        if nodo.izquierdo.nullable:
            nodo.firstpos = nodo.izquierdo.firstpos | nodo.derecho.firstpos
        else:
            nodo.firstpos = nodo.izquierdo.firstpos

        if nodo.derecho.nullable:
            nodo.lastpos = nodo.izquierdo.lastpos | nodo.derecho.lastpos
        else:
            nodo.lastpos = nodo.derecho.lastpos

        for i in nodo.izquierdo.lastpos:
            followpos[i].update(nodo.derecho.firstpos)

    elif nodo.valor == '*':

        nodo.nullable = True
        nodo.firstpos = nodo.izquierdo.firstpos
        nodo.lastpos = nodo.izquierdo.lastpos

        for i in nodo.lastpos:
            followpos[i].update(nodo.firstpos)

    elif nodo.valor == '+':

        nodo.nullable = nodo.izquierdo.nullable
        nodo.firstpos = nodo.izquierdo.firstpos
        nodo.lastpos = nodo.izquierdo.lastpos

        for i in nodo.lastpos:
            followpos[i].update(nodo.firstpos)

    elif nodo.valor == '?':
        nodo.nullable = True
        nodo.firstpos = nodo.izquierdo.firstpos
        nodo.lastpos = nodo.izquierdo.lastpos


def construir_afd_directo(regex, alfabeto):

    # 🔥 AGREGAR # AUTOMÁTICAMENTE
    regex = f"({regex}).#"

    postfijo = regex_a_postfijo(regex)

    raiz, simbolo_pos = construir_arbol(postfijo)

    followpos = {i: set() for i in simbolo_pos}

    calcular_propiedades(raiz, followpos)

    # 🔥 encontrar posición de #
    pos_final = None
    for p, s in simbolo_pos.items():
        if s == '#':
            pos_final = p
            break

    if pos_final is None:
        raise ValueError("No se encontró símbolo de fin '#'")

    estado_inicial = frozenset(raiz.firstpos)

    estados = [estado_inicial]
    cola = deque([estado_inicial])

    transiciones = {}
    aceptacion = set()

    while cola:

        estado = cola.popleft()
        transiciones[estado] = {}

        if pos_final in estado:
            aceptacion.add(estado)

        for simbolo in alfabeto:

            u = set()

            for p in estado:
                if simbolo_pos[p] == simbolo:
                    u.update(followpos[p])

            if u:
                u = frozenset(u)
                transiciones[estado][simbolo] = u

                if u not in estados:
                    estados.append(u)
                    cola.append(u)

    nombres = {estado: f"S{i}" for i, estado in enumerate(estados)}

    return {
        "postfijo": postfijo,
        "followpos": followpos,
        "simbolo_pos": simbolo_pos,
        "estado_inicial": estado_inicial,
        "estados": estados,
        "transiciones": transiciones,
        "aceptacion": aceptacion,
        "nombres": nombres
    }