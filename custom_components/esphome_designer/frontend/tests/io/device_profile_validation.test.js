import { describe, expect, it } from 'vitest';

import { findDeviceProfileConflicts } from '../../js/io/device_profile_validation.js';

const profile = (overrides = {}) => ({
    name: 'Example Board',
    chip: 'esp32-s3',
    displayPlatform: 'qspi_dbi',
    displayModel: 'EXAMPLE',
    resolution: { width: 480, height: 320 },
    pins: { display: { cs: 'GPIO1' } },
    ...overrides
});

describe('device profile duplicate validation', () => {
    it('detects names duplicated through spacing, punctuation, or case changes', () => {
        const errors = findDeviceProfileConflicts({
            first: profile({ name: 'Seeed Studio reTerminal Sticky', hardwarePackage: 'hardware/first.yaml' }),
            second: profile({ name: 'seeedstudio-reterminal-sticky', hardwarePackage: 'hardware/second.yaml', chip: 'esp32' })
        });

        expect(errors).toContain('second duplicates normalized device name of first');
    });

    it('detects canonical profiles that reuse a hardware package despite different labels', () => {
        const errors = findDeviceProfileConflicts({
            first: profile({ name: 'Board A', hardwarePackage: 'hardware/shared.yaml' }),
            second: profile({ name: 'Board B', hardwarePackage: 'hardware/shared.yaml', displayModel: 'OTHER' })
        });

        expect(errors).toContain('second reuses hardware package hardware/shared.yaml from first');
    });

    it('detects copied generated profiles after descriptive metadata changes', () => {
        const errors = findDeviceProfileConflicts({
            first: profile({ name: 'Board A' }),
            second: profile({ name: 'Board B', isUntestedProfile: true })
        });

        expect(errors).toContain('second duplicates hardware definition of first');
    });

    it('allows different boards to share a controller and resolution', () => {
        const errors = findDeviceProfileConflicts({
            first: profile({ name: 'Board A', pins: { display: { cs: 'GPIO1' } } }),
            second: profile({ name: 'Board B', pins: { display: { cs: 'GPIO2' } } })
        });

        expect(errors).toEqual([]);
    });

    it('allows a compatible legacy alias that points directly to its canonical profile', () => {
        const canonical = profile({ name: 'Corrected Board', hardwarePackage: 'hardware/board.yaml' });
        const errors = findDeviceProfileConflicts({
            canonical,
            old_id: {
                ...canonical,
                name: 'Corrected Board (Legacy ID)',
                legacyAliasFor: 'canonical',
                isUntestedProfile: true
            }
        }, ['canonical']);

        expect(errors).toEqual([]);
    });

    it('rejects missing, chained, incompatible, and selectable aliases', () => {
        const canonical = profile({ name: 'Canonical', hardwarePackage: 'hardware/board.yaml' });
        const errors = findDeviceProfileConflicts({
            canonical,
            missing: { ...canonical, name: 'Missing', legacyAliasFor: 'does_not_exist' },
            alias: { ...canonical, name: 'Alias', legacyAliasFor: 'canonical' },
            chained: { ...canonical, name: 'Chained', legacyAliasFor: 'alias' },
            incompatible: {
                ...canonical,
                name: 'Incompatible',
                pins: { display: { cs: 'GPIO2' } },
                legacyAliasFor: 'canonical'
            }
        }, ['canonical', 'alias']);

        expect(errors).toContain('missing points to missing legacy alias target does_not_exist');
        expect(errors).toContain('alias is a legacy alias but is included in SUPPORTED_DEVICE_IDS');
        expect(errors).toContain('chained must point directly to a canonical profile, not alias alias');
        expect(errors).toContain('incompatible does not match hardware definition of canonical');
    });
});
