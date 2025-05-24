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
    const buttonDiv = document.querySelector('#barcode-button-div');
    buttonDiv.innerHTML = `<button type="button" onclick="readBarcode()">バーコード読み取り</button>`;
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
    const buttonDiv = document.querySelector('#barcode-button-div');
    buttonDiv.innerHTML = `<button type="button" onclick="stopBarcode()">カメラを閉じる</button>`;
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

            buttonDiv.innerHTML = `<button type="button" onclick="readBarcode()">バーコード読み取り</button>`;
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
        const buttonDiv = document.querySelector('#barcode-button-div');
        buttonDiv.innerHTML = `<button type="button" onclick="readBarcode()">バーコード読み取り</button>`;
        document.querySelector('#barcode-scanner').innerHTML = '';
    } catch (e) {
        console.error('カメラ停止エラー:', e);
    }
}
function submitManualIsbn() {
    const rawIsbn = document.getElementById('isbn-input').value;
    const isbn = rawIsbn.replace(/-/g, '');

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

let currentBookData = null;

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
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            currentBookData = data.book;
            document.getElementById('result-isbn').textContent = data.book.isbn;
            document.getElementById('result-title').textContent = `タイトル: ${data.book.title}`;
            document.getElementById('result-author').textContent = `著者: ${data.book.author}`;
            document.getElementById('result-image').src = data.book.image_link || '';
            // availabilityの修正
            const availability = data.book.availability;
            let availabilityText = '滋賀県立図書館:情報取得中...';
            if (availability.libkey) {
                const libraryStatus = Object.values(availability.libkey)[0] || '不明';
                availabilityText = `滋賀県立図書館: ${libraryStatus}`;
            }
            document.getElementById('result-availability').textContent = availabilityText;
            document.getElementById('result-calil-link').href = data.book.calil_link;

            const resultModal = document.getElementById('result-modal');
            resultModal.classList.add('active');
            document.getElementById('isbn-popup').style.display = 'none';

            const buttonsDiv = resultModal.querySelector('.buttons');
            if (!buttonsDiv) {
                console.error('ボタンコンテナが見つかりません');
                return;
            }
            console.log('ボタン生成開始:', data.book.is_added);
            if (data.book.is_added) {
                    buttonsDiv.innerHTML = `
                    <span style="color: green;">[追加✓]</span>
                    <button onclick="updateBook()">変更</button>
                    <button onclick="cancelAdd()">追加取消</button>
                    <button onclick="restartScan()">もう一度読み取る</button>
                `;
            } else {
                buttonsDiv.innerHTML = `
                    <button onclick="addBook()">追加</button>
                    <button onclick="restartScan()">もう一度読み取る</button>
                `;
            }
            console.log('ボタン生成完了:', buttonsDiv.innerHTML);
        } else {
            alert(data.message || '検索に失敗しました');
        }
    })
    .catch(error => console.error('検索エラー:', error));
}

function updateBook() {
    if (!currentBookData) return;
    const status = document.querySelector('input[name="status"]:checked')?.value;
    if (!status) {
        alert('ステータスを選択してください');
        return;
    }
    const formData = new FormData();
    formData.append('isbn', currentBookData.isbn); // 既存
    formData.append('status', status); // ステータスを追加
    fetch(`/update/${currentBookData.isbn}/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'updated') {
            alert('ステータスが変更されました');
            window.dispatchEvent(new CustomEvent('dataChangedfromModalContent'));
        } else {
            alert('変更に失敗しました: ' + (data.message || ''));
        }
    })
    .catch(error => console.error('更新エラー:', error));
}

// 追加関数
function addBook() {
    if (!currentBookData) return;
    const formData = new FormData();
    formData.append('title', currentBookData.title);
    formData.append('author', currentBookData.author);
    formData.append('isbn_id', currentBookData.isbn);
    formData.append('status', 'want');
    fetch('/add/', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'added') {
            alert('本が追加されました');
            currentBookData.is_added = true;
            // ボタンをクライアント側で更新
            const buttonsDiv = document.querySelector('.buttons');
                buttonsDiv.innerHTML = `
                <span style="color: green;">[追加✓]</span>
                <button onclick="updateBook()">変更</button>
                <button onclick="cancelAdd()">追加取消</button>
                <button onclick="restartScan()">もう一度読み取る</button>
            `;
            window.dispatchEvent(new CustomEvent('dataChangedfromModalContent'));
        } else {
            alert('追加に失敗しました');
        }
    })
    .catch(error => console.error('追加エラー:', error));
}

function cancelAdd() {
    if (!currentBookData) return;
    fetch(`/delete/${currentBookData.isbn}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'deleted') {
            alert('本が削除されました');
            currentBookData.is_added = false;
            // ボタンをクライアント側で更新
            const buttonsDiv = document.querySelector('.buttons');
            buttonsDiv.innerHTML = `
                <button onclick="addBook()">追加</button>
                <button onclick="restartScan()">もう一度読み取る</button>
            `;
            window.dispatchEvent(new CustomEvent('dataChangedfromModalContent'));
        } else {
            alert('削除に失敗しました');
        }
    })
    .catch(error => console.error('削除エラー:', error));
}

function restartScan() {
    closeResultModal();
    document.getElementById('barcodeModal').style.display = 'block';
}

function closeResultModal() {
    document.getElementById('result-modal').classList.remove('active');
    currentBookData = null;
}


// モーダル外クリックで閉じる
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('barcodeModal');
    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeBarcodeModal();
        }
    });
    const resultModal = document.getElementById('result-modal');
    resultModal.addEventListener('click', (event) => {
        if (event.target === resultModal.parentElement) {
            closeResultModal();
        }
    });
});