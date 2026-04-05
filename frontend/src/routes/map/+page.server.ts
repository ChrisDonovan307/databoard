import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

interface InstallationProperties {
    name: string;
    country: string;
    description: string;
    doi_authority: string;
    hostname: string;
    launch_year: string;
    metrics: boolean;
    url: string;
}

interface InstallationsGeoJSON {
    features: { geometry: { coordinates: [number, number] }; properties: InstallationProperties }[];
}

type DatasetsByInstallation = { installation: string; count: number }[];
type InstallationsByCountry = { country: string; count: number }[];

const FLASK_URL = process.env.FLASK_URL ?? 'http://localhost:5000/databoard';

export const load: PageServerLoad = async ({ fetch, setHeaders }) => {
    setHeaders({ 'cache-control': 'max-age=300' });

    let instRes, dvRes, countriesRes;

    try {
        [instRes, dvRes, countriesRes] = await Promise.all([
            fetch(`${FLASK_URL}/api/installations`),
            fetch(`${FLASK_URL}/api/datasets-by-installation`),
            fetch(`${FLASK_URL}/api/installations-by-country`)
        ]);
    } catch (e) {
        throw error(503, `Cannot reach Flask: ${e instanceof Error ? e.message : e}`);
    }

    if (!instRes.ok) {
        const body = await instRes.text();
        throw error(instRes.status, `Bad response from Flask (${instRes.status}): ${body}`);
    }
    if (!dvRes.ok) {
        const body = await dvRes.text();
        throw error(dvRes.status, `Bad response from Flask (${dvRes.status}): ${body}`);
    }
    if (!countriesRes.ok) {
        const body = await countriesRes.text();
        throw error(countriesRes.status, `Bad response from Flask (${countriesRes.status}): ${body}`);
    }

    const installations = await instRes.json() as InstallationsGeoJSON;
    const dataverses = await dvRes.json() as DatasetsByInstallation;
    const countries = await countriesRes.json() as InstallationsByCountry;
    return { installations, dataverses, countries };
};