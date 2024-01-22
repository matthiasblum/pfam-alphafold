import {
    getAlphaFoldColor,
    plotDistribution,
    resetSearchInputs
} from "./utils.js";

function useSummaryHist() {
    return document.querySelector('input[name="hist-type"]:checked').value === 'summary';
}

function initEntriesTable() {
    // let summaryHist = useSummaryHist();
    const summaryHist = false;

    $('#entries').DataTable({
        serverSide: true,
        processing: true,
        ajax: {
            url: '/api/entries/',
            // Extra param
            // data: function (d) {
            //     d.summary = summaryHist;
            // },
            // Do not look for the 'data' property in the payload
            // dataSrc: ''
        },
        initComplete: function (settings, data) {
        },
        lengthChange: false,
        pageLength: 15,
        columns: [
            {
                data: 'id',
                render: function ( data ) {
                    return `<a href="/entry/${data}/">${data}</a>`;
                }
            },
            {
                data: 'name'
            },
            {
                data: 'description',
                visible: false,
            },
            {
                data: 'count',
                render: function ( data ) {
                    return data.toLocaleString();
                }
            },
            {
                data: 'glo_score',
                render: function ( data ) {
                    return data.toFixed(2);
                }
            },
            {
                data: 'glo_hist',
            },
            {
                data: 'dom_score',
                render: function ( data ) {
                    return data.toFixed(2);
                }
            },
            {
                data: 'dom_hist',
            },
            {
                data: 'delta',
                render: function ( data ) {
                    if (data < 0)
                        return data.toFixed(2);

                    return `+${data.toFixed(2)}`;
                }
            }
        ],
        columnDefs: [
            {
                targets: [3, 4, 6, 8],
                className: 'right-align',
                searchable: false,
            },
            {
                targets: [5, 7],
                data: null,
                className: 'center-align',
                orderable: false,
                render: function ( data, type, row, meta ) {
                    if (summaryHist) {
                        const arr = [data.m50, data.p50, data.p70, data.p90];

                        arr.forEach((n, i) => {
                            arr[i] = Math.floor(n * 100 / row.count);
                        });

                        const max = Math.max(...arr);
                        const d = 100 - arr.reduce((p, c) => p + c);

                        if (d > 0) {
                            const i = arr.indexOf(max);
                            arr[i] += d;
                        }

                        return [
                            '<div class="histobar">',
                            `<div style="width: ${arr[0]}%; background-color: ${getAlphaFoldColor(0)};"></div>`,
                            `<div style="width: ${arr[1]}%; background-color: ${getAlphaFoldColor(50)};"></div>`,
                            `<div style="width: ${arr[2]}%; background-color: ${getAlphaFoldColor(70)};"></div>`,
                            `<div style="width: ${arr[3]}%; background-color: ${getAlphaFoldColor(90)};"></div>`,
                            '</div>'
                        ].join('');
                    } else {
                        let html = '<svg xmlns="http://www.w3.org/2000/svg" class="hist" width="200" height="15">';
                        let color = null;
                        let x = 0;
                        let width = 0;

                        data.forEach((n, i) => {
                            if (n > 0) {
                                const _color = getAlphaFoldColor(i);

                                if (_color === color) {
                                    width++;
                                    return;
                                }

                                if (color !== null) {
                                    html += `<rect x="${x*2}" width="${width*2}" y="0" height="100%" fill="${color}" />`;
                                }

                                color = _color;
                                width = 1;
                                x = i;
                                return;
                            }

                            if (color !== null) {
                                html += `<rect x="${x*2}" width="${width*2}" y="0" height="100%" fill="${color}" />`;
                                color = null;
                                width = 1;
                                x = i;
                                return;
                            }

                            x++;
                        });

                        if (color !== null)
                            html += `<rect x="${x}%" width="${width}%" y="0" height="100%" fill="${color}" />`;

                        // html += '</div>';
                        html += '</svg>';
                        return html;
                    }
                }
            },
        ]
    });

    resetSearchInputs();
    // document.querySelectorAll('input[name="hist-type"]')
    //     .forEach((elem) => {
    //         elem.addEventListener('change', (e,) => {
    //             summaryHist = useSummaryHist();
    //             table.ajax.reload();
    //         });
    //     });
}

async function plotAlphaFold() {
    const response = await fetch('/api/entry/alphafold/');
    const payload = await response.json()
    const result = payload.results[0];

    const inputs =  ['fragment', 'origin'];
    const params = {
        data: result.distributions,
        elementId: 'distribution',
        onClick: (point,) => {
            const params = new URLSearchParams();
            params.set('score', point.name);
            inputs.forEach((name,) => {
                const value = document.querySelector(`input[name="${name}"]:checked`).value;
                if (value.length)
                    params.set(name, value);
            });

            location.href = `/structures/?${params.toString()}`;
        }
    };

    let [total, _] = plotDistribution(params);
    document.querySelector('.sub-header').innerHTML = `${total.toLocaleString()} structures`;

    inputs.forEach((name,) => {
        document.querySelectorAll(`input[type="radio"][name="${name}"]`)
            .forEach((elem) => {
                elem.addEventListener('change', (e,) => {
                    [total, _] = plotDistribution(params);
                    document.querySelector('.sub-header').innerHTML = `${total.toLocaleString()} structures`;
                });
            });
    });
}

async function plotEntries() {
    const response = await fetch('/api/entries/?basic=true');
    const payload = await response.json();
    const data = payload.data;

    const series = new Map([
        [
            getAlphaFoldColor(0),
            {
                name: 'Very low',
                color: getAlphaFoldColor(0),
                data: [],
                extra: []
            }
        ],
        [
            getAlphaFoldColor(50),
            {
                name: 'Low',
                color: getAlphaFoldColor(50),
                data: [],
                extra: []
            }
        ],
        [
            getAlphaFoldColor(70),
            {
                name: 'Confident',
                color: getAlphaFoldColor(70),
                data: [],
                extra: []
            }
        ],
        [
            getAlphaFoldColor(90),
            {
                name: 'Very high',
                color: getAlphaFoldColor(90),
                data: [],
                extra: []
            }
        ],
    ]);

    let yMax = 0;
    data.map((entry,) => {
        if (entry.count === 0) return;
        if (entry.count > yMax) yMax = entry.count;
        const key = getAlphaFoldColor(entry.dom_score);
        const s = series.get(key);
        s.data.push([entry.dom_score, entry.count])
        s.extra.push({id: entry.id, name: entry.name})
    });

    Highcharts.chart('sequences-vs-score', {
        chart: { zoomType: 'xy', type: 'scatter' },
        xAxis: {
            min: 0,
            max: 100,
            title: { text: 'Mean domain pLDDT' },
        },
        yAxis: {
            min: 0,
            max: yMax,
            title: { text: 'Sequences' },
            // type: 'logarithmic',
            events: {
                setExtremes(e) {
                    let radius;

                    if (e.min === undefined && e.max === undefined) {
                        radius = 1;
                    } else {
                        const s = e.max - e.min;

                        if (s < 1000)
                            radius = 4;
                        else if (s < 5000)
                            radius = 3;
                        else if (s < 10000)
                            radius = 2;
                        else
                            return;
                    }

                    this.chart.series.forEach(series => {
                        series.update({
                            marker: {
                                radius: radius
                            }
                        })
                    });
                }
            }
        },
        // credits: { enabled: false },
        title: { text: null },
        legend: { enabled: false },
        series: [...series.values()],
        plotOptions: {
            series: {
                marker: {
                    radius: 1,
                    symbol: 'circle'
                },
                point: {
                    events: {
                        click: function(event) {
                            const key = event.point.series.color;
                            const i = event.point.index;
                            const entry = series.get(key).extra[i];
                            window.open(`/entry/${entry.id}/`, '_blank');
                        },
                        mouseOver: function() {
                            if (this.series.halo) {
                                this.series.halo.attr({
                                    'class': 'highcharts-tracker',
                                }).toFront();
                            }
                        }
                    }
                },
            }
        },
        tooltip: {
            followPointer: false,
            formatter: function() {
                const key = this.point.series.color;
                const i = this.point.index;
                const entry = series.get(key).extra[i];
                return `
                    <span style="font-size: 11px">${entry.name}</span><br>
                    pLDDT: <b>${this.point.x.toFixed(1)}</b><br>
                    sequences: <b>${this.point.y.toLocaleString()}</b>
                `;
            }
        }

    });
}

async function initSpecies() {
    const params = new URLSearchParams();

    document.querySelectorAll('[data-taxon-id]')
        .forEach((elem) => {
            params.append('id', elem.dataset.taxonId);
        });

    const response = await fetch(`/api/species/?${params.toString()}`);
    const results = await response.json();

    const species = new Map();
    results.forEach((item) => {
        species.set(item.id, item);
    });

    params.getAll('id').forEach((taxonId) => {
        const elem = document.querySelector(`[data-taxon-id="${taxonId}"]`);
        if (elem !== null) {
            const count = species.has(taxonId) ? species.get(taxonId).count : 0;
            elem.querySelector(':scope > p')
                .innerHTML = count > 0 ? `<a href="/structures/?species=${taxonId}">${count.toLocaleString()} structures</a>` : '0 structures';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    plotAlphaFold();
    initEntriesTable();
    initSpecies();
    plotEntries();
});