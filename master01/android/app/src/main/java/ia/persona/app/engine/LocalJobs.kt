package ia.persona.app.engine

import android.content.Context
import android.os.Build
import android.os.PowerManager
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Orchestrateur : UNE tâche à la fois (génération, téléchargement ou quantification), état observable,
 * historique local hors ligne. L'exécution réelle a lieu dans GenerationService (premier plan).
 */
object LocalJobs {
    data class Status(
        val kind: String = "idle",          // idle | generate | download | quantize
        val running: Boolean = false,
        val stage: String = "",
        val step: Int = 0,
        val totalSteps: Int = 0,
        val message: String = "",
        val error: String? = null,
        val resultId: String? = null,
        val bytes: Long = 0, val totalBytes: Long = 0,
    )

    @Volatile var status = Status(); private set
    private val listeners = CopyOnWriteArrayList<(Status) -> Unit>()
    @Volatile var engine: LocalEngine? = null
    @Volatile var cancelFlag = false

    fun listen(l: (Status) -> Unit) { listeners += l; l(status) }
    fun unlisten(l: (Status) -> Unit) { listeners -= l }
    fun update(s: Status) { status = s; listeners.forEach { it(s) } }

    @Synchronized fun tryStart(kind: String): Boolean {
        if (status.running) return false
        cancelFlag = false
        update(Status(kind = kind, running = true, stage = "démarrage"))
        return true
    }

    fun cancel() { cancelFlag = true; engine?.cancel() }

    /** Variante optimisée (dotprod/fp16, ex. Dimensity 8500) si le processeur l'annonce, sinon générique. */
    fun binary(ctx: Context): File {
        val dir = File(ctx.applicationInfo.nativeLibraryDir)
        val fast = File(dir, "libsdcli.so")
        val generic = File(dir, "libsdcli_generic.so")
        val features = runCatching { File("/proc/cpuinfo").readText() }.getOrDefault("")
        val dotprod = Regex("""\basimddp\b""").containsMatchIn(features) && Regex("""\basimdhp\b""").containsMatchIn(features)
        return if (generic.isFile && !dotprod) generic else fast
    }
    fun store(ctx: Context) = ModelStore(File(ctx.filesDir, "models"))
    fun historyDir(ctx: Context) = File(ctx.filesDir, "history").apply { mkdirs() }
    fun newEngine(ctx: Context) = LocalEngine(binary(ctx), File(ctx.cacheDir, "engine").apply { mkdirs() })

    /** Paramètres réellement appliqués par profil (les deux profils sont fonctionnels, seul le coût change). */
    data class Profile(val id: String, val label: String, val longSide: Int, val steps: Int, val threads: Int)

    fun profiles(): List<Profile> {
        val cores = Runtime.getRuntime().availableProcessors()
        return listOf(
            Profile("prudent", "Prudent (plus rapide, moins détaillé)", 640, 5, (cores / 2).coerceIn(2, 4)),
            Profile("standard", "Standard (768 px, référence des tests)", 768, 6, cores.coerceIn(2, 8)),
        )
    }

    fun dims(format: String, longSide: Int): Pair<Int, Int> {
        val short = (longSide * 3 / 4) / 64 * 64
        return when (format) {
            "portrait" -> short to longSide
            "paysage" -> longSide to short
            else -> longSide to longSide
        }
    }

    fun thermalStatus(ctx: Context): Int =
        if (Build.VERSION.SDK_INT >= 29) (ctx.getSystemService(Context.POWER_SERVICE) as PowerManager).currentThermalStatus else 0

    // ---------------------------------------------------------------- historique
    fun history(ctx: Context): List<JSONObject> =
        historyDir(ctx).listFiles()?.mapNotNull { d -> runCatching { JSONObject(File(d, "meta.json").readText()) }.getOrNull() }
            ?.sortedByDescending { it.optLong("created_ms") } ?: emptyList()

    fun newHistoryEntry(ctx: Context): Pair<String, File> {
        val id = UUID.randomUUID().toString().substring(0, 12)
        return id to File(historyDir(ctx), id).apply { mkdirs() }
    }

    fun deleteEntry(ctx: Context, id: String) { File(historyDir(ctx), id).deleteRecursively() }

    fun refIds(shas: List<String>) = JSONArray().apply { shas.forEach { put(it.take(16)) } }
}
