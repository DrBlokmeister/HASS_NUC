import { describe, expect, it, vi } from 'vitest';

import {
    exportDirect,
    exportLVGL,
    exportOEPL,
    exportOpenDisplay
} from '../../features/sun_times/exports.js';
import { formatSunTimeValue } from '../../features/sun_times/shared.js';

const directCtx = () => ({
    lines: [],
    addFont: vi.fn((family, weight, size) => `font_${size}`),
    getColorConst: vi.fn((value) => `COLOR_${String(value).toUpperCase()}`),
    getConditionCheck: vi.fn(() => '')
});

const lvglCtx = {
    common: { id: 'sun_1', x: 421, y: 0, width: 140, height: 54 },
    convertColor: vi.fn((value) => `Color(${value})`),
    getLVGLFont: vi.fn(() => 'font_ptr')
};

describe('sun_times exports (Issue #516)', () => {
    it('centers the two-row block in a 54px widget like the flex preview', () => {
        const ctx = directCtx();
        exportDirect({ x: 421, y: 0, width: 140, height: 54, props: {} }, ctx);

        const output = ctx.lines.join('\n');
        // Rows span 6..48 in a 0..54 box, i.e. block center = 27, matching a
        // CENTER_LEFT single-line widget at y=27 (see datetime export).
        expect(output).toContain('it.printf(427, 6, id(font_18)');
        expect(output).toContain('it.printf(453, 7, id(font_16)');
        expect(output).toContain('it.printf(427, 30, id(font_18)');
        expect(output).toContain('it.printf(453, 31, id(font_16)');
        expect(output).toContain('TextAlign::TOP_LEFT');
    });

    it('keeps the row block inside large padding', () => {
        const ctx = directCtx();
        exportDirect(
            { x: 0, y: 0, width: 140, height: 54, props: { padding: 10 } },
            ctx
        );

        const output = ctx.lines.join('\n');
        // Block placement respects padding: top = max(padding, (h-C)/2).
        expect(output).toContain('it.printf(10, 10, id(font_18)');
        expect(output).toContain('it.printf(36, 11, id(font_16)');
    });

    it('centers a single row within the widget height', () => {
        const ctx = directCtx();
        exportDirect(
            {
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: { show_sunrise: true, show_sunset: false }
            },
            ctx
        );

        const output = ctx.lines.join('\n');
        // contentHeight = 18 -> top = (54-18)/2 = 18; 16px text at 19..35
        // is centered around 27 just like a CENTER_LEFT line at y=27.
        expect(output).toContain('it.printf(6, 18, id(font_18)');
        expect(output).toContain('it.printf(32, 19, id(font_16)');
        expect(output).not.toContain('F059B');
    });

    it('centers the icon within the row when the font is taller than the icon', () => {
        const ctx = directCtx();
        exportDirect(
            {
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: {
                    show_sunrise: true,
                    show_sunset: false,
                    icon_size: 16,
                    font_size: 24
                }
            },
            ctx
        );

        const output = ctx.lines.join('\n');
        // rowHeight = 24, top = (54-24)/2 = 15; text stays at 15 while the
        // 16px icon moves to 15 + (24-16)/2 = 19 (preview align-items:center).
        expect(output).toContain('it.printf(6, 19, id(font_16)');
        expect(output).toContain('it.printf(30, 15, id(font_24)');
    });

    it('keeps default icon/text rows unchanged when the icon is taller', () => {
        const ctx = directCtx();
        exportDirect(
            {
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: { show_sunrise: true, show_sunset: false }
            },
            ctx
        );

        const output = ctx.lines.join('\n');
        expect(output).toContain('it.printf(6, 18, id(font_18)');
    });

    it('mirrors the icon centering in LVGL export', () => {
        const output = exportLVGL(
            {
                id: 'sun_1',
                x: 421,
                y: 0,
                width: 140,
                height: 54,
                props: {
                    show_sunrise: true,
                    show_sunset: false,
                    icon_size: 16,
                    font_size: 24
                }
            },
            lvglCtx
        );

        const labels = output.obj.widgets.map((entry) => entry.label);
        expect(labels[0].y).toBe(19);
        expect(labels[1].y).toBe(15);
    });

    it('mirrors the icon centering in OEPL protocol rows', () => {
        const rows = exportOEPL(
            {
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: {
                    show_sunrise: true,
                    show_sunset: false,
                    icon_size: 16,
                    font_size: 24
                }
            },
            { _layout: {}, _page: {} }
        );

        expect(rows[0].y).toBe(19);
        expect(rows[0].anchor).toBe('lt');
        expect(rows[1].y).toBe(15);
    });

    it('keeps OpenDisplay middle-anchored rows on the row center', () => {
        const rows = exportOpenDisplay(
            {
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: { show_sunrise: true, show_sunset: false }
            },
            { layout: { darkMode: false } }
        );

        // Single row: top = 18, middle = 18 + 18/2 = 27.
        expect(rows[0].y).toBe(27);
        expect(rows[0].anchor).toBe('lm');
        expect(rows[1].y).toBe(27);
    });
});

describe('sun_times 12h clock mode (Issue #540)', () => {
    it('emits 12h conversion code in direct export when clock_mode is 12h', () => {
        const ctx = directCtx();
        exportDirect({
            x: 0,
            y: 0,
            width: 140,
            height: 54,
            props: { clock_mode: '12h' }
        }, ctx);

        const output = ctx.lines.join('\n');
        expect(output).toContain('int display_hour = hour_value % 12;');
        expect(output).toContain('snprintf(buf, sizeof(buf), "%d:%02d %s", display_hour, minute_value, ampm);');
        expect(output).not.toContain('snprintf(buf, sizeof(buf), "%02d:%02d"');
    });

    it('keeps 24h conversion code by default', () => {
        const ctx = directCtx();
        exportDirect({ x: 0, y: 0, width: 140, height: 54, props: {} }, ctx);

        const output = ctx.lines.join('\n');
        expect(output).toContain('snprintf(buf, sizeof(buf), "%02d:%02d", hour_value, minute_value);');
        expect(output).not.toContain('display_hour');
    });

    it('uses 12h strftime in protocol templates when clock_mode is 12h', () => {
        const rows = exportOEPL(
            {
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: {
                    sunrise_entity: 'sensor.sun_next_rising',
                    sunset_entity: 'sensor.sun_next_setting',
                    clock_mode: '12h'
                }
            },
            { _layout: {}, _page: {} }
        );

        const texts = rows.map((row) => row.value).join('\n');
        expect(texts).toContain("%-I:%M %p");
        expect(texts).not.toContain("%H:%M");
    });

    it('emits 12h conversion code in LVGL display lambdas when clock_mode is 12h', () => {
        const output = exportLVGL(
            {
                id: 'sun_12h',
                x: 0,
                y: 0,
                width: 140,
                height: 54,
                props: {
                    sunrise_entity: 'sensor.sun_next_rising',
                    clock_mode: '12h'
                }
            },
            lvglCtx
        );

        const texts = output.obj.widgets
            .map((entry) => entry.label)
            .filter((label) => label.id.endsWith('_text'))
            .map((label) => label.text)
            .join('\n');
        expect(texts).toContain('%d:%02d %s');
        expect(texts).not.toContain('%02d:%02d');
    });

    it('formats preview values in 12h mode when requested', () => {
        expect(formatSunTimeValue('2026-10-03T15:05:00', 'n.d.', '12h')).toBe('3:05 PM');
        expect(formatSunTimeValue('2026-10-03T00:05:00', 'n.d.', '12h')).toBe('12:05 AM');
        expect(formatSunTimeValue('2026-10-03T06:05:00', 'n.d.', '24h')).toBe('06:05');
        expect(formatSunTimeValue('unknown', 'n.d.', '12h')).toBe('n.d.');
    });
});
