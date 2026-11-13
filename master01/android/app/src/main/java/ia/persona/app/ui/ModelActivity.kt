package ia.persona.app.ui

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.widget.TextView
import ia.persona.app.engine.GenerationService
import ia.persona.app.engine.LocalJobs
import ia.persona.app.engine.ModelStore
import java.util.concurrent.Executors

/** Installation guidée du paquet de modèles locaux (une fois), puis tout fonctionne en mode avion. */
class ModelActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private lateinit var info: TextView
    private lateinit var progress: TextView
    private val listener: (LocalJobs.Status) -> Unit = { s -> ui { render(s) } }
    private var importSpec: ModelStore.Spec? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("Modèle local")
        col.label("Moteur sur le téléphone", 20f, bold = true, color = Color.BLACK)
        col.label("stable-diffusion.cpp (MIT) intégré à l'application · RealVisXL V4.0 Lightning (OpenRAIL++-M) · " +
            "VAE SDXL fp16-fix (MIT) · PhotoMaker v1 (Apache-2.0). Gratuit. Après installation, aucune connexion n'est utilisée.", 13f)
        info = col.label("", 14f)
        progress = col.label("", 14f)
        col.button("1. Télécharger les fichiers (≈ 8,2 Go, Wi-Fi conseillé)") {
            AlertDialog.Builder(this).setTitle("Téléchargement des modèles")
                .setMessage("Seuls ces 3 fichiers publics sont téléchargés depuis huggingface.co, à des versions figées, puis vérifiés (SHA-256). " +
                    "Aucune photo, aucun texte et aucun résultat n'est envoyé. Le téléchargement reprend là où il s'est arrêté.")
                .setPositiveButton("Télécharger") { _, _ -> if (!GenerationService.start(this, GenerationService.TASK_DOWNLOAD)) busy() }
                .setNegativeButton("Annuler", null).show()
        }
        col.button("…ou importer un fichier déjà téléchargé (sans réseau)") { chooseImport() }
        col.button("2. Préparer le modèle sur le téléphone (quantification q8_0)") {
            if (!GenerationService.start(this, GenerationService.TASK_QUANTIZE)) busy()
        }
        col.button("Arrêter la tâche en cours") { LocalJobs.cancel() }
        col.button("Vérifier le moteur natif") {
            io.execute {
                val msg = try { "Moteur OK : " + LocalJobs.newEngine(this).selfTest() } catch (e: Exception) { "Moteur indisponible : ${e.message}" }
                ui { progress.text = msg }
            }
        }
        col.button("Supprimer les modèles") {
            AlertDialog.Builder(this).setMessage("Supprimer tous les fichiers de modèle de l'application ?")
                .setPositiveButton("Supprimer") { _, _ -> LocalJobs.store(this).wipe(); refresh() }
                .setNegativeButton("Annuler", null).show()
        }
    }

    private fun busy() { progress.text = "Une autre tâche est en cours." }

    private fun chooseImport() {
        val specs = ModelStore.SPECS
        AlertDialog.Builder(this).setTitle("Quel fichier importer ?")
            .setItems(specs.map { "${it.file} (${it.size / ModelStore.MB} Mo)" }.toTypedArray()) { _, i ->
                importSpec = specs[i]
                startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE); type = "*/*"
                }, REQ_IMPORT)
            }.show()
    }

    @Deprecated("Activity API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri = data?.data ?: return
        val spec = importSpec ?: return
        if (requestCode != REQ_IMPORT || resultCode != RESULT_OK) return
        if (!LocalJobs.tryStart("import")) return busy()
        io.execute {
            try {
                LocalJobs.store(this).import(spec, contentResolver.openInputStream(uri)!!) { d, t ->
                    if (d % (64 * ModelStore.MB) < (1 shl 20)) LocalJobs.update(LocalJobs.status.copy(stage = "import ${spec.file}", bytes = d, totalBytes = t))
                }
                LocalJobs.update(LocalJobs.status.copy(running = false, stage = "${spec.file} importé et vérifié"))
            } catch (e: Exception) {
                LocalJobs.update(LocalJobs.status.copy(running = false, error = e.message))
            }
        }
    }

    private fun refresh() {
        val st = LocalJobs.store(this)
        val lines = ModelStore.SPECS.map { s ->
            val state = if (s === ModelStore.SDXL && st.quantReady()) "remplacé par la version quantifiée" else when (st.state(s)) {
                ModelStore.State.VERIFIED -> "vérifié ✓"; ModelStore.State.PARTIAL -> "téléchargement partiel (reprise possible)"
                ModelStore.State.PRESENT_UNVERIFIED -> "présent, à vérifier"; ModelStore.State.CORRUPT -> "corrompu : à retélécharger"
                ModelStore.State.ABSENT -> "absent"
            }
            "• ${s.file} — $state"
        }
        val q = st.quantInfo()
        info.text = lines.joinToString("\n") + "\n• ${ModelStore.QUANT_FILE} — " +
            (if (st.quantReady()) "prêt ✓ (${q?.optLong("size")?.div(ModelStore.MB)} Mo)" else "à préparer") +
            "\nEspace libre : ${st.freeBytes() / ModelStore.MB} Mo · encore nécessaire : ${st.bytesNeeded() / ModelStore.MB} Mo" +
            "\nÉtat : " + if (st.ready()) "PRÊT — la génération fonctionne hors ligne." else "installation incomplète."
        info.setTextColor(if (st.ready()) Color.rgb(0, 110, 0) else Color.DKGRAY)
    }

    private fun render(s: LocalJobs.Status) {
        val bytes = if (s.totalBytes > 0) " — ${s.bytes / ModelStore.MB}/${s.totalBytes / ModelStore.MB} Mo" else ""
        progress.setTextColor(if (s.error != null) Color.RED else Color.DKGRAY)
        progress.text = (s.error ?: (s.stage + bytes)) + if (s.running) "\n(en cours…)" else ""
        if (!s.running) refresh()
    }

    override fun onResume() { super.onResume(); refresh(); LocalJobs.listen(listener) }
    override fun onPause() { LocalJobs.unlisten(listener); super.onPause() }
    override fun onDestroy() { io.shutdown(); super.onDestroy() }

    companion object { const val REQ_IMPORT = 51 }
}
