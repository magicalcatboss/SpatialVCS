/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                "primary": "#00f0ff",
                "background-dark": "#0a0a0f",
                "surface-dark": "#101016",
                "surface-darker": "#050508",
                "ui-panel": "#14141a",
            },
            fontFamily: {
                "display": ["Inter", "sans-serif"],
                "mono": ["JetBrains Mono", "monospace"]
            },
            borderRadius: { "DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "2xl": "1rem", "full": "9999px" },
            backgroundImage: {
                'cyber-grid': "linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px)"
            },
            backgroundSize: {
                'cyber-grid': '20px 20px'
            },
            boxShadow: {
                'neon': '0 0 10px rgba(0, 240, 255, 0.3), 0 0 20px rgba(0, 240, 255, 0.1)',
                'neon-strong': '0 0 15px rgba(0, 240, 255, 0.5), 0 0 30px rgba(0, 240, 255, 0.2)',
            },
            animation: {
                'scan-vertical': 'scanVertical 3s linear infinite',
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            keyframes: {
                scanVertical: {
                    '0%': { top: '0%' },
                    '100%': { top: '100%' }
                }
            }
        },
    },
    plugins: [],
}
