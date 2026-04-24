console.log("=== SCRIPT.JS CARGADO ===");

document.addEventListener('DOMContentLoaded', () => {
    console.log("=== DOM LISTO ===");

    const botonEjecutar = document.getElementById('run-btn');
    const seccionResultados = document.getElementById('results');
    const indicadorCarga = document.getElementById('loader');
    const contenedorDatos = document.getElementById('data-results');
    const textoRmse = document.getElementById('res-rmse');
    const textoR2 = document.getElementById('res-r2');
    const textoProfundidad = document.getElementById('res-depth');
    const textoTamano = document.getElementById('res-size');
    const textoMejorExpresion = document.getElementById('res-expression');

    console.log("Elementos encontrados:", {
        boton: !!botonEjecutar,
        resultados: !!seccionResultados,
        loader: !!indicadorCarga,
        contenedor: !!contenedorDatos
    });

    // Verificar elemento dataset
    const datasetElement = document.getElementById('dataset');
    console.log("Elemento dataset encontrado:", datasetElement);

    const generationsElement = document.getElementById('generations');
    const populationElement = document.getElementById('population');

    console.log("generations element:", generationsElement);
    console.log("population element:", populationElement);

    // Listeners para los radio buttons
    const modoPredefinido = document.getElementById('modo-predefinido');
    const modoPersonalizado = document.getElementById('modo-personalizado');
    const predefinidoSection = document.getElementById('predefinido-section');
    const personalizadoSection = document.getElementById('personalizado-section');

    if (modoPredefinido && modoPersonalizado) {
        modoPredefinido.addEventListener('change', function () {
            if (predefinidoSection) predefinidoSection.style.display = 'block';
            if (personalizadoSection) personalizadoSection.style.display = 'none';
        });

        modoPersonalizado.addEventListener('change', function () {
            if (predefinidoSection) predefinidoSection.style.display = 'none';
            if (personalizadoSection) personalizadoSection.style.display = 'block';
        });
    }

    if (!botonEjecutar) {
        console.error("ERROR: No se encontró el botón 'run-btn'");
        return;
    }

    botonEjecutar.addEventListener('click', async () => {
        console.log("=== INICIO DE EJECUCIÓN ===");

        // Obtener modo seleccionado
        const modoRadio = document.querySelector('input[name="modo"]:checked');
        const modoSeleccionado = modoRadio ? modoRadio.value : 'predefinido';

        // Obtener valores con validación
        const datasetElement = document.getElementById('dataset');
        const conjuntoDatosSeleccionado = datasetElement ? datasetElement.value : null;

        const generationsElement = document.getElementById('generations');
        const numeroGeneraciones = generationsElement ? parseInt(generationsElement.value) : 20;

        const populationElement = document.getElementById('population');
        const tamanoPoblacion = populationElement ? parseInt(populationElement.value) : 200;

        console.log("Parámetros:", {
            modoSeleccionado,
            conjuntoDatosSeleccionado,
            numeroGeneraciones,
            tamanoPoblacion
        });

        // Validar
        if (modoSeleccionado === 'predefinido' && !conjuntoDatosSeleccionado) {
            alert('Por favor selecciona un dataset');
            return;
        }

        if (isNaN(numeroGeneraciones) || isNaN(tamanoPoblacion)) {
            alert('Por favor completa todos los campos correctamente.');
            return;
        }

        botonEjecutar.disabled = true;
        botonEjecutar.textContent = 'Evolucionando...';
        seccionResultados.classList.remove('hidden');
        contenedorDatos.classList.add('hidden');
        indicadorCarga.classList.remove('hidden');

        try {
            let datosRecibidos;

            if (modoSeleccionado === 'predefinido') {
                console.log("Llamando a /api/experimento...");
                const respuestaServidor = await fetch('/api/experimento', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dataset: conjuntoDatosSeleccionado,
                        generations: numeroGeneraciones,
                        population_size: tamanoPoblacion
                    })
                });
                if (!respuestaServidor.ok) throw new Error(await respuestaServidor.text());
                datosRecibidos = await respuestaServidor.json();
            } else {
                const datosPersonalizados = procesarDatosCSVPersonalizado();
                if (!datosPersonalizados) throw new Error('Datos personalizados inválidos');

                console.log("Llamando a /api/personalizado/entrenar...");
                const respuestaServidor = await fetch('/api/personalizado/entrenar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(datosPersonalizados)
                });
                if (!respuestaServidor.ok) throw new Error(await respuestaServidor.text());
                datosRecibidos = await respuestaServidor.json();
            }

            console.log("Datos recibidos:", datosRecibidos);

            // Mostrar métricas
            if (textoRmse) textoRmse.textContent = datosRecibidos.rmse_test_original ? datosRecibidos.rmse_test_original.toFixed(4) : '0.00';
            if (textoR2) textoR2.textContent = datosRecibidos.r2_test ? datosRecibidos.r2_test.toFixed(4) : '0.00';
            if (textoProfundidad) textoProfundidad.textContent = datosRecibidos.profundidad || '0';
            if (textoTamano) textoTamano.textContent = datosRecibidos.tamanio || '0';
            if (textoMejorExpresion) textoMejorExpresion.textContent = datosRecibidos.mejor_expresion || 'No se encontró expresión';

            // Dibujar árbol
            if (datosRecibidos.arbol_dict) {
                dibujarArbolJerarquicoVisual(datosRecibidos.arbol_dict);
            }

            // Dibujar gráficas
            dibujarGraficas(datosRecibidos);

            if (indicadorCarga) indicadorCarga.classList.add('hidden');
            if (contenedorDatos) contenedorDatos.classList.remove('hidden');
            console.log("=== EJECUCIÓN COMPLETADA ===");

        } catch (errorCapturado) {
            console.error("Error:", errorCapturado);
            alert('Ocurrió un error: ' + errorCapturado.message);
            if (seccionResultados) seccionResultados.classList.add('hidden');
        } finally {
            botonEjecutar.disabled = false;
            botonEjecutar.textContent = 'Ejecutar Experimento';
        }
    });

    function procesarDatosCSVPersonalizado() {
        const textoCSV = document.getElementById('csv-input');
        const targetColumn = document.getElementById('target-column');

        if (!textoCSV || !textoCSV.value.trim()) {
            alert('Por favor ingresa datos CSV');
            return null;
        }

        if (!targetColumn || !targetColumn.value.trim()) {
            alert('Por favor especifica la columna objetivo');
            return null;
        }

        const lineas = textoCSV.value.trim().split('\n');
        const encabezados = lineas[0].split(',').map(h => h.trim());
        const columnaObjetivo = targetColumn.value.trim();

        if (!encabezados.includes(columnaObjetivo)) {
            alert(`Columna "${columnaObjetivo}" no encontrada. Columnas disponibles: ${encabezados.join(', ')}`);
            return null;
        }

        const datos = [];
        for (let i = 1; i < lineas.length; i++) {
            const valores = lineas[i].split(',').map(v => parseFloat(v.trim()));
            if (valores.some(isNaN)) continue;
            const fila = {};
            encabezados.forEach((h, idx) => { fila[h] = valores[idx]; });
            datos.push(fila);
        }

        return { datos: datos, columna_objetivo: columnaObjetivo };
    }

    function dibujarGraficas(resultados) {
        console.log("=== DIBUJANDO GRÁFICAS ===");

        if (typeof Plotly === 'undefined') {
            console.error("Plotly no está cargado!");
            return;
        }

        try {
            const graficaEvolucion = document.getElementById('grafica-evolucion');
            const graficaBarras = document.getElementById('grafica-barras');

            if (!graficaEvolucion || !graficaBarras) {
                console.error("No se encontraron los contenedores");
                return;
            }

            const config = {
                responsive: true,
                displayModeBar: false,
                scrollZoom: false,
                doubleClick: false,
                displaylogo: false
            };

            // ============================================
            // GRÁFICA 1: Evolución del RMSE
            // ============================================
            if (resultados.historial && resultados.historial.length > 0) {
                let valoresRMSE = [...resultados.historial];
                if (valoresRMSE[0] > 10) {
                    valoresRMSE = valoresRMSE.map(v => Math.sqrt(Math.abs(v)));
                }

                const generaciones = valoresRMSE.map((_, i) => i);

                const traceEvolucion = {
                    x: generaciones,
                    y: valoresRMSE,
                    mode: 'lines+markers',
                    type: 'scatter',
                    name: 'RMSE',
                    line: { color: '#3b82f6', width: 2 },
                    marker: { size: 5, color: '#8b5cf6' }
                };

                const layoutEvolucion = {
                    autosize: true,
                    width: undefined,
                    margin: { t: 35, l: 45, r: 20, b: 35 },
                    xaxis: {
                        title: 'Generación',
                        color: '#cbd5e1',
                        gridcolor: 'rgba(255,255,255,0.1)',
                        showgrid: true,
                        fixedrange: true
                    },
                    yaxis: {
                        title: 'RMSE',
                        color: '#cbd5e1',
                        gridcolor: 'rgba(255,255,255,0.1)',
                        showgrid: true,
                        fixedrange: true
                    },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(30,41,59,0.25)',
                    font: { color: '#cbd5e1', family: 'Inter, sans-serif' },
                    hovermode: 'closest'
                };

                Plotly.newPlot('grafica-evolucion', [traceEvolucion], layoutEvolucion, config);
            } else {
                Plotly.newPlot('grafica-evolucion', [], {
                    autosize: true,
                    height: 300,
                    title: 'Ejecuta un experimento',
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(30,41,59,0.25)',
                    font: { color: '#94a3b8' }
                }, config);
            }

            // ============================================
            // GRÁFICA 2: Barras de métricas
            // ============================================
            const metricas = ['RMSE', 'R²', 'Profundidad', 'Nodos'];
            const valores = [
                Number(resultados.rmse_test_original) || 0,
                Number(resultados.r2_test) || 0,
                Number(resultados.profundidad) || 0,
                Number(resultados.tamanio) || 0
            ];

            const textos = [
                valores[0].toFixed(4),
                valores[1].toFixed(4),
                valores[2].toFixed(1),
                valores[3].toFixed(1)
            ];

            const colores = ['#3b82f6', '#a78bfa', '#ec4899', '#06b6d4'];

            const traceBarras = {
                x: metricas,
                y: valores,
                type: 'bar',
                marker: {
                    color: colores,
                    line: { color: 'rgba(255,255,255,0.2)', width: 1 }
                },
                text: textos,
                textposition: 'outside',
                textfont: { color: '#f8fafc', size: 10 }
            };

            const layoutBarras = {
                autosize: true,
                width: undefined,
                margin: { t: 35, l: 45, r: 20, b: 35 },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(30,41,59,0.25)',
                font: { color: '#cbd5e1', family: 'Inter, sans-serif' },
                yaxis: {
                    title: 'Valor',
                    color: '#cbd5e1',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    showgrid: true,
                    zeroline: true,
                    zerolinecolor: 'rgba(255,255,255,0.2)',
                    fixedrange: true
                },
                xaxis: {
                    color: '#cbd5e1',
                    fixedrange: true
                },
                showlegend: false,
                bargap: 0.3
            };

            Plotly.newPlot('grafica-barras', [traceBarras], layoutBarras, config);

            console.log("Gráficas dibujadas - Altura reducida a 300px");

        } catch (error) {
            console.error('Error en gráficas:', error);
        }
    }

    function dibujarArbolJerarquicoVisual(datosDelArbol) {
        const contenedorDelArbol = document.getElementById('tree-container');
        if (!contenedorDelArbol) return;

        contenedorDelArbol.innerHTML = '';

        const anchuraPantalla = contenedorDelArbol.clientWidth || 800;
        const alturaPantalla = 600;

        const espaciadoHorizontal = 140;
        const espaciadoVertical = 160;

        const lienzoSvg = d3.select('#tree-container')
            .append('svg')
            .attr('width', anchuraPantalla)
            .attr('height', alturaPantalla)
            .style('cursor', 'grab');

        const grupoPrincipal = lienzoSvg.append('g');

        const jerarquiaDeNodos = d3.hierarchy(datosDelArbol, nodo => nodo.children);

        const mapaDelArbol = d3.tree().nodeSize([espaciadoHorizontal, espaciadoVertical]);
        mapaDelArbol(jerarquiaDeNodos);

        let coordenadaMinimaX = Infinity, coordenadaMaximaX = -Infinity, coordenadaMaximaY = -Infinity;
        jerarquiaDeNodos.each(nodoHijo => {
            if (nodoHijo.x < coordenadaMinimaX) coordenadaMinimaX = nodoHijo.x;
            if (nodoHijo.x > coordenadaMaximaX) coordenadaMaximaX = nodoHijo.x;
            if (nodoHijo.y > coordenadaMaximaY) coordenadaMaximaY = nodoHijo.y;
        });

        const anchuraArbol = (coordenadaMaximaX - coordenadaMinimaX) + 120;
        const alturaArbol = coordenadaMaximaY + 100;
        const escalaMinimaAuto = Math.min(anchuraPantalla / anchuraArbol, alturaPantalla / alturaArbol);
        const escalaAjuste = Math.min(escalaMinimaAuto, 1.0);
        const limiteEscalaMinima = escalaAjuste * 0.5;

        const comportamientoZoom = d3.zoom()
            .scaleExtent([limiteEscalaMinima, 2])
            .translateExtent([
                [coordenadaMinimaX - anchuraPantalla, -500],
                [coordenadaMaximaX + anchuraPantalla, coordenadaMaximaY + 500]
            ])
            .on('zoom', (eventoZoom) => {
                grupoPrincipal.attr('transform', eventoZoom.transform);
            });

        lienzoSvg.call(comportamientoZoom);

        const escalaInicial = Math.min(0.9, escalaAjuste);
        const translacionInicialX = anchuraPantalla / 2;
        const translacionInicialY = 50;

        lienzoSvg.call(
            comportamientoZoom.transform,
            d3.zoomIdentity.translate(translacionInicialX, translacionInicialY).scale(escalaInicial)
        );

        grupoPrincipal.selectAll('.link')
            .data(jerarquiaDeNodos.descendants().slice(1))
            .enter().append('path')
            .attr('class', 'link')
            .attr('d', nodoHijo => {
                return `M${nodoHijo.x},${nodoHijo.y}
                        C${nodoHijo.x},${(nodoHijo.y + nodoHijo.parent.y) / 2}
                         ${nodoHijo.parent.x},${(nodoHijo.y + nodoHijo.parent.y) / 2}
                         ${nodoHijo.parent.x},${nodoHijo.parent.y}`;
            });

        const elementoNodo = grupoPrincipal.selectAll('.node')
            .data(jerarquiaDeNodos.descendants())
            .enter().append('g')
            .attr('class', nodoHijo => 'node' + (nodoHijo.children ? ' node--internal' : ' node--leaf'))
            .attr('transform', nodoHijo => `translate(${nodoHijo.x},${nodoHijo.y})`);

        elementoNodo.append('circle')
            .attr('r', 18);

        elementoNodo.append('text')
            .attr('dy', '.35em')
            .attr('x', nodoHijo => nodoHijo.children ? -25 : 25)
            .style('text-anchor', nodoHijo => nodoHijo.children ? 'end' : 'start')
            .style('font-weight', '600')
            .text(nodoHijo => nodoHijo.data.name)
            .clone(true).lower()
            .attr('stroke', 'rgba(15, 23, 42, 0.9)')
            .attr('stroke-width', 4);
    }
});