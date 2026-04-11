import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

type DatasetsByInstallation = { installation: string; count: number }[];

const FLASK_URL = process.env.FLASK_URL ?? 'http://localhost:5000/databoard';

export const load: PageServerLoad = async ({ fetch, setHeaders }) => {
    setHeaders({ 'cache-control': 'max-age=300' });

    let instRes, dvRes, countriesRes;

    try {
        [ dvRes ] = await Promise.all([
            fetch(`${FLASK_URL}/api/dataverses`),
        ]);
    } catch (e) {
        throw error(503, `Cannot reach Flask: ${e instanceof Error ? e.message : e}`);
    }
    if (!dvRes.ok) {
        const body = await dvRes.text();
        throw error(dvRes.status, `Bad response from Flask (${dvRes.status}): ${body}`);
    }

    const dataverses = await dvRes.json() as DatasetsByInstallation;
    return { dataverses };
};