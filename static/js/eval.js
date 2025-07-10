// Blok: Efek Visual 'Shine'
// Fungsi ini menambahkan efek kilatan singkat pada sebuah elemen.
// Berguna untuk memberikan feedback visual bahwa konten di dalam elemen tersebut baru saja diperbarui.
function addShineEffect(element) {
    // Menghapus efek kilatan sebelumnya jika masih ada, untuk mencegah tumpukan.
    const existingShine = element.querySelector('.shine-effect');
    if (existingShine) existingShine.remove();
    
    // Membuat dan menambahkan elemen div baru untuk efek kilatan.
    const shine = document.createElement('div');
    shine.className = 'shine-effect';
    element.appendChild(shine);
    
    // Menghapus elemen kilatan setelah animasi selesai (800ms) agar tidak mengganggu elemen lain.
    setTimeout(() => {
        shine.remove();
    }, 800);
}

// Blok: Fungsi untuk Membuat Placeholder Evaluasi
// Membuat elemen 'skeleton screen' (tampilan loading) untuk satu blok evaluasi.
// Ini ditampilkan saat menunggu hasil evaluasi dari server.
function createEvalPlaceholder(modelName, uniquePrefix) {
    const placeholder = document.createElement('div');
    placeholder.className = 'results-output single-evaluation-block placeholder';
    
    // Membuat ID unik untuk placeholder agar bisa ditargetkan dengan mudah nanti.
    const placeholderId = `eval-placeholder-${uniquePrefix}-${modelName.replace(/[^a-zA-Z0-9]/g, '-')}`;
    placeholder.id = placeholderId;
    
    // Struktur HTML untuk placeholder, meniru layout konten evaluasi yang sebenarnya.
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

// Blok: Fungsi untuk Mengisi Placeholder dengan Data Evaluasi
// Fungsi ini mengubah placeholder yang tadinya 'loading' menjadi blok konten yang berisi data evaluasi sebenarnya.
function fillEvalPlaceholder(placeholder, modelName, evalData, observer) {
    // 1. Terapkan efek kilatan untuk menandakan pembaruan.
    addShineEffect(placeholder); 
    placeholder.classList.remove('placeholder'); // Hapus kelas 'placeholder' untuk mengubah styling.
    
    let contentHTML = '';
    // 2. Cek apakah ada error. Jika ya, tampilkan pesan kesalahan.
    if (evalData.error) {
        contentHTML = `<p class="error-text">Juri AI (${modelName}) gagal memberikan evaluasi: ${evalData.error}</p>`;
    } else {
        // 3. Jika tidak ada error, render konten evaluasi.
        // Fungsi bantuan untuk merender setiap item skor rinci (misal: Relevansi, Koherensi).
        const renderDetailScore = (label, data, customLabelText) => {
            if (!data) return '';
            const score = data.skor || 0;
            // Menentukan warna progress bar berdasarkan skor.
            let barColorClass = 'high';
            if (score < 75) barColorClass = 'medium';
            if (score < 50) barColorClass = 'low';
            return `<div class="detail-score-item">
                    <div class="detail-score-header"><span class="detail-score-label">${customLabelText}</span><span class="detail-score-value">${score}/100</span></div>
                    <div class="detail-score-bar-bg"><div class="detail-score-bar-fg ${barColorClass}" data-score="${score}"></div></div>
                    <p class="detail-score-justification">${data.justifikasi || '<em>Tidak ada justifikasi.</em>'}</p>
                </div>`;
        };
        
        // Membedakan metrik evaluasi antara ringkasan biasa dan terjemahan.
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

        // Menggabungkan semua bagian (skor keseluruhan, ringkasan, saran, dan skor rinci) menjadi satu blok HTML.
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
    
    // 4. Masukkan HTML yang sudah jadi ke dalam elemen placeholder.
    placeholder.innerHTML = `<h3 class="eval-section-title"><i class="fa-solid fa-gavel"></i> Penilaian dari: ${modelName}</h3><div class="eval-content">${contentHTML}</div>`;
    
    // 5. Daftarkan elemen ini ke 'IntersectionObserver' untuk memicu animasi saat elemen terlihat di layar.
    if (observer) {
        observer.observe(placeholder);
    }
}

// Blok: Fungsi Utama untuk Mendapatkan dan Merender Evaluasi
// Fungsi ini mengorkestrasi seluruh proses evaluasi: membuat placeholder, mengambil data dari server, dan menampilkannya.
async function getAndRenderEvaluations(arg1, arg2, arg3, arg4, arg5, arg6) {
    // 1. Persiapan AbortController untuk membatalkan permintaan fetch jika permintaan baru dibuat.
    window.currentEvalController = new AbortController();
    const signal = window.currentEvalController.signal;

    // Fleksibilitas Argumen: Mendukung dua cara pemanggilan fungsi (dengan objek payload atau dengan argumen terpisah).
    let payload, endpointUrl, resultsContainer, useGridLayout, modelNameToEvaluate;
    if (typeof arg1 === 'object' && arg1 !== null) { // Cara 1: Menggunakan objek
        payload = arg1;
        endpointUrl = arg2;
        resultsContainer = arg3;
        modelNameToEvaluate = arg4 || '';
        useGridLayout = arg5 || false;
    } else { // Cara 2: Menggunakan argumen terpisah (untuk kompatibilitas)
        payload = { original_text: arg1, summary_text: arg2, lang_summarizer: arg3 };
        endpointUrl = '/summarizer/evaluate';
        resultsContainer = arg4;
        useGridLayout = arg5 || false;
        modelNameToEvaluate = arg6 || '';
    }

    // Daftar model "juri AI" yang akan digunakan untuk mengevaluasi.
    const judgeModels = ["Cohere Command A 2025", "Google Gemma 3", "Meta Llama 4 Maverick"]; 
    
    // 2. Persiapan IntersectionObserver untuk animasi progress bar.
    // Animasi baru berjalan saat elemen evaluasi masuk ke dalam viewport (layar pengguna).
    const animationObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                const bars = entry.target.querySelectorAll('.detail-score-bar-fg');
                bars.forEach(bar => {
                    setTimeout(() => { bar.style.width = `${bar.dataset.score}%`; }, 200); // Animasikan lebar bar
                });
                observer.unobserve(entry.target); // Hentikan observasi setelah animasi berjalan sekali.
            }
        });
    }, { threshold: 0.1 });

    // 3. Membuat UI awal: wrapper utama, judul panel, dan kontainer untuk placeholder.
    const evalWrapper = document.createElement('div');
    evalWrapper.className = 'evaluation-wrapper';
    
    const aiJudgesTitle = document.createElement('h2');
    aiJudgesTitle.className = 'panel-main-title';
    aiJudgesTitle.innerHTML = `<span class="res-icon">⚖️</span> Panel Penilaian untuk: <strong>${modelNameToEvaluate}</strong>`;
    evalWrapper.appendChild(aiJudgesTitle);
    
    // Gunakan layout grid jika ada lebih dari satu hasil yang ditampilkan.
    let placeholderContainer = evalWrapper;
    if (useGridLayout) {
        const gridContainer = document.createElement('div');
        gridContainer.className = 'evaluation-grid-container';
        evalWrapper.appendChild(gridContainer);
        placeholderContainer = gridContainer;
    }
    
    resultsContainer.appendChild(evalWrapper);

    // 4. Buat dan tampilkan placeholder untuk setiap juri AI.
    const uniquePrefix = modelNameToEvaluate.replace(/[^a-zA-Z0-9]/g, '');
    judgeModels.forEach(modelName => {
        const placeholder = createEvalPlaceholder(modelName, uniquePrefix);
        placeholderContainer.appendChild(placeholder);
    });

    try {
        // 5. Kirim permintaan ke server untuk mendapatkan data evaluasi.
        const response = await fetch(endpointUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: signal // Gunakan AbortSignal
        });

        const allEvaluations = await response.json();
        
        if (!response.ok) {
            throw new Error(allEvaluations.error || "Gagal mendapatkan data evaluasi dari server.");
        }
        
        // 6. Proses respons: Cocokkan data evaluasi dengan placeholder yang sesuai dan isi.
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
        // 7. Penanganan Error: Jika permintaan dibatalkan (aborted), hapus seluruh wrapper evaluasi.
        if (error.name === 'AbortError') {
            evalWrapper.remove();
        } else { // Jika error lain, tampilkan pesan kesalahan di dalam kontainer.
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-text';
            errorDiv.innerHTML = `<strong>Gagal Memuat Evaluasi:</strong> ${error.message}`;
            placeholderContainer.innerHTML = '';
            placeholderContainer.appendChild(errorDiv);
        }
    } finally {
        // 8. Reset controller setelah selesai atau gagal, agar siap untuk permintaan berikutnya.
        if (window.currentEvalController && window.currentEvalController.signal === signal) {
            window.currentEvalController = null;
        }
    }
}