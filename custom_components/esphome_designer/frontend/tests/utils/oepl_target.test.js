import { describe, expect, it } from 'vitest';
import { getOEPLTarget } from '../../js/utils/oepl_target.js';

describe('getOEPLTarget', () => {
    it('targets a device id', () => {
        expect(getOEPLTarget(' 95b2d0433f2c26d08088d6296a00a70d ')).toEqual({ device_id: '95b2d0433f2c26d08088d6296a00a70d' });
    });

    it('keeps legacy entity ids and falls back to the placeholder', () => {
        expect(getOEPLTarget('open_epaper_link.1234567890abcdef')).toEqual({ entity_id: 'open_epaper_link.1234567890abcdef' });
        expect(getOEPLTarget('')).toEqual({ entity_id: 'open_epaper_link.0000000000000000' });
        expect(getOEPLTarget(undefined)).toEqual({ entity_id: 'open_epaper_link.0000000000000000' });
    });
});
