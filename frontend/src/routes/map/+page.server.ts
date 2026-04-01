import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const FLASK_URL = process.env.FLASK_URL ?? 'http://localhost:5000/databoard';

export const load: PageServerLoad = async ({ fetch }) => {
    let res;
    try {
        res = await fetch(`${FLASK_URL}/api/installations`);
        debugger;
    } catch (e) {
        throw error(503, `Cannot reach Flask: ${e instanceof Error ? e.message : e}`);
    }

    if (!res.ok) {
        const body = await res.text();
        throw error(res.status, `Bad response from Flask (${res.status}): ${body}`);
    }

    const installations = await res.json();
    return { installations };
};