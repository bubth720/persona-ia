package ia.persona.app.engine

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import ia.persona.app.ui.App
import org.json.JSONObject
import java.io.File

/**
 * Service au premier plan : garde le calcul vivant pendant plusieurs minutes (écran éteint compris),
 * affiche une notification, et exécute la tâche demandée. L'inférence elle-même tourne dans le
 * processus natif séparé lancé par LocalEngine. Pas de reprise au milieu d'une inférence : après un arrêt,
 * l'utilisateur relance (les modèles et l'historique sont conservés).
 */
class GenerationService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val task = intent?.getStringExtra(EXTRA_TASK) ?: return START_NOT_STICKY
        val params = intent!!.getStringExtra(EXTRA_PARAMS)
        goForeground("PERSONA IA — ${label(task)}")
        val wake = (getSystemService(Context.POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "persona:generation").apply { acquire(3 * 60 * 60 * 1000L) }
        Thread {
            try {
                when (task) {
                    TASK_GENERATE -> runGenerate(JSONObject(params!!))
                    TASK_DOWNLOAD -> runDownload()
                    TASK_QUANTIZE -> runQuantize()
                }
            } catch (e: Throwable) {
                LocalJobs.update(LocalJobs.status.copy(running = false, error = e.message ?: e.javaClass.simpleName))
            } finally {
                LocalJobs.engine = null
                if (LocalJobs.status.running) LocalJobs.update(LocalJobs.status.copy(running = false))
                if (wake.isHeld) wake.release()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf(startId)
            }
        }.start()
        return START_NOT_STICKY
    }

    private fun label(task: String) = when (task) {
        TASK_GENERATE -> "génération locale"; TASK_DOWNLOAD -> "installation du modèle"; else -> "préparation du modèle"
    }

    private fun goForeground(text: String) {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "Calcul local", NotificationManager.IMPORTANCE_LOW))
        val n = Notification.Builder(this, CHANNEL).setContentTitle(text)
            .setContentText("Calcul sur le téléphone, sans réseau. Peut durer plusieurs minutes et chauffer.")
            .setSmallIcon(android.R.drawable.ic_menu_gallery).setOngoing(true).build()
        if (Build.VERSION.SDK_INT >= 34) startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        else startForeground(NOTIF_ID, n)
    }

    private fun runGenerate(p: JSONObject) {
        val store = LocalJobs.store(this)
        if (!store.ready()) throw IllegalStateException("modèle local non installé")
        val lib = App.library(this)
        val shas = (0 until p.getJSONArray("refs").length()).map { p.getJSONArray("refs").getString(it) }
        val refs = shas.mapNotNull { lib.get(it) }.filter { it.authorized }.map { lib.fileFor(it) }
        if (refs.isEmpty()) throw IllegalStateException("aucune référence autorisée sélectionnée")
        val engine = LocalJobs.newEngine(this)
        LocalJobs.engine = engine
        val (id, dir) = LocalJobs.newHistoryEntry(this)
        val out = File(dir, "result.png")
        val req = LocalEngine.Request(
            prompt = p.getString("prompt"), negative = p.getString("negative"),
            width = p.getInt("width"), height = p.getInt("height"), steps = p.getInt("steps"),
            cfg = p.getDouble("cfg").toFloat(), seed = p.getLong("seed"), references = refs,
            styleStrength = p.optInt("style_strength", 20), threads = p.getInt("threads"))
        val thermalStart = LocalJobs.thermalStatus(this)
        val meta = JSONObject().put("id", id).put("created_ms", System.currentTimeMillis())
            .put("engine", "stable-diffusion.cpp (libsdcli.so, ARM64 CPU)").put("profile", p.optString("profile"))
            .put("prompt", req.prompt).put("user_description", p.optString("description")).put("negative", req.negative)
            .put("seed", req.seed).put("width", req.width).put("height", req.height).put("steps", req.steps)
            .put("cfg", req.cfg.toDouble()).put("threads", req.threads)
            .put("references", LocalJobs.refIds(shas))
            .put("models", JSONObject().put("diffusion", ModelStore.QUANT_FILE)
                .put("diffusion_sha256", store.quantInfo()?.optString("sha256"))
                .put("vae", ModelStore.VAE.file).put("photomaker", ModelStore.PHOTOMAKER.file))
            .put("thermal_status_start", thermalStart)
        try {
            val r = engine.generate(req, store.models(), out) { ev ->
                val thermal = LocalJobs.thermalStatus(this)
                if (thermal >= PowerManager.THERMAL_STATUS_SEVERE) {
                    meta.put("stopped_for_heat", thermal); engine.cancel()
                }
                LocalJobs.update(LocalJobs.status.copy(stage = ev.stage.label, step = ev.step, totalSteps = ev.totalSteps,
                    message = if (thermal >= PowerManager.THERMAL_STATUS_MODERATE) "L'appareil chauffe." else ""))
            }
            meta.put("status", "generated").put("seconds", r.seconds).put("peak_rss_mb", r.peakRssMb)
                .put("thermal_status_end", LocalJobs.thermalStatus(this))
                .put("result_sha256", ModelStore.sha256(out.inputStream(), out.length()) { _, _ -> })
            File(dir, "engine.log").writeText(r.log.takeLast(20_000))
            File(dir, "meta.json").writeText(meta.toString(2))
            LocalJobs.update(LocalJobs.status.copy(running = false, stage = "terminé", resultId = id))
        } catch (e: LocalEngine.EngineError) {
            meta.put("status", "failed").put("error_kind", e.kind.name).put("error", e.message)
            File(dir, "engine.log").writeText(e.logTail)
            File(dir, "meta.json").writeText(meta.toString(2))
            val msg = when (e.kind) {
                LocalEngine.ErrorKind.OUT_OF_MEMORY -> "Mémoire insuffisante : fermez d'autres applications ou passez en profil Prudent."
                LocalEngine.ErrorKind.CANCELLED -> if (meta.has("stopped_for_heat")) "Arrêt : l'appareil est trop chaud." else "Annulé."
                LocalEngine.ErrorKind.MODEL_MISSING -> "Modèle manquant : réinstallez-le depuis l'écran Modèle local."
                LocalEngine.ErrorKind.ENGINE_MISSING -> "Moteur natif absent de cette APK."
                else -> "Échec du moteur : ${e.message}"
            }
            LocalJobs.update(LocalJobs.status.copy(running = false, error = msg))
        }
    }

    private fun runDownload() {
        val store = LocalJobs.store(this)
        for (s in ModelStore.SPECS) {
            if (s === ModelStore.SDXL && store.quantReady()) continue
            if (store.state(s) == ModelStore.State.PRESENT_UNVERIFIED) {
                LocalJobs.update(LocalJobs.status.copy(stage = "vérification ${s.file}"))
                if (store.verify(s)) continue else store.target(s).delete()
            }
            LocalJobs.update(LocalJobs.status.copy(stage = "téléchargement ${s.file}", bytes = 0, totalBytes = s.size))
            var last = 0L
            store.download(s, cancelled = { LocalJobs.cancelFlag }, onProgress = { done, total ->
                if (done - last > 8 * ModelStore.MB || done == total) {
                    last = done; LocalJobs.update(LocalJobs.status.copy(bytes = done, totalBytes = total))
                }
            })
        }
        LocalJobs.update(LocalJobs.status.copy(running = false, stage = "fichiers téléchargés et vérifiés"))
    }

    private fun runQuantize() {
        val store = LocalJobs.store(this)
        val engine = LocalJobs.newEngine(this)
        LocalJobs.engine = engine
        LocalJobs.update(LocalJobs.status.copy(stage = "quantification q8_0 (quelques minutes)"))
        val info = store.quantize(engine) { }
        store.deleteOriginalSdxl()
        LocalJobs.update(LocalJobs.status.copy(running = false,
            stage = "modèle prêt (${info.getLong("size") / ModelStore.MB} Mo, empreinte " +
                (if (info.getBoolean("matches_ci_reference")) "identique à la CI" else "différente de la CI x86 : signalé") + ")"))
    }

    companion object {
        const val CHANNEL = "persona_local"
        const val NOTIF_ID = 42
        const val EXTRA_TASK = "task"
        const val EXTRA_PARAMS = "params"
        const val TASK_GENERATE = "generate"
        const val TASK_DOWNLOAD = "download"
        const val TASK_QUANTIZE = "quantize"

        fun start(ctx: Context, task: String, params: JSONObject? = null): Boolean {
            if (!LocalJobs.tryStart(task)) return false
            val i = Intent(ctx, GenerationService::class.java).putExtra(EXTRA_TASK, task)
            params?.let { i.putExtra(EXTRA_PARAMS, it.toString()) }
            ctx.startForegroundService(i)
            return true
        }
    }
}
