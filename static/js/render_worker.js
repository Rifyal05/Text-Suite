// Blok: Impor Skrip Eksternal
// Mengimpor library 'marked.js' dari CDN. Library ini digunakan untuk mengubah teks
// berformat Markdown (yang sering dihasilkan AI) menjadi HTML agar dapat dirender dengan benar di browser.
self.importScripts('https://cdn.jsdelivr.net/npm/marked/marked.min.js');

// Blok: Inisialisasi Variabel Global
// Variabel `marked` akan menyimpan instance dari library Marked setelah diinisialisasi.
// Dideklarasikan di scope global worker agar bisa diakses di seluruh skrip.
let marked;

// Blok: Fungsi Utilitas Pembersihan Teks
// Membersihkan teks output dari AI untuk meningkatkan keterbacaan dan konsistensi format.
function cleanUpAiOutput(text) {
    if (!text) return "";
    let cleanedText = text;
    // Mengubah berbagai jenis bullet points (• atau - dengan spasi) menjadi format standar '- '.
    cleanedText = cleanedText.replace(/^\s*[-•]\s*/gm, '- ');
    // Menambahkan spasi setelah tanda baca jika belum ada (memperbaiki "kata.Kata" menjadi "kata. Kata").
    cleanedText = cleanedText.replace(/([.?!,")-])([a-zA-Z0-9À-ÖØ-öø-ÿ])/g, '$1 $2');
    // Menghapus spasi yang tidak perlu di akhir baris.
    cleanedText = cleanedText.replace(/ \n/g, '\n');
    // Membatasi baris baru yang berurutan maksimal dua (menghindari paragraf yang terlalu renggang).
    cleanedText = cleanedText.replace(/\n{3,}/g, '\n\n');
    // Menambahkan spasi di antara huruf kecil dan huruf besar (camelCase), sering terjadi pada output AI.
    cleanedText = cleanedText.replace(/([a-z])([A-Z])/g, '$1 $2');
    // Menghapus spasi di awal dan akhir teks hasil pembersihan.
    return cleanedText.trim();
}

// Blok: Event Listener Utama Worker
// Ini adalah titik masuk utama worker. Kode di dalam blok ini akan dieksekusi setiap kali
// thread utama mengirim pesan ke worker ini menggunakan `worker.postMessage()`.
self.onmessage = async (event) => {
    // Inisialisasi Library (Lazy Loading): Memeriksa apakah library 'marked' sudah diinisialisasi.
    // Jika belum, library akan dikonfigurasi. Ini hanya terjadi sekali pada pesan pertama yang diterima.
    if (!marked) {
        marked = self.marked;
        marked.setOptions({ gfm: true, breaks: true, sanitize: false, silent: true });
    }
    
    // Mendestrukturisasi data yang dikirim dari thread utama.
    const { type, data } = event.data;
    
    // Pengaturan Efek Mengetik: Menyiapkan variabel-variabel yang dibutuhkan.
    let accumulatedText = ""; // Teks yang sudah "diketik" dan siap ditampilkan.
    let textBuffer = "";      // Teks yang baru diterima dari server dan menunggu untuk "diketik".
    const TYPING_SPEED = 5;   // Kecepatan mengetik dalam milidetik per karakter.

    // Interval untuk Efek Mengetik: Memulai interval yang secara berkala memindahkan karakter
    // dari `textBuffer` ke `accumulatedText` dan mengirim update ke thread utama.
    const typingIntervalId = setInterval(() => {
        if (textBuffer.length > 0) {
            const char = textBuffer.substring(0, 1);
            accumulatedText += char;
            textBuffer = textBuffer.substring(1);
            // Mengirim pesan 'update' dengan konten yang sudah di-parse menjadi HTML.
            self.postMessage({ type: 'update', content: marked.parse(accumulatedText) });
        }
    }, TYPING_SPEED);

    // Blok Logika Utama dan Penanganan Kesalahan
    try {
        // Mode Streaming: Jika pesan bertipe 'stream', worker akan menangani Server-Sent Events (SSE).
        if (type === 'stream') {
            const response = await fetch(data.url, data.options);
            if (!response.ok || !response.body) {
                throw new Error('Gagal melakukan streaming dari server.');
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            // Loop untuk membaca data stream secara terus-menerus.
            while (true) {
                const { done, value } = await reader.read();
                if (done) break; // Keluar dari loop jika stream selesai.
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                for (const line of lines) {
                    // Menangani pesan error khusus dari server.
                    if (line.startsWith('event: error')) {
                        const errorMessage = line.substring(line.indexOf('data:') + 5).trim();
                        throw new Error(errorMessage || 'Kesalahan dari server saat streaming.');
                    }
                    // Menangani data teks.
                    if (line.startsWith('data: ')) {
                        // Menambahkan data yang diterima ke buffer untuk diproses oleh interval pengetikan.
                        textBuffer += line.substring(6).trim().replace(/\\n/g, '\n');
                    }
                }
            }
        // Mode Statis: Jika pesan bertipe 'static', seluruh teks langsung dimasukkan ke buffer.
        } else if (type === 'static') {
            textBuffer = data.text;
        }

        // Interval untuk Finalisasi: Ini adalah 'penjaga' yang memastikan proses berakhir dengan bersih.
        // Interval ini terus memeriksa apakah `textBuffer` sudah kosong (artinya semua teks dari server sudah "diketik").
        const finalizationCheck = setInterval(() => {
            if (textBuffer.length === 0) {
                // Jika sudah kosong, hentikan semua interval.
                clearInterval(finalizationCheck);
                clearInterval(typingIntervalId);
                
                // Bersihkan teks final sebelum mengirim.
                const cleanedFinalText = cleanUpAiOutput(accumulatedText);
                
                // Kirim pesan 'done' dengan hasil akhir yang sudah bersih.
                self.postMessage({ type: 'done', finalContent: cleanedFinalText });
                
                // Tutup worker untuk membebaskan memori dan resource.
                self.close();
            }
        }, 50);

    } catch (e) {
        // Penanganan Kesalahan (Catch Block): Jika terjadi error di mana pun dalam blok `try`.
        clearInterval(typingIntervalId); // Hentikan interval pengetikan.
        // Kirim pesan 'error' ke thread utama dengan pesan kesalahannya.
        self.postMessage({ type: 'error', message: e.message });
        // Tutup worker.
        self.close();
    }
};