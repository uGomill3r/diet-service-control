// Bloqueo de feriados en planificación (si decides cargar dinámicamente)
document.addEventListener("DOMContentLoaded", function () {
    const feriados = ["2025-10-08", "2025-12-25", "2026-01-01"];
    for (let i = 0; i < 5; i++) {
        const fechaInput = document.querySelector(`input[name="dia${i}"]`);
        if (fechaInput) {
            fechaInput.addEventListener("change", function () {
                if (feriados.includes(fechaInput.value)) {
                    alert("Este día es feriado. No se puede planificar servicio.");
                    fechaInput.value = "";
                }
            });
        }
    }
});
