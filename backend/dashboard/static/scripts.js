    const gauges = {}; // guarda as instâncias dos gráficos Chart.js

    // Função para criar ou atualizar gauge
    function createOrUpdateGauge(canvasId, value, maxValue, minValue, unit, colorRanges) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error('Canvas não encontrado:', canvasId);
            return;
        }

        const numValue = parseFloat(value);
        if (isNaN(numValue)) {
            console.error('Valor inválido para', canvasId, ':', value);
            return;
        }

        const ctx = canvas.getContext('2d');
        const valueRange = maxValue - minValue;
        const currentValue = Math.max(minValue, Math.min(maxValue, numValue));
        const filledValue = currentValue - minValue;
        const emptyValue = maxValue - currentValue;

        // Se já existe, apenas atualiza
        if (gauges[canvasId]) {
            const chart = gauges[canvasId];
            chart.data.datasets[0].data = [filledValue, emptyValue];
            chart.data.datasets[0].backgroundColor[0] = getColorForValue(numValue, colorRanges);
            chart.options.plugins.gaugeText.value = numValue.toFixed(1);
            chart.update();
            return;
        }

        // Criação do novo gauge
        gauges[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [filledValue, emptyValue],
                    backgroundColor: [
                        getColorForValue(numValue, colorRanges),
                        '#e0e0e0'
                    ],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                    gaugeText: { value: numValue.toFixed(1), unit: unit }
                }
            },
            plugins: [{
                id: 'gaugeText',
                afterDraw: (chart) => {
                    const ctx = chart.ctx;
                    const {left, right, top, bottom} = chart.chartArea;
                    const centerX = left + (right - left) / 2;
                    const centerY = top + (bottom - top) / 1.1; // ajusta posição do texto

                    const value = chart.options.plugins.gaugeText.value;
                    const unit = chart.options.plugins.gaugeText.unit;

                    ctx.save();
                    ctx.font = 'bold 32px Arial';
                    ctx.fillStyle = '#333';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(value, centerX, centerY);

                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#666';
                    ctx.fillText(unit, centerX, centerY + 25);
                    ctx.restore();
                }
            }]
        });
    }

    // Função de cor dinâmica
    function getColorForValue(value, ranges) {
        for (let range of ranges) {
            if (value >= range.min && value <= range.max) return range.color;
        }
        return '#999';
    }

    // Atualiza os dados periodicamente
    async function updateData() {
        try {
            const response = await fetch(HOSPITAL_DATA_URL);
            const data = await response.json();
            console.log("Dados atualizados:", data);

            if (data.pressure !== undefined) {
                createOrUpdateGauge('pressure-gauge', data.pressure, 12, 0, '', [
                    { min: 0, max: 5, color: '#ff4444' },
                    { min: 5, max: 7, color: '#ffaa00' },
                    { min: 7, max: 12, color: '#00cc44' }
                ]);
            }

            if (data.dew_point !== undefined) {
                createOrUpdateGauge('dew-gauge', data.dew_point, 10, -100, '', [
                    { min: -100, max: -45, color: '#00cc44' },
                    { min: -45, max: -10, color: '#ffaa00' },
                    { min: -10, max: 10, color: '#ff4444' }
                ]);
            }

            if (data.vacuo !== undefined) {
                createOrUpdateGauge('vacuo-gauge', Math.abs(data.vacuo), 760, 0, '', [
                    { min: 0, max: 300, color: '#ff4444' },
                    { min: 300, max: 500, color: '#ffaa00' },
                    { min: 500, max: 760, color: '#00cc44' }
                ]);
            }

            if (data.rede !== undefined) {
                createOrUpdateGauge('rede-gauge', data.rede, 12, 0, '', [
                    { min: 0, max: 5, color: '#ff4444' },
                    { min: 5, max: 8, color: '#ffaa00' },
                    { min: 8, max: 12, color: '#00cc44' }
                ]);
            }

        } catch (error) {
            console.error("Erro ao buscar dados:", error);
        }
    }

    // Atualiza a cada 5 segundos
    setInterval(updateData, 5000);

    // Atualiza ao carregar a página
    window.addEventListener('load', updateData);