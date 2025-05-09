let isScanning = false; // スキャン状態を管理

function handleSearch(event) {
    event.preventDefault();
    const input = event.target.querySelector('input[name="query"]');
    if (input.value.length > 0) {
        event.target.submit();
    }
}

function toggleBarcodeButton(input) {
    const barcodeBtn = input.nextElementSibling;
    barcodeBtn.classList.toggle('hidden', input.value.length > 0);
}

function openBarcodeModal() {
    document.getElementById('barcodeModal').style.display = 'block';
}

function closeBarcodeModal() {
    try {
        Quagga.stop(); // カメラ停止（エラー対策）
        isScanning = false;
    } catch (e) {
        console.error('Quagga停止エラー:', e);
    }
    const modal = document.getElementById('barcodeModal');
    if (modal) {
        modal.style.display = 'none';
        document.querySelector('#barcode-scanner').innerHTML = '';
    }
}

function getCsrfToken() {
    return document.cookie.split('; ').find(row => row.startsWith('csrftoken=')).split('=')[1];
}

function readBarcode() {
    if (isScanning) return; // すでにスキャン中ならスキップ
    isScanning = true;

    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector('#barcode-scanner'),
            constraints: { width: 640, height: 480, facingMode: "environment" }
        },
        decoder: { readers: ["ean_reader"] }
    }, function(err) {
        if (err) {
            console.error('Quagga初期化エラー:', err);
            alert('カメラの初期化に失敗しました。手動でISBNを入力してください。');
            isScanning = false;
            return;
        }
        Quagga.start();
    });

    Quagga.onDetected(function(result) {
        const barcode = result.codeResult.code;
        if (barcode) {
            Quagga.stop();
            isScanning = false;
            document.querySelector('#barcode-scanner').innerHTML = '';
            fetch('/extract-isbn/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCsrfToken() },
                body: 'barcode=' + encodeURIComponent(barcode)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') showPopup(data.isbn);
                else alert(data.message || 'バーコード読み取りに失敗しました');
            })
            .catch(error => alert('バーコード読み取りエラー: ' + error.message));
        }
    });
}
function stopBarcode() {
    try {
        Quagga.stop();
        isScanning = false;
        document.querySelector('#barcode-scanner').innerHTML = '';
    } catch (e) {
        console.error('カメラ停止エラー:', e);
    }
}
function submitManualIsbn() {
    const isbn = document.getElementById('isbn-input').value;
    if (isbn && isbn.match(/^\d{13}$/)) {
        confirmIsbn(isbn); // 直接confirmIsbnを呼び出し
    } else {
        alert('ISBNは13桁の数字で入力してください');
    }
}

function showPopup(isbn) {
    const popup = document.getElementById('isbn-popup');
    const scannedIsbn = document.getElementById('scanned-isbn');
    const isbnEdit = document.getElementById('isbn-edit');
    scannedIsbn.textContent = isbn;
    isbnEdit.value = isbn;
    popup.style.display = 'block';
}

function closePopup() {
    document.getElementById('isbn-popup').style.display = 'none';
}

function confirmIsbn(isbn = document.getElementById('isbn-edit').value) {
    if (!isbn.match(/^\d{13}$/)) {
        alert('ISBNは13桁の数字で入力してください');
        return;
    }
    const formData = new FormData();
    formData.append('isbn', isbn);
    fetch('/search-book/', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(response => response.text())
    .then(html => {
        document.body.innerHTML = html;
        closeBarcodeModal();
    })
    .catch(error => console.error('検索エラー:', error));
}