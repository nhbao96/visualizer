window.onload = function() {
    const uploadForm = document.getElementById('upload-form');
    const uploadMessage = document.getElementById('upload-message');
    const chartsContainer = document.getElementById('charts-container');

    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData();
        const fileInput = document.getElementById('file-input');
        formData.append('file', fileInput.files[0]);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                uploadMessage.textContent = 'Lỗi: ' + data.error;
            } else {
                uploadMessage.textContent = 'Upload thành công!';
                loadChartsRealtime();
            }
        })
        .catch(error => {
            console.error('Lỗi khi upload file', error);
            uploadMessage.textContent = 'Lỗi khi upload file';
        });
    });

    function loadChartsRealtime() {
        fetch('/list_charts')
            .then(response => response.json())
            .then(data => {
                chartsContainer.innerHTML = '';

                data.charts.forEach(chart => {
                    const chartItem = document.createElement('div');
                    chartItem.className = 'chart-item';
                    
                    const img = document.createElement('img');
                    img.src = `/chart/${chart}?t=${new Date().getTime()}`;
                    img.alt = chart;

                    chartItem.appendChild(img);
                    chartsContainer.appendChild(chartItem);
                });
            })
            .catch(error => {
                console.error('Không thể tải danh sách biểu đồ', error);
                chartsContainer.innerHTML = '<p>Không thể tải danh sách biểu đồ</p>';
            });
    }

    // Lắng nghe sự kiện SSE
    const eventSource = new EventSource('/events');
    eventSource.onmessage = function(event) {
        if (event.data === 'update') {
            loadChartsRealtime(); // Cập nhật biểu đồ khi nhận được thông báo từ SSE
        }
    };

    loadChartsRealtime(); // Tải danh sách biểu đồ khi trang được tải
};
