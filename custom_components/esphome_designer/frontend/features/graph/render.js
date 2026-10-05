import { drawInternalGrid, drawSmartAxisLabels, generateHistoricalDataPoints, parseDuration } from '../../js/utils/graph_helpers.js';
import { fetchEntityHistory, getEntityAttributes } from '../../js/io/ha_api.js';
import { emit, EVENTS } from '../../js/core/events.js';

const historyCache = new Map();
const fetchInProgress = new Set();

/** @typedef {Widget & { props?: Record<string, any>, entity_id?: string, title?: string }} GraphWidget */

/**
 * @param {HTMLElement} el
 * @param {GraphWidget} widget
 * @param {{ getColorStyle: (value?: string) => string }} helpers
 */
export const render = (el, widget, { getColorStyle }) => {
    const props = widget.props || {};
    const entityId = widget.entity_id || "";
    const borderEnabled = props.border !== false;
    const isDark = getColorStyle() === "#ffffff";
    const fontFamily = props.font_family || "Roboto";
    const fontSize = Math.max(8, parseInt(String(props.font_size || 12), 10) || 12);
    const fontWeight = String(parseInt(String(props.font_weight || 400), 10) || 400);

    let bgColor = props.background_color;
    if (!bgColor || bgColor === "transparent" || bgColor === "inherit") {
        bgColor = isDark ? "black" : "white";
    }

    let color = props.color || "theme_auto";
    if (color === bgColor) {
        color = bgColor === "white" || bgColor === "#ffffff" ? "black" : "white";
    }

    const colorStyle = getColorStyle(color);
    const bgStyle = getColorStyle(bgColor);

    el.style.boxSizing = "border-box";
    el.style.backgroundColor = bgStyle;
    el.style.overflow = "hidden";

    if (props.border_width !== undefined ? props.border_width > 0 : borderEnabled) {
        const borderWidth = props.border_width !== undefined ? props.border_width : 2;
        const borderColor = getColorStyle(props.border_color || color);
        el.style.border = `${borderWidth}px solid ${borderColor}`;
        el.style.borderRadius = `${props.border_radius || 0}px`;
    } else {
        el.style.border = "none";
    }

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("viewBox", `0 0 ${widget.width} ${widget.height}`);
    svg.style.display = "block";

    const minValue = props.auto_scale !== false ? Number.NaN : (parseFloat(props.min_value) || 0);
    const maxValue = props.auto_scale !== false ? Number.NaN : (parseFloat(props.max_value) || 100);

    /** @type {Array<{ state: string | number, last_changed: number }> | null} */
    let historyData = null;
    /** @type {Array<Array<{ state: string | number, last_changed: number }>> | null} */
    let historyRuns = null;
    // Collects raw entries as { state, tsMs } where tsMs is null when the
    // payload carries no timestamp (legacy flat values).
    const collectEntries = (rawData) => {
        /** @type {Array<{ state: any, tsMs: number | null }>} */
        const entries = [];
        const pushValue = (state, tsMs) => {
            entries.push({ state, tsMs });
        };
        const pushPair = (item) => {
            if (!Array.isArray(item) || item.length < 2) return false;
            const ts = Number(item[0]);
            const raw = item[1];
            const value = raw === null || raw === undefined || raw === '' ? NaN : parseFloat(raw);
            pushValue(value, Number.isFinite(ts) ? ts * 1000 : null);
            return true;
        };
        if (Array.isArray(rawData)) {
            rawData.forEach((/** @type {any} */ item) => {
                if (pushPair(item)) return;
                if (typeof item === 'number') pushValue(item, null);
                else if (typeof item === 'string') {
                    const parsed = parseFloat(item);
                    if (!isNaN(parsed)) pushValue(parsed, null);
                } else if (typeof item === 'object' && item !== null && item.value !== undefined) {
                    const parsed = parseFloat(item.value);
                    if (!isNaN(parsed)) pushValue(parsed, null);
                }
            });
        } else if (typeof rawData === 'string') {
            try {
                const parsed = JSON.parse(rawData);
                if (Array.isArray(parsed)) {
                    parsed.forEach((/** @type {any} */ item) => {
                        if (pushPair(item)) return;
                        if (typeof item === 'number') pushValue(item, null);
                        else if (item?.value !== undefined) pushValue(parseFloat(item.value), null);
                    });
                }
            } catch {
                if (rawData.includes('value:') || rawData.includes('value :')) {
                    const regex = /value\s*:\s*([\d.-]+)/g;
                    /** @type {RegExpExecArray | null} */
                    let match;
                    while ((match = regex.exec(rawData)) !== null) {
                        pushValue(parseFloat(match[1]), null);
                    }
                } else {
                    const cleaned = rawData.replace(/[[\]"']/g, '');
                    cleaned.split(',').forEach((/** @type {string} */ segment) => {
                        const parsed = parseFloat(segment.trim());
                        if (!isNaN(parsed)) pushValue(parsed, null);
                    });
                }
            }
        }
        return entries;
    };
    if (entityId) {
        if (props.use_ha_history) {
            const attrs = getEntityAttributes(entityId);
            const attrName = props.history_attribute || 'history';
            if (attrs && attrs[attrName]) {
                const entries = collectEntries(attrs[attrName]);
                if (entries.length > 0) {
                    if (entries.some((entry) => entry.tsMs !== null)) {
                        // Timestamped v2 payload: keep true positions and split
                        // NaN gaps into separate runs like HA does (Issue #517).
                        historyData = entries
                            .filter((entry) => entry.tsMs !== null)
                            .map((entry) => ({ state: entry.state, last_changed: entry.tsMs }));
                        historyRuns = [];
                        let run = [];
                        historyData.forEach((entry) => {
                            if (isNaN(parseFloat(String(entry.state)))) {
                                if (run.length > 0) {
                                    historyRuns.push(run);
                                    run = [];
                                }
                            } else {
                                run.push(entry);
                            }
                        });
                        if (run.length > 0) historyRuns.push(run);
                    } else {
                        // Legacy payload without timestamps: spread evenly, exactly
                        // like the firmware renders legacy data.
                        const durationMs = parseDuration(props.duration || '1h') * 1000;
                        const now = Date.now();
                        const values = entries.map((entry) => entry.state);
                        const step = durationMs / Math.max(values.length - 1, 1);
                        historyData = values.map((value, index) => ({
                            state: value,
                            last_changed: now - durationMs + (index * step)
                        }));
                    }
                }
            }
        } else {
            const duration = props.duration || "1h";
            const cacheKey = `${entityId}_${duration}`;
            const cached = historyCache.get(cacheKey);

            if (cached && (Date.now() - cached.timestamp < 60000)) {
                historyData = cached.data;
            } else if (!fetchInProgress.has(cacheKey)) {
                fetchInProgress.add(cacheKey);
                fetchEntityHistory(entityId, duration).then((/** @type {any[]} */ data) => {
                    historyCache.set(cacheKey, { data, timestamp: Date.now() });
                    fetchInProgress.delete(cacheKey);
                    emit(EVENTS.WIDGET_UPDATED, widget.id);
                }).catch(() => {
                    fetchInProgress.delete(cacheKey);
                });
            }
        }
    }

    let effectiveMin = minValue;
    let effectiveMax = maxValue;
    if (historyData && historyData.length > 0 && (isNaN(minValue) || isNaN(maxValue))) {
        const values = historyData.map((/** @type {{ state: string | number }} */ item) => parseFloat(String(item.state))).filter((/** @type {number} */ value) => !isNaN(value));
        if (values.length > 0) {
            effectiveMin = Math.min(...values);
            effectiveMax = Math.max(...values);
            const pad = (effectiveMax - effectiveMin) * 0.1 || 1.0;
            effectiveMin -= pad;
            effectiveMax += pad;
        }
    }
    if (isNaN(effectiveMin)) effectiveMin = 0;
    if (isNaN(effectiveMax)) effectiveMax = 100;

    // Drawn after the scale is known so the y-grid step maps to real divisions.
    if (props.grid !== false) {
        drawInternalGrid(
            svg,
            widget.width,
            widget.height,
            props.x_grid,
            props.y_grid,
            isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
            {
                duration: props.duration || "1h",
                minValue: effectiveMin,
                maxValue: effectiveMax
            }
        );
    }

    const runs = historyRuns || [historyData || []];
    runs.forEach((run) => {
        const points = generateHistoricalDataPoints(
            widget.width,
            widget.height,
            effectiveMin,
            effectiveMax,
            run,
            props.duration,
            // HA-history runs keep true positions: never extend stale data to
            // "Now" (Issue #517). Live data keeps the previous behavior.
            { extendToNow: !props.use_ha_history }
        );
        if (points.length === 0) return;

        const polyline = document.createElementNS(svgNS, "polyline");
        polyline.setAttribute("points", points.map((point) => `${point.x},${point.y}`).join(" "));
        polyline.setAttribute("fill", "none");
        polyline.setAttribute("stroke", colorStyle);
        polyline.setAttribute("stroke-width", String(parseInt(props.line_thickness || 3, 10)));
        polyline.setAttribute("stroke-linejoin", "round");

        const lineType = props.line_type || "SOLID";
        if (lineType === "DASHED") {
            polyline.setAttribute("stroke-dasharray", "5,5");
        } else if (lineType === "DOTTED") {
            polyline.setAttribute("stroke-dasharray", "2,2");
        }

        svg.appendChild(polyline);
    });
    el.appendChild(svg);

    const ownerDocument = el.ownerDocument || document;
    setTimeout(() => {
        if (ownerDocument.visibilityState === 'hidden' || !el.isConnected) {
            return;
        }

        const artboard = /** @type {HTMLElement | null} */ (el.closest('.artboard'));
        if (artboard && artboard.isConnected) {
            drawSmartAxisLabels(
                artboard,
                widget.x,
                widget.y,
                widget.width,
                widget.height,
                effectiveMin,
                effectiveMax,
                props.duration,
                widget.id,
                isDark ? "#ffffff" : "#666666",
                {
                    fontFamily,
                    fontSize,
                    fontWeight
                }
            );
        }
    }, 0);

    if (widget.title) {
        const label = document.createElement("div");
        label.style.position = "absolute";
        label.style.top = "2px";
        label.style.left = "50%";
        label.style.transform = "translateX(-50%)";
        label.style.fontSize = `${fontSize}px`;
        label.style.fontFamily = `${fontFamily}, system-ui, sans-serif`;
        label.style.fontWeight = fontWeight;
        label.style.color = colorStyle;
        label.style.backgroundColor = bgColor === "black" ? "rgba(0,0,0,0.7)" : "rgba(255,255,255,0.7)";
        label.style.padding = "0 4px";
        label.style.borderRadius = "2px";
        label.style.whiteSpace = "nowrap";
        label.textContent = widget.title;
        el.appendChild(label);
    } else if (!entityId) {
        const label = document.createElement("div");
        label.style.position = "absolute";
        label.style.top = "50%";
        label.style.left = "50%";
        label.style.transform = "translate(-50%, -50%)";
        label.style.fontSize = `${fontSize}px`;
        label.style.fontFamily = `${fontFamily}, system-ui, sans-serif`;
        label.style.fontWeight = fontWeight;
        label.style.color = isDark ? "#ccc" : "#999";
        label.style.backgroundColor = bgColor === "black" ? "rgba(0,0,0,0.8)" : "rgba(255,255,255,0.8)";
        label.style.padding = "2px 6px";
        label.textContent = "graph (No Entity)";
        el.appendChild(label);
    }
};
