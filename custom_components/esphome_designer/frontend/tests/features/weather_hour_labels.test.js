import { describe, expect, it } from 'vitest';

import { formatHourLabel, isTwelveHourClock } from '../../features/weather_forecast/day_labels.js';

describe('weather forecast hour labels (Issue #521)', () => {
    it('detects the 12h clock mode', () => {
        expect(isTwelveHourClock('12h')).toBe(true);
        expect(isTwelveHourClock('24h')).toBe(false);
        expect(isTwelveHourClock(undefined)).toBe(false);
        expect(isTwelveHourClock('')).toBe(false);
    });

    it('formats 24h labels zero-padded with :00', () => {
        expect(formatHourLabel(6, '24h')).toBe('06:00');
        expect(formatHourLabel('15', '24h')).toBe('15:00');
        expect(formatHourLabel(0)).toBe('00:00');
    });

    it('formats 12h labels compactly with AM/PM', () => {
        expect(formatHourLabel(0, '12h')).toBe('12AM');
        expect(formatHourLabel(6, '12h')).toBe('6AM');
        expect(formatHourLabel('09', '12h')).toBe('9AM');
        expect(formatHourLabel(12, '12h')).toBe('12PM');
        expect(formatHourLabel(15, '12h')).toBe('3PM');
        expect(formatHourLabel(23, '12h')).toBe('11PM');
    });

    it('normalizes out-of-range and invalid hours', () => {
        expect(formatHourLabel(24, '12h')).toBe('12AM');
        expect(formatHourLabel(25, '24h')).toBe('01:00');
        expect(formatHourLabel('bogus', '12h')).toBe('12AM');
    });
});
