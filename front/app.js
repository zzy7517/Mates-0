document.addEventListener('DOMContentLoaded', () => {
    const recordButton = document.getElementById('recordButton');
    const transcriptionResult = document.getElementById('transcriptionResult');
    const statusIndicator = document.getElementById('statusIndicator');
    
    let ws = null;
    let record = null;
    let timeInte = null;
    let isRecording = false;

    navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia;

    function updateStatus(message, isError = false) {
        statusIndicator.textContent = message;
        statusIndicator.className = `mt-4 text-center text-sm ${isError ? 'text-red-600' : 'text-gray-600'}`;
    }

    function updateRecordButton(recording) {
        if (recording) {
            recordButton.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            recordButton.classList.add('bg-red-600', 'hover:bg-red-700', 'recording-pulse');
            recordButton.innerHTML = `
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="6" y="6" width="12" height="12" />
                </svg>
                Stop Recording
            `;
        } else {
            recordButton.classList.remove('bg-red-600', 'hover:bg-red-700', 'recording-pulse');
            recordButton.classList.add('bg-blue-600', 'hover:bg-blue-700');
            recordButton.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="6" stroke-width="2"/>
                </svg>
                Start Recording
            `;
        }
    }

    function startRecording() {
        const speakerVerificationCheckbox = document.getElementById('speakerVerification');
        const sv = speakerVerificationCheckbox.checked ? 1 : 0;
        const lang = document.getElementById("lang").value;
        
        const queryParams = [];
        if (lang) queryParams.push(`lang=${lang}`);
        if (sv) queryParams.push('sv=1');
        const queryString = queryParams.length > 0 ? `?${queryParams.join('&')}` : '';

        ws = new WebSocket(`ws://127.0.0.1:27000${queryString}`);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
            updateStatus('Connected to server');
            record.start();
            timeInte = setInterval(() => {
                if (ws.readyState === 1) {
                    const audioBlob = record.getBlob();
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        ws.send(audioBlob);
                        record.clear();
                    };
                    reader.readAsArrayBuffer(audioBlob);
                }
            }, 500);
        };

        ws.onmessage = (evt) => {
            try {
                const resJson = JSON.parse(evt.data);
                transcriptionResult.textContent += "\n" + (resJson.data || 'No speech recognized');
                transcriptionResult.scrollTop = transcriptionResult.scrollHeight;
            } catch (e) {
                transcriptionResult.textContent += "\n" + evt.data;
            }
        };

        ws.onclose = () => updateStatus('Disconnected from server');
        ws.onerror = (error) => updateStatus('Connection error', true);

        updateRecordButton(true);
        isRecording = true;
    }

    function stopRecording() {
        if (ws) {
            ws.close();
            record.stop();
            clearInterval(timeInte);
        }
        updateRecordButton(false);
        updateStatus('Ready to record');
        isRecording = false;
    }

    recordButton.onclick = () => {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    };

    if (!navigator.getUserMedia) {
        updateStatus('Your browser does not support audio input', true);
    } else {
        navigator.getUserMedia(
            { audio: true },
            (mediaStream) => {
                record = new Recorder(mediaStream);
                updateStatus('Ready to record');
            },
            (error) => {
                console.error(error);
                updateStatus('Error accessing microphone', true);
            }
        );
    }
});