document.addEventListener('DOMContentLoaded', () => {
    const runBtn = document.getElementById('run-btn');
    const resultsSection = document.getElementById('results');
    const loader = document.getElementById('loader');
    const dataResults = document.getElementById('data-results');
    const resRmse = document.getElementById('res-rmse');
    const resR2 = document.getElementById('res-r2');
    const resDepth = document.getElementById('res-depth');
    const resSize = document.getElementById('res-size');
    const resExpression = document.getElementById('res-expression');

    runBtn.addEventListener('click', async () => {
        const dataset = document.getElementById('dataset').value;
        const generations = parseInt(document.getElementById('generations').value);
        const population = parseInt(document.getElementById('population').value);

        if (!dataset || isNaN(generations) || isNaN(population)) {
            alert('Por favor completa todos los campos correctamente.');
            return;
        }
        runBtn.disabled = true;
        runBtn.textContent = 'Evolucionando...';
        resultsSection.classList.remove('hidden');
        dataResults.classList.add('hidden');
        loader.classList.remove('hidden');

        try {
            const response = await fetch('/api/experimento', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dataset: dataset,
                    generations: generations,
                    population_size: population
                })
            });

            if (!response.ok) {
                let errorMessage = 'Unknown server error';
                try {
                    const errData = await response.json();
                    errorMessage = errData.detail || errorMessage;
                } catch (e) {
                    // Fallback to raw text if JSON parsing fails
                    errorMessage = await response.text();
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            resRmse.textContent = data.rmse_test_original.toFixed(4);
            resR2.textContent = data.r2_test.toFixed(4);
            resDepth.textContent = data.profundidad;
            resSize.textContent = data.tamanio;
            resExpression.textContent = data.mejor_expresion;
            
            if (data.arbol_dict) {
                drawTree(data.arbol_dict);
            }

            loader.classList.add('hidden');
            dataResults.classList.remove('hidden');

        } catch (error) {
            alert('Ocurrió un error: ' + error.message);
            resultsSection.classList.add('hidden');
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = 'Ejecutar Experimento';
        }
    });

    function drawTree(treeData) {
        const container = document.getElementById('tree-container');
        container.innerHTML = ''; // Clear previous

        const width = container.clientWidth || 800;
        const height = 600;

        // Aumentar el espaciado entre nodos para evitar que se vea amontonado
        const dx = 140; 
        const dy = 160;

        const svg = d3.select('#tree-container')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .style('cursor', 'grab');

        // Grupo principal que será escalado/movido por el zoom
        const g = svg.append('g');

        // Jerarquía de los datos
        const root = d3.hierarchy(treeData, d => d.children);

        // Usamos nodeSize para que el árbol crezca según lo necesite en lugar de amontonarse
        const treemap = d3.tree().nodeSize([dx, dy]);
        treemap(root);

        // Calcular los límites del árbol generado para limitar el paneo
        let minX = Infinity, maxX = -Infinity, maxY = -Infinity;
        root.each(d => {
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y > maxY) maxY = d.y;
        });

        // Comportamiento de Zoom y Paneo con límites
        const treeWidth = (maxX - minX) + 120;
        const treeHeight = maxY + 100;
        const autoMinScale = Math.min(width / treeWidth, height / treeHeight);
        const fitScale = Math.min(autoMinScale, 1.0);
        const minScaleLimit = fitScale * 0.5; // Allow 50% more zoom out than perfect fit

        const zoom = d3.zoom()
            .scaleExtent([minScaleLimit, 2])
            .translateExtent([
                [minX - width, -500], 
                [maxX + width, maxY + 500]
            ])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        
        svg.call(zoom);

        // Centrado inicial de la cámara
        const initialScale = Math.min(0.9, fitScale);
        const initialTranslateX = width / 2;
        const initialTranslateY = 50; // Margen superior
        
        svg.call(
            zoom.transform, 
            d3.zoomIdentity.translate(initialTranslateX, initialTranslateY).scale(initialScale)
        );

        // Trazado de las líneas (Links)
        g.selectAll('.link')
            .data(root.descendants().slice(1))
            .enter().append('path')
            .attr('class', 'link')
            .attr('d', d => {
                return `M${d.x},${d.y}
                        C${d.x},${(d.y + d.parent.y) / 2}
                         ${d.parent.x},${(d.y + d.parent.y) / 2}
                         ${d.parent.x},${d.parent.y}`;
            });

        // Nodos
        const node = g.selectAll('.node')
            .data(root.descendants())
            .enter().append('g')
            .attr('class', d => 'node' + (d.children ? ' node--internal' : ' node--leaf'))
            .attr('transform', d => `translate(${d.x},${d.y})`);

        node.append('circle')
            .attr('r', 18);

        node.append('text')
            .attr('dy', '.35em')
            .attr('x', d => d.children ? -25 : 25)
            .style('text-anchor', d => d.children ? 'end' : 'start')
            .style('font-weight', '600')
            .text(d => d.data.name)
            .clone(true).lower()
            .attr('stroke', 'rgba(15, 23, 42, 0.9)')
            .attr('stroke-width', 4);
    }
});
