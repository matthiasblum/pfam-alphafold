export function getAlphaFoldColor(score) {
    if (score >= 90)
        return '#0053d6';
    else if (score >= 70)
        return '#65cbf3';
    else if (score >= 50)
        return '#ffdb13';
    else
        return '#ff7d45';
}

export function resetSearchInputs() {
    document.querySelectorAll('.dataTables_wrapper input[type="search"]')
        .forEach((elem,) => {
            elem.className = 'browser-default';
        });
}

export function plotDistribution(
    {
        data,
        elementId,
        chartHeight = 400,
        onClick = undefined,
        prefix = 'glo',
        showLegend = true,
        title = { text: null },
        xAxisCrosshair = false,
        xAxisTitle = 'Mean sequence pLDDT',
        onShowSeries = undefined,
        onHideSeries = undefined,
        showCredits = true
    }
) {
    const taxOption = document.querySelector('input[type="radio"][name="origin"]:checked').value;
    const fragOption = document.querySelector('input[type="radio"][name="fragment"]:checked').value;
    let suffix = fragOption === 'false' ? '_nofrags' : '';

    let series = [];
    const allSuperkingdoms = ['arch', 'bact', 'euk', 'others'];
    const names = ['Archaea', 'Bacteria', 'Eukaryotes', 'Others'];
    const colors = ['#2baad3', '#cd545c', '#69a753', '#a168bd'];

    if (taxOption === 'stacked') {
        allSuperkingdoms.forEach((sk, i) => {
            const hist = data[`${prefix}_${sk}${suffix}`].map((n, i) => ({
                name: i.toString(),
                y: n
            }));

            if (fragOption === 'true') {
                data[`${prefix}_${sk}_nofrags`].forEach((n, i) => {
                    hist[i].y -= n;
                });
            }

            series.push({
                name: names[i],
                color: colors[i],
                data: hist,
            })
        });
    } else {
        const superkingdoms = taxOption === 'merged' ? allSuperkingdoms : [taxOption];

        const hist = [...new Array(100)].map((_, i) => ({
            name: i.toString(),
            y: 0,
            color: getAlphaFoldColor(i)
        }));

        for (const sk of superkingdoms) {
            data[`${prefix}_${sk}${suffix}`].forEach((n, i) => {
                hist[i].y += n;
            });
        }

        if (fragOption === 'true') {
            for (const sk of superkingdoms) {
                data[`${prefix}_${sk}_nofrags`].forEach((n, i) => {
                    hist[i].y -= n;
                });
            }
        }

        series = series.concat([
            {
                name: 'Sequences',
                data: hist,
                showInLegend: false
            },
            {
                name: 'Very low',
                color: getAlphaFoldColor(0),
                events: {
                    legendItemClick: function(e) {
                        e.preventDefault()
                    }
                }
            },
            {
                name: 'Low',
                color: getAlphaFoldColor(50),
                events: {
                    legendItemClick: function(e) {
                        e.preventDefault()
                    }
                }
            },
            {
                name: 'Confident',
                color: getAlphaFoldColor(70),
                events: {
                    legendItemClick: function(e) {
                        e.preventDefault()
                    }
                }
            },
            {
                name: 'Very high',
                color: getAlphaFoldColor(90),
                events: {
                    legendItemClick: function(e) {
                        e.preventDefault()
                    }
                }
            }
        ]);
    }

    let total = 0;
    series
        .forEach((s,) => {
            if (s.data !== undefined)
                total += s.data.reduce((prev, value) => prev + value.y, 0);
        });

    return [
        total,
        Highcharts.chart(elementId, {
            chart: {
                type: 'column',
                height: chartHeight
            },
            title: { ...title },
            subtitle: { text: null },
            credits: { enabled: showCredits },
            legend: { enabled: showLegend },
            xAxis: {
                title: { text: xAxisTitle },
                type: 'category',
                crosshair: xAxisCrosshair,
                labels: {
                    step: 5
                }
            },
            yAxis: {
                title: { text: 'Structures' },
            },
            series: series,
            tooltip: {
                // Shared tooltip to force showing it even if y=0
                shared: true,
                formatter: function () {
                    let html = `<span style="font-size: 11px">${this.points[0].x} &le; pLDDT &lt; ${this.points[0].x+1}</span>`;

                    for (const point of this.points) {
                        html += `<br><span style="color:${point.color}">\u25CF</span> ${point.series.name}: <b>${point.y.toLocaleString()}</b>`;
                    }

                    return html;
                },
            },
            plotOptions: {
                column: {
                    pointPadding: 0.1,
                    borderWidth: 0,
                    groupPadding: 0,
                    shadow: false,
                    cursor: 'pointer',
                    stacking: 'normal',
                    point: {
                        events: {
                            click: function(e) {
                                if (onClick !== undefined) {
                                    onClick(e.point);
                                }
                            },
                        }
                    },
                    events: {
                        show: onShowSeries,
                        hide: onHideSeries
                    }
                }
            }
        })
    ];
}
