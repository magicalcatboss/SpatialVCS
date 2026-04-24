import { useRef, useState } from 'react';

export function useVoiceSearch({ apiKey, runSearch, setQuery }) {
    const [isListening, setIsListening] = useState(false);
    const recorderRef = useRef(null);
    const chunksRef = useRef([]);

    const startVoiceSearch = async () => {
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            alert('Voice recording not supported in this browser');
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mimeType = MediaRecorder.isTypeSupported?.('audio/webm') ? 'audio/webm' : '';
            const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
            chunksRef.current = [];
            recorderRef.current = recorder;
            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) chunksRef.current.push(event.data);
            };
            recorder.onstop = async () => {
                stream.getTracks().forEach(track => track.stop());
                setIsListening(false);
                const blobType = mimeType || recorder.mimeType || 'audio/webm';
                const fileExt = blobType.includes('mp4') ? 'm4a' : blobType.includes('ogg') ? 'ogg' : 'webm';
                const blob = new Blob(chunksRef.current, { type: blobType });
                const formData = new FormData();
                formData.append('file', blob, `voice-search.${fileExt}`);
                try {
                    const res = await fetch('/audio/transcribe', {
                        method: 'POST',
                        headers: { 'x-api-key': apiKey },
                        body: formData
                    });
                    if (!res.ok) throw new Error(res.statusText);
                    const data = await res.json();
                    const transcript = data.text || '';
                    if (transcript) {
                        setQuery(transcript);
                        await runSearch(transcript);
                    }
                } catch (err) {
                    console.error('Voice search failed:', err);
                    alert('Voice search failed.');
                }
            };
            setIsListening(true);
            recorder.start();
            window.setTimeout(() => {
                if (recorder.state === 'recording') recorder.stop();
            }, 4000);
        } catch (err) {
            console.error('Voice capture failed:', err);
            setIsListening(false);
        }
    };

    return { isListening, startVoiceSearch };
}
