import {
    AllCommunityModule,
    ModuleRegistry,
    createGrid,
    // Part,
    colorSchemeDarkWarm,
    colorSchemeLightWarm,
    themeQuartz
} from "ag-grid-community";

ModuleRegistry.registerModules([AllCommunityModule]);


export function initGrid(container: HTMLElement, rowData: Record<string, unknown>[]) {
    const columnDefs = Object.keys(rowData[0] ?? {}).map((field) => ({ field }));
    // const myTheme = themeQuartz.withPart(colorScheme);
    return createGrid(
        container,
        {
            // theme: myTheme,
            rowData,
            columnDefs,
            defaultColDef: { 
                flex: 1, 
                filter: true, 
                floatingFilter: true, 
                minWidth: 150
            }
        }
    );
}