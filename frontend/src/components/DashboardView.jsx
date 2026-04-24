import React, { useState, useEffect } from 'react';
import { ReadyState } from 'react-use-websocket';
import { Search, Database, Box, Play, Wifi, Cpu, Activity, Clock, Settings, RefreshCw, Trash2, Mic, Volume2 } from 'lucide-react';
import SpatialView3D from './SpatialView3D';
import { useApiKey } from '../hooks/useApiKey';
import { useDashboardSocket } from '../hooks/useDashboardSocket';
import { useScans } from '../hooks/useScans';
import { useSpatialDiff } from '../hooks/useSpatialDiff';
import { useSpatialQuery } from '../hooks/useSpatialQuery';
import { useVoiceSearch } from '../hooks/useVoiceSearch';

const stringToColor = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
    return '#' + '00000'.substring(0, 6 - c.length) + c;
};

export default function DashboardView() {
    const [spatialSnapshot, setSpatialSnapshot] = useState([]);
    const [show3D, setShow3D] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [diffThreshold, setDiffThreshold] = useState(0.5);
    const [diffResult, setDiffResult] = useState(null);
    const [motionNow, setMotionNow] = useState(() => Date.now());
    const { apiKey, handleSaveKey } = useApiKey();
    const { afterScanId, beforeScanId, fetchScans, scanList, setAfterScanId, setBeforeScanId } = useScans();
    const { diffLoading, handleRunDiff, isLiveDiff, referenceObjects, toggleLiveDiff } = useSpatialDiff({
        apiKey,
        beforeScanId,
        afterScanId,
        diffThreshold,
        setDiffResult,
    });
    const {
        lastSeen,
        liveDetections,
        readyState,
        resetLiveData,
        stats,
        trajectories
    } = useDashboardSocket({ isLiveDiff, referenceObjects, diffThreshold, setDiffResult });
    const {
        handleSearch,
        isSearching,
        isSpeaking,
        query,
        runSearch,
        searchAnswer,
        searchResults,
        setQuery,
        speakAnswer
    } = useSpatialQuery({ apiKey, diffResult, isLiveDiff });
    const { isListening, startVoiceSearch } = useVoiceSearch({ apiKey, runSearch, setQuery });

    // 3D snapshot refresh every 3 seconds (non-realtime for stability)
    useEffect(() => {
        if (!show3D) return;
        const interval = setInterval(() => {
            setSpatialSnapshot([...liveDetections]);
        }, 3000);
        return () => clearInterval(interval);
    }, [show3D, liveDetections]);

    useEffect(() => {
        if (!isLiveDiff) return;
        const interval = setInterval(() => setMotionNow(Date.now()), 1000);
        return () => clearInterval(interval);
    }, [isLiveDiff]);

    return (
        <div className="bg-background-dark min-h-screen text-slate-200 font-display selection:bg-primary selection:text-background-dark p-6 flex flex-col">

            {/* Settings Modal */}
            {showSettings && (
                <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-surface-dark border border-primary/30 rounded-lg p-6 w-full max-w-sm shadow-neon">
                        <h3 className="text-lg font-bold text-primary mb-4 flex items-center">
                            <Settings className="w-5 h-5 mr-2" /> CONFIG
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs text-slate-400 mb-1 block">GEMINI API KEY</label>
                                <input
                                    type="text"
                                    value={apiKey}
                                    onChange={(e) => handleSaveKey(e.target.value)}
                                    placeholder="AIzaSy..."
                                    className="w-full bg-black border border-slate-700 rounded p-2 text-xs font-mono text-white focus:border-primary outline-none"
                                />
                            </div>
                            <button
                                onClick={() => setShowSettings(false)}
                                className="w-full bg-primary/20 hover:bg-primary/30 text-primary border border-primary/50 rounded py-2 text-sm font-bold transition-colors"
                            >
                                CLOSE
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <header className="flex items-center justify-between mb-8 border-b border-white/5 pb-4">
                <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-gradient-to-br from-primary to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary/20 border border-primary/30">
                        <Box className="text-white w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center">
                            SPATIAL<span className="text-primary">VCS</span>
                        </h1>
                        <p className="text-[10px] font-mono text-primary/60 tracking-widest uppercase">Command Center</p>
                    </div>
                </div>

                <div className="flex items-center space-x-6">
                    {/* Key Config Button */}
                    <button
                        onClick={() => setShowSettings(true)}
                        className={`flex items-center space-x-2 px-3 py-1.5 rounded border border-slate-700 text-xs font-mono transition-colors ${apiKey ? 'text-green-400 border-green-900/50 bg-green-900/10' : 'text-red-400 border-red-900/50 bg-red-900/10 animate-pulse'}`}
                    >
                        <Settings className="w-3 h-3" />
                        <span>{apiKey ? 'API KEY SET' : 'NO API KEY'}</span>
                    </button>

                    <div className="flex items-center space-x-6">
                        {/* Stats Items */}
                        <div className="flex items-center space-x-3 bg-surface-dark px-4 py-2 rounded border border-white/5">
                            <div className="p-1.5 bg-blue-500/10 rounded text-blue-400"><Activity className="w-4 h-4" /></div>
                            <div>
                                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Frames Processed</div>
                                <div className="text-lg font-bold text-white leading-none">{stats.frames}</div>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3 bg-surface-dark px-4 py-2 rounded border border-white/5">
                            <div className="p-1.5 bg-purple-500/10 rounded text-purple-400"><Database className="w-4 h-4" /></div>
                            <div>
                                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Objects Scanned</div>
                                <div className="text-lg font-bold text-white leading-none">{stats.objects}</div>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3 bg-surface-dark px-4 py-2 rounded border border-white/5">
                            <div className="p-1.5 bg-green-500/10 rounded text-green-400"><Clock className="w-4 h-4" /></div>
                            <div>
                                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Real-time FPS</div>
                                <div className="text-lg font-bold text-white leading-none">{stats.fps}</div>
                            </div>
                        </div>
                    </div>

                    <div className={`px-3 py-1 rounded border flex items-center space-x-2 ${readyState === ReadyState.OPEN ? 'border-green-500/50 bg-green-500/10 text-green-400' : 'border-red-500/50 bg-red-500/10 text-red-400'}`}>
                        <div className={`w-2 h-2 rounded-full ${readyState === ReadyState.OPEN ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                        <span className="text-xs font-mono font-bold">{readyState === ReadyState.OPEN ? 'ONLINE' : 'OFFLINE'}</span>
                    </div>

                    {/* Force Refresh Button */}
                    <button
                        onClick={() => {
                            resetLiveData();
                            fetchScans();
                            window.location.reload(); // Hard reload as requested
                        }}
                        className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded border border-slate-700 transition-colors mr-2"
                        title="Force Reload & Reset"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>

                    {/* Wipe Database Button */}
                    <button
                        onClick={async () => {
                            if (confirm("⚠️ DANGER: This will delete ALL scan history and spatial memory. Are you sure?")) {
                                try {
                                    const res = await fetch('/spatial/reset', {
                                        method: 'DELETE',
                                        headers: { 'x-api-key': apiKey }
                                    });
                                    if (!res.ok) {
                                        const body = await res.json().catch(() => ({}));
                                        alert("Wipe failed: " + (body.detail || res.statusText));
                                        return;
                                    }
                                    alert("System Wiped.");
                                    window.location.reload();
                                } catch (e) {
                                    alert("Wipe failed: " + e);
                                }
                            }
                        }}
                        className="p-2 bg-red-900/20 hover:bg-red-900/40 text-red-500 hover:text-red-400 rounded border border-red-900/50 transition-colors"
                        title="WIPE ALL DATA (Factory Reset)"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </header>

            <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">

                {/* Left: Live Detections */}
                <div className="col-span-8 flex flex-col space-y-4">
                    <div className="flex justify-between items-center">
                        <h2 className="text-sm font-mono text-primary/80 flex items-center"><Wifi className="w-4 h-4 mr-2" /> LIVE INTERCEPT</h2>
                        <button
                            onClick={() => { setShow3D(!show3D); if (!show3D) setSpatialSnapshot([...liveDetections]); }}
                            className={`px-3 py-1 rounded text-xs font-mono font-bold border transition-colors ${show3D ? 'bg-primary/20 text-primary border-primary/50' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'}`}
                        >
                            {show3D ? '⬛ HIDE 3D' : '🧊 SHOW 3D'}
                        </button>
                    </div>

                    {/* 3D Spatial View */}
                    {show3D && (
                        <div className="h-72 w-full">
                            <SpatialView3D objects={spatialSnapshot} />
                        </div>
                    )}

                    <div className="flex-1 grid grid-cols-3 gap-4 overflow-y-auto pr-2 content-start">
                        {liveDetections.map((obj, idx) => (
                            <div key={obj.id || `${obj.label}-${idx}`} className="bg-surface-dark border border-slate-800 p-4 rounded-lg hover:border-primary/50 transition-colors group relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-2 opacity-50 text-[10px] font-mono text-slate-500">#{String(obj.id || `${obj.label}-${idx}`).toUpperCase()}</div>
                                <div className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                                    <Box className="w-5 h-5 text-slate-400 group-hover:text-primary" />
                                </div>
                                <h3 className="text-lg font-bold text-white mb-1 group-hover:text-primary transition-colors">{obj.label}</h3>
                                <div className="text-xs font-mono text-slate-500 mb-3">CONFIDENCE: {(obj.confidence * 100).toFixed(1)}%</div>
                                <div className="p-2 bg-black rounded text-[10px] font-mono text-slate-400 grid grid-cols-3 gap-1 text-center">
                                    <div>X: {obj.position?.x.toFixed(1)}</div>
                                    <div>Y: {obj.position?.y.toFixed(1)}</div>
                                    <div>Z: {obj.position?.z.toFixed(1)}</div>
                                </div>
                            </div>
                        ))}
                        {liveDetections.length === 0 && (
                            <div className="col-span-3 h-64 flex items-center justify-center border-2 border-dashed border-slate-800 rounded-xl text-slate-600 font-mono">
                                WAITING FOR PROBE DATA...
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: Search */}
                <div className="col-span-4 bg-surface-darker/50 border-l border-slate-800 pl-6 flex flex-col">
                    <h2 className="text-sm font-mono text-primary/80 mb-4 flex items-center"><Cpu className="w-4 h-4 mr-2" /> SEMANTIC QUERY</h2>

                    <form id="search-form" onSubmit={handleSearch} className="mb-6 relative">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Example: 'Where are my keys?'"
                            className="w-full bg-surface-dark border border-slate-700 rounded-lg py-3 pl-4 pr-20 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
                        />
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center space-x-1">
                            <button
                                type="button"
                                onClick={startVoiceSearch}
                                disabled={isListening}
                                className={`p-1.5 rounded transition-colors ${isListening ? 'bg-red-500 text-white animate-pulse' : 'bg-slate-700 text-slate-400 hover:text-white hover:bg-slate-600'}`}
                                title="Voice Search"
                            >
                                <Mic className="w-4 h-4" />
                            </button>
                            <button type="submit" disabled={isSearching} className="p-1.5 bg-primary rounded text-black hover:bg-white transition-colors disabled:opacity-50">
                                {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                            </button>
                        </div>
                    </form>

                    {/* AI Answer Block */}
                    {searchAnswer && (
                        <div className="mb-4 bg-primary/10 border border-primary/30 p-3 rounded-lg">
                            <div className="flex justify-between items-start">
                                <h3 className="text-[10px] font-mono text-primary mb-1 uppercase tracking-wider flex items-center">
                                    <Cpu className="w-3 h-3 mr-1" /> AI Analysis
                                </h3>
                                <button
                                    onClick={() => speakAnswer(searchAnswer)}
                                    disabled={isSpeaking}
                                    className={`p-1 rounded transition-colors ${isSpeaking ? 'text-primary animate-pulse' : 'text-slate-400 hover:text-white'}`}
                                    title="Read aloud"
                                >
                                    <Volume2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                            <p className="text-sm text-white leading-relaxed font-sans">{searchAnswer}</p>
                        </div>
                    )}

                    <div className="flex-1 overflow-y-auto space-y-4">
                        {Array.isArray(searchResults) && searchResults.map((res, i) => (
                            <div key={i} className="bg-ui-panel border border-slate-700 rounded p-3 hover:border-primary/40 transition-colors">
                                <div className="text-xs font-mono text-green-400 mb-1">MATCH SCORE: {(res.score * 100).toFixed(0)}%</div>
                                <p className="text-sm text-slate-300 mb-2">{res.description}</p>
                                {res.frame_url && (
                                    <div className="h-24 bg-black rounded overflow-hidden relative group cursor-pointer">
                                        {/* Use relative path for proxy */}
                                        <img src={res.frame_url} className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                )}
                            </div>
                        ))}

                        <div className="border-t border-slate-800 pt-4 mt-4">
                            <h3 className="text-xs font-mono text-primary/80 mb-3">SPATIAL DIFF</h3>
                            <form onSubmit={handleRunDiff} className="space-y-2 mb-3">
                                <select
                                    value={beforeScanId}
                                    onChange={(e) => setBeforeScanId(e.target.value)}
                                    className="w-full bg-surface-dark border border-slate-700 rounded p-2 text-xs text-white"
                                >
                                    <option value="">Select BEFORE scan</option>
                                    {scanList.map((s) => (
                                        <option key={`before-${s.scan_id}`} value={s.scan_id}>
                                            {s.scan_id}
                                        </option>
                                    ))}
                                </select>
                                <select
                                    value={afterScanId}
                                    onChange={(e) => setAfterScanId(e.target.value)}
                                    className="w-full bg-surface-dark border border-slate-700 rounded p-2 text-xs text-white"
                                >
                                    <option value="">Select AFTER scan</option>
                                    {scanList.map((s) => (
                                        <option key={`after-${s.scan_id}`} value={s.scan_id}>
                                            {s.scan_id}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    type="number"
                                    min="0"
                                    step="0.1"
                                    value={diffThreshold}
                                    onChange={(e) => setDiffThreshold(e.target.value)}
                                    className="w-full bg-surface-dark border border-slate-700 rounded p-2 text-xs text-white"
                                    placeholder="Threshold (meters)"
                                />
                                <button
                                    type="submit"
                                    disabled={diffLoading}
                                    className="w-full bg-primary text-black rounded py-2 text-xs font-bold disabled:opacity-60"
                                >
                                    {diffLoading ? 'RUNNING...' : 'RUN DIFF'}
                                </button>

                                <button
                                    type="button"
                                    onClick={toggleLiveDiff}
                                    className={`w-full mt-2 rounded py-2 text-xs font-bold transition-colors ${isLiveDiff
                                        ? 'bg-red-500/20 text-red-400 border border-red-500/50 animate-pulse'
                                        : 'bg-green-500/20 text-green-400 border border-green-500/50 hover:bg-green-500/30'
                                        }`}
                                >
                                    {isLiveDiff ? 'STOP LIVE DIFF (BETA)' : 'START LIVE DIFF (BETA)'}
                                </button>
                            </form>

                            {diffResult && (
                                <div className="space-y-2">
                                    <div className="text-[11px] text-slate-300">
                                        {diffResult.summary}
                                    </div>
                                    {Array.isArray(diffResult.events) && diffResult.events.map((ev, idx) => (
                                        <div key={idx} className="border border-slate-700 rounded p-2 text-[11px]">
                                            <div className="font-mono text-primary">
                                                {ev.type} · {ev.label}
                                            </div>
                                            {typeof ev.distance === 'number' && (
                                                <div className="text-slate-400">distance: {ev.distance.toFixed(3)}m</div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Motion Tracker (Trajectories) */}
                            {isLiveDiff && (
                                <div className="mt-6 border-t border-slate-800 pt-4">
                                    <h3 className="text-xs font-mono text-primary/80 mb-3 flex items-center">
                                        <Activity className="w-3 h-3 mr-2" /> MOTION TRACKER (Top-Down X/Z)
                                    </h3>
                                    <div className="relative w-full h-48 bg-black/50 border border-slate-800 rounded overflow-hidden">
                                        {/* Grid */}
                                        <div className="absolute inset-0 grid grid-cols-4 grid-rows-4 pointer-events-none">
                                            {[...Array(16)].map((_, i) => <div key={i} className="border-slate-800/30 border-[0.5px]"></div>)}
                                        </div>

                                        {/* Render Dots */}
                                        {Object.entries(trajectories).map(([label, points]) => {
                                            // Simple scaling: Map -2m to 2m range to 0-100%
                                            const mapX = (x) => 50 + (x * 25); // Scale factor
                                            const mapZ = (z) => 50 + (z * 25);

                                            // Only show if active recently
                                            if (motionNow - (lastSeen[label] || 0) > 5000) return null;

                                            const color = stringToColor(label);

                                            return (
                                                <React.Fragment key={label}>
                                                    {/* Path */}
                                                    <svg className="absolute inset-0 w-full h-full pointer-events-none">
                                                        <polyline
                                                            points={points.map(p => `${mapX(p.x)},${mapZ(p.z)}`).join(' ')}
                                                            fill="none"
                                                            stroke={color}
                                                            strokeWidth="2"
                                                            opacity="0.5"
                                                        />
                                                    </svg>

                                                    {/* Current Point */}
                                                    {points.length > 0 && (() => {
                                                        const last = points[points.length - 1];
                                                        return (
                                                            <div
                                                                className="absolute w-2 h-2 rounded-full transform -translate-x-1/2 -translate-y-1/2 shadow-[0_0_10px_currentColor]"
                                                                style={{
                                                                    left: `${mapX(last.x)}%`,
                                                                    top: `${mapZ(last.z)}%`,
                                                                    backgroundColor: color,
                                                                    color: color
                                                                }}
                                                            >
                                                                <span className="absolute top-3 left-1/2 -translate-x-1/2 text-[9px] font-mono whitespace-nowrap">{label}</span>
                                                            </div>
                                                        );
                                                    })()}
                                                </React.Fragment>
                                            )
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
