import {plotDistribution} from "./utils.js";

let SCORE_TYPE = null;
let SCORE_VALUE = null;

async function getStructures(accession) {
    // $.fn.DataTable.ext.pager.numbers_length = 5;
    return $('#structures').DataTable({
        serverSide: true,
        processing: true,
        ajax: {
            url: `/api/entry/${accession}/alphafold/`,
            data: function (d) {
                new URLSearchParams(location.search)
                    .forEach((value, key) => {
                        d[key] = value;
                    });

                document.querySelectorAll('input[type="radio"]:checked')
                    .forEach((elem) => {
                        d[elem.name] = elem.value;
                    });

                if (SCORE_TYPE !== null && SCORE_VALUE !== null)
                    d[SCORE_TYPE] = SCORE_VALUE;
            },
        },
        lengthChange: false,
        pageLength: 15,
        searching: false,
        columns: [
            {
                data: 'id',
                render: function ( data ) {
                    return `<a href="https://www.ebi.ac.uk/interpro/protein/UniProt/${data}/alphafold/" target="_blank">${data}</a>`;
                    // return `<a href="https://alphafold.ebi.ac.uk/entry/${data}/" target="_blank">${data}</a>`;
                }
            },
            {
                data: 'reviewed',
                render: function ( data ) {
                    return data ? 'Reviewed (Swiss-Prot)' : 'Unreviewed (TrEMBL)';
                },
                sortable: false
            },
            {
                data: 'fragment',
                render: function ( data ) {
                    return data ? 'Fragment' : 'Complete';
                },
                sortable: false
            },
            {
                data: 'length',
                className: 'right-align',
                sortable: false
            },
            {
                data: 'species',
                sortable: false
            },
            {
                data: 'glo_score',
                className: 'right-align',
                render: function ( data ) {
                    return data.toFixed(2);
                }
            },
            {
                data: 'dom_score',
                className: 'right-align',
                render: function ( data ) {
                    return data.toFixed(2);
                }
            },
            {
                data: 'delta',
                className: 'right-align',
                render: function ( data, type, row, meta ) {
                    const d = row.dom_score - row.glo_score;

                    if ( type === 'sort')
                        return Math.abs(d)
                    else if (d < 0)
                        return d.toFixed(2);

                    return `+${d.toFixed(2)}`;
                }
            }
        ],
        order: [[6, 'desc']],
    });
}


function plotDistributions(entry, onClick) {
    const [total, gloChart] = plotDistribution({
        data: entry.distributions,
        elementId: 'glo-hist',
        chartHeight: 300,
        showLegend: false,
        title: {
            text: 'Mean sequence pLDDT',
            align: 'left',
            margin: 0,
            x: 30
        },
        xAxisCrosshair: true,
        xAxisTitle: null,
        onClick: onClick,
        showCredits: false
    });

    document.querySelector('h3 .sub-header').innerHTML = `${total.toLocaleString()} structures`;

    const [_, domChart] = plotDistribution({
        data: entry.distributions,
        elementId: 'dom-hist',
        chartHeight: 300,
        prefix: 'dom',
        title: {
            text: 'Mean domain pLDDT',
            align: 'left',
            margin: 0,
            x: 30
        },
        xAxisCrosshair: true,
        xAxisTitle: null,
        onClick: onClick,
        onShowSeries: function () {
            gloChart.series[this.index].show();
        },
        onHideSeries: function () {
            gloChart.series[this.index].hide();
        }
    });

    const yMax = Math.max(gloChart.yAxis[0].max, domChart.yAxis[0].max);

    [gloChart, domChart].forEach((chart) => {
        // chart.yAxis[0].update({ max: yMax });

        chart.pointer.reset = function () {
            return undefined;
        }
    });

    ['mousemove', 'touchmove', 'touchstart'].forEach((eventType,) => {
        document.getElementById('hists').addEventListener(eventType, (e,) => {
            [gloChart, domChart].forEach((chart,) => {
                // Find coordinates within the chart
                const event = chart?.pointer?.normalize(e);

                if (event === undefined)
                    return;

                // Get the hovered point
                const point = chart.series[0].searchPoint(event, true);

                if (point) {
                    // Highlight point
                    point.onMouseOver(); // Show the hover marker
                    point.series.chart.xAxis[0].drawCrosshair(event, point); // Show the crosshair
                }
            });
        });
    });
}

async function getEntry(accession) {
    const response = await fetch(`/api/entry/${accession}/`);
    const payload = await response.json();
    const entry = payload.results[0];

    document.title = `${entry.id} - ${entry.name} - ${document.title}`;
    document.getElementById('header').innerHTML = `
        ${entry.description}
        <div class="sub-header">${entry.name} &ndash; ${entry.id}</div>
    `;
    return entry;
}

document.addEventListener('DOMContentLoaded', () => {
    Promise.all([getEntry(ACCESSION), getStructures(ACCESSION)])
        .then(([entry, table]) => {
            const onClick = (point,) => {
                const score = point.name;
                if (score === SCORE_VALUE) {
                    SCORE_VALUE = null;
                    SCORE_TYPE = null;
                } else {
                    SCORE_VALUE = score;
                    SCORE_TYPE = point.series.chart.title.textStr === "Mean sequence pLDDT" ? 'glo_score' : 'dom_score';
                }

                table.ajax.reload();
            };

            plotDistributions(entry, onClick);

            ['fragment', 'origin']
                .forEach((name,) => {
                    document.querySelectorAll(`input[type="radio"][name="${name}"]`)
                        .forEach((elem) => {
                            elem.addEventListener('change', (e,) => {
                                plotDistributions(entry, onClick);
                                table.ajax.reload();
                            });
                        });
                });
        });
});