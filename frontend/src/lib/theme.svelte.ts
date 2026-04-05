// Define themeState as state that will be called across different pages

type Theme = 'dim' | 'emerald';

function createThemeState() {
    let value = $state<Theme>('dim');

    return {
        get value() { return value; },
        set value(v: Theme) {
            value = v;
            document.documentElement.setAttribute('data-theme', v);
        }
    };
}

export const themeState = createThemeState();
