document.addEventListener('DOMContentLoaded', () => {
    const botonEjecutar = document.getElementById('run-btn');
    const seccionResultados = document.getElementById('results');
    const indicadorCarga = document.getElementById('loader');
    const contenedorDatos = document.getElementById('data-results');
    const textoRmse = document.getElementById('res-rmse');
    const textoR2 = document.getElementById('res-r2');
    const textoProfundidad = document.getElementById('res-depth');
    const textoTamano = document.getElementById('res-size');
    const textoMejorExpresion = document.getElementById('res-expression');

    botonEjecutar.addEventListener('click', async () => {
        const conjuntoDatosSeleccionado = document.getElementById('dataset').value;
        const numeroGeneraciones = parseInt(document.getElementById('generations').value);
        const tamanoPoblacion = parseInt(document.getElementById('population').value);

        if (!conjuntoDatosSeleccionado || isNaN(numeroGeneraciones) || isNaN(tamanoPoblacion)) {
            alert('Por favor completa todos los campos correctamente.');
            return;
        }
        botonEjecutar.disabled = true;
        botonEjecutar.textContent = 'Evolucionando...';
        seccionResultados.classList.remove('hidden');
        contenedorDatos.classList.add('hidden');
        indicadorCarga.classList.remove('hidden');

        try {
            const respuestaServidor = await fetch('/api/experimento', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dataset: conjuntoDatosSeleccionado,
                    generations: numeroGeneraciones,
                    population_size: tamanoPoblacion
                })
            });

            if (!respuestaServidor.ok) {
                let detalleError = 'Error desconocido en el servidor';
                try {
                    const datosError = await respuestaServidor.json();
                    detalleError = datosError.detail || detalleError;
                } catch (e) {
                    // Si no es JSON, capturar el texto bruto (evita el error de parseo)
                    detalleError = await respuestaServidor.text();
                }
                throw new Error(detalleError);
            }

            const datosRecibidos = await respuestaServidor.json();
            textoRmse.textContent = datosRecibidos.rmse_test_original.toFixed(4);
            textoR2.textContent = datosRecibidos.r2_test.toFixed(4);
            textoProfundidad.textContent = datosRecibidos.profundidad;
            textoTamano.textContent = datosRecibidos.tamanio;
            textoMejorExpresion.textContent = datosRecibidos.mejor_expresion;
            
            if (datosRecibidos.arbol_dict) {
                dibujarArbolJerarquicoVisual(datosRecibidos.arbol_dict);
            }

            indicadorCarga.classList.add('hidden');
            contenedorDatos.classList.remove('hidden');

        } catch (errorCapturado) {
            alert('Ocurrió un error: ' + errorCapturado.message);
            seccionResultados.classList.add('hidden');
        } finally {
            botonEjecutar.disabled = false;
            botonEjecutar.textContent = 'Ejecutar Experimento';
        }
    });

    function dibujarArbolJerarquicoVisual(datosDelArbol) {
        const contenedorDelArbol = document.getElementById('tree-container');
        contenedorDelArbol.innerHTML = ''; 

        const anchuraPantalla = contenedorDelArbol.clientWidth || 800;
        const alturaPantalla = 600;

        // Aumentar el espaciado para que el árbol no se vea amontonado (horizontal, vertical)
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
        const limiteEscalaMinima = escalaAjuste * 0.5; // Permitir 50% más de zoom hacia fuera del ajuste perfecto

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
