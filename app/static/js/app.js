let map=null, markers=[], charts={}, state={years:[2022,2023,2024,2025], activeYears:{2022:true,2023:true,2024:true,2025:true}, data:{}, page:'overview'};
const MONTHS=['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
const COLORS={HH:'#ef4444',HL:'#f59e0b',LH:'#3b82f6',LL:'#6366f1',NS:'#64748b'};
const YEAR_COLORS={2022:'#f97316',2023:'#38bdf8',2024:'#a78bfa',2025:'#22d3ee'};
const SEASON=[0.055,0.065,0.15,0.18,0.14,0.085,0.075,0.13,0.115,0.08,0.06,0.05];
const chartBase={responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9bc3ef',boxWidth:12,font:{family:'Inter',size:12}}},tooltip:{backgroundColor:'#111f35',titleColor:'#e2e8f0',bodyColor:'#9bc3ef',borderColor:'#1e3354',borderWidth:1}},scales:{x:{grid:{color:'rgba(30,51,84,.75)'},ticks:{color:'#4a6380',font:{family:'Inter',size:11}}},y:{grid:{color:'rgba(30,51,84,.75)'},ticks:{color:'#4a6380',font:{family:'Inter',size:11}},beginAtZero:true}}};
async function getJSON(url){const r=await fetch(url); if(!r.ok) throw new Error(url); return r.json();}
function fmt(n){return Number(n||0).toLocaleString('id-ID');}
function makeChart(id,cfg){const el=document.getElementById(id); if(!el)return; if(charts[id])charts[id].destroy(); charts[id]=new Chart(el,cfg);}
function getSelectedYear(id){return parseInt(document.getElementById(id).value||'2025');}
function setOptions(){['overviewYear','mapYear','spatialYear'].forEach(id=>{const el=document.getElementById(id); if(!el)return; el.innerHTML=state.years.map(y=>`<option value="${y}" ${y===2025?'selected':''}>${y}</option>`).join('');});}
function monthlyForYear(year){const ts=state.data.ts||{annual:[],monthly:[]}; const detail=ts.monthly.filter(x=>x.tahun===year); if(detail.length){let arr=Array(12).fill(0); detail.forEach(x=>arr[x.bulan-1]=x.jumlah_kasus); return arr;} const ann=(ts.annual||[]).find(x=>x.tahun===year)?.jumlah_kasus||0; let arr=SEASON.map(w=>Math.round(ann*w)); let diff=ann-arr.reduce((a,b)=>a+b,0); if(arr.length) arr[3]+=diff; return arr;}
function lisaLabel(c){return {HH:'HH – Hotspot',HL:'HL – Spatial Outlier',LH:'LH – Spatial Outlier',LL:'LL – Coldspot',NS:'NS – Tidak Signifikan'}[c]||c;}
function lisaText(c){return {HH:'Kasus tinggi dikelilingi kecamatan berkasus tinggi',HL:'Kasus tinggi dikelilingi kecamatan berkasus rendah',LH:'Kasus rendah dikelilingi kecamatan berkasus tinggi',LL:'Kasus rendah dikelilingi kecamatan berkasus rendah',NS:'Tidak signifikan'}[c]||'-';}
async function loadYearData(year){if(state.data.kec?.[year]&&state.data.spatial?.[year])return; const [kec,sp]=await Promise.all([getJSON('/api/kecamatan?year='+year),getJSON('/api/spatial?year='+year)]); state.data.kec=state.data.kec||{}; state.data.spatial=state.data.spatial||{}; state.data.kec[year]=kec; state.data.spatial[year]=sp;}
async function init(){setOptions(); const [summary,ts,fc]=await Promise.all([getJSON('/api/summary'),getJSON('/api/timeseries'),getJSON('/api/forecast?steps=6')]); state.data.summary=summary; state.data.ts=ts; state.data.fc=fc; const yrs=[...new Set([...(ts.annual||[]).map(x=>x.tahun),2025])].sort(); if(yrs.length) state.years=yrs; setOptions(); await loadYearData(2025); initNav(); bindEvents(); fillKecamatanSelect(); renderAll();}
function initNav(){document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>showPage(btn.dataset.page)));}
function showPage(page){state.page=page; document.querySelectorAll('.page').forEach(p=>p.classList.remove('active')); document.getElementById('page-'+page)?.classList.add('active'); document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page)); setTimeout(()=>{if(page==='webgis'&&map) map.invalidateSize(); if(page==='integrasi'&&state.integrasiMap) state.integrasiMap.invalidateSize();},120);}
function bindEvents(){['overviewYear','mapYear','spatialYear'].forEach(id=>document.getElementById(id)?.addEventListener('change',renderAll)); document.getElementById('mapMode')?.addEventListener('change',renderWebGIS); document.querySelectorAll('.year-tabs button').forEach(b=>b.addEventListener('click',()=>{state.activeYears[b.dataset.y]=!state.activeYears[b.dataset.y]; b.classList.toggle('active',state.activeYears[b.dataset.y]); renderTimeSeries();})); document.getElementById('tsKecamatan')?.addEventListener('change',renderTimeSeries); document.getElementById('runPredict')?.addEventListener('click',runPredict); document.getElementById('uploadForm')?.addEventListener('submit',uploadDataset);}
function fillKecamatanSelect(){const rows=state.data.kec?.[2025]||[]; const el=document.getElementById('tsKecamatan'); if(!el)return; el.innerHTML='<option value="all">Semua Kecamatan</option>'+rows.map(r=>`<option value="${r.kecamatan}">${r.kecamatan}</option>`).join('');}
async function renderAll(){await Promise.all([loadYearData(getSelectedYear('overviewYear')),loadYearData(getSelectedYear('mapYear')),loadYearData(getSelectedYear('spatialYear')),loadYearData(2025)]); renderOverview(); renderWebGIS(); renderSpatial(); renderTimeSeries(); renderRF(); renderIntegrasi(); renderLaporan();}
function renderOverview() {
    const year = getSelectedYear('overviewYear');
    const rows = state.data.kec[year] || [];
    const sp = state.data.spatial[year] || {};
    const clusters = sp.clusters || [];

    const total = rows.reduce(
        (a, b) => a + Number(b.jumlah_kasus || 0),
        0
    );

    document.getElementById('ovTotal').textContent = fmt(total);
    document.getElementById('ovTotalSub').textContent = `Tahun ${year} · ${rows.length} kecamatan`;

    document.getElementById('ovMoran').textContent = sp.moran_i ?? '-';
    document.getElementById('ovMoranSub').textContent = sp.z_score
        ? `Z-score ${sp.z_score}`
        : 'Data belum cukup';

    const hh = clusters.filter(x => x.lisa_cluster === 'HH').length;
    document.getElementById('ovHH').textContent = hh;
    document.getElementById('ovHHSub').textContent = `dari ${rows.length} kecamatan`;



    const arr = monthlyForYear(year);

    makeChart('ovTrendChart', {
        type: 'line',
        data: {
            labels: MONTHS,
            datasets: [{
                label: 'Kasus ' + year,
                data: arr,
                borderColor: YEAR_COLORS[year] || '#22d3ee',
                backgroundColor: 'rgba(139,92,246,.16)',
                fill: true,
                tension: .42,
                pointRadius: 4,
                borderWidth: 2
            }]
        },
        options: chartBase
    });

    const top = [...rows]
        .map(r => ({
            kecamatan: r.kecamatan || r.Kecamatan || r.nama || '-',
            jumlah_kasus: Number(
                r.jumlah_kasus ||
                r.Jumlah_Kasus ||
                r.kasus ||
                r.total_kasus ||
                0
            )
        }))
        .filter(r => r.jumlah_kasus > 0)
        .sort((a, b) => b.jumlah_kasus - a.jumlah_kasus)
        .slice(0, 5);

    console.log("TOP 5 KECAMATAN:", top);

    makeChart('ovTopChart', {
        type: 'doughnut',
        data: {
            labels: top.map(x => x.kecamatan),
            datasets: [{
                label: 'Jumlah Kasus',
                data: top.map(x => x.jumlah_kasus),
                backgroundColor: [
                    'rgba(239,68,68,.90)',
                    'rgba(249,115,22,.90)',
                    'rgba(245,158,11,.90)',
                    'rgba(34,211,238,.90)',
                    'rgba(59,130,246,.90)'
                ],
                borderColor: '#0f1e38',
                borderWidth: 3,
                hoverOffset: 12,
                spacing: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '58%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#9bc3ef',
                        font: {
                            family: 'Inter',
                            size: 11
                        },
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 14
                    }
                },
                tooltip: {
                    backgroundColor: '#111f35',
                    titleColor: '#e2e8f0',
                    bodyColor: '#9bc3ef',
                    borderColor: '#1e3354',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const totalTop = context.dataset.data.reduce(
                                (a, b) => a + b,
                                0
                            );

                            const value = context.raw;
                            const percent = totalTop
                                ? ((value / totalTop) * 100).toFixed(1)
                                : 0;

                            return `${context.label}: ${fmt(value)} kasus (${percent}%)`;
                        }
                    }
                }
            }
        }
    });

    makeChart('ovCompareChart', {
        type: 'bar',
        data: {
            labels: MONTHS,
            datasets: state.years.map(y => ({
                label: String(y),
                data: monthlyForYear(y),
                backgroundColor: (YEAR_COLORS[y] || '#22d3ee') + 'bb',
                borderColor: YEAR_COLORS[y] || '#22d3ee',
                borderWidth: 2,
                borderRadius: 4
            }))
        },
        options: chartBase
    });
}
function renderWebGIS(){const year=getSelectedYear('mapYear'), mode=document.getElementById('mapMode').value, sp=state.data.spatial[year]||{}, rows=(sp.clusters?.length?sp.clusters:state.data.kec[year])||[]; if(!map){map=L.map('map').setView([-7.02,113.87],9); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(map);} markers.forEach(m=>m.remove()); markers=[]; const max=Math.max(...rows.map(r=>r.jumlah_kasus),1); rows.forEach(r=>{let color=mode==='lisa'?(COLORS[r.lisa_cluster]||'#64748b'):caseColor(r.jumlah_kasus,max); const marker=L.circleMarker([r.lat,r.lng],{radius:7+(r.jumlah_kasus/max)*21,color:'rgba(255,255,255,.55)',weight:1.4,fillColor:color,fillOpacity:.86}).addTo(map); marker.bindPopup(`<b>${r.kecamatan}</b><br>Kasus ${year}: <b>${r.jumlah_kasus}</b><br>LISA: <b>${r.lisa_cluster||'-'}</b><br>Spatial Lag: ${r.spatial_lag??'-'}`); markers.push(marker);}); document.getElementById('mapLegend').innerHTML=mode==='lisa'?Object.keys(COLORS).filter(k=>k!=='NS').map(k=>`<span><i class="dot" style="background:${COLORS[k]}"></i>${lisaLabel(k)}</span>`).join(''):`<span><i class="dot" style="background:#2563eb"></i>Rendah</span><span><i class="dot" style="background:#16a34a"></i>Sedang</span><span><i class="dot" style="background:#f59e0b"></i>Tinggi</span><span><i class="dot" style="background:#dc2626"></i>Sangat Tinggi</span>`; document.getElementById('kecTable').innerHTML=rows.map((r,i)=>`<tr><td>${i+1}</td><td><b>${r.kecamatan}</b></td><td>${r.jumlah_kasus}</td><td>${r.spatial_lag??'-'}</td><td><span class="badge b-${r.lisa_cluster||'NS'}">${r.lisa_cluster||'-'}</span></td><td style="color:#10b981;font-size:18px;font-weight:900">↓</td></tr>`).join(''); setTimeout(()=>map.invalidateSize(),80);}
function caseColor(v,max){const r=v/max; if(r>.7)return '#dc2626'; if(r>.5)return '#f97316'; if(r>.3)return '#f59e0b'; if(r>.15)return '#16a34a'; return '#2563eb';}
function renderSpatial(){const year=getSelectedYear('spatialYear'), sp=state.data.spatial[year]||{}, rows=sp.clusters||[]; document.getElementById('spMoran').textContent=sp.moran_i??'-'; document.getElementById('spMoranSub').textContent=`Expected I: ${sp.expected_i??'-'} · Z-score: ${sp.z_score??'-'} · p-value: ${sp.p_value??'-'}`; document.getElementById('spInterpretasi').innerHTML=sp.moran_i!=null?`Nilai Moran's I = <b style="color:#22d3ee">${sp.moran_i}</b>. Nilai ini dihitung dari jumlah kasus per kecamatan, GeoJSON kecamatan Sumenep, dan spatial lag wilayah sekitar.`:'Data belum cukup untuk menghitung Moran dan LISA.'; const counts={HH:0,LH:0,HL:0,LL:0}; rows.forEach(r=>{if(counts[r.lisa_cluster]!=null)counts[r.lisa_cluster]++;}); makeChart('lisaBarChart',{type:'bar',data:{labels:Object.keys(counts).map(lisaLabel),datasets:[{data:Object.values(counts),backgroundColor:Object.keys(counts).map(k=>COLORS[k]+'dd'),borderColor:Object.keys(counts).map(k=>COLORS[k]),borderWidth:2,borderRadius:6}]},options:{...chartBase,plugins:{...chartBase.plugins,legend:{display:false}}}}); const scatter=(sp.scatter&&sp.scatter.length)?sp.scatter:rows.map(r=>({x:r.z_score_local||0,y:r.lag_z||0,cluster:r.lisa_cluster,kecamatan:r.kecamatan})); makeChart('moranScatterChart',{type:'scatter',data:{datasets:[{label:'Kecamatan',data:scatter.map(r=>({x:Number(r.x),y:Number(r.y),kecamatan:r.kecamatan})),backgroundColor:scatter.map(r=>(COLORS[r.cluster]||'#22d3ee')+'bb'),borderColor:'#22d3ee',pointRadius:6},{label:`Garis Regresi (I=${sp.moran_i??'-'})`,type:'line',data:[{x:-3,y:-3*(sp.moran_i||0)},{x:3,y:3*(sp.moran_i||0)}],borderColor:'#f97316',borderDash:[5,4],pointRadius:0,borderWidth:2}]},options:{...chartBase,plugins:{...chartBase.plugins,tooltip:{...chartBase.plugins.tooltip,callbacks:{label:(ctx)=>{const r=ctx.raw; return `${r.kecamatan||'Kecamatan'}: z=${Number(r.x).toFixed(2)}, lag=${Number(r.y).toFixed(2)}`;}}}},scales:{x:{...chartBase.scales.x,type:'linear',min:-3,max:3,title:{display:true,text:'Standardized Kasus (z-score)',color:'#4a6380'}},y:{...chartBase.scales.y,min:-3,max:3,beginAtZero:false,title:{display:true,text:'Standardized Spatial Lag',color:'#4a6380'}}}}}); document.getElementById('lisaTable').innerHTML=rows.sort((a,b)=>b.jumlah_kasus-a.jumlah_kasus).map(r=>`<tr><td><b>${r.kecamatan}</b></td><td>${r.jumlah_kasus}</td><td>${r.spatial_lag??'-'}</td><td><span class="badge b-${r.lisa_cluster}">${r.lisa_cluster}</span></td><td>${lisaText(r.lisa_cluster)}</td></tr>`).join('');}
function renderTimeSeries(){const selected=document.getElementById('tsKecamatan')?.value||'all'; const datasets=state.years.filter(y=>state.activeYears[y]).map(y=>{let arr=monthlyForYear(y); if(selected!=='all'){const row=(state.data.kec?.[y]||[]).find(r=>r.kecamatan===selected); const total=(state.data.kec?.[y]||[]).reduce((a,b)=>a+b.jumlah_kasus,0)||1; arr=arr.map(v=>Math.round(v*((row?.jumlah_kasus||0)/total)));} return {label:String(y),data:arr,borderColor:YEAR_COLORS[y]||'#22d3ee',backgroundColor:(YEAR_COLORS[y]||'#22d3ee')+'22',fill:true,tension:.42,pointRadius:3,borderWidth:2};}); makeChart('tsMultiChart',{type:'line',data:{labels:MONTHS,datasets},options:chartBase}); const avg=MONTHS.map((_,i)=>Math.round(state.years.reduce((s,y)=>s+monthlyForYear(y)[i],0)/state.years.length)); makeChart('seasonChart',{type:'bar',data:{labels:MONTHS,datasets:[{data:avg,backgroundColor:avg.map(v=>v>Math.max(...avg)*.75?'#ef4444bb':v>Math.max(...avg)*.5?'#f59e0bbb':'#22d3eebb'),borderRadius:5}]},options:{...chartBase,plugins:{...chartBase.plugins,legend:{display:false}}}}); const annual=state.data.ts.annual||[]; const yoy=[]; for(let i=1;i<annual.length;i++)yoy.push({label:`${annual[i-1].tahun}→${annual[i].tahun}`,val:+(((annual[i].jumlah_kasus-annual[i-1].jumlah_kasus)/(annual[i-1].jumlah_kasus||1))*100).toFixed(1)}); makeChart('yoyChart',{type:'line',data:{labels:yoy.map(x=>x.label),datasets:[{label:'YoY (%)',data:yoy.map(x=>x.val),borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,.15)',fill:true,tension:.35}]},options:{...chartBase,scales:{x:chartBase.scales.x,y:{...chartBase.scales.y,beginAtZero:false}}}});}
function renderRF(){const fc=state.data.fc||{}, fi=fc.feature_importance||[]; const labels=fi.length?fi.map(x=>x.feature):['lag_1','lag_2','lag_3','bulan','tren','spatial_lag']; const vals=fi.length?fi.map(x=>x.importance):[0,0,0,0,0,0]; makeChart('featureChart',{type:'bar',data:{labels:labels,datasets:[{label:'Feature Importance',data:vals,backgroundColor:['#22d3eecc','#38bdf8cc','#60a5facc','#818cf8cc','#a78bfacc','#c4b5fdcc'],borderColor:'#22d3ee',borderWidth:1,borderRadius:6}]},options:{...chartBase,indexAxis:'y',plugins:{...chartBase.plugins,legend:{display:false}},scales:{x:{...chartBase.scales.x,beginAtZero:true,max:1},y:chartBase.scales.y}}});}
async function runPredict(){const l1=+document.getElementById('lag1').value||0,l2=+document.getElementById('lag2').value||0,l3=+document.getElementById('lag3').value||0,l4=+document.getElementById('lag4').value||0,m=+document.getElementById('predMonth').value||1,y=+document.getElementById('predYear').value||2026; try { const r=await getJSON(`/api/predict?lag1=${l1}&lag2=${l2}&lag3=${l3}&lag4=${l4}&month=${m}&year=${y}`); if(r.error) throw new Error(r.error); const pred=Math.round(r.prediction||0); let risiko=pred>80?'Risiko TINGGI':pred>40?'Risiko SEDANG':'Risiko RENDAH'; document.getElementById('predResult').textContent=pred; document.getElementById('predNote').innerHTML=`kasus prediksi bulan ${MONTHS[m-1]} ${y} · <b style="color:${pred>80?'#ef4444':pred>40?'#f59e0b':'#10b981'}">${risiko}</b>`; } catch(err) { console.error(err); alert('Gagal menjalankan prediksi model dari server.'); }}
function renderEvaluasi(){}
function renderIntegrasi(){
  // This is an async self-executing wrapper
  (async function(){
    const sp=state.data.spatial[2025]||{};
    const clusters=sp.clusters||[];
    if(!clusters.length) return;

    // Fetch 12-step forecast if not cached
    if(!state.data.fc12){
      try { state.data.fc12=await getJSON('/api/forecast?steps=12'); } catch(e){ state.data.fc12={forecast:[]}; }
    }
    const forecasts12=state.data.fc12.forecast||[];

    // Fetch GeoJSON if not cached
    if(!state.data.geojson){
      try { state.data.geojson=await getJSON('/api/geojson'); } catch(e){ state.data.geojson=null; }
    }

    // LISA score weights
    const lisaScoreMap={HH:4,HL:3,LH:2,LL:1,NS:1};

    // Build monthly RF map per kecamatan: { KEC: { 1: val, 2: val, ... , total: val } }
    const rfMonthly={};
    const rfTotalMap={};
    forecasts12.forEach(f=>{
      const k=f.kecamatan;
      if(!rfMonthly[k]) rfMonthly[k]={};
      rfMonthly[k][f.bulan]=(rfMonthly[k][f.bulan]||0)+Number(f.predicted||0);
      rfTotalMap[k]=(rfTotalMap[k]||0)+Number(f.predicted||0);
    });

    const allCases=clusters.map(r=>r.jumlah_kasus||0);
    const maxCases=Math.max(...allCases,1);
    const maxRF=Math.max(...Object.values(rfTotalMap),1)||1;

    // Build priority rows
    const rows=clusters.map(r=>{
      const kec=r.kecamatan;
      const lisa=r.lisa_cluster||'NS';
      const kasus=r.jumlah_kasus||0;
      const rfTotal=rfTotalMap[kec]||0;
      const skorLISA=(lisaScoreMap[lisa]||1)/4;
      const skorKasus=kasus/maxCases;
      const skorRF=rfTotal/maxRF;
      const skor=((skorLISA*0.5)+(skorKasus*0.3)+(skorRF*0.2));
      let prioritas,warna,rekomendasi,pNum;
      if(skor>=0.65||lisa==='HH'){
        prioritas='I – Sangat Tinggi'; warna='#ef4444'; pNum=1;
        rekomendasi='Intervensi segera: surveilans intensif, sweeping imunisasi, dan investigasi KLB';
      } else if(skor>=0.40||(lisa==='HL'&&kasus>0)){
        prioritas='II – Tinggi'; warna='#f97316'; pNum=2;
        rekomendasi='Pemantauan mingguan, peningkatan cakupan imunisasi, dan kesiapan respon cepat';
      } else if(skor>=0.20||lisa==='LH'){
        prioritas='III – Sedang'; warna='#f59e0b'; pNum=3;
        rekomendasi='Imunisasi rutin ditingkatkan, edukasi masyarakat, dan pemantauan bulanan';
      } else {
        prioritas='IV – Rendah'; warna='#10b981'; pNum=4;
        rekomendasi='Pertahankan imunisasi rutin dan surveilans berkala';
      }
      return {kec,lisa,kasus,rfTotal:Math.round(rfTotal),skor:+(skor*100).toFixed(1),prioritas,warna,pNum,rekomendasi,lat:r.lat,lng:r.lng};
    }).sort((a,b)=>b.skor-a.skor);

    // Priority lookup by kecamatan name
    const priorityMap={};
    rows.forEach(r=>{ priorityMap[r.kec]=r; });

    // KPI counts
    const c1=rows.filter(r=>r.pNum===1).length;
    const c2=rows.filter(r=>r.pNum===2).length;
    const c3=rows.filter(r=>r.pNum===3).length;
    const c4=rows.filter(r=>r.pNum===4).length;
    document.getElementById('iKpi1').textContent=c1+' kecamatan';
    document.getElementById('iKpi2').textContent=c2+' kecamatan';
    document.getElementById('iKpi3').textContent=c3+' kecamatan';
    document.getElementById('iKpi4').textContent=c4+' kecamatan';

    // ========== LEAFLET MAP ==========
    const mapEl=document.getElementById('integrasiMap');
    if(mapEl){
      // Initialize map if not yet
      if(!state.integrasiMap){
        state.integrasiMap=L.map('integrasiMap').setView([-7.02,113.87],9);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(state.integrasiMap);
      }
      const imap=state.integrasiMap;

      // Remove old layers
      if(state.integrasiLayers){
        state.integrasiLayers.forEach(l=>l.remove());
      }
      state.integrasiLayers=[];

      // Render GeoJSON choropleth if available
      if(state.data.geojson && state.data.geojson.features){
        const geoLayer=L.geoJSON(state.data.geojson,{
          style: function(feature){
            const kecStd=feature.properties.kecamatan_std||'';
            const info=priorityMap[kecStd];
            const fillColor=info?info.warna:'#334155';
            return {fillColor:fillColor, weight:2, opacity:1, color:'rgba(255,255,255,0.5)', fillOpacity:0.7};
          },
          onEachFeature: function(feature, layer){
            const kecStd=feature.properties.kecamatan_std||'';
            const info=priorityMap[kecStd];
            if(info){
              layer.bindPopup(`<div style="min-width:200px"><b style="font-size:14px">${info.kec}</b><br><hr style="margin:6px 0;border-color:rgba(255,255,255,.2)"><table style="width:100%;font-size:12px"><tr><td>Klaster LISA</td><td style="text-align:right"><b>${info.lisa}</b></td></tr><tr><td>Kasus 2025</td><td style="text-align:right"><b>${info.kasus}</b></td></tr><tr><td>Prediksi 2026</td><td style="text-align:right"><b>${info.rfTotal} kasus</b></td></tr><tr><td>Skor Integrasi</td><td style="text-align:right"><b>${info.skor}%</b></td></tr><tr><td>Kategori</td><td style="text-align:right"><span style="background:${info.warna};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">Prioritas ${info.prioritas}</span></td></tr></table></div>`);
              layer.bindTooltip(info.kec,{permanent:false,direction:'center',className:'map-tooltip'});
            }
          }
        }).addTo(imap);
        state.integrasiLayers.push(geoLayer);
      }

      // Also add circle markers for additional visibility
      rows.forEach(r=>{
        if(r.lat && r.lng){
          const cm=L.circleMarker([r.lat,r.lng],{radius:8+(r.skor/100)*15,color:'rgba(255,255,255,.7)',weight:1.5,fillColor:r.warna,fillOpacity:0.9}).addTo(imap);
          cm.bindPopup(`<b>${r.kec}</b><br>Prioritas ${r.prioritas}<br>Skor: ${r.skor}%<br>Prediksi 2026: ${r.rfTotal} kasus`);
          state.integrasiLayers.push(cm);
        }
      });

      // Legend
      document.getElementById('integrasiMapLegend').innerHTML=
        '<span><i class="dot" style="background:#ef4444"></i>Prioritas I – Sangat Tinggi</span>'+
        '<span><i class="dot" style="background:#f97316"></i>Prioritas II – Tinggi</span>'+
        '<span><i class="dot" style="background:#f59e0b"></i>Prioritas III – Sedang</span>'+
        '<span><i class="dot" style="background:#10b981"></i>Prioritas IV – Rendah</span>';

      setTimeout(()=>imap.invalidateSize(),150);
    }

    // ========== CHARTS ==========
    makeChart('integrasiBarChart',{
      type:'bar',
      data:{
        labels:rows.map(r=>r.kec),
        datasets:[{
          label:'Skor Integrasi (%)',
          data:rows.map(r=>r.skor),
          backgroundColor:rows.map(r=>r.warna+'cc'),
          borderColor:rows.map(r=>r.warna),
          borderWidth:2,
          borderRadius:5
        }]
      },
      options:{...chartBase,plugins:{...chartBase.plugins,legend:{display:false}},scales:{x:{...chartBase.scales.x,ticks:{...chartBase.scales.x.ticks,maxRotation:60,minRotation:45}},y:{...chartBase.scales.y,max:100,title:{display:true,text:'Skor (%)',color:'#4a6380'}}}}
    });

    makeChart('integrasiDonutChart',{
      type:'doughnut',
      data:{
        labels:['Prioritas I','Prioritas II','Prioritas III','Prioritas IV'],
        datasets:[{data:[c1,c2,c3,c4],backgroundColor:['#ef4444cc','#f97316cc','#f59e0bcc','#10b981cc'],borderColor:'#0f1e38',borderWidth:3,hoverOffset:10}]
      },
      options:{responsive:true,maintainAspectRatio:false,cutout:'55%',plugins:{legend:{position:'bottom',labels:{color:'#9bc3ef',font:{family:'Inter',size:12},usePointStyle:true,padding:14}},tooltip:{backgroundColor:'#111f35',titleColor:'#e2e8f0',bodyColor:'#9bc3ef',borderColor:'#1e3354',borderWidth:1}}}
    });

    // ========== PRIORITY TABLE ==========
    document.getElementById('integrasiTableBody').innerHTML=rows.map((r,i)=>{
      const ps=r.pNum===1?'background:#ef4444;color:#fff':r.pNum===2?'background:#f97316;color:#fff':r.pNum===3?'background:#f59e0b;color:#000':'background:#10b981;color:#fff';
      return `<tr>
        <td>${i+1}</td>
        <td><b>${r.kec}</b></td>
        <td>${r.kasus}</td>
        <td><span class="badge b-${r.lisa}">${r.lisa}</span></td>
        <td>${r.rfTotal} kasus</td>
        <td><b>${r.skor}</b></td>
        <td><span style="${ps};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap">Prioritas ${r.prioritas}</span></td>
        <td style="font-size:12px;color:#94a3b8">${r.rekomendasi}</td>
      </tr>`;
    }).join('');

    // ========== 2026 MONTHLY PREDICTION TABLE ==========
    const kecNames=[...new Set(forecasts12.map(f=>f.kecamatan))].sort();
    document.getElementById('prediksi2026Body').innerHTML=kecNames.map((kec,i)=>{
      const monthly=rfMonthly[kec]||{};
      let total=0;
      let cells='';
      for(let m=1;m<=12;m++){
        const val=Math.round(monthly[m]||0);
        total+=val;
        const bg=val>80?'color:#ef4444;font-weight:700':val>40?'color:#f59e0b;font-weight:600':val>10?'color:#38bdf8':'color:#64748b';
        cells+=`<td style="${bg}">${val}</td>`;
      }
      const info=priorityMap[kec];
      const rowBg=info&&info.pNum===1?'background:rgba(239,68,68,.08)':info&&info.pNum===2?'background:rgba(249,115,22,.06)':'';
      return `<tr style="${rowBg}">
        <td>${i+1}</td>
        <td><b>${kec}</b></td>
        ${cells}
        <td><b style="color:#22d3ee">${total}</b></td>
      </tr>`;
    }).join('');

  })();
}
function renderLaporan(){const year=getSelectedYear('overviewYear'), rows=state.data.kec[year]||[], total=rows.reduce((a,b)=>a+b.jumlah_kasus,0), sp=state.data.spatial[year]||{}, clusters=sp.clusters||[], hh=clusters.filter(x=>x.lisa_cluster==='HH').map(x=>x.kecamatan).slice(0,8), ll=clusters.filter(x=>x.lisa_cluster==='LL').map(x=>x.kecamatan).slice(0,8), fc=state.data.fc||{}; document.getElementById('reportCards').innerHTML=`<div class="report-card"><h3><i class="fa-solid fa-bullseye"></i> Tujuan Penelitian</h3><p>Mengintegrasikan <b>analisis spasial</b> Moran's I dan LISA dengan <b>Random Forest Regression</b> berbasis lag feature untuk deteksi dan prediksi persebaran kasus campak di Kabupaten Sumenep.</p></div><div class="report-card"><h3><i class="fa-solid fa-database"></i> Data dan Periode Analisis</h3><ul><li>Data kasus campak dari <b>${rows.length} kecamatan</b>.</li><li>Tahun aktif dashboard: <b>${year}</b>.</li><li>Total kasus tahun terpilih: <b>${fmt(total)} kasus</b>.</li><li>Sumber data diperbarui melalui menu <b>Upload Dataset Excel</b>.</li></ul></div><div class="report-card"><h3><i class="fa-solid fa-location-dot"></i> Temuan Analisis Spasial</h3><ul><li>Moran's I Global = <b>${sp.moran_i??'-'}</b>, Expected I = <b>${sp.expected_i??'-'}</b>, Z-score = <b>${sp.z_score??'-'}</b>.</li><li>Kecamatan hotspot HH: <b>${hh.join(', ')||'-'}</b>.</li><li>Kecamatan coldspot LL: <b>${ll.join(', ')||'-'}</b>.</li></ul></div><div class="report-card"><h3><i class="fa-solid fa-chart-line"></i> Temuan Time Series dan Prediksi</h3><ul><li>Tren bulanan dibentuk dari data detail dan/atau estimasi distribusi musiman untuk data rekap tahunan.</li><li>Random Forest memakai Lag_1, Lag_2, Lag_3, Lag_4, Bulan, dan Tahun sebagai fitur model terlatih.</li></ul></div><div class="report-card"><h3><i class="fa-solid fa-lightbulb"></i> Rekomendasi Kebijakan</h3><ul><li>Prioritaskan surveilans dan imunisasi pada wilayah hotspot HH.</li><li>Gunakan prediksi RF sebagai bahan deteksi dini peningkatan kasus.</li><li>Tambahkan GeoJSON/shapefile kecamatan untuk hasil Moran dan LISA final skripsi yang lebih valid.</li></ul></div>`;}
async function uploadDataset(e){e.preventDefault(); const fd=new FormData(e.target), msg=document.getElementById('uploadMsg'); msg.textContent='Mengupload dataset...'; const r=await fetch('/api/upload',{method:'POST',body:fd}); const j=await r.json(); msg.textContent=j.message||j.error||'Selesai.'; if(r.ok){state.data={}; charts={}; await init(); showPage('overview');}}
init().catch(err=>{console.error(err); alert('Dashboard gagal memuat data. Pastikan Flask berjalan dan dataset Excel tersedia.');});
