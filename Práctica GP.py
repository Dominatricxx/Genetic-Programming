import numpy as np
import pandas as pd

# =========================
# 🌳 Definición del Nodo
# =========================
class Nodo:
    def __init__(self, valor, hijos=None):
        self.valor = valor
        self.hijos = hijos if hijos is not None else []

    def es_hoja(self):
        return len(self.hijos) == 0


# =========================
# ⚙️ Funciones disponibles
# =========================
FUNCIONES = {
    '+': 2, '-': 2, '*': 2, '/': 2,
    'sin': 1, 'cos': 1, 'exp': 1, 'log': 1
}


# =========================
# 🌱 Generación de árboles
# =========================
def generar_terminal(num_variables):
    if np.random.rand() < 0.5:
        return Nodo(('var', np.random.randint(0, num_variables)))
    else:
        return Nodo(('const', np.random.uniform(-5, 5)))


def generar_arbol_full(profundidad, num_variables):
    if profundidad == 0:
        return generar_terminal(num_variables)

    func = np.random.choice(list(FUNCIONES.keys()))
    aridad = FUNCIONES[func]
    hijos = [generar_arbol_full(profundidad - 1, num_variables) for _ in range(aridad)]
    return Nodo(func, hijos)


def generar_arbol_grow(profundidad, num_variables):
    if profundidad == 0 or np.random.rand() > 0.5:
        return generar_terminal(num_variables)

    func = np.random.choice(list(FUNCIONES.keys()))
    aridad = FUNCIONES[func]
    hijos = [generar_arbol_grow(profundidad - 1, num_variables) for _ in range(aridad)]
    return Nodo(func, hijos)


def inicializar_poblacion(size, profundidad_max, num_variables):
    poblacion = []

    for d in range(1, profundidad_max + 1):
        for _ in range(size // (2 * profundidad_max)):
            poblacion.append(generar_arbol_full(d, num_variables))
            poblacion.append(generar_arbol_grow(d, num_variables))

    while len(poblacion) < size:
        poblacion.append(generar_arbol_grow(profundidad_max, num_variables))

    return poblacion


# =========================
# 🧮 Evaluación protegida
# =========================
def evaluar(nodo, X):
    if nodo.es_hoja():
        tipo, valor = nodo.valor
        if tipo == 'var':
            return X[:, valor]
        else:
            return np.full(X.shape[0], valor)

    hijos_eval = [evaluar(h, X) for h in nodo.hijos]

    try:
        if nodo.valor == '+':
            return hijos_eval[0] + hijos_eval[1]

        elif nodo.valor == '-':
            return hijos_eval[0] - hijos_eval[1]

        elif nodo.valor == '*':
            return hijos_eval[0] * hijos_eval[1]

        elif nodo.valor == '/':
            denom = np.where(np.abs(hijos_eval[1]) < 1e-10, 1.0, hijos_eval[1])
            return hijos_eval[0] / denom

        elif nodo.valor == 'sin':
            return np.sin(hijos_eval[0])

        elif nodo.valor == 'cos':
            return np.cos(hijos_eval[0])

        elif nodo.valor == 'exp':
            return np.exp(np.clip(hijos_eval[0], -20, 20))

        elif nodo.valor == 'log':
            val = np.where(hijos_eval[0] <= 0, np.abs(hijos_eval[0]) + 1e-10, hijos_eval[0])
            return np.log(val)

    except:
        return np.full(X.shape[0], 1.0)


# =========================
# 📊 Fitness
# =========================
def fitness(individuo, X, y):
    y_pred = evaluar(individuo, X)
    y_pred = np.nan_to_num(y_pred, nan=1.0, posinf=1.0, neginf=1.0)
    return np.mean((y - y_pred) ** 2)


# =========================
# 🔁 Utilidades
# =========================
def copiar_arbol(nodo):
    return Nodo(nodo.valor, [copiar_arbol(h) for h in nodo.hijos])


def obtener_nodos(nodo):
    nodos = [nodo]
    for h in nodo.hijos:
        nodos.extend(obtener_nodos(h))
    return nodos


# =========================
# 🎯 Selección
# =========================
def seleccion_torneo(poblacion, fitness_vals, k=7):
    idx = np.random.choice(len(poblacion), k, replace=False)
    mejor = idx[0]
    for i in idx:
        if fitness_vals[i] < fitness_vals[mejor]:
            mejor = i
    return poblacion[mejor]


# =========================
# 🔀 Crossover
# =========================
def crossover(padre1, padre2):
    hijo = copiar_arbol(padre1)
    n1 = np.random.choice(obtener_nodos(hijo))
    n2 = np.random.choice(obtener_nodos(padre2))

    n1.valor = n2.valor
    n1.hijos = [copiar_arbol(h) for h in n2.hijos]

    return hijo


# =========================
# 🔧 Mutación
# =========================
def mutacion_punto(nodo):
    if nodo.valor in FUNCIONES:
        aridad = FUNCIONES[nodo.valor]
        candidatos = [f for f in FUNCIONES if FUNCIONES[f] == aridad]
        nodo.valor = np.random.choice(candidatos)
    return nodo


def mutacion_subarbol(nodo, num_variables):
    nuevo = generar_arbol_grow(2, num_variables)
    nodo.valor = nuevo.valor
    nodo.hijos = nuevo.hijos
    return nodo


def mutar(nodo, num_variables, p_punto=0.1, p_subarbol=0.1):
    if np.random.rand() < p_subarbol:
        return mutacion_subarbol(nodo, num_variables)

    if np.random.rand() < p_punto:
        return mutacion_punto(nodo)

    if not nodo.es_hoja():
        nodo.hijos = [mutar(h, num_variables, p_punto, p_subarbol) for h in nodo.hijos]

    return nodo


# =========================
# 🚀 Evolución
# =========================
def evolucionar(X, y, generaciones=50, poblacion_size=100, profundidad_max=4):
    num_variables = X.shape[1]
    poblacion = inicializar_poblacion(poblacion_size, profundidad_max, num_variables)

    mejor_global = None
    mejor_fitness = float('inf')

    for gen in range(generaciones):
        fitness_vals = np.array([fitness(ind, X, y) for ind in poblacion])

        idx = np.argmin(fitness_vals)
        if fitness_vals[idx] < mejor_fitness:
            mejor_fitness = fitness_vals[idx]
            mejor_global = copiar_arbol(poblacion[idx])

        print(f"Gen {gen} | Mejor MSE: {mejor_fitness}")

        nueva = [copiar_arbol(mejor_global)]  # elitismo

        while len(nueva) < poblacion_size:
            p1 = seleccion_torneo(poblacion, fitness_vals)
            p2 = seleccion_torneo(poblacion, fitness_vals)

            hijo = crossover(p1, p2)
            hijo = mutar(hijo, num_variables)

            nueva.append(hijo)

        poblacion = nueva

    return mejor_global


# =========================
# 📂 Dataset externo
# =========================
def cargar_dataset():
    path = input("Ruta del CSV: ")
    target = input("Nombre de la columna objetivo: ")

    df = pd.read_csv(path)
    X = df.drop(columns=[target]).values
    y = df[target].values

    return X, y


# =========================
# 🎲 Dataset sintético
# =========================
def generar_dataset_sintetico(n=200):
    print("\nFunciones disponibles:")
    print("1: x^2 + x")
    print("2: sin(x) + x")
    print("3: x^3 - x")

    opcion = input("Elige función: ")

    X = np.random.uniform(-5, 5, (n, 1))
    x = X[:, 0]

    if opcion == "1":
        y = x**2 + x
    elif opcion == "2":
        y = np.sin(x) + x
    else:
        y = x**3 - x

    # ruido
    y += np.random.normal(0, 0.1, size=n)

    return X, y


# =========================
# 🧭 MENÚ PRINCIPAL
# =========================
def main():
    print("\n=== PROGRAMACIÓN GENÉTICA ===")
    print("1. Cargar dataset")
    print("2. Generar dataset sintético")

    opcion = input("Selecciona opción: ")

    if opcion == "1":
        X, y = cargar_dataset()
    else:
        X, y = generar_dataset_sintetico()

    mejor = evolucionar(X, y)

    print("\nMejor individuo encontrado:")
    print(mejor.valor)


# =========================
# ▶️ Ejecutar
# =========================
if __name__ == "__main__":
    main()