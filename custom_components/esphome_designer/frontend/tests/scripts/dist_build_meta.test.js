import { describe, expect, it } from 'vitest';

import {
    computeSourceSignature,
    computeSourceSignatureFromGitRef
} from '../../../../../scripts/dist_build_meta.cjs';

describe('dist build metadata inputs (Issue #537)', () => {
    it('excludes runtime-fetched hardware recipes from the workspace signature', () => {
        const { files } = computeSourceSignature();

        expect(files.length).toBeGreaterThan(0);
        expect(files.filter((file) => file.includes('frontend/hardware/'))).toEqual([]);
        // Sanity: the actually bundled inputs stay tracked.
        expect(files.some((file) => file.includes('frontend/features/'))).toBe(true);
        expect(files.some((file) => file.includes('frontend/js/'))).toBe(true);
        expect(files).toContain('vite.config.js');
        expect(files).toContain('package.json');
    });

    it('excludes runtime-fetched hardware recipes from the committed-ref signature', () => {
        const { files } = computeSourceSignatureFromGitRef('HEAD');

        expect(files.length).toBeGreaterThan(0);
        expect(files.filter((file) => file.includes('frontend/hardware/'))).toEqual([]);
    });
});
