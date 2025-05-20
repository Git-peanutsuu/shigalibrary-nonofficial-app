let deletedBooks = {};
function updateStatusText(li, status) {
    const statusText = li.querySelector('.status-text') || li.appendChild(document.createElement('span'));
    statusText.className = 'status-text';
    statusText.style.color = 'green';
    statusText.textContent = status ? `${status === 'want' ? '✓読みたい' : status === 'reading' ? '✓読んでいる' : '✓読んだ'}` : '未設定';
}

document.querySelectorAll('.book-form').forEach(form => {
    form.addEventListener('submit', function(e) {

        e.preventDefault();
        const li = this.closest('li');
        const isbn = li.dataset.isbn;
        fetch(this.action, {
            method: 'POST',
            body: new FormData(this),
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'updated') {
                updateStatusText(li, data.current_status);
            }
        })
        .catch(error => console.error('更新エラー:', error));
    });
});

function getCsrfToken() {
    return document.cookie.split('; ').find(row => row.startsWith('csrftoken=')).split('=')[1];
}

function attachDeleteEvent(btn) {
    btn.addEventListener('click', function() {
        const isbn = this.dataset.isbn;
        const li = btn.closest('li');
        const form = li.querySelector('form');
        const bookData = {
            title: li.dataset.title,
            author: li.dataset.author,
            status: form.querySelector('input[name=status]:checked')?.value || 'want'
        };
        fetch(`/delete/${isbn}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken() // Cookieから取得
            },
            body: new FormData(form) // 必要ならformデータを送信
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'deleted') {
                deletedBooks[isbn] = bookData;
                const statusText = li.querySelector('.status-text');
                statusText.style.color = 'red';
                statusText.textContent = '[削除済み]';
                btn.remove();
                form.innerHTML = `
                    <button type="button" class="undo-btn" data-isbn="${isbn}">削除を取り消す</button>
                `;
                attachUndoEvent(li.querySelector('.undo-btn'));
            } else {
                const errorMessage = li.querySelector('.error-message');
                errorMessage.style.display = 'block';
                errorMessage.textContent = '既に本は削除されています。一度読み込んでください';
            }
        })
        .catch(error => {
            console.error('削除エラー:', error);
            const errorMessage = li.querySelector('.error-message');
            errorMessage.style.display = 'block';
            errorMessage.textContent = '削除中にエラーが発生しました。';
        });
    });
}

function attachUndoEvent(btn) {
    btn.addEventListener('click', function() {
        const isbn = this.dataset.isbn;
        const li = btn.closest('li');
        const form = li.querySelector('form');
        const undoData = deletedBooks[isbn];
        if (!undoData) {
            console.error('削除データが見つかりません:', isbn);
            const errorMessage = li.querySelector('.error-message');
            errorMessage.style.display = 'block';
            errorMessage.textContent = '取り消しデータが見つかりません。';
            return;
        }
        const formData = new FormData();
        formData.append('title', undoData.title);
        formData.append('author', undoData.author);
        formData.append('isbn_id', isbn);
        formData.append('status', undoData.status);
        fetch('/add/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: new URLSearchParams(formData) // サーバーが期待する形式に
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'added') {
                updateStatusText(li, undoData.status);
                form.action = `/update/${isbn}/`;
                form.innerHTML = `
                <form class="book-form" method="post" action="/update/${isbn}/">
                    <div class="form-check">
                        <label><input type="radio" name="status" value="want" ${undoData.status === 'want' ? 'checked' : ''}>読みたい</label>
                        <label><input type="radio" name="status" value="reading" ${undoData.status === 'reading' ? 'checked' : ''}>読んでいる</label>
                        <label><input type="radio" name="status" value="read" ${undoData.status === 'read' ? 'checked' : ''}>読んだ</label>
                    </div>
                    <button type="submit" class="update-btn">変更</button>
                    <button type="button" class="delete-btn" data-isbn="${isbn}">削除</button>
                </form>
                `;
                delete deletedBooks[isbn];
                attachDeleteEvent(li.querySelector('.delete-btn'));
            } else {
                const errorMessage = li.querySelector('.error-message');
                errorMessage.style.display = 'block';
                errorMessage.textContent = data.message || '取り消しに失敗しました。';
            }
        })
        .catch(error => {
            console.error('取り消しエラー:', error);
            const errorMessage = li.querySelector('.error-message');
            errorMessage.style.display = 'block';
            errorMessage.textContent = '取り消し中にエラーが発生しました。';
        });
    });
}

document.querySelectorAll('.delete-btn').forEach(attachDeleteEvent);