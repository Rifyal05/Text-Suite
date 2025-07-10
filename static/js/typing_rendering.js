// Blok: Utilitas Global untuk Efek Mengetik (Typing Effect)
// Fungsi ini merender teks ke sebuah elemen HTML seolah-olah sedang diketik secara real-time, karakter per karakter.

// Blok: Konstanta Pengaturan
// Mengontrol kecepatan efek mengetik dalam milidetik per karakter. Semakin kecil nilainya, semakin cepat ketikannya.
const TYPING_SPEED = 3;

// Fungsi utama yang menginisialisasi dan mengontrol seluruh proses efek mengetik.
async function renderWithTypingEffect(targetDiv, textToRender, onProcessEndCallback) {
    // 1. Persiapan: Mengambil library 'marked' secara asinkron untuk parsing Markdown.
    // Ini memungkinkan teks yang diketik bisa mengandung format Markdown (seperti **tebal** atau *miring*).
    const marked = await getMarked(); 
    
    // 2. Inisialisasi Variabel Status: Menyimpan keadaan proses mengetik.
    let accumulatedText = ""; // Teks yang sudah ditampilkan di layar.
    let textBuffer = textToRender || ""; // Sisa teks yang belum ditampilkan.
    let typingIntervalId = null; // ID dari interval utama untuk bisa dihentikan nanti.
    let renderFinalized = false; // Flag untuk memastikan proses akhir hanya berjalan sekali.
    const scrollContainer = document.querySelector('.page-container') || document.documentElement; // Elemen yang akan di-scroll otomatis agar teks yang baru diketik selalu terlihat.

    // Blok: Fungsi Inti Pengetikan Karakter
    // Fungsi ini dipanggil berulang kali oleh setInterval. Tugasnya adalah mengambil satu karakter
    // dari buffer, menambahkannya ke teks yang sudah ada, lalu merender hasilnya (yang sudah diparsing
    // sebagai Markdown) ke dalam elemen target dan melakukan auto-scroll.
    function typeCharacter() {
        if (renderFinalized || textBuffer.length === 0) return;
        const char = textBuffer.substring(0, 1);
        accumulatedText += char;
        textBuffer = textBuffer.substring(1);
        targetDiv.innerHTML = marked.parse(accumulatedText);
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }

    // Blok: Penanganan Perubahan Visibilitas Tab
    // Ini adalah optimasi penting. Jika pengguna beralih ke tab lain, efek mengetik
    // akan dihentikan dan sisa teks langsung ditampilkan. Ini menghemat resource browser
    // dan memastikan pengguna melihat hasil lengkap saat kembali.
    const handleVisibilityChange = () => {
        if (document.visibilityState === 'hidden' && !renderFinalized) {
            clearInterval(typingIntervalId);
            accumulatedText += textBuffer;
            textBuffer = "";
            targetDiv.innerHTML = marked.parse(accumulatedText);
            finalizeRender(false);
        }
    };

    // Blok: Fungsi Finalisasi Render
    // Fungsi ini bertanggung jawab untuk membersihkan semua proses yang berjalan (interval,
    // event listener) setelah pengetikan selesai atau dihentikan. Ini juga memastikan
    // seluruh teks ditampilkan secara utuh dan memanggil callback jika ada.
    function finalizeRender(hadError = false) {
        if (renderFinalized) return;
        renderFinalized = true;
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        clearInterval(typingIntervalId);
        // Jika masih ada sisa teks di buffer, tampilkan semuanya.
        if (!hadError && textBuffer.length > 0) {
            accumulatedText += textBuffer;
            targetDiv.innerHTML = marked.parse(accumulatedText);
        }
        // Panggil callback untuk menandakan bahwa proses telah selesai.
        if (onProcessEndCallback) onProcessEndCallback(hadError, accumulatedText);
    }
    
    // 3. Pendaftaran Event Listener: Memantau jika pengguna meninggalkan tab.
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 4. Inisialisasi Tampilan: Mengosongkan elemen target sebelum memulai.
    targetDiv.innerHTML = '';
    
    // 5. Memulai Proses Mengetik: Menjalankan fungsi typeCharacter secara berkala.
    typingIntervalId = setInterval(typeCharacter, TYPING_SPEED);

    // 6. Memulai Pengecekan Akhir: Interval kedua yang bertugas memeriksa kapan
    // teks sudah habis diketik untuk kemudian memanggil fungsi finalisasi.
    const finalizationCheck = setInterval(() => {
        if (textBuffer.length === 0) {
            clearInterval(finalizationCheck);
            if (!renderFinalized) {
                finalizeRender(false);
            }
        }
    }, 100);
}