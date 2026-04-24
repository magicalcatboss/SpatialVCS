import { useEffect, useState } from 'react';

export function useScans() {
    const [scanList, setScanList] = useState([]);
    const [beforeScanId, setBeforeScanId] = useState('');
    const [afterScanId, setAfterScanId] = useState('');

    const fetchScans = async () => {
        try {
            const res = await fetch('/spatial/scans');
            if (!res.ok) return;
            const data = await res.json();
            const scans = Array.isArray(data.scans) ? data.scans : [];
            setScanList(scans);
            setBeforeScanId(prev => prev || scans[0]?.scan_id || '');
            setAfterScanId(prev => prev || scans[1]?.scan_id || scans[0]?.scan_id || '');
        } catch (err) {
            console.error('Fetch scans failed:', err);
        }
    };

    useEffect(() => {
        const initialFetch = window.setTimeout(fetchScans, 0);
        const timer = setInterval(fetchScans, 5000);
        return () => {
            window.clearTimeout(initialFetch);
            clearInterval(timer);
        };
    }, []);

    return { afterScanId, beforeScanId, fetchScans, scanList, setAfterScanId, setBeforeScanId };
}
