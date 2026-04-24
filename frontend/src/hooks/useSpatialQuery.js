import { useState } from 'react';

export function useSpatialQuery({ apiKey, diffResult, isLiveDiff }) {
    const [query, setQuery] = useState('');
    const [searchAnswer, setSearchAnswer] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);

    const runSearch = async (nextQuery = query) => {
        setIsSearching(true);
        setSearchAnswer('');
        setSearchResults([]);
        try {
            const res = await fetch('/spatial/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': apiKey
                },
                body: JSON.stringify({ query: nextQuery, top_k: 4 })
            });
            if (!res.ok) {
                setSearchAnswer(`Error: ${res.statusText}`);
                return;
            }
            const data = await res.json();
            setSearchAnswer(data.answer || 'No synthesis available.');
            let results = data.results || [];
            if (isLiveDiff && diffResult && diffResult.events) {
                results = results.map(res => {
                    const relevantEvent = diffResult.events.find(ev =>
                        res.description.toLowerCase().includes(ev.label.toLowerCase()) ||
                        ev.label.toLowerCase().includes(res.label?.toLowerCase() || '')
                    );
                    if (!relevantEvent) return res;
                    return {
                        ...res,
                        description: `${res.description} \n\n[LIVE INSIGHT]: This object appears to be ${relevantEvent.type} (Distance: ${relevantEvent.distance?.toFixed(2)}m)!`
                    };
                });
            }
            setSearchResults(results);
        } catch (err) {
            console.error('Search Exception:', err);
            setSearchAnswer('Error: Network failed.');
        } finally {
            setIsSearching(false);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        await runSearch(query);
    };

    const speakAnswer = (text) => {
        if (!text || isSpeaking) return;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);
        speechSynthesis.cancel();
        speechSynthesis.speak(utterance);
    };

    return {
        handleSearch,
        isSearching,
        isSpeaking,
        query,
        runSearch,
        searchAnswer,
        searchResults,
        setQuery,
        speakAnswer
    };
}
