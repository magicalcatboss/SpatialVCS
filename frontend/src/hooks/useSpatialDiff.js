import { useState } from 'react';
import { canonicalLabel } from './useDashboardSocket';

export function useSpatialDiff({ apiKey, beforeScanId, afterScanId, diffThreshold, setDiffResult }) {
    const [diffLoading, setDiffLoading] = useState(false);
    const [isLiveDiff, setIsLiveDiff] = useState(false);
    const [referenceObjects, setReferenceObjects] = useState({});

    const toggleLiveDiff = async () => {
        if (!isLiveDiff) {
            if (!beforeScanId) {
                alert('Please select a BEFORE scan as reference!');
                return;
            }
            try {
                const res = await fetch(`/spatial/memory/${beforeScanId}`);
                if (!res.ok) throw new Error('Failed to fetch scan data');
                const data = await res.json();
                const refMap = {};
                (data.detections || []).forEach(d => {
                    const key = canonicalLabel(d);
                    refMap[key] = {
                        position: d.position_3d,
                        display: d.gemini_name || d.label || key
                    };
                });
                setReferenceObjects(refMap);
                setIsLiveDiff(true);
            } catch (e) {
                alert('Error fetching reference scan: ' + e.message);
                setIsLiveDiff(false);
            }
        } else {
            setIsLiveDiff(false);
            setDiffResult(null);
        }
    };

    const handleRunDiff = async (e) => {
        e.preventDefault();
        if (!beforeScanId || !afterScanId) {
            alert('Please select both before/after scans.');
            return;
        }
        setDiffLoading(true);
        try {
            const res = await fetch('/spatial/diff', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': apiKey
                },
                body: JSON.stringify({
                    scan_id_before: beforeScanId,
                    scan_id_after: afterScanId,
                    threshold: Number(diffThreshold),
                })
            });
            if (!res.ok) {
                const errText = await res.text();
                console.error('Diff failed:', res.status, errText);
                alert(`Diff failed: ${res.status} ${res.statusText}`);
                setDiffResult(null);
                return;
            }
            setDiffResult(await res.json());
        } catch (err) {
            console.error('Diff exception:', err);
            alert('Diff error (see console)');
            setDiffResult(null);
        } finally {
            setDiffLoading(false);
        }
    };

    return { diffLoading, handleRunDiff, isLiveDiff, referenceObjects, toggleLiveDiff };
}
