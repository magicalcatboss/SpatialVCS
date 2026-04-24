import { useState } from 'react';

export function useApiKey() {
    const [apiKey, setApiKey] = useState(() => localStorage.getItem('gemini_api_key') || '');

    const handleSaveKey = (key) => {
        setApiKey(key);
        localStorage.setItem('gemini_api_key', key);
    };

    return { apiKey, handleSaveKey };
}
