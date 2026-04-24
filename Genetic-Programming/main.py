import numpy as np
import pandas as pd
import copy
import time
import os
import json
from typing import Optional, List, Union, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots

CONFIGURACION_ALGORITMO = {
    "tamano_poblacion": 200,
    "generaciones": 20,
    "probabilidad_cruce": 0.9,
    "probabilidad_mutacion_subarbol": 0.1,
    "probabilidad_mutacion_punto": 0.05,
    "tamano_torneo": 7,
    "profundidad_maxima_inicial": 4,
    "profundidad_maxima_evolucion": 7,
    "funciones_matematicas": ["+", "-", "*", "/", "sin", "cos", "log"],
    "funciones_binarias": ["+", "-", "*", "/"],
    "funciones_unarias": ["sin", "cos", "log"],
    "elitismo": True,
    "semilla_aleatoria": 42,
}

CONFIGURACIONES_CONJUNTOS_DE_DATOS = {
    "concrete": {
        "enlace_descarga": "https://archive.ics.uci.edu/ml/machine-learning-databases/concrete/compressive/Concrete_Data.xls",
        "columna_objetivo": -1,
        "separador": None,
        "cabecera": 0,
        "tipo_archivo": "excel",
    },

    "yacht": {
        "enlace_descarga": "https://archive.ics.uci.edu/ml/machine-learning-databases/00243/yacht_hydrodynamics.data",
        "columna_objetivo": -1,
        "separador": r"\s+",
        "cabecera": None,
        "tipo_archivo": "csv",
    },
    "housing": {
        "enlace_descarga": "https://archive.ics.uci.edu/ml/machine-learning-databases/housing/housing.data",
        "columna_objetivo": -1,
        "separador": r"\s+",
        "cabecera": None,
        "tipo_archivo": "csv",
    },
    "energy_cooling": {
        "enlace_descarga": "https://archive.ics.uci.edu/ml/machine-learning-databases/00242/ENB2012_data.xlsx",
        "columna_objetivo": -1,   
        "separador": None,
        "cabecera": 0,
        "tipo_archivo": "excel",
        "columnas_a_usar": list(range(9)),   
        "forzar_columna_objetivo": 9,
    },
    "energy_heating": {
        "enlace_descarga": "https://archive.ics.uci.edu/ml/machine-learning-databases/00242/ENB2012_data.xlsx",
        "columna_objetivo": -2,   
        "separador": None,
        "cabecera": 0,
        "tipo_archivo": "excel",
        "columnas_a_usar": list(range(9)),
        "forzar_columna_objetivo": 8,

    }
}

class NodoArbolMatematico:
    __slots__ = ("valor_almacenado", "hijo_izquierdo", "hijo_derecho")

    def __init__(self, valor_almacenado, hijo_izquierdo=None, hijo_derecho=None):
        self.valor_almacenado = valor_almacenado
        self.hijo_izquierdo = hijo_izquierdo
        self.hijo_derecho = hijo_derecho

    def esNodoHojaSinHijos(self) -> bool:
        return self.hijo_izquierdo is None and self.hijo_derecho is None

    def esOperadorMatematicoBinario(self) -> bool:
        return self.valor_almacenado in CONFIGURACION_ALGORITMO["funciones_binarias"]

    def esOperadorMatematicoUnario(self) -> bool:
        return self.valor_almacenado in CONFIGURACION_ALGORITMO["funciones_unarias"]

    def calcularProfundidadMaxima(self) -> int:
        if self.esNodoHojaSinHijos():
            return 0
        profundidades_hijos = []
        if self.hijo_izquierdo:
            profundidades_hijos.append(self.hijo_izquierdo.calcularProfundidadMaxima())
        if self.hijo_derecho:
            profundidades_hijos.append(self.hijo_derecho.calcularProfundidadMaxima())
        return 1 + max(profundidades_hijos)

    def contarNodosTotales(self) -> int:
        numero_nodos = 1
        if self.hijo_izquierdo:
            numero_nodos += self.hijo_izquierdo.contarNodosTotales()
        if self.hijo_derecho:
            numero_nodos += self.hijo_derecho.contarNodosTotales()
        return numero_nodos

    def convertirADiccionario(self) -> dict:
        diccionario = {"name": str(self.valor_almacenado)}
        hijos = []
        if self.hijo_izquierdo:
            hijos.append(self.hijo_izquierdo.convertirADiccionario())
        if self.hijo_derecho:
            hijos.append(self.hijo_derecho.convertirADiccionario())
        if hijos:
            diccionario["children"] = hijos
        return diccionario

    def __repr__(self) -> str:
        if self.esNodoHojaSinHijos():
            return str(self.valor_almacenado)
        if self.esOperadorMatematicoUnario():
            return f"{self.valor_almacenado}({self.hijo_izquierdo})"
        return f"({self.hijo_izquierdo} {self.valor_almacenado} {self.hijo_derecho})"

def evaluarEcuacionMatematica(nodo_actual: NodoArbolMatematico, matriz_datos_entrada: np.ndarray) -> np.ndarray:
    valor_nodo = nodo_actual.valor_almacenado

    if isinstance(valor_nodo, str) and valor_nodo.startswith("x_"):
        indice_variable = int(valor_nodo.split("_")[1])
        return matriz_datos_entrada[:, indice_variable].astype(float)

    if isinstance(valor_nodo, (int, float, np.floating)):
        return np.full(matriz_datos_entrada.shape[0], float(valor_nodo))

    resultado_izquierdo = evaluarEcuacionMatematica(nodo_actual.hijo_izquierdo, matriz_datos_entrada)
    if nodo_actual.esOperadorMatematicoBinario():
        resultado_derecho = evaluarEcuacionMatematica(nodo_actual.hijo_derecho, matriz_datos_entrada)

        if valor_nodo == "+":
            return resultado_izquierdo + resultado_derecho
        if valor_nodo == "-":
            return resultado_izquierdo - resultado_derecho
        if valor_nodo == "*":
            return resultado_izquierdo * resultado_derecho
        if valor_nodo == "/":
            denominador_seguro = np.where(np.abs(resultado_derecho) < 1e-10, 1.0, resultado_derecho)
            return resultado_izquierdo / denominador_seguro

    if valor_nodo == "sin":
        return np.sin(resultado_izquierdo)
    if valor_nodo == "cos":
        return np.cos(resultado_izquierdo)
    if valor_nodo == "log":
        valor_seguro_logaritmo = np.maximum(np.abs(resultado_izquierdo), 1e-10)
        return np.log(valor_seguro_logaritmo)
    if valor_nodo == "exp":
        valor_recortado = np.clip(resultado_izquierdo, -500, 500)
        return np.exp(valor_recortado)
    if valor_nodo == "sqrt":
        return np.sqrt(np.abs(resultado_izquierdo))

    raise ValueError(f"Operador matematico desconocido: {valor_nodo}")

def generarNodoTerminalAleatorio(cantidad_variables: int, generador_aleatorio: np.random.Generator) -> NodoArbolMatematico:
    if generador_aleatorio.random() < 0.5:
        indice_variable = int(generador_aleatorio.integers(0, cantidad_variables))
        return NodoArbolMatematico(f"x_{indice_variable}")
    else:
        constante_numerica = float(generador_aleatorio.uniform(-1, 1))
        return NodoArbolMatematico(constante_numerica)


def generarArbolPorMetodoCompleto(profundidad_actual: int, cantidad_variables: int, generador_aleatorio: np.random.Generator) -> NodoArbolMatematico:
    if profundidad_actual == 0:
        return generarNodoTerminalAleatorio(cantidad_variables, generador_aleatorio)

    funcion_elegida = generador_aleatorio.choice(CONFIGURACION_ALGORITMO["funciones_matematicas"])
    if funcion_elegida in CONFIGURACION_ALGORITMO["funciones_binarias"]:
        rama_izquierda = generarArbolPorMetodoCompleto(profundidad_actual - 1, cantidad_variables, generador_aleatorio)
        rama_derecha = generarArbolPorMetodoCompleto(profundidad_actual - 1, cantidad_variables, generador_aleatorio)
        return NodoArbolMatematico(funcion_elegida, rama_izquierda, rama_derecha)
    else:
        rama_izquierda = generarArbolPorMetodoCompleto(profundidad_actual - 1, cantidad_variables, generador_aleatorio)
        return NodoArbolMatematico(funcion_elegida, rama_izquierda)


def generarArbolPorMetodoCrecimiento(profundidad_actual: int, cantidad_variables: int, generador_aleatorio: np.random.Generator) -> NodoArbolMatematico:
    if profundidad_actual == 0:
        return generarNodoTerminalAleatorio(cantidad_variables, generador_aleatorio)

    cantidad_terminales = cantidad_variables + 1  
    cantidad_total_opciones = len(CONFIGURACION_ALGORITMO["funciones_matematicas"]) + cantidad_terminales
    probabilidad_elegir_terminal = cantidad_terminales / cantidad_total_opciones

    if generador_aleatorio.random() < probabilidad_elegir_terminal:
        return generarNodoTerminalAleatorio(cantidad_variables, generador_aleatorio)

    funcion_elegida = generador_aleatorio.choice(CONFIGURACION_ALGORITMO["funciones_matematicas"])
    if funcion_elegida in CONFIGURACION_ALGORITMO["funciones_binarias"]:
        rama_izquierda = generarArbolPorMetodoCrecimiento(profundidad_actual - 1, cantidad_variables, generador_aleatorio)
        rama_derecha = generarArbolPorMetodoCrecimiento(profundidad_actual - 1, cantidad_variables, generador_aleatorio)
        return NodoArbolMatematico(funcion_elegida, rama_izquierda, rama_derecha)
    else:
        rama_izquierda = generarArbolPorMetodoCrecimiento(profundidad_actual - 1, cantidad_variables, generador_aleatorio)
        return NodoArbolMatematico(funcion_elegida, rama_izquierda)


def generarPoblacionInicialMitadYMitad(cantidad_individuos: int, profundidad_maxima: int, cantidad_variables: int,
                          generador_aleatorio: np.random.Generator) -> List[NodoArbolMatematico]:
    poblacion_generada = []
    niveles_profundidad = list(range(2, profundidad_maxima + 1))
    individuos_por_nivel = max(1, cantidad_individuos // (2 * len(niveles_profundidad)))

    for nivel in niveles_profundidad:
        for _ in range(individuos_por_nivel):
            poblacion_generada.append(generarArbolPorMetodoCompleto(nivel, cantidad_variables, generador_aleatorio))
        for _ in range(individuos_por_nivel):
            poblacion_generada.append(generarArbolPorMetodoCrecimiento(nivel, cantidad_variables, generador_aleatorio))

    while len(poblacion_generada) < cantidad_individuos:
        nivel_aleatorio = int(generador_aleatorio.integers(2, profundidad_maxima + 1))
        if generador_aleatorio.random() < 0.5:
            poblacion_generada.append(generarArbolPorMetodoCompleto(nivel_aleatorio, cantidad_variables, generador_aleatorio))
        else:
            poblacion_generada.append(generarArbolPorMetodoCrecimiento(nivel_aleatorio, cantidad_variables, generador_aleatorio))

    return poblacion_generada[:cantidad_individuos]


def calcularErrorCuadraticoMedio(arbol_evaluado: NodoArbolMatematico, matriz_datos_entrada: np.ndarray, vector_respuestas_reales: np.ndarray) -> float:
    try:
        prediccion_obtenida = evaluarEcuacionMatematica(arbol_evaluado, matriz_datos_entrada)
        
        prediccion_obtenida = np.where(np.isfinite(prediccion_obtenida), prediccion_obtenida, 1e6)
        error_cuadratico_medio = float(np.mean((prediccion_obtenida - vector_respuestas_reales) ** 2))
        if not np.isfinite(error_cuadratico_medio):
            return 1e18
        return error_cuadratico_medio
    except Exception:
        return 1e18


def seleccionarIndividuoPorTorneo(poblacion_actual: List[NodoArbolMatematico], lista_errores_aptitud: List[float],
           cantidad_competidores: int, generador_aleatorio: np.random.Generator) -> NodoArbolMatematico:
    indices_elegidos_azar = generador_aleatorio.choice(len(poblacion_actual), size=cantidad_competidores, replace=False)
    indice_del_ganador = indices_elegidos_azar[np.argmin([lista_errores_aptitud[i] for i in indices_elegidos_azar])]
    return copy.deepcopy(poblacion_actual[indice_del_ganador])


def obtenerTodosLosNodosDelArbol(arbol_raiz: NodoArbolMatematico) -> List[NodoArbolMatematico]:
    lista_de_nodos_encontrados = []
    pila_recorrido = [arbol_raiz]
    while pila_recorrido:
        nodo_extraido = pila_recorrido.pop()
        lista_de_nodos_encontrados.append(nodo_extraido)
        if nodo_extraido.hijo_izquierdo:
            pila_recorrido.append(nodo_extraido.hijo_izquierdo)
        if nodo_extraido.hijo_derecho:
            pila_recorrido.append(nodo_extraido.hijo_derecho)
    return lista_de_nodos_encontrados


def seleccionarUnNodoAlAzar(arbol_raiz: NodoArbolMatematico, generador_aleatorio: np.random.Generator):
    nodos_con_referencia_al_padre = []  

    def recorrer_arbol_y_guardar_referencias(nodo_actual, nodo_padre, lado_del_padre):
        nodos_con_referencia_al_padre.append((nodo_padre, lado_del_padre, nodo_actual))
        if nodo_actual.hijo_izquierdo:
            recorrer_arbol_y_guardar_referencias(nodo_actual.hijo_izquierdo, nodo_actual, "hijo_izquierdo")
        if nodo_actual.hijo_derecho:
            recorrer_arbol_y_guardar_referencias(nodo_actual.hijo_derecho, nodo_actual, "hijo_derecho")

    recorrer_arbol_y_guardar_referencias(arbol_raiz, None, None)
    indice_aleatorio = int(generador_aleatorio.integers(0, len(nodos_con_referencia_al_padre)))
    return nodos_con_referencia_al_padre[indice_aleatorio]


def cruzarDosArbolesGeneticamente(padre_receptor: NodoArbolMatematico, padre_donante: NodoArbolMatematico, generador_aleatorio: np.random.Generator,
          profundidad_maxima_permitida: int) -> NodoArbolMatematico:
    hijo_creado = copy.deepcopy(padre_receptor)
    donante_copiado = copy.deepcopy(padre_donante)

    padre_en_hijo, lado_en_hijo, nodo_reemplazado = seleccionarUnNodoAlAzar(hijo_creado, generador_aleatorio)
    _, _, nodo_que_se_inyecta = seleccionarUnNodoAlAzar(donante_copiado, generador_aleatorio)

    if padre_en_hijo is None:
        resultado_cruzamiento = nodo_que_se_inyecta
    else:
        setattr(padre_en_hijo, lado_en_hijo, nodo_que_se_inyecta)
        resultado_cruzamiento = hijo_creado

    if resultado_cruzamiento.calcularProfundidadMaxima() > profundidad_maxima_permitida:
        return copy.deepcopy(padre_receptor)  
    return resultado_cruzamiento


def mutarOperadorMatematicoUnico(arbol_original: NodoArbolMatematico, generador_aleatorio: np.random.Generator) -> NodoArbolMatematico:
    hijo_mutado = copy.deepcopy(arbol_original)
    todos_los_nodos = obtenerTodosLosNodosDelArbol(hijo_mutado)
    nodos_que_son_operadores = [nodo for nodo in todos_los_nodos if not nodo.esNodoHojaSinHijos()]

    if not nodos_que_son_operadores:
        return hijo_mutado

    nodo_seleccionado_para_mutar = nodos_que_son_operadores[int(generador_aleatorio.integers(0, len(nodos_que_son_operadores)))]

    if nodo_seleccionado_para_mutar.esOperadorMatematicoBinario():
        operadores_alternativos = [op for op in CONFIGURACION_ALGORITMO["funciones_binarias"] if op != nodo_seleccionado_para_mutar.valor_almacenado]
    else:
        operadores_alternativos = [op for op in CONFIGURACION_ALGORITMO["funciones_unarias"] if op != nodo_seleccionado_para_mutar.valor_almacenado]

    if operadores_alternativos:
        nodo_seleccionado_para_mutar.valor_almacenado = str(generador_aleatorio.choice(operadores_alternativos))

    return hijo_mutado


def mutarSubarbolCompleto(arbol_original: NodoArbolMatematico, cantidad_variables: int, generador_aleatorio: np.random.Generator,
                       profundidad_maxima_permitida: int) -> NodoArbolMatematico:
    hijo_mutado = copy.deepcopy(arbol_original)
    padre_del_nodo, lado_del_nodo, _ = seleccionarUnNodoAlAzar(hijo_mutado, generador_aleatorio)

    profundidad_del_nuevo_subarbol = int(generador_aleatorio.integers(1, 4))
    if generador_aleatorio.random() < 0.5:
        nuevo_subarbol_generado = generarArbolPorMetodoCompleto(profundidad_del_nuevo_subarbol, cantidad_variables, generador_aleatorio)
    else:
        nuevo_subarbol_generado = generarArbolPorMetodoCrecimiento(profundidad_del_nuevo_subarbol, cantidad_variables, generador_aleatorio)

    if padre_del_nodo is None:
        resultado_mutacion = nuevo_subarbol_generado
    else:
        setattr(padre_del_nodo, lado_del_nodo, nuevo_subarbol_generado)
        resultado_mutacion = hijo_mutado

    if resultado_mutacion.calcularProfundidadMaxima() > profundidad_maxima_permitida:
        return arbol_original
    return resultado_mutacion
def simplificar_expresion(arbol):
    """Simplifica la expresión eliminando operaciones redundantes"""
    
    def simplificar_nodo(nodo):
        if nodo.esNodoHojaSinHijos():
            return nodo
        
        # Simplificar hijos primero
        if nodo.hijo_izquierdo:
            nodo.hijo_izquierdo = simplificar_nodo(nodo.hijo_izquierdo)
        if nodo.hijo_derecho:
            nodo.hijo_derecho = simplificar_nodo(nodo.hijo_derecho)
        
        # Reglas de simplificación
        if nodo.valor_almacenado == '+':
            # x + 0 = x
            if isinstance(nodo.hijo_derecho.valor_almacenado, (int, float)) and abs(float(nodo.hijo_derecho.valor_almacenado)) < 1e-10:
                return nodo.hijo_izquierdo
            # 0 + x = x
            if isinstance(nodo.hijo_izquierdo.valor_almacenado, (int, float)) and abs(float(nodo.hijo_izquierdo.valor_almacenado)) < 1e-10:
                return nodo.hijo_derecho
            # x + x = 2*x
            if str(nodo.hijo_izquierdo) == str(nodo.hijo_derecho):
                return NodoArbolMatematico('*', NodoArbolMatematico(2.0), nodo.hijo_izquierdo)
                
        elif nodo.valor_almacenado == '-':
            # x - 0 = x
            if isinstance(nodo.hijo_derecho.valor_almacenado, (int, float)) and abs(float(nodo.hijo_derecho.valor_almacenado)) < 1e-10:
                return nodo.hijo_izquierdo
            # x - x = 0
            if str(nodo.hijo_izquierdo) == str(nodo.hijo_derecho):
                return NodoArbolMatematico(0.0)
                
        elif nodo.valor_almacenado == '*':
            # x * 1 = x
            if isinstance(nodo.hijo_derecho.valor_almacenado, (int, float)) and abs(float(nodo.hijo_derecho.valor_almacenado) - 1.0) < 1e-10:
                return nodo.hijo_izquierdo
            # 1 * x = x
            if isinstance(nodo.hijo_izquierdo.valor_almacenado, (int, float)) and abs(float(nodo.hijo_izquierdo.valor_almacenado) - 1.0) < 1e-10:
                return nodo.hijo_derecho
            # x * 0 = 0
            if isinstance(nodo.hijo_derecho.valor_almacenado, (int, float)) and abs(float(nodo.hijo_derecho.valor_almacenado)) < 1e-10:
                return NodoArbolMatematico(0.0)
            if isinstance(nodo.hijo_izquierdo.valor_almacenado, (int, float)) and abs(float(nodo.hijo_izquierdo.valor_almacenado)) < 1e-10:
                return NodoArbolMatematico(0.0)
                
        elif nodo.valor_almacenado == '/':
            # x / 1 = x
            if isinstance(nodo.hijo_derecho.valor_almacenado, (int, float)) and abs(float(nodo.hijo_derecho.valor_almacenado) - 1.0) < 1e-10:
                return nodo.hijo_izquierdo
            # 0 / x = 0
            if isinstance(nodo.hijo_izquierdo.valor_almacenado, (int, float)) and abs(float(nodo.hijo_izquierdo.valor_almacenado)) < 1e-10:
                return NodoArbolMatematico(0.0)
                
        elif nodo.valor_almacenado == 'log':
            # log(e) = 1
            if isinstance(nodo.hijo_izquierdo.valor_almacenado, (int, float)) and abs(float(nodo.hijo_izquierdo.valor_almacenado) - 2.71828) < 0.1:
                return NodoArbolMatematico(1.0)
                
        elif nodo.valor_almacenado == 'sin':
            # sin(0) = 0
            if isinstance(nodo.hijo_izquierdo.valor_almacenado, (int, float)) and abs(float(nodo.hijo_izquierdo.valor_almacenado)) < 1e-10:
                return NodoArbolMatematico(0.0)
                
        return nodo
    
    return simplificar_nodo(arbol)

class MotorProgramacionGenetica:
    def __init__(self, configuracion_personalizada: dict = None):
        self.configuracion_actual = configuracion_personalizada if configuracion_personalizada else CONFIGURACION_ALGORITMO
        self.generador_aleatorio_interno = np.random.default_rng(self.configuracion_actual.get("semilla_aleatoria", 42))
        self.mejor_individuo_encontrado: Optional[NodoArbolMatematico] = None
        self.mejor_error_encontrado: float = float("inf")
        self.historial_de_errores_por_generacion: List[float] = []

def entrenarModeloEvolutivo(self, matriz_entrenamiento_x: np.ndarray, vector_entrenamiento_y: np.ndarray, imprimir_progreso: bool = True):
    cantidad_variables = matriz_entrenamiento_x.shape[1]
    tamano_de_poblacion = self.configuracion_actual["tamano_poblacion"]
    numero_de_generaciones = self.configuracion_actual["generaciones"]
    probabilidad_de_cruce = self.configuracion_actual["probabilidad_cruce"]
    probabilidad_mutacion_subarbol = self.configuracion_actual["probabilidad_mutacion_subarbol"]
    probabilidad_mutacion_punto = self.configuracion_actual["probabilidad_mutacion_punto"]
    cantidad_competidores_torneo = self.configuracion_actual["tamano_torneo"]
    profundidad_maxima_al_iniciar = self.configuracion_actual["profundidad_maxima_inicial"]
    profundidad_maxima_durante_evolucion = self.configuracion_actual["profundidad_maxima_evolucion"]

    tiempo_inicio = time.time()

    if imprimir_progreso:
        print(f"  Inicializando poblacion ({tamano_de_poblacion} individuos)...")
    poblacion_actual = generarPoblacionInicialMitadYMitad(tamano_de_poblacion, profundidad_maxima_al_iniciar, cantidad_variables, self.generador_aleatorio_interno)

    lista_errores_aptitud = [calcularErrorCuadraticoMedio(individuo, matriz_entrenamiento_x, vector_entrenamiento_y) for individuo in poblacion_actual]

    indice_del_mejor = int(np.argmin(lista_errores_aptitud))
    self.mejor_individuo_encontrado = copy.deepcopy(poblacion_actual[indice_del_mejor])
    self.mejor_individuo_encontrado = simplificar_expresion(self.mejor_individuo_encontrado)
    self.mejor_error_encontrado = lista_errores_aptitud[indice_del_mejor]
    # CAMBIO: Guardar RMSE en lugar de MSE
    self.historial_de_errores_por_generacion = [np.sqrt(self.mejor_error_encontrado)]

    if imprimir_progreso:
        print(f"  Generacion 0 | Mejor RMSE: {np.sqrt(self.mejor_error_encontrado):.6f} | Tiempo: {time.time()-tiempo_inicio:.1f}s")

    for generacion_actual in range(1, numero_de_generaciones + 1):
        nueva_poblacion_creada = []
        nuevos_errores_calculados = []

        if self.configuracion_actual.get("elitismo", True):
            nueva_poblacion_creada.append(copy.deepcopy(self.mejor_individuo_encontrado))
            nuevos_errores_calculados.append(self.mejor_error_encontrado)

        while len(nueva_poblacion_creada) < tamano_de_poblacion:
            probabilidad_aleatoria = self.generador_aleatorio_interno.random()

            if probabilidad_aleatoria < probabilidad_de_cruce:
                padre_uno = seleccionarIndividuoPorTorneo(poblacion_actual, lista_errores_aptitud, cantidad_competidores_torneo, self.generador_aleatorio_interno)
                padre_dos = seleccionarIndividuoPorTorneo(poblacion_actual, lista_errores_aptitud, cantidad_competidores_torneo, self.generador_aleatorio_interno)
                hijo_resultante = cruzarDosArbolesGeneticamente(padre_uno, padre_dos, self.generador_aleatorio_interno, profundidad_maxima_durante_evolucion)
            elif probabilidad_aleatoria < probabilidad_de_cruce + probabilidad_mutacion_subarbol:
                padre_uno = seleccionarIndividuoPorTorneo(poblacion_actual, lista_errores_aptitud, cantidad_competidores_torneo, self.generador_aleatorio_interno)
                hijo_resultante = mutarSubarbolCompleto(padre_uno, cantidad_variables, self.generador_aleatorio_interno, profundidad_maxima_durante_evolucion)
            elif probabilidad_aleatoria < probabilidad_de_cruce + probabilidad_mutacion_subarbol + probabilidad_mutacion_punto:
                padre_uno = seleccionarIndividuoPorTorneo(poblacion_actual, lista_errores_aptitud, cantidad_competidores_torneo, self.generador_aleatorio_interno)
                hijo_resultante = mutarOperadorMatematicoUnico(padre_uno, self.generador_aleatorio_interno)
            else:
                hijo_resultante = seleccionarIndividuoPorTorneo(poblacion_actual, lista_errores_aptitud, cantidad_competidores_torneo, self.generador_aleatorio_interno)

            error_del_hijo = calcularErrorCuadraticoMedio(hijo_resultante, matriz_entrenamiento_x, vector_entrenamiento_y)
            nueva_poblacion_creada.append(hijo_resultante)
            nuevos_errores_calculados.append(error_del_hijo)

        poblacion_actual = nueva_poblacion_creada[:tamano_de_poblacion]
        lista_errores_aptitud = nuevos_errores_calculados[:tamano_de_poblacion]

        indice_del_mejor = int(np.argmin(lista_errores_aptitud))
        if lista_errores_aptitud[indice_del_mejor] < self.mejor_error_encontrado:
            self.mejor_error_encontrado = lista_errores_aptitud[indice_del_mejor]
            self.mejor_individuo_encontrado = copy.deepcopy(poblacion_actual[indice_del_mejor])
            self.mejor_individuo_encontrado = simplificar_expresion(self.mejor_individuo_encontrado)

        # CAMBIO: Guardar RMSE en lugar de MSE
        self.historial_de_errores_por_generacion.append(np.sqrt(self.mejor_error_encontrado))

        if imprimir_progreso and (generacion_actual % 10 == 0 or generacion_actual == 1):
            error_promedio_poblacion = float(np.mean(lista_errores_aptitud))
            print(f"  Generacion {generacion_actual:3d} | Mejor RMSE: {np.sqrt(self.mejor_error_encontrado):.6f} | "
                  f"Promedio MSE: {error_promedio_poblacion:.6f} | "
                  f"Profundidad: {self.mejor_individuo_encontrado.calcularProfundidadMaxima()} | "
                  f"Tiempo: {time.time()-tiempo_inicio:.1f}s")

    if imprimir_progreso:
        print(f"\n  FINALIZADO | Mejor RMSE: {np.sqrt(self.mejor_error_encontrado):.6f}")
        print(f"  Mejor ecuacion encontrada: {self.mejor_individuo_encontrado}")
        print(f"  Tiempo total transcurrido: {time.time()-tiempo_inicio:.2f}s")

    return self

    def predecirNuevosValores(self, matriz_datos_x: np.ndarray) -> np.ndarray:
        if self.mejor_individuo_encontrado is None:
            raise RuntimeError("El modelo no ha sido entrenado aun.")
        predicciones_generadas = evaluarEcuacionMatematica(self.mejor_individuo_encontrado, matriz_datos_x)
        return np.where(np.isfinite(predicciones_generadas), predicciones_generadas, 0.0)

    def calcularMetricaR2(self, matriz_datos_x: np.ndarray, vector_real_y: np.ndarray) -> float:
        predicciones_generadas = self.predecirNuevosValores(matriz_datos_x)
        suma_cuadrados_residuos = np.sum((vector_real_y - predicciones_generadas) ** 2)
        suma_cuadrados_totales = np.sum((vector_real_y - np.mean(vector_real_y)) ** 2)
        if suma_cuadrados_totales < 1e-10:
            return 0.0
        return float(1 - suma_cuadrados_residuos / suma_cuadrados_totales)


def cargarConjuntoDeDatosCSV(nombre_del_conjunto: str, ruta_local_del_archivo: str = None):
    configuracion_del_conjunto = CONFIGURACIONES_CONJUNTOS_DE_DATOS.get(nombre_del_conjunto)
    if configuracion_del_conjunto is None:
        raise ValueError(f"Conjunto de datos '{nombre_del_conjunto}' no reconocido.")

    fuente_de_datos = ruta_local_del_archivo if ruta_local_del_archivo else configuracion_del_conjunto.get("enlace_descarga", configuracion_del_conjunto.get("nombre_archivo"))

    try:
        if configuracion_del_conjunto["tipo_archivo"] == "excel":
            dataframe_pandas = pd.read_excel(fuente_de_datos, 
                                           header=configuracion_del_conjunto.get("cabecera", 0))
        else:
            dataframe_pandas = pd.read_csv(
                fuente_de_datos,
                sep=configuracion_del_conjunto.get("separador", ","),
                header=configuracion_del_conjunto.get("cabecera")
            )
    except Exception as error_lectura:
        raise RuntimeError(f"No se pudo cargar '{nombre_del_conjunto}' desde '{fuente_de_datos}'. Error: {error_lectura}")

    if "forzar_columna_objetivo" in configuracion_del_conjunto:
        indice_objetivo = configuracion_del_conjunto["forzar_columna_objetivo"]
        matriz_x = dataframe_pandas.iloc[:, :indice_objetivo].values.astype(float)
        vector_y = dataframe_pandas.iloc[:, indice_objetivo].values.astype(float)
    else:
        columna_objetivo = configuracion_del_conjunto["columna_objetivo"]
        if columna_objetivo == -1:
            matriz_x = dataframe_pandas.iloc[:, :-1].values.astype(float)
            vector_y = dataframe_pandas.iloc[:, -1].values.astype(float)
        elif columna_objetivo == -2:
            matriz_x = dataframe_pandas.iloc[:, :-2].values.astype(float)
            vector_y = dataframe_pandas.iloc[:, -2].values.astype(float)
        else:
            matriz_x = dataframe_pandas.drop(dataframe_pandas.columns[columna_objetivo], axis=1).values.astype(float)
            vector_y = dataframe_pandas.iloc[:, columna_objetivo].values.astype(float)

    mascara_valores_validos = np.all(np.isfinite(matriz_x), axis=1) & np.isfinite(vector_y)
    matriz_x, vector_y = matriz_x[mascara_valores_validos], vector_y[mascara_valores_validos]

    return matriz_x, vector_y


def normalizarDatosEstadisticamente(matriz_x: np.ndarray, vector_y: np.ndarray):
    promedio_x = matriz_x.mean(axis=0)
    desviacion_estandar_x = matriz_x.std(axis=0)
    desviacion_estandar_x = np.where(desviacion_estandar_x < 1e-10, 1.0, desviacion_estandar_x)
    matriz_x_normalizada = (matriz_x - promedio_x) / desviacion_estandar_x

    promedio_y = vector_y.mean()
    desviacion_estandar_y = vector_y.std() if vector_y.std() > 1e-10 else 1.0
    vector_y_normalizado = (vector_y - promedio_y) / desviacion_estandar_y

    return matriz_x_normalizada, vector_y_normalizado, (promedio_x, desviacion_estandar_x, promedio_y, desviacion_estandar_y)


def dividirDatosEnEntrenamientoYPrueba(matriz_x: np.ndarray, vector_y: np.ndarray, proporcion_prueba: float = 0.2, semilla_aleatoria: int = 42):
    generador_aleatorio = np.random.default_rng(semilla_aleatoria)
    cantidad_muestras = matriz_x.shape[0]
    indices_mezclados = generador_aleatorio.permutation(cantidad_muestras)
    cantidad_prueba = int(cantidad_muestras * proporcion_prueba)
    indices_prueba = indices_mezclados[:cantidad_prueba]
    indices_entrenamiento = indices_mezclados[cantidad_prueba:]
    return matriz_x[indices_entrenamiento], matriz_x[indices_prueba], vector_y[indices_entrenamiento], vector_y[indices_prueba]

def ejecutarProcesoEvolutivoCompleto(
    nombre_del_conjunto_datos: str,
    ruta_local_archivo: str = None,
    configuracion_personalizada: dict = None,
    imprimir_resultados_consola: bool = True,
):
    configuracion_final = configuracion_personalizada if configuracion_personalizada else CONFIGURACION_ALGORITMO

    matriz_datos_x, vector_resultados_y = cargarConjuntoDeDatosCSV(nombre_del_conjunto_datos, ruta_local_archivo)

    matriz_x_entrenamiento, matriz_x_prueba, vector_y_entrenamiento, vector_y_prueba = dividirDatosEnEntrenamientoYPrueba(
        matriz_datos_x, vector_resultados_y, proporcion_prueba=0.2, semilla_aleatoria=configuracion_final.get("semilla_aleatoria", 42))

    matriz_x_entren_norm, vector_y_entren_norm, estadisticas_normalizacion = normalizarDatosEstadisticamente(matriz_x_entrenamiento, vector_y_entrenamiento)
    promedio_x, desviacion_std_x, promedio_y, desviacion_std_y = estadisticas_normalizacion
    matriz_x_prueba_norm = (matriz_x_prueba - promedio_x) / desviacion_std_x

    motor_genetico = MotorProgramacionGenetica(configuracion_personalizada=configuracion_final)
    motor_genetico.entrenarModeloEvolutivo(matriz_x_entren_norm, vector_y_entren_norm, imprimir_progreso=imprimir_resultados_consola)

    error_entrenamiento_normalizado = calcularErrorCuadraticoMedio(motor_genetico.mejor_individuo_encontrado, matriz_x_entren_norm, vector_y_entren_norm)
    error_prueba_normalizado = calcularErrorCuadraticoMedio(motor_genetico.mejor_individuo_encontrado, matriz_x_prueba_norm, vector_y_prueba / desviacion_std_y - promedio_y / desviacion_std_y)

    predicciones_prueba_norm = motor_genetico.predecirNuevosValores(matriz_x_prueba_norm)
    predicciones_prueba_escala_original = predicciones_prueba_norm * desviacion_std_y + promedio_y
    suma_residuos = np.sum((vector_y_prueba - predicciones_prueba_escala_original) ** 2)
    suma_total = np.sum((vector_y_prueba - np.mean(vector_y_prueba)) ** 2)
    metrica_r2_prueba = float(1 - suma_residuos / suma_total) if suma_total > 1e-10 else 0.0

    raiz_error_cuadratico_medio = float(np.sqrt(np.mean((vector_y_prueba - predicciones_prueba_escala_original) ** 2)))

    diccionario_de_resultados = {
        "dataset": nombre_del_conjunto_datos,
        "mse_train_norm": error_entrenamiento_normalizado,
        "mse_test_norm": error_prueba_normalizado,
        "rmse_test_original": raiz_error_cuadratico_medio,
        "r2_test": metrica_r2_prueba,
        "mejor_expresion": str(motor_genetico.mejor_individuo_encontrado),
        "arbol_dict": motor_genetico.mejor_individuo_encontrado.convertirADiccionario(),
        "profundidad": motor_genetico.mejor_individuo_encontrado.calcularProfundidadMaxima(),
        "tamanio": motor_genetico.mejor_individuo_encontrado.contarNodosTotales(),
        "historial": motor_genetico.historial_de_errores_por_generacion,
        "predicciones": predicciones_prueba_escala_original.tolist(),
        "valores_reales": vector_y_prueba.tolist()
    }

    return diccionario_de_resultados


def ejecutarEvolucionEnTodosLosDatasets(rutas_archivos_locales: dict = None, imprimir_progreso: bool = True):
    rutas_archivos = rutas_archivos_locales if rutas_archivos_locales else {}
    nombres_de_conjuntos = list(CONFIGURACIONES_CONJUNTOS_DE_DATOS.keys())
    resultados_totales = {}

    for nombre_conjunto in nombres_de_conjuntos:
        ruta_archivo = rutas_archivos.get(nombre_conjunto)
        try:
            resultado_individual = ejecutarProcesoEvolutivoCompleto(nombre_conjunto, ruta_local_archivo=ruta_archivo, imprimir_resultados_consola=imprimir_progreso)
            resultados_totales[nombre_conjunto] = resultado_individual
        except Exception as excepcion_ocurrida:
            resultados_totales[nombre_conjunto] = {"error": str(excepcion_ocurrida)}

    return resultados_totales

def generar_graficas_resultados(resultados: dict) -> Dict[str, str]:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Evolución del Error (MSE)', 'Predicciones vs Reales',
                        'Distribución de Errores', 'Residuos'),
        specs=[[{}, {}], [{'type': 'box'}, {}]]
    )
    
    historial = resultados.get('historial', [])
    if historial:
        fig.add_trace(
            go.Scatter(y=historial, mode='lines+markers', name='Mejor MSE',
                      line=dict(color='#3b82f6', width=2),
                      marker=dict(size=4, color='#8b5cf6')),
            row=1, col=1
        )
        fig.update_xaxes(title_text="Generación", row=1, col=1)
        fig.update_yaxes(title_text="MSE", row=1, col=1, type='log')
    
    predicciones = resultados.get('predicciones', [])
    valores_reales = resultados.get('valores_reales', [])
    if predicciones and valores_reales:
        fig.add_trace(
            go.Scatter(x=valores_reales, y=predicciones, mode='markers',
                      name='Predicciones', marker=dict(color='#a78bfa', size=8, opacity=0.7)),
            row=1, col=2
        )
        min_val = min(min(valores_reales), min(predicciones))
        max_val = max(max(valores_reales), max(predicciones))
        fig.add_trace(
            go.Scatter(x=[min_val, max_val], y=[min_val, max_val], mode='lines',
                      name='Ideal', line=dict(color='#ec4899', dash='dash')),
            row=1, col=2
        )
        fig.update_xaxes(title_text="Valores Reales", row=1, col=2)
        fig.update_yaxes(title_text="Predicciones", row=1, col=2)
    
    errores = [abs(r - p) for r, p in zip(valores_reales, predicciones)] if predicciones and valores_reales else []
    if errores:
        fig.add_trace(
            go.Box(y=errores, name='Error Absoluto', marker_color='#3b82f6',
                  boxmean='sd', jitter=0.3),
            row=2, col=1
        )
        fig.update_yaxes(title_text="Error Absoluto", row=2, col=1)
    
    if predicciones and valores_reales:
        fig.add_trace(
            go.Scatter(x=predicciones, y=[r-p for r,p in zip(valores_reales, predicciones)],
                      mode='markers', name='Residuos', marker=dict(color='#8b5cf6', size=6, opacity=0.6)),
            row=2, col=2
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#ec4899", row=2, col=2)
        fig.update_xaxes(title_text="Predicciones", row=2, col=2)
        fig.update_yaxes(title_text="Residuos", row=2, col=2)
    
    fig.update_layout(
        title_text=f"Resultados del Experimento - {resultados.get('dataset', 'Dataset')}",
        title_font_size=16,
        showlegend=True,
        template='plotly_dark',
        height=800,
        width=1000,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.3)',
        font=dict(color='#f8fafc')
    )
    
    graficas = {}
    graficas['evolucion'] = json.loads(fig.to_json())
    
    fig_bar = go.Figure()
    metricas = ['RMSE', 'R²', 'Profundidad', 'Nodos']
    valores_metricas = [
        resultados.get('rmse_test_original', 0),
        resultados.get('r2_test', 0),
        resultados.get('profundidad', 0),
        resultados.get('tamanio', 0)
    ]
    colores = ['#3b82f6', '#a78bfa', '#ec4899', '#06b6d4']
    fig_bar.add_trace(go.Bar(x=metricas, y=valores_metricas, marker_color=colores, text=valores_metricas, textposition='auto'))
    fig_bar.update_layout(title="Métricas de Rendimiento", template='plotly_dark', height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#f8fafc'))
    graficas['barras'] = json.loads(fig_bar.to_json())
    
    return graficas


aplicacion_servidor_web = FastAPI(title="API de Programación Genética")

aplicacion_servidor_web.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PeticionParaEjecutarExperimento(BaseModel):
    dataset: str
    generations: int = 50
    population_size: int = 500

class PeticionDatosPersonalizados(BaseModel):
    datos: List[Dict[str, float]]
    columna_objetivo: str

@aplicacion_servidor_web.post("/api/experimento")
def apiRecibirPeticionDeEvolucion(peticion_recibida: PeticionParaEjecutarExperimento):
    if peticion_recibida.dataset not in CONFIGURACIONES_CONJUNTOS_DE_DATOS:
        raise HTTPException(status_code=400, detail="Conjunto de datos no valido")
    
    configuracion_para_esta_peticion = CONFIGURACION_ALGORITMO.copy()
    configuracion_para_esta_peticion["generaciones"] = peticion_recibida.generations
    configuracion_para_esta_peticion["tamano_poblacion"] = peticion_recibida.population_size

    try:
        resultado_final = ejecutarProcesoEvolutivoCompleto(peticion_recibida.dataset, configuracion_personalizada=configuracion_para_esta_peticion, imprimir_resultados_consola=False)
        return resultado_final
    except Exception as excepcion_en_ejecucion:
        raise HTTPException(status_code=500, detail=str(excepcion_en_ejecucion))

directorio_archivos_estaticos = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(directorio_archivos_estaticos):
    aplicacion_servidor_web.mount("/static", StaticFiles(directory=directorio_archivos_estaticos), name="static")

@aplicacion_servidor_web.get("/")
@aplicacion_servidor_web.post("/api/personalizado/entrenar")
async def apiEntrenarDatosPersonalizados(peticion: PeticionDatosPersonalizados):
    try:
        df = pd.DataFrame(peticion.datos)
        if peticion.columna_objetivo not in df.columns:
            raise HTTPException(status_code=400, detail=f"Columna '{peticion.columna_objetivo}' no encontrada")
        
        vector_y = df[peticion.columna_objetivo].values.astype(float)
        matriz_x = df.drop(columns=[peticion.columna_objetivo]).values.astype(float)
        
        configuracion_personalizada = CONFIGURACION_ALGORITMO.copy()
        
        matriz_x_entren, matriz_x_prueba, vector_y_entren, vector_y_prueba = dividirDatosEnEntrenamientoYPrueba(
            matriz_x, vector_y, proporcion_prueba=0.2, semilla_aleatoria=42)
        
        matriz_x_entren_norm, vector_y_entren_norm, estadisticas = normalizarDatosEstadisticamente(matriz_x_entren, vector_y_entren)
        promedio_x, desviacion_std_x, promedio_y, desviacion_std_y = estadisticas
        matriz_x_prueba_norm = (matriz_x_prueba - promedio_x) / desviacion_std_x
        
        motor = MotorProgramacionGenetica(configuracion_personalizada=configuracion_personalizada)
        motor.entrenarModeloEvolutivo(matriz_x_entren_norm, vector_y_entren_norm, imprimir_progreso=False)
        
        predicciones_prueba_norm = motor.predecirNuevosValores(matriz_x_prueba_norm)
        predicciones_original = predicciones_prueba_norm * desviacion_std_y + promedio_y
        
        rmse = float(np.sqrt(np.mean((vector_y_prueba - predicciones_original) ** 2)))
        ss_res = np.sum((vector_y_prueba - predicciones_original) ** 2)
        ss_tot = np.sum((vector_y_prueba - np.mean(vector_y_prueba)) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 1e-10 else 0.0
        
        resultados = {
            "dataset": "personalizado",
            "mejor_expresion": str(motor.mejor_individuo_encontrado),
            "arbol_dict": motor.mejor_individuo_encontrado.convertirADiccionario(),
            "rmse_test_original": rmse,
            "r2_test": r2,
            "profundidad": motor.mejor_individuo_encontrado.calcularProfundidadMaxima(),
            "tamanio": motor.mejor_individuo_encontrado.contarNodosTotales(),
            "predicciones": predicciones_original.tolist(),
            "valores_reales": vector_y_prueba.tolist(),
            "historial": motor.historial_de_errores_por_generacion
        }
        
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@aplicacion_servidor_web.post("/api/generar-graficas")
async def apiGenerarGraficas(resultados: dict):
    try:
        graficas = generar_graficas_resultados(resultados)
        return graficas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
def servirInterfazGraficaWeb():
    ruta_archivo_principal = os.path.join(directorio_archivos_estaticos, "index.html")
    if os.path.exists(ruta_archivo_principal):
        return FileResponse(ruta_archivo_principal)
    return {"message": "Interfaz grafica no encontrada."}
@aplicacion_servidor_web.post("/api/personalizado/entrenar")
async def apiEntrenarDatosPersonalizados(peticion: PeticionDatosPersonalizados):
    try:
        df = pd.DataFrame(peticion.datos)
        if peticion.columna_objetivo not in df.columns:
            raise HTTPException(status_code=400, detail=f"Columna '{peticion.columna_objetivo}' no encontrada")
        
        vector_y = df[peticion.columna_objetivo].values.astype(float)
        matriz_x = df.drop(columns=[peticion.columna_objetivo]).values.astype(float)
        
        configuracion_personalizada = CONFIGURACION_ALGORITMO.copy()
        
        matriz_x_entren, matriz_x_prueba, vector_y_entren, vector_y_prueba = dividirDatosEnEntrenamientoYPrueba(
            matriz_x, vector_y, proporcion_prueba=0.2, semilla_aleatoria=42)
        
        matriz_x_entren_norm, vector_y_entren_norm, estadisticas = normalizarDatosEstadisticamente(matriz_x_entren, vector_y_entren)
        promedio_x, desviacion_std_x, promedio_y, desviacion_std_y = estadisticas
        matriz_x_prueba_norm = (matriz_x_prueba - promedio_x) / desviacion_std_x
        
        motor = MotorProgramacionGenetica(configuracion_personalizada=configuracion_personalizada)
        motor.entrenarModeloEvolutivo(matriz_x_entren_norm, vector_y_entren_norm, imprimir_progreso=False)
        
        predicciones_prueba_norm = motor.predecirNuevosValores(matriz_x_prueba_norm)
        predicciones_original = predicciones_prueba_norm * desviacion_std_y + promedio_y
        
        rmse = float(np.sqrt(np.mean((vector_y_prueba - predicciones_original) ** 2)))
        ss_res = np.sum((vector_y_prueba - predicciones_original) ** 2)
        ss_tot = np.sum((vector_y_prueba - np.mean(vector_y_prueba)) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 1e-10 else 0.0
        
        resultados = {
            "dataset": "personalizado",
            "mejor_expresion": str(motor.mejor_individuo_encontrado),
            "arbol_dict": motor.mejor_individuo_encontrado.convertirADiccionario(),
            "rmse_test_original": rmse,
            "r2_test": r2,
            "profundidad": motor.mejor_individuo_encontrado.calcularProfundidadMaxima(),
            "tamanio": motor.mejor_individuo_encontrado.contarNodosTotales(),
            "predicciones": predicciones_original.tolist(),
            "valores_reales": vector_y_prueba.tolist(),
            "historial": motor.historial_de_errores_por_generacion
        }
        
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
def generar_graficas_resultados(resultados: dict) -> Dict[str, str]:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Evolución del Error (MSE)', 'Predicciones vs Reales',
                        'Distribución de Errores', 'Residuos'),
        specs=[[{}, {}], [{'type': 'box'}, {}]]
    )
    
    historial = resultados.get('historial', [])
    if historial:
        fig.add_trace(
            go.Scatter(y=historial, mode='lines+markers', name='Mejor MSE',
                      line=dict(color='#3b82f6', width=2),
                      marker=dict(size=4, color='#8b5cf6')),
            row=1, col=1
        )
        fig.update_xaxes(title_text="Generación", row=1, col=1)
        fig.update_yaxes(title_text="MSE", row=1, col=1, type='log')
    
    predicciones = resultados.get('predicciones', [])
    valores_reales = resultados.get('valores_reales', [])
    if predicciones and valores_reales:
        fig.add_trace(
            go.Scatter(x=valores_reales, y=predicciones, mode='markers',
                      name='Predicciones', marker=dict(color='#a78bfa', size=8, opacity=0.7)),
            row=1, col=2
        )
        min_val = min(min(valores_reales), min(predicciones))
        max_val = max(max(valores_reales), max(predicciones))
        fig.add_trace(
            go.Scatter(x=[min_val, max_val], y=[min_val, max_val], mode='lines',
                      name='Ideal', line=dict(color='#ec4899', dash='dash')),
            row=1, col=2
        )
        fig.update_xaxes(title_text="Valores Reales", row=1, col=2)
        fig.update_yaxes(title_text="Predicciones", row=1, col=2)
    
    errores = [abs(r - p) for r, p in zip(valores_reales, predicciones)] if predicciones and valores_reales else []
    if errores:
        fig.add_trace(
            go.Box(y=errores, name='Error Absoluto', marker_color='#3b82f6',
                  boxmean='sd', jitter=0.3),
            row=2, col=1
        )
        fig.update_yaxes(title_text="Error Absoluto", row=2, col=1)
    
    if predicciones and valores_reales:
        fig.add_trace(
            go.Scatter(x=predicciones, y=[r-p for r,p in zip(valores_reales, predicciones)],
                      mode='markers', name='Residuos', marker=dict(color='#8b5cf6', size=6, opacity=0.6)),
            row=2, col=2
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#ec4899", row=2, col=2)
        fig.update_xaxes(title_text="Predicciones", row=2, col=2)
        fig.update_yaxes(title_text="Residuos", row=2, col=2)
    
    fig.update_layout(
        title_text=f"Resultados del Experimento - {resultados.get('dataset', 'Dataset')}",
        title_font_size=16,
        showlegend=True,
        template='plotly_dark',
        height=800,
        width=1000,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.3)',
        font=dict(color='#f8fafc')
    )
    
    graficas = {}
    graficas['evolucion'] = json.loads(fig.to_json())
    
    fig_bar = go.Figure()
    metricas = ['RMSE', 'R²', 'Profundidad', 'Nodos']
    valores_metricas = [
        resultados.get('rmse_test_original', 0),
        resultados.get('r2_test', 0),
        resultados.get('profundidad', 0),
        resultados.get('tamanio', 0)
    ]
    colores = ['#3b82f6', '#a78bfa', '#ec4899', '#06b6d4']
    fig_bar.add_trace(go.Bar(x=metricas, y=valores_metricas, marker_color=colores, text=valores_metricas, textposition='auto'))
    fig_bar.update_layout(title="Métricas de Rendimiento", template='plotly_dark', height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#f8fafc'))
    graficas['barras'] = json.loads(fig_bar.to_json())
    
    return graficas

@aplicacion_servidor_web.post("/api/personalizado/predecir")
async def apiPredecirConModeloPersonalizado(datos: List[Dict[str, float]]):
    raise HTTPException(status_code=400, detail="Primero debe entrenar un modelo con /api/personalizado/entrenar")

@aplicacion_servidor_web.post("/api/generar-graficas")
async def apiGenerarGraficas(resultados: dict):
    try:
        graficas = generar_graficas_resultados(resultados)
        return graficas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@aplicacion_servidor_web.get("/api/test-plotly")
async def test_plotly():
    fig = go.Figure(data=[go.Bar(x=['A', 'B', 'C'], y=[1, 3, 2])])
    return JSONResponse(content=json.loads(fig.to_json()))