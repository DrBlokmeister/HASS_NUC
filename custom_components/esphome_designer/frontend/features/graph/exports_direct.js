/** @typedef {Widget & { props?: Record<string, any>, entity_id?: string, title?: string }} GraphWidget */

import { clampFontWeight } from '../../js/core/font_weights.js';
import {
    formatGraphLookbackLabel,
    getGraphGridDivisions,
    inferGraphTimeGrid,
    parseDuration,
    resolveGraphValueGrid,
    toEsphomeTimePeriod
} from '../../js/utils/graph_helpers.js';

/**
 * @param {GraphWidget} w
 * @param {Record<string, any>} context
 */
export const exportDoc = (w, context) => {
    const {
        lines, addFont, getColorConst, addDitherMask, getConditionCheck, isEpaper, sanitize
    } = context;

    const p = w.props || {};
    const entityId = (w.entity_id || "").trim();
    const title = sanitize(w.title || "");
    const duration = p.duration || "1h";
    const windowSec = Math.max(60, Math.round(parseDuration(duration)));
    const borderEnabled = p.border !== false;
    const backgroundProp = p.bg_color || p.background_color || "transparent";
    const bgColor = backgroundProp !== "transparent" ? getColorConst(backgroundProp) : null;
    const colorProp = p.color || "theme_auto";
    const color = getColorConst(colorProp);
    const lineThickness = parseInt(p.line_thickness || 3, 10);
    const fontFamily = p.font_family || "Roboto";
    const fontSize = parseInt(p.font_size || 12, 10) || 12;
    const fontWeight = clampFontWeight(fontFamily, parseInt(p.font_weight || 400, 10) || 400);
    const minValue = p.min_value || "";
    const maxValue = p.max_value || "";

    const safeId = `graph_${w.id}`.replace(/-/g, "_");
    const fontId = addFont(fontFamily, fontWeight, fontSize);

    const gridEnabled = p.grid !== false;
    const xGrid = gridEnabled
        ? toEsphomeTimePeriod(p.x_grid || inferGraphTimeGrid(duration), inferGraphTimeGrid(duration))
        : "";
    const yGrid = gridEnabled ? resolveGraphValueGrid(p.y_grid, minValue, maxValue) : "";
    // The native it.graph() renderer draws its own grid from the graph: component
    // config, so a hand-drawn overlay is only needed for the HA-history path.
    const usesNativeGraph = !p.use_ha_history;
    const gridDivisions = getGraphGridDivisions({
        duration,
        xGrid,
        yGrid,
        minValue: parseFloat(minValue) || 0,
        maxValue: parseFloat(maxValue) || 100
    });

    const cond = getConditionCheck(w);
    if (cond) lines.push(`        ${cond}`);

    if (bgColor) {
        lines.push(`        it.filled_rectangle(${w.x}, ${w.y}, ${w.width}, ${w.height}, ${bgColor});`);
    }

    if (entityId) {
        if (p.use_ha_history) {
            const histId = `hist_${w.id}`.replace(/-/g, "_");
            const useAutoScale = p.auto_scale !== false;

            lines.push(`        // Draw historical graph from global arrays ${histId} / ${histId}_ts`);
            lines.push('        // (_ts holds seconds since window start at fetch time). Each point');
            lines.push('        // sits at its true time position, so sparse data is NOT stretched');
            lines.push('        // across the window and gaps stay empty like in HA (Issue #517).');
            lines.push('        {');
            if (useAutoScale) {
                lines.push(`          float g_min = id(${histId}_min);`);
                lines.push(`          float g_max = id(${histId}_max);`);
                lines.push('          // Add slight padding to scale');
                lines.push('          float g_pad = (g_max - g_min) * 0.05;');
                lines.push('          if (g_pad == 0) g_pad = 1.0;');
                lines.push('          g_min -= g_pad; g_max += g_pad;');
                lines.push('          float g_range = g_max - g_min;');
            } else {
                lines.push(`          float g_min = ${minValue || "0"};`);
                lines.push(`          float g_max = ${maxValue || "100"};`);
                lines.push('          float g_range = g_max - g_min;');
            }
            lines.push('          if (g_range == 0) g_range = 1.0;');
            lines.push(`          const float g_win = ${windowSec};`);
            lines.push(`          int hist_count = id(${histId}_count);`);
            lines.push('          float g_shift = 0;');
            lines.push('          if (id(ha_time).now().is_valid()) {');
            lines.push(`            g_shift = (float)((long) id(ha_time).now().timestamp - (long) id(${histId}_fetch));`);
            lines.push('            if (g_shift < 0) g_shift = 0;');
            lines.push('          }');
            lines.push('          for (int i = 0; i + 1 < hist_count; i++) {');
            lines.push(`            float val1 = id(${histId})[i];`);
            lines.push(`            float val2 = id(${histId})[i+1];`);
            lines.push('            if (isnan(val1) || isnan(val2)) continue;');
            lines.push(`            float t1 = id(${histId}_ts)[i] - g_shift;`);
            lines.push(`            float t2 = id(${histId}_ts)[i+1] - g_shift;`);
            lines.push('            if ((t1 < 0 && t2 < 0) || (t1 > g_win && t2 > g_win)) continue;');
            lines.push('            if (t1 < 0) t1 = 0;');
            lines.push('            if (t2 < 0) t2 = 0;');
            lines.push('            if (t1 > g_win) t1 = g_win;');
            lines.push('            if (t2 > g_win) t2 = g_win;');
            lines.push(`            int x1 = ${w.x} + (int)(t1 / g_win * ${w.width});`);
            lines.push(`            int x2 = ${w.x} + (int)(t2 / g_win * ${w.width});`);
            lines.push(`            int y1 = ${w.y} + ${w.height} - (int)((val1 - g_min) / g_range * ${w.height});`);
            lines.push(`            int y2 = ${w.y} + ${w.height} - (int)((val2 - g_min) / g_range * ${w.height});`);
            lines.push(`            it.line(x1, y1, x2, y2, ${color});`);
            if (lineThickness > 1) {
                lines.push(`            it.line(x1, y1+1, x2, y2+1, ${color});`);
            }
            lines.push('          }');
            lines.push('          if (hist_count == 1) {');
            lines.push(`            float vsolo = id(${histId})[0];`);
            lines.push('            if (!isnan(vsolo)) {');
            lines.push(`              float tsolo = id(${histId}_ts)[0] - g_shift;`);
            lines.push('              if (tsolo < 0) tsolo = 0;');
            lines.push('              if (tsolo > g_win) tsolo = g_win;');
            lines.push(`              int xsolo = ${w.x} + (int)(tsolo / g_win * ${w.width});`);
            lines.push(`              int ysolo = ${w.y} + ${w.height} - (int)((vsolo - g_min) / g_range * ${w.height});`);
            lines.push(`              it.filled_circle(xsolo, ysolo, 2, ${color});`);
            lines.push('            }');
            lines.push('          }');
            lines.push("");
            lines.push('          // Y-axis labels (Dynamic)');
            lines.push('          for (int i = 0; i <= 4; i++) {');
            lines.push('            float val = g_min + (g_range * i / 4.0);');
            lines.push(`            int yOffset = ${w.height} * (4 - i) / 4;`);
            lines.push('            const char* fmt = g_range >= 10 ? "%.0f" : "%.1f";');
            lines.push(`            it.printf(${w.x} - 4, ${w.y} + yOffset - 6, id(${fontId}), ${color}, TextAlign::TOP_RIGHT, fmt, val);`);
            lines.push('          }');
            lines.push('        }');
        } else {
            lines.push(`        it.graph(${w.x}, ${w.y}, id(${safeId}));`);
            lines.push("");

            if (p.auto_scale !== false && (!minValue && !maxValue)) {
                lines.push('        // [Designer] Graph is auto-scaled without HA History or static Min/Max bounds.');
                lines.push('        // Y-axis labels are omitted because the scale is unknown at compile time.');
            } else {
                lines.push('        // Y-axis labels (Static Reference)');
                const minY = parseFloat(minValue) || 0;
                const maxY = parseFloat(maxValue) || 100;
                const yRange = maxY - minY;
                const ySteps = 4;
                for (let index = 0; index <= ySteps; index += 1) {
                    const ratio = index / ySteps;
                    const value = minY + (yRange * ratio);
                    const yOffset = Math.round(w.height * (1 - ratio));
                    const valueFormat = yRange >= 10 ? "%.0f" : "%.1f";
                    lines.push(`        it.printf(${w.x} - 4, ${w.y} + ${yOffset} - 6, id(${fontId}), ${color}, TextAlign::TOP_RIGHT, "${valueFormat}", (float)${value});`);
                }
            }
        }

        const borderWidth = parseInt(p.border_width !== undefined ? p.border_width : (borderEnabled ? 2 : 0), 10);
        if (borderWidth > 0) {
            const borderColorProp = p.border_color || colorProp;
            const borderColorConst = getColorConst(borderColorProp);
            for (let index = 0; index < borderWidth; index += 1) {
                lines.push(`        it.rectangle(${w.x} + ${index}, ${w.y} + ${index}, ${w.width} - 2 * ${index}, ${w.height} - 2 * ${index}, ${borderColorConst});`);
            }
            addDitherMask(lines, colorProp, isEpaper, w.x, w.y, w.width, w.height);
        }

        if (!usesNativeGraph && gridEnabled) {
            if (yGrid) {
                const ySteps = gridDivisions.y;
                for (let index = 1; index < ySteps; index += 1) {
                    const yOffset = Math.round(w.height * (index / ySteps));
                    lines.push(`        for (int i = 0; i < ${w.width}; i += 4) {`);
                    lines.push(`          it.draw_pixel_at(${w.x} + i, ${w.y + yOffset}, ${color});`);
                    lines.push('        }');
                }
            }

            if (xGrid) {
                const xSteps = gridDivisions.x;
                for (let index = 1; index < xSteps; index += 1) {
                    const xOffset = Math.round(w.width * (index / xSteps));
                    lines.push(`        for (int i = 0; i < ${w.height}; i += 4) {`);
                    lines.push(`          it.draw_pixel_at(${w.x + xOffset}, ${w.y} + i, ${color});`);
                    lines.push('        }');
                }
            }
        }

        if (title) {
            lines.push(`        it.printf(${w.x}+4, ${w.y}+2, id(${fontId}), ${color}, TextAlign::TOP_LEFT, "${title}");`);
        }

        const durationSec = parseDuration(duration);

        const xLabelSteps = 2;
        for (let index = 0; index <= xLabelSteps; index += 1) {
            const ratio = index / xLabelSteps;
            const xOffset = Math.round(w.width * ratio);
            let align = "TextAlign::TOP_CENTER";
            if (index === 0) align = "TextAlign::TOP_LEFT";
            if (index === xLabelSteps) align = "TextAlign::TOP_RIGHT";

            const labelText = index === xLabelSteps ? "Now" : formatGraphLookbackLabel(durationSec * (1 - ratio));
            lines.push(`        it.printf(${w.x} + ${xOffset}, ${w.y} + ${w.height} + 2, id(${fontId}), ${color}, ${align}, "${labelText}");`);
        }
    } else {
        lines.push(`        it.printf(${w.x}+5, ${w.y}+5, id(${fontId}), ${color}, TextAlign::TOP_LEFT, "Graph (no entity)");`);
    }

    if (cond) lines.push('        }');
};
