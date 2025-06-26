document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('mainFeatureForm');
    if (!form) return;

    const resultsContainer = document.getElementById('resultsContainer');
    const submitButton = document.getElementById('submitBtn');
    const mainTextarea = document.getElementById('mainTextarea');
    const styleSelect = document.getElementById('correction_style');

    const SVG_SPINNER_ICON = `<svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>`;
    const ORIGINAL_SUBMIT_ICON = '<i class="fa-solid fa-arrow-up"></i>';

    function updateUIState(isLoading) {
        submitButton.disabled = isLoading;
        submitButton.innerHTML = isLoading ? SVG_SPINNER_ICON : ORIGINAL_SUBMIT_ICON;
    }

    function createActionBar(originalText, textToCopy, isOutputBlock) {
        const actionBar = document.createElement('div');
        actionBar.className = 'action-bar';
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Salin';
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalContent = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tersalin';
                setTimeout(() => { copyBtn.innerHTML = originalContent; }, 2000);
            });
        });
        actionBar.appendChild(copyBtn);
        
        const actionBtn = document.createElement('button');
        actionBtn.className = 'action-btn';
        if (isOutputBlock) {
            actionBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Coba Lagi';
            actionBtn.addEventListener('click', () => { if (submitButton.disabled) return; mainTextarea.value = originalText; form.requestSubmit(); });
        } else {
            actionBtn.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Ubah';
            actionBtn.addEventListener('click', () => { mainTextarea.value = originalText; mainTextarea.focus(); });
        }
        actionBar.appendChild(actionBtn);
        return actionBar;
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const text = mainTextarea.value.trim();
        if (!text) {
            alert('Teks untuk dikoreksi tidak boleh kosong!');
            return;
        }
        if (submitButton.disabled) return;
        updateUIState(true);

        const payload = {
            text_to_proofread: text,
            correction_style: styleSelect.value
        };

        mainTextarea.value = '';
        mainTextarea.style.height = 'auto'; 

        resultsContainer.innerHTML = '';
        
        const inputDiv = document.createElement('div');
        inputDiv.className = 'results-output user-input-display';
        inputDiv.innerHTML = `<h2><span class="res-icon">👤</span> Teks Asli Anda:</h2><pre></pre>`;
        inputDiv.querySelector('pre').textContent = text;
        inputDiv.appendChild(createActionBar(text, text, false));
        resultsContainer.appendChild(inputDiv);
        
        const outputDiv = document.createElement('div');
        outputDiv.className = 'results-output ai-output-display';
        outputDiv.innerHTML = `<h2><span class="res-icon">✨</span> Teks yang Diperbaiki:</h2><p><em>Menganalisis dan mengoreksi...</em></p>`;
        resultsContainer.appendChild(outputDiv);

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Gagal memproses permintaan.');

            const correctedText = data.corrected_text || "[Teks yang dikoreksi tidak diterima]";
            outputDiv.innerHTML = `<h2><span class="res-icon">✨</span> Teks yang Diperbaiki:</h2><pre></pre>`;
            outputDiv.querySelector('pre').textContent = correctedText;
            outputDiv.appendChild(createActionBar(text, correctedText, true));

            if (data.changes && data.changes.length > 0) {
                const changesDiv = document.createElement('div');
                changesDiv.className = 'results-output';
                let tableHTML = `<h2><span class="res-icon">📋</span> Laporan Perubahan</h2>
                                 <table class="changes-table">
                                     <thead>
                                         <tr>
                                             <th>Asli</th>
                                             <th>Koreksi</th>
                                             <th>Alasan</th>
                                         </tr>
                                     </thead>
                                     <tbody>`;
                data.changes.forEach(change => {
                    tableHTML += `<tr>
                                     <td><del>${change.original}</del></td>
                                     <td><ins>${change.correction}</ins></td>
                                     <td>${change.reason}</td>
                                 </tr>`;
                });
                tableHTML += `</tbody></table>`;
                changesDiv.innerHTML = tableHTML;
                resultsContainer.appendChild(changesDiv);
            } else {
                 const noChangesDiv = document.createElement('div');
                 noChangesDiv.className = 'results-output';
                 noChangesDiv.innerHTML = `<h2><span class="res-icon">✅</span> Laporan Perubahan</h2><p>Tidak ada perubahan yang signifikan. Teks Anda sudah bagus!</p>`;
                 resultsContainer.appendChild(noChangesDiv);
            }

        } catch (error) {
            outputDiv.innerHTML = `<div class="error-text"><strong>Error:</strong> ${error.message}</div>`;
        } finally {
            updateUIState(false);
        }
    });

    mainTextarea.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            form.requestSubmit();
        }
    });
});