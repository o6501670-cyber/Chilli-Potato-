export const environment = {
  production: false,
  // Browser requests stay same-origin; Angular's dev server proxies these
  // paths to Django so the app also works inside a remote preview.
  apiUrl: ''
};
