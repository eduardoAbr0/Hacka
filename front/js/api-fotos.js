// Llamadas a la API de fotos (API_foto.py)

const apiFotos = {
    async estado() {
        const r = await fetch(`${API_URL}/api/estado`);
        return r.json();
    },

    async listar() {
        const r = await fetch(`${API_URL}/api/fotos`);
        return r.json();
    },

    urlFoto(foto) {
        return `${API_URL}${foto.url}`;
    }
};
