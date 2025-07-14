// Blok: Inisialisasi Variabel Global
// Variabel-variabel ini digunakan untuk mengelola status aplikasi di level global,
// seperti mengontrol permintaan evaluasi yang sedang berjalan atau worker.
window.currentEvalController = null;
let currentWorker = null; // Catatan: Variabel ini dideklarasikan tetapi tidak digunakan secara global di kode ini.

// Blok: Konstanta UI
// Mendefinisikan string HTML untuk ikon-ikon yang akan digunakan di tombol submit.
// Ini membuat penggantian ikon menjadi lebih mudah dan terpusat.
const SVG_SPINNER_ICON = '<svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>';
const ORIGINAL_SUBMIT_ICON = '<i class="fa-solid fa-arrow-up"></i>';

// Blok: Fungsi Utilitas untuk Menampilkan Pesan Kesalahan
// Fungsi sederhana untuk menampilkan pesan error yang diformat dengan baik
// di dalam elemen kontainer yang ditentukan.
function showErrorMessage(container, message) {
    container.innerHTML = `<div class="error-text"><strong>Oops! Terjadi kesalahan:</strong><br>${message}</div>`;
}

// Blok: Fungsi Utilitas untuk Membuat Placeholder 'Loading'
// Membuat dan mengembalikan elemen div yang berisi animasi 'skeleton screen'.
// Ini ditampilkan saat menunggu hasil dari server untuk memberikan feedback visual (loading state) kepada pengguna.
function createResultPlaceholder() {
    const placeholder = document.createElement('div');
    placeholder.className = 'markdown-content result-placeholder';
    placeholder.innerHTML = `
        <div class="placeholder-line"></div>
        <div class="placeholder-line"></div>
        <div class="placeholder-line short"></div>
        <br>
        <div class="placeholder-line title"></div>
        <div class="placeholder-line short"></div>
        <div class="placeholder-line short"></div>
    `;
    return placeholder;
}

// Blok: Logika Utama Aplikasi
// Menjalankan semua skrip setelah seluruh halaman (DOM) selesai dimuat untuk memastikan
// semua elemen HTML sudah siap untuk dimanipulasi.
document.addEventListener('DOMContentLoaded', async function() {
    // Mengambil semua elemen interaktif dari halaman (form, tombol, area teks, dll).
    const form = document.getElementById('mainFeatureForm');
    const resultsContainer = document.getElementById('resultsContainer');
    const submitButton = document.getElementById('submitBtn');
    const mainTextarea = document.getElementById('mainTextarea');
    const algoSelect = document.getElementById('summarizer_algo');
    const comparisonAlgoSelect = document.getElementById('comparison_algo');
    const langSelect = document.getElementById('lang_summarizer');

    // Pengaman: Jika salah satu elemen penting tidak ditemukan, hentikan eksekusi skrip.
    if (!form || !resultsContainer || !submitButton || !mainTextarea || !algoSelect || !langSelect) return;

    // Blok: Fungsi untuk Mengelola Status UI
    // Mengaktifkan atau menonaktifkan elemen input dan tombol selama pemrosesan.
    // Juga mengubah ikon tombol submit menjadi spinner saat sedang bekerja, dan mengembalikannya setelah selesai.
    function updateUIState(isProcessing) {
        submitButton.disabled = isProcessing;
        mainTextarea.disabled = isProcessing;
        submitButton.innerHTML = isProcessing ? SVG_SPINNER_ICON : ORIGINAL_SUBMIT_ICON;
    }

    // Blok: Fungsi untuk Membuat Tombol Aksi (Salin, Coba Lagi, Ubah)
    // Membuat sebuah 'action bar' yang berisi tombol-tombol fungsional.
    // Logikanya berbeda tergantung apakah ini untuk blok input pengguna ('Ubah') atau blok hasil AI ('Coba Lagi').
    function createActionBar(originalText, textToCopy, isOutputBlock) {
        const actionBar = document.createElement('div');
        actionBar.className = 'action-bar';
        
        // Tombol Salin: Menyalin teks yang diberikan ke clipboard pengguna.
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Salin';
        copyBtn.addEventListener('click', () => { navigator.clipboard.writeText(textToCopy).then(() => { const originalContent = copyBtn.innerHTML; copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tersalin'; setTimeout(() => { copyBtn.innerHTML = originalContent; }, 2000); }); });
        actionBar.appendChild(copyBtn);

        // Tombol Aksi: 'Coba Lagi' untuk output, 'Ubah' untuk input.
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
    
    // Blok: Fungsi untuk Memproses Permintaan ke Satu Model
    // Fungsi ini bertanggung jawab untuk menangani seluruh alur kerja untuk satu model/algoritma,
    // mulai dari persiapan UI, pengiriman permintaan, hingga menampilkan hasil.
    function processSingleModel(modelAlgo, originalText, commonPayload) {
        return new Promise(async (resolve, reject) => {
            // 1. Persiapan: Mengambil nama model yang mudah dibaca dan membuat payload khusus untuk model ini.
            const selectElement = document.getElementById('summarizer_algo');
            const selectedOption = Array.from(selectElement.options).find(opt => opt.value === modelAlgo);
            const modelNameText = selectedOption ? selectedOption.text.trim() : modelAlgo;
            
            const modelPayload = { ...commonPayload, summarizer_algo: modelAlgo };
            
            // 2. UI: Membuat kontainer output, menampilkan placeholder 'loading', dan scroll ke tampilan.
            const outputContainer = document.createElement('div');
            outputContainer.className = 'results-output ai-output-display';
            outputContainer.innerHTML = `<h2><span class="res-icon">✨</span> Hasil (${modelNameText})</h2>`;
            const resultPlaceholder = createResultPlaceholder();
            outputContainer.appendChild(resultPlaceholder);
            resultsContainer.appendChild(outputContainer);
            
            setTimeout(() => { outputContainer.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);

            // 3. Web Worker: Membuat worker baru untuk menangani permintaan di background agar UI utama tidak freeze.
            const worker = new Worker(URL_TO_WORKER_JS);
            
            // 4. Penanganan Pesan dari Worker: Mengatur apa yang harus dilakukan saat worker mengirim data.
            worker.onmessage = (e) => {
                const { type, content, finalContent, message } = e.data;
                if (type === 'update') { // Untuk hasil streaming, perbarui konten secara bertahap.
                    if (resultPlaceholder.classList.contains('result-placeholder')) {
                        resultPlaceholder.classList.remove('result-placeholder');
                    }
                    resultPlaceholder.innerHTML = content;
                    outputContainer.scrollIntoView({ behavior: 'auto', block: 'end' });
                } else if (type === 'done') { // Saat proses selesai, tampilkan hasil final dan action bar.
                    resultPlaceholder.innerHTML = marked.parse(finalContent); // Menggunakan library 'marked' untuk merender Markdown.
                    outputContainer.appendChild(createActionBar(originalText, finalContent, true));
                    worker.terminate();
                    resolve({ result: finalContent, name: modelNameText });
                } else if (type === 'error') { // Jika terjadi error, tampilkan pesan kesalahan.
                    showErrorMessage(resultPlaceholder, message);
                    worker.terminate();
                    reject(new Error(message));
                }
            };
            
            // 5. Eksekusi: Membedakan antara model yang mendukung streaming (seperti Gemini) dan yang tidak (statis).
            const aiStreamModels = ['gemini', 'learnlm'];
            if (aiStreamModels.includes(modelAlgo)) {
                // Untuk model streaming, kirim instruksi ke worker untuk memulai streaming.
                worker.postMessage({ type: 'stream', data: { url: form.action, options: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(modelPayload) } } });
            } else {
                // Untuk model statis (seperti TF-IDF), ambil hasilnya terlebih dahulu lalu kirim ke worker untuk diproses.
                try {
                    const response = await fetch(form.action, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(modelPayload) });
                    if (!response.ok) {
                        const errData = await response.json().catch(() => ({}));
                        throw new Error(errData.error || `Server merespons dengan status ${response.status}`);
                    }
                    const data = await response.json();
                    if (data.error) throw new Error(data.error);
                    worker.postMessage({ type: 'static', data: { text: data.result } });
                } catch (error) {
                    worker.onmessage({ data: { type: 'error', message: error.message } });
                }
            }
        });
    }

    // Blok: Event Listener Utama untuk Form Submission
    // Ini adalah 'otak' dari interaksi pengguna. Dipicu saat pengguna menekan tombol submit.
    form.addEventListener('submit', async function(event) {
        event.preventDefault(); // Mencegah perilaku default form (reload halaman).
        
        if (submitButton.disabled) return;
        if (window.currentEvalController) window.currentEvalController.abort(); // Batalkan proses evaluasi yang mungkin sedang berjalan.
        
        const originalText = mainTextarea.value.trim();
        if (!originalText) {
            alert('Teks tidak boleh kosong!');
            return;
        }
        
        updateUIState(true); // Ubah UI ke status 'processing'.

        // Siapkan payload data umum yang akan dikirim ke server.
        const mainModelAlgo = algoSelect.value;
        const comparisonModelAlgo = comparisonAlgoSelect.value;
        const commonPayload = {
            original_text: originalText,
            num_sentences_summary: document.getElementById('num_sentences_summary').value,
            max_keywords_summary: document.getElementById('max_keywords_summary').value,
            lang_summarizer: langSelect.value
        };
        
        // Kosongkan textarea dan kontainer hasil untuk menampilkan hasil yang baru.
        mainTextarea.value = '';
        mainTextarea.style.height = 'auto';
        resultsContainer.innerHTML = '';

        // Tampilkan kembali teks asli pengguna di area hasil.
        const userInputDiv = document.createElement('div');
        userInputDiv.className = 'results-output user-input-display';
        userInputDiv.innerHTML = `<h2><span class="res-icon">👤</span> Teks Anda:</h2><pre></pre>`;
        userInputDiv.querySelector('pre').textContent = originalText;
        userInputDiv.appendChild(createActionBar(originalText, originalText, false));
        resultsContainer.appendChild(userInputDiv);
        
        let mainModelData = null;
        let comparisonModelData = null;

        try {
            // Proses model utama.
            mainModelData = await processSingleModel(mainModelAlgo, originalText, commonPayload);
            // Jika ada model perbandingan yang dipilih, proses juga model tersebut.
            if (comparisonModelAlgo !== 'none') {
                comparisonModelData = await processSingleModel(comparisonModelAlgo, originalText, commonPayload);
            }
        } catch (error) {
            console.error("Terjadi kesalahan pada salah satu proses model:", error.message);
        }

        const useGrid = !!comparisonModelData; // Gunakan layout grid jika ada 2 hasil.

        // Jika ada fungsi evaluasi, panggil untuk menampilkan skor perbandingan untuk model utama.
        if (mainModelData && typeof getAndRenderEvaluations === 'function') {
            getAndRenderEvaluations(originalText, mainModelData.result, langSelect.value, resultsContainer, useGrid, mainModelData.name);
        }

        // Jika ada fungsi evaluasi dan model pembanding, panggil juga untuk model pembanding.
        if (comparisonModelData && typeof getAndRenderEvaluations === 'function') {
            getAndRenderEvaluations(originalText, comparisonModelData.result, langSelect.value, resultsContainer, useGrid, comparisonModelData.name);
        }
        
        // Setelah semua selesai, scroll ke bagian hasil evaluasi (jika ada).
        if (mainModelData || comparisonModelData) {
            const firstEvalWrapper = resultsContainer.querySelector('.evaluation-wrapper');
            if (firstEvalWrapper) {
                setTimeout(() => { firstEvalWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 200);
            }
        }
        
        updateUIState(false); // Kembalikan UI ke status normal.
    });

    // Blok: Logika Dinamis untuk Pilihan Bahasa
    // Bagian ini mengelola opsi bahasa yang tersedia di dropdown agar sesuai dengan algoritma yang dipilih.
    // Definisikan opsi bahasa yang valid untuk setiap algoritma.
    const languageOptions = { gemini: [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }], learnlm: [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', 'text': 'English' }], gpt: [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }], textrank: [{ value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }], tfidf: [{ value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', 'text': 'English' }],  'gpt-4o-nano': [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }] };
    // Fungsi untuk memperbarui dropdown bahasa berdasarkan algoritma yang dipilih dan mengingat pilihan terakhir pengguna.
    function updateLanguageOptions() { const selectedAlgo = algoSelect.value; const last = sessionStorage.getItem(`lastLangFor_${selectedAlgo}`); const options = languageOptions[selectedAlgo] || languageOptions.textrank; langSelect.innerHTML = ''; options.forEach(o => { const opt = document.createElement('option'); opt.value = o.value; opt.textContent = o.text; langSelect.appendChild(opt); }); langSelect.value = options.some(o => o.value === last) ? last : options[0].value; }
    // Tambahkan event listener untuk menjalankan fungsi di atas saat pilihan berubah.
    algoSelect.addEventListener('change', updateLanguageOptions); langSelect.addEventListener('change', () => sessionStorage.setItem(`lastLangFor_${algoSelect.value}`, langSelect.value)); updateLanguageOptions();
    
    // Blok: Shortcut Keyboard
    // Memungkinkan pengguna untuk submit form dengan menekan Ctrl+Enter (Windows/Linux) atau Cmd+Enter (Mac) di textarea.
    mainTextarea.addEventListener('keydown', function(event) { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); form.requestSubmit(); } });
});