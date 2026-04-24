import { useEffect, useRef, useState } from 'react';
import useWebSocket from 'react-use-websocket';

const getDistance = (p1, p2) => {
    const x = (p1.x || 0) - (p2.x || 0);
    const y = (p1.y || 0) - (p2.y || 0);
    const z = (p1.z || 0) - (p2.z || 0);
    return Math.sqrt(x * x + y * y + z * z);
};

const toStableFallbackKey = (obj) => {
    const baseLabel = obj?.yolo_label || obj?.label || 'unknown';
    const bbox = obj?.bbox || [0, 0, 0, 0];
    const cx = Math.floor((((bbox[0] || 0) + (bbox[2] || 0)) / 2) / 96);
    const cy = Math.floor((((bbox[1] || 0) + (bbox[3] || 0)) / 2) / 96);
    const z = obj?.position?.z ?? 0;
    const zb = Math.round(z * 2);
    return `${baseLabel}_cell_${cx}_${cy}_${zb}`;
};

const normalizeDetection = (key, obj) => {
    const position = obj?.position || {
        x: obj?.x ?? 0,
        y: obj?.y ?? 0,
        z: obj?.z ?? 0
    };
    return {
        id: obj?.object_key || key,
        object_key: obj?.object_key || key,
        label: obj?.label || 'unknown',
        yolo_label: obj?.yolo_label || obj?.label || 'unknown',
        canonical_label: obj?.canonical_label || obj?.label || 'unknown',
        details: obj?.details || '',
        confidence: Number(obj?.confidence ?? 0),
        label_confidence: Number(obj?.label_confidence ?? obj?.confidence ?? 0),
        label_source: obj?.label_source || 'unknown',
        track_id: Number(obj?.track_id ?? -1),
        position
    };
};

const canonicalLabel = (obj) => (obj?.yolo_label || obj?.label || 'unknown');

export function useDashboardSocket({ isLiveDiff, referenceObjects, diffThreshold, setDiffResult }) {
    const [liveDetections, setLiveDetections] = useState([]);
    const [stats, setStats] = useState({ frames: 0, objects: 0, fps: 0 });
    const [activeScanId, setActiveScanId] = useState('');
    const [trajectories, setTrajectories] = useState({});
    const [lastSeen, setLastSeen] = useState({});
    const persistenceMap = useRef(new Map());
    const trajectoriesRef = useRef({});
    const lastSeenRef = useRef({});

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socketUrl = `${protocol}//${window.location.host}/ws/dashboard/dashboard_Main`;

    const { lastMessage, readyState } = useWebSocket(socketUrl, {
        shouldReconnect: () => true,
        onOpen: () => console.log('Dashboard Connected'),
    });

    useEffect(() => {
        if (lastMessage === null) return;
        const handle = window.setTimeout(() => {
            try {
                const data = JSON.parse(lastMessage.data);
                if (data.type !== 'detection' || !Array.isArray(data.objects)) return;
                if (data.scan_id) setActiveScanId(data.scan_id);

                const now = Date.now();
                const stateVector = data.state_vector || {};
                if (Object.keys(stateVector).length > 0) {
                    Object.entries(stateVector).forEach(([key, vec]) => {
                        persistenceMap.current.set(key, { ...normalizeDetection(key, vec), lastSeen: now });
                    });
                } else {
                    data.objects.forEach(obj => {
                        const key = obj.object_key || (obj.track_id > -1 ? `${obj.label}_${obj.track_id}` : toStableFallbackKey(obj));
                        persistenceMap.current.set(key, { ...normalizeDetection(key, obj), lastSeen: now });
                    });
                }

                for (const [key, val] of persistenceMap.current.entries()) {
                    if (now - val.lastSeen > 1800) persistenceMap.current.delete(key);
                }

                const liveSnapshot = Array.from(persistenceMap.current.values());
                setLiveDetections(liveSnapshot);

                if (isLiveDiff && Object.keys(referenceObjects).length > 0) {
                    const events = [];
                    const newTraj = { ...trajectoriesRef.current };
                    const newLastSeen = { ...lastSeenRef.current };
                    const liveKeys = new Set();

                    liveSnapshot.forEach(liveObj => {
                        const key = canonicalLabel(liveObj);
                        const display = liveObj?.label || key;
                        liveKeys.add(key);
                        if (!newTraj[key]) newTraj[key] = [];
                        newTraj[key].push(liveObj.position);
                        if (newTraj[key].length > 50) newTraj[key].shift();
                        newLastSeen[key] = now;

                        const refObj = referenceObjects[key];
                        if (refObj) {
                            const dist = getDistance(liveObj.position, refObj.position);
                            if (dist > Number(diffThreshold)) events.push({ type: 'MOVE', label: display, distance: dist });
                        } else {
                            events.push({ type: 'ADDED', label: display, distance: null });
                        }
                    });

                    Object.keys(referenceObjects).forEach(refKey => {
                        if (!liveKeys.has(refKey)) {
                            events.push({ type: 'MISSING', label: referenceObjects[refKey]?.display || refKey, distance: null });
                        }
                    });

                    trajectoriesRef.current = newTraj;
                    lastSeenRef.current = newLastSeen;
                    setTrajectories(newTraj);
                    setLastSeen(newLastSeen);
                    setDiffResult({ summary: `LIVE: ${events.length} changes detected`, events });
                }

                setStats(prev => ({
                    frames: prev.frames + 1,
                    objects: prev.objects + data.objects.length,
                    fps: Math.round(1000 / (Date.now() - prev.lastFrameTime || 1000)) || 30,
                    lastFrameTime: Date.now()
                }));
            } catch (e) {
                console.error('Parse error', e);
            }
        }, 0);
        return () => window.clearTimeout(handle);
    }, [lastMessage, isLiveDiff, referenceObjects, diffThreshold, setDiffResult]);

    const resetLiveData = () => {
        persistenceMap.current.clear();
        setLiveDetections([]);
        setStats({ frames: 0, objects: 0, fps: 0 });
        setDiffResult(null);
    };

    return {
        activeScanId,
        lastSeen,
        liveDetections,
        readyState,
        resetLiveData,
        stats,
        trajectories
    };
}

export { canonicalLabel };
