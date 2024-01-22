import {getAlphaFoldColor} from "./utils.js";

async function plotScoreVersusLength() {
    const params = new URLSearchParams(location.search);
    params.set('length', '0')
    const url = `/api/structures/?${params.toString()}`;

    const response = await fetch(url);
    const payload = await response.json();

    const series = new Map([
        [
            getAlphaFoldColor(0),
            {
                name: 'Very low',
                color: getAlphaFoldColor(0),
                data: [],
                extra: [],
            }
        ],
        [
            getAlphaFoldColor(50),
            {
                name: 'Low',
                color: getAlphaFoldColor(50),
                data: [],
                extra: [],
            }
        ],
        [
            getAlphaFoldColor(70),
            {
                name: 'Confident',
                color: getAlphaFoldColor(70),
                data: [],
                extra: [],
            }
        ],
        [
            getAlphaFoldColor(90),
            {
                name: 'Very high',
                color: getAlphaFoldColor(90),
                data: [],
                extra: [],
            }
        ],
    ]);

    let yMax  = 0;
    payload.data.map((entry,) => {
        if (entry.length > yMax) yMax = entry.length;

        const key = getAlphaFoldColor(entry.score);
        const val = series.get(key);
        val.data.push([entry.score, entry.length]);
        val.extra.push(entry.id);
    });

    Highcharts.chart('length-vs-score-chart', {
        chart: { zoomType: 'xy', type: 'scatter' },
        xAxis: {
            min: 0,
            max: 100,
            title: { text: 'Mean sequence pLDDT' },
        },
        yAxis: {
            min: 0,
            max: yMax,
            title: { text: 'Length' }
        },
        // credits: { enabled: false },
        title: { text: null },
        legend: { enabled: false },
        series: [...series.values()],
        plotOptions: {
            series: {
                marker: {
                    radius: 4,
                    symbol: 'circle'
                },
                point: {
                    events: {
                        click: function(event) {
                            const key = event.point.series.color;
                            const i = event.point.index;
                            const seqId = series.get(key).extra[i];
                            window.open(`https://www.ebi.ac.uk/interpro/protein/UniProt/${seqId}/alphafold/`, '_blank');
                            // window.open(`https://alphafold.ebi.ac.uk/entry/${seqId}/`, '_blank');
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
                const seqId = series.get(key).extra[i];
                return `
                    <span style="font-size: 11px">${seqId}</span><br>
                    pLDDT: <b>${this.point.x.toFixed(1)}</b><br>
                    Length: <b>${this.point.y.toLocaleString()}</b>
                `;
            }
        }
    });
}

async function initTableOfStructures(onLoad) {
    return $('#structures')
        .on('xhr.dt', (e, settings, json, xhr) => {
            onLoad(e, json);
        })
        .DataTable({
            serverSide: true,
            processing: true,
            ajax: {
                url: '/api/structures/',
                data: function (d) {
                    new URLSearchParams(location.search).forEach((value, key) => {
                        d[key] = value;
                    });
                }
            },
            lengthChange: false,
            searching: false,
            pageLength: 15,
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
                    data: 'organism',
                    sortable: false
                },
                {
                    data: 'score',
                    className: 'right-align',
                    render: function ( data ) {
                        return data.toFixed(5);
                    }
                },
                {
                    data: 'in_pfam',
                    className: 'center-align',
                    sortable: false,
                    render: function ( data ) {
                        if (data) {
                            return `
                                <label>
                                    <input type="checkbox" class="filled-in" checked="checked" disabled="disabled" />
                                    <span></span>
                                </label>                            
                            `;
                        }
                        return '';
                    }
                }
            ],
            order: [[5, 'desc']],
        });
}

document.addEventListener('DOMContentLoaded', () => {
    let table = null;
    const params = new URLSearchParams(location.search);

    if (!params.has('score'))
        params.set('score', '-1');

    params.forEach((value, key) => {
        const input = document.querySelector(`input[name="${key}"]`);
        if (input === null)
            return;

        if (input.type === 'radio') {
            console.log(key, value);
            document.querySelector(`input[name="${key}"][value="${value}"]`).checked = true;
        } else {
            input.value = value;
        }
    });

    let drawChart = true;
    initTableOfStructures((event, json) => {
        // console.log(event, json);
    })
        .then((result) => {
            table = result;
        });

    document.querySelectorAll('input')
        .forEach((input) => {
            input.addEventListener('change', (e) => {
                const input = e.currentTarget;
                const name = input.name;
                const value = input.value.trim();

                const url = new URL(location.href);

                if (value.length > 0)
                    url.searchParams.set(input.name, input.value);
                else if (url.searchParams.has(name))
                    url.searchParams.delete(name);

                history.replaceState(null, '', url.toString());

                if (table !== null) {
                    table.ajax.reload();
                    drawChart = true;
                }
            });
        });

    document.getElementById('length-vs-score-btn')
        .addEventListener('click', (event) => {
            plotScoreVersusLength();
        });
});