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

interface dataverses {
    rowId: number;
    country: string;
    type: string;
    identifier: string;
    publishedAt: string;
    installation: string;
    installationUrl: string;
    imageUrl: string;
    publicationStatuses: string;
    affiliation: string;
    parentDataverseName: string;
    parentDataverseIdentifer: string;
    datasetCount: number;
}

interface InstallationsGeoJSON {
    features: { geometry: { coordinates: [number, number] }; properties: InstallationProperties }[];
}

const FLASK_URL = process.env.FLASK_URL ?? 'http://localhost:5000/databoard';

export const load: PageServerLoad = async ({ fetch }) => {
    let instRes, dvRes;
    try {
        [instRes, dvRes] = await Promise.all([
            fetch(`${FLASK_URL}/api/installations`),
            fetch(`${FLASK_URL}/api/dataverses`)
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

    const installations = await instRes.json() as InstallationsGeoJSON;
    const dataverses = await dvRes.json() as dataverses[];
    return { installations, dataverses };
};