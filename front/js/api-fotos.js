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

    async obtenerProductos() {
        try {
            const r = await fetch(`${API_URL}/api/productos`);
            if (r.ok) return await r.json();
        } catch (e) { }
        return [];
    },

    async buscarProductoPorCodigo(codigo) {
        try {
            const r = await fetch(`${API_URL}/api/productos/${codigo}`);
            if (r.ok) return await r.json();
        } catch (e) { }
        return null;
    },

    async trigger() {
        const r = await fetch(`${API_URL}/api/trigger`, { method: "POST" });
        return r.json();
    },

    async configCamara() {
        const r = await fetch(`${API_URL}/api/config_camara`);
        return r.json();
    },

    async guardarConfigCamara(ip_cam_url) {
        const r = await fetch(`${API_URL}/api/config_camara`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip_cam_url })
        });
        return r.json();
    },

    urlFoto(foto) {
        return `${API_URL}${foto.url}`;
    }
};
