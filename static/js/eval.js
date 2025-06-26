function addShineEffect(element) {
    const existingShine = element.querySelector('.shine-effect');
    if (existingShine) existingShine.remove();
    
    const shine = document.createElement('div');
    shine.className = 'shine-effect';
    element.appendChild(shine);
    setTimeout(() => {
        shine.remove();
    }, 800);
}

function createEvalPlaceholder(modelName, uniquePrefix) {
    const placeholder = document.createElement('div');
    placeholder.className = 'results-output single-evaluation-block placeholder';
    const placeholderId = `eval-placeholder-${uniquePrefix}-${modelName.replace(/[^a-zA-Z0-9]/g, '-')}`;
    placeholder.id = placeholderId;
    placeholder.innerHTML = `
        <h3 class="eval-section-title"><i class="fa-solid fa-gavel"></i> Penilaian dari: ${modelName}</h3>
        <div class="eval-content-placeholder">
            <div class="placeholder-line title"></div>
            <div class="placeholder-line"></div>
            <div class="placeholder-line short"></div>
            <div class="placeholder-line"></div>
        </div>
    `;
    return placeholder;
}

function fillEvalPlaceholder(placeholder, modelName, evalData, observer) {
    addShineEffect(placeholder); 
    placeholder.classList.remove('placeholder');
    
    let contentHTML = '';
    if (evalData.error) {
        contentHTML = `<p class="error-text">Juri AI (${modelName}) gagal memberikan evaluasi: ${evalData.error}</p>`;
    } else {
        const renderDetailScore = (label, data, customLabelText) => {
            if (!data) return '';
            const score = data.skor || 0;
            let barColorClass = 'high';
            if (score < 75) barColorClass = 'medium';
            if (score < 50) barColorClass = 'low';
            return `<div class="detail-score-item">
                    <div class="detail-score-header"><span class="detail-score-label">${customLabelText}</span><span class="detail-score-value">${score}/100</span></div>
                    <div class="detail-score-bar-bg"><div class="detail-score-bar-fg ${barColorClass}" data-score="${score}"></div></div>
                    <p class="detail-score-justification">${data.justifikasi || '<em>Tidak ada justifikasi.</em>'}</p>
                </div>`;
        };
        const isTranslationEval = !evalData.skor_rinci?.kefasihan;
        
        const detailScoresHTML = isTranslationEval ? `
            ${renderDetailScore('relevansi', evalData.skor_rinci?.relevansi, 'Akurasi Makna')}
            ${renderDetailScore('kepadatan', evalData.skor_rinci?.kepadatan, 'Kefasihan & Alami')}
            ${renderDetailScore('koherensi', evalData.skor_rinci?.koherensi, 'Konteks & Nuansa')}
            ${renderDetailScore('konsistensi_faktual', evalData.skor_rinci?.konsistensi_faktual, 'Tata Bahasa & Ejaan')}
        ` : `
            ${renderDetailScore('relevansi', evalData.skor_rinci?.relevansi, 'Relevansi')}
            ${renderDetailScore('kepadatan', evalData.skor_rinci?.kepadatan, 'Kepadatan')}
            ${renderDetailScore('koherensi', evalData.skor_rinci?.koherensi, 'Koherensi')}
            ${renderDetailScore('konsistensi_faktual', evalData.skor_rinci?.konsistensi_faktual, 'Konsistensi Faktual')}
            ${renderDetailScore('kefasihan', evalData.skor_rinci?.kefasihan, 'Kefasihan')}
        `;

        contentHTML = `
            <div class="evaluation-summary">
                <div class="evaluation-score"><span class="score-value">${evalData.skor_keseluruhan || 'N/A'}</span><span class="score-label">/ 100</span></div>
                <div class="evaluation-summary-text">
                     <p class="evaluation-text">"${evalData.evaluasi_singkat || 'Evaluasi tidak tersedia.'}"</p>
                     <p class="evaluation-suggestion"><strong>Saran Utama:</strong> ${evalData.saran_perbaikan_utama || 'Tidak ada.'}</p>
                </div>
            </div>
            <div class="evaluation-details-grid">
                ${detailScoresHTML}
            </div>`;
    }
    placeholder.innerHTML = `<h3 class="eval-section-title"><i class="fa-solid fa-gavel"></i> Penilaian dari: ${modelName}</h3><div class="eval-content">${contentHTML}</div>`;
    
    if (observer) {
        observer.observe(placeholder);
    }
}

async function getAndRenderEvaluations(arg1, arg2, arg3, arg4, arg5, arg6) {
    window.currentEvalController = new AbortController();
    const signal = window.currentEvalController.signal;

    let payload, endpointUrl, resultsContainer, useGridLayout, modelNameToEvaluate;

    if (typeof arg1 === 'object' && arg1 !== null) {
        payload = arg1;
        endpointUrl = arg2;
        resultsContainer = arg3;
        modelNameToEvaluate = arg4 || '';
        useGridLayout = arg5 || false;
    } else {
        const originalText = arg1;
        const summaryText = arg2;
        const languageCode = arg3;
        resultsContainer = arg4;
        useGridLayout = arg5 || false;
        modelNameToEvaluate = arg6 || '';
        
        payload = {
            original_text: originalText,
            summary_text: summaryText,
            lang_summarizer: languageCode
        };
        endpointUrl = '/summarizer/evaluate';
    }

    const judgeModels = ["Cohere Command A 2025", "Google Gemma 3", "Meta Llama 4 Maverick"]; 
    
    const animationObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                const bars = entry.target.querySelectorAll('.detail-score-bar-fg');
                bars.forEach(bar => {
                    setTimeout(() => { bar.style.width = `${bar.dataset.score}%`; }, 200);
                });
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    const evalWrapper = document.createElement('div');
    evalWrapper.className = 'evaluation-wrapper';
    
    const aiJudgesTitle = document.createElement('h2');
    aiJudgesTitle.className = 'panel-main-title';
    aiJudgesTitle.innerHTML = `<span class="res-icon">⚖️</span> Panel Penilaian untuk: <strong>${modelNameToEvaluate}</strong>`;
    evalWrapper.appendChild(aiJudgesTitle);
    
    let placeholderContainer = evalWrapper;
    if (useGridLayout) {
        const gridContainer = document.createElement('div');
        gridContainer.className = 'evaluation-grid-container';
        evalWrapper.appendChild(gridContainer);
        placeholderContainer = gridContainer;
    }
    
    resultsContainer.appendChild(evalWrapper);

    const uniquePrefix = modelNameToEvaluate.replace(/[^a-zA-Z0-9]/g, '');
    judgeModels.forEach(modelName => {
        const placeholder = createEvalPlaceholder(modelName, uniquePrefix);
        placeholderContainer.appendChild(placeholder);
    });

    try {
        const response = await fetch(endpointUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: signal
        });

        const allEvaluations = await response.json();
        
        if (!response.ok) {
            throw new Error(allEvaluations.error || "Gagal mendapatkan data evaluasi dari server.");
        }
        
        if (allEvaluations.ai_judges) {
            judgeModels.forEach(modelNameToFind => {
                const placeholderId = `eval-placeholder-${uniquePrefix}-${modelNameToFind.replace(/[^a-zA-Z0-9]/g, '-')}`;
                const placeholderElement = document.getElementById(placeholderId);

                if (placeholderElement) {
                    const evalData = allEvaluations.ai_judges[modelNameToFind] || { error: "Tidak ada data evaluasi yang diterima untuk juri ini." };
                    fillEvalPlaceholder(placeholderElement, modelNameToFind, evalData, animationObserver);
                }
            });
        } else {
             throw new Error("Tidak ada data evaluasi yang diterima dari server.");
        }

    } catch (error) {
        if (error.name === 'AbortError') {
            evalWrapper.remove();
        } else {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-text';
            errorDiv.innerHTML = `<strong>Gagal Memuat Evaluasi:</strong> ${error.message}`;
            placeholderContainer.innerHTML = '';
            placeholderContainer.appendChild(errorDiv);
        }
    } finally {
        if (window.currentEvalController && window.currentEvalController.signal === signal) {
            window.currentEvalController = null;
        }
    }
}