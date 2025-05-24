let currentIsbn = null;

function getCsrfToken() {
    return document.cookie.split('; ').find(row => row.startsWith('csrftoken=')).split('=')[1];
}

function openStatusModal(isbn) {
    currentIsbn = isbn;
    document.getElementById('status-modal').style.display = 'block';
    const defaultRadio = document.querySelector('input[name="status"][value="want"]');
    if (defaultRadio) { // 念のため要素が存在するかチェック
        defaultRadio.checked = true;
    }
}

function changeStatusModal(isbn,currentBookStatus) {
    currentIsbn = isbn;
    document.getElementById('status-modal').style.display = 'block';
    const radioButtons = document.querySelectorAll('input[name="status"]');

    // 受け取った currentBookStatus に基づいてラジオボタンをチェック
    radioButtons.forEach(radio => {
        if (radio.value === currentBookStatus) {
            radio.checked = true; // 該当するラジオボタンをチェック
        } else {
            radio.checked = false; // それ以外のラジオボタンのチェックを外す
        }
    });
}

function closeStatusModal() {
    document.getElementById('status-modal').style.display = 'none';
    currentIsbn = null;
}
window.onclick = function(event) {
    const modal = document.getElementById('status-modal');
    if (event.target == modal) {
        closeStatusModal();
    }
}


function submitStatus() {
    const status = document.querySelector('input[name="status"]:checked')?.value;
    if (!status) return alert('ステータスを選択してください');
    const card = document.querySelector(`[data-isbn="${currentIsbn}"]`);
    const buttonsDiv = card.querySelector('.buttons');
    const url = buttonsDiv.dataset.added === 'true' ? `/update/${currentIsbn}/` : '/add/';
    const formData = new FormData();
    formData.append('isbn_id', currentIsbn);
    formData.append('status', status);
    formData.append('title', card.dataset.title);
    formData.append('author', card.dataset.author);
    fetch(url, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'added' || data.status === 'updated') {
            buttonsDiv.dataset.added = 'true';
            buttonsDiv.innerHTML = `
                <button class="update-btn"
                    onclick="changeStatusModal('${currentIsbn}', this.dataset.status)"
                    data-status="${status}">変更
                </button>
                <button class="delete-btn" onclick="deleteBook('${currentIsbn}')">削除</button>
                <span class="status-text">[${status === 'want' ? '読みたい' : status === 'reading' ? '読んでいる' : '読んだ'} に追加✓]</span>
            `;
            closeStatusModal();
        } else {
            alert('操作に失敗しました');
        }
    })
    .catch(error => console.error('エラー:', error));
}

function deleteBook(isbn) {
    fetch(`/delete/${isbn}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'deleted') {
            const card = document.querySelector(`[data-isbn="${isbn}"]`);
            const buttonsDiv = card.querySelector('.buttons');
            buttonsDiv.dataset.added = 'false';
            buttonsDiv.innerHTML = `<button class="add-btn" onclick="openStatusModal('${isbn}')">追加</button>`;
        } else {
            alert('削除に失敗しました');
        }
    })
    .catch(error => console.error('削除エラー:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('status-modal');
    modal.addEventListener('click', (event) => {
        if (event.target === modal) closeStatusModal();
    });
});