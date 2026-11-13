package ia.persona.app.engine

import java.io.File
import java.io.InputStreamReader
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Moteur de génération 100 % local : binaire natif stable-diffusion.cpp (sd-cli) embarqué dans l'APK
 * sous le nom libsdcli.so (extrait dans nativeLibraryDir) et exécuté dans un PROCESSUS SÉPARÉ :
 * - isolation : un crash ou un manque de mémoire du moteur ne tue pas l'application ;
 * - annulation effective : arrêt du processus, toutes ses ressources sont libérées par le système ;
 * - aucun réseau, aucun Termux, aucun Python : le binaire ne lit que des fichiers locaux.
 */
class LocalEngine(private val binary: File, private val workDir: File) {

    enum class Stage(val label: String) {
        STARTING("démarrage"), LOADING("chargement du modèle"), PREPARING("préparation (identité, texte)"),
        SAMPLING("inférence"), DECODING("décodage"), SAVING("enregistrement"), DONE("terminé")
    }

    enum class ErrorKind { ENGINE_MISSING, MODEL_MISSING, OUT_OF_MEMORY, CANCELLED, NO_OUTPUT, FAILED }

    class EngineError(val kind: ErrorKind, message: String, val logTail: String = "") : Exception(message)

    data class Event(val stage: Stage, val step: Int = 0, val totalSteps: Int = 0, val line: String = "")

    data class Models(val diffusion: File, val vae: File?, val photomaker: File?)

    data class Request(
        val prompt: String,
        val negative: String,
        val width: Int,
        val height: Int,
        val steps: Int,
        val cfg: Float,
        val seed: Long,
        val references: List<File>,          // vide => génération sans PhotoMaker
        val styleStrength: Int = 20,
        val threads: Int,
        val sampler: String = "euler",
        val scheduler: String = "sgm_uniform",
    )

    data class Result(val output: File, val seconds: Double, val peakRssMb: Long, val log: String, val args: List<String>)

    private val cancelled = AtomicBoolean(false)
    @Volatile private var process: Process? = null
    @Volatile private var pid: Int = -1

    fun available(): Boolean = binary.isFile && binary.canExecute()

    fun cancel() {
        cancelled.set(true)
        val p = pid
        if (p > 0) runCatching { android.os.Process.sendSignal(p, 9) }
        process?.destroyForcibly()
    }

    /** Vérifie que le binaire s'exécute sur cet appareil (ABI, W^X) sans charger de modèle. */
    fun selfTest(): String {
        if (!available()) throw EngineError(ErrorKind.ENGINE_MISSING, "moteur natif absent de cette APK (${binary.path})")
        val p = ProcessBuilder(binary.path, "--help").redirectErrorStream(true).start()
        val out = p.inputStream.bufferedReader().readText()
        p.waitFor()
        return out.lineSequence().firstOrNull { it.isNotBlank() } ?: "(aucune sortie)"
    }

    fun buildArgs(req: Request, models: Models, output: File, idDir: File?): List<String> {
        val a = mutableListOf(
            "-m", models.diffusion.path, "-p", req.prompt, "-n", req.negative,
            "--seed", req.seed.toString(), "-W", req.width.toString(), "-H", req.height.toString(),
            "--steps", req.steps.toString(), "--cfg-scale", req.cfg.toString(),
            "--sampling-method", req.sampler, "--scheduler", req.scheduler,
            "--threads", req.threads.toString(), "--vae-tiling", "-o", output.path,
        )
        models.vae?.let { a += listOf("--vae", it.path) }
        if (idDir != null) {
            val pm = models.photomaker ?: throw EngineError(ErrorKind.MODEL_MISSING, "fichier PhotoMaker absent")
            a += listOf("--photo-maker", pm.path, "--pm-id-images-dir", idDir.path,
                "--pm-style-strength", req.styleStrength.toString())
        }
        return a
    }

    fun generate(req: Request, models: Models, output: File, onEvent: (Event) -> Unit): Result {
        if (!available()) throw EngineError(ErrorKind.ENGINE_MISSING, "moteur natif absent de cette APK")
        for (f in listOfNotNull(models.diffusion, models.vae, models.photomaker))
            if (!f.isFile) throw EngineError(ErrorKind.MODEL_MISSING, "fichier modèle manquant : ${f.name}")
        cancelled.set(false)
        val idDir = if (req.references.isNotEmpty()) File(workDir, "ids-${System.nanoTime()}").apply { mkdirs() } else null
        try {
            req.references.take(4).forEachIndexed { i, f ->
                val ext = if (isPng(f)) "png" else "jpg"
                f.copyTo(File(idDir, "ref$i.$ext"), overwrite = true)
            }
            output.parentFile?.mkdirs()
            output.delete()
            val args = buildArgs(req, models, output, idDir)
            return runProcess(listOf(binary.path) + args, req.steps, output, onEvent)
        } finally {
            idDir?.deleteRecursively()          // copies temporaires des références supprimées
        }
    }

    /** Conversion/quantification d'un modèle (étape d'installation, aussi locale). */
    fun convert(src: File, dst: File, type: String, onEvent: (Event) -> Unit): Result {
        if (!available()) throw EngineError(ErrorKind.ENGINE_MISSING, "moteur natif absent de cette APK")
        cancelled.set(false)
        dst.delete()
        return runProcess(listOf(binary.path, "-M", "convert", "-m", src.path, "-o", dst.path, "--type", type), 0, dst, onEvent)
    }

    private fun runProcess(cmd: List<String>, totalSteps: Int, output: File, onEvent: (Event) -> Unit): Result {
        val t0 = System.nanoTime()
        onEvent(Event(Stage.STARTING))
        // sh affiche d'abord son PID puis est remplacé par le moteur (exec) : même PID, mesurable via /proc.
        val pb = ProcessBuilder(listOf(SHELL, "-c", "echo PERSONA_PID=\$\$; exec \"\$@\"", "sh") + cmd)
            .directory(workDir).redirectErrorStream(true)
        val p = pb.start()
        process = p
        val log = StringBuilder()
        var peakKb = 0L
        val monitor = Thread {
            while (process === p && p.isAlive) {
                val id = pid
                if (id > 0) peakKb = maxOf(peakKb, readVmHwmKb(id))
                try { Thread.sleep(500) } catch (_: InterruptedException) { break }
            }
        }.apply { isDaemon = true; start() }
        val parser = LogParser(totalSteps)
        InputStreamReader(p.inputStream).use { r ->
            val line = StringBuilder()
            while (true) {
                val c = r.read()
                if (c < 0 || c == '\n'.code || c == '\r'.code) {
                    if (line.isNotEmpty()) {
                        val s = line.toString()
                        line.setLength(0)
                        if (s.startsWith("PERSONA_PID=")) pid = s.removePrefix("PERSONA_PID=").trim().toIntOrNull() ?: -1
                        else {
                            if (log.length < 200_000) log.append(s).append('\n')
                            parser.parse(s)?.let(onEvent)
                        }
                    }
                    if (c < 0) break
                } else line.append(c.toChar())
            }
        }
        val code = p.waitFor()
        val id = pid
        if (id > 0) peakKb = maxOf(peakKb, readVmHwmKb(id))
        process = null
        pid = -1
        monitor.interrupt()
        val seconds = (System.nanoTime() - t0) / 1e9
        val tail = log.takeLast(2000).toString()
        if (cancelled.get()) throw EngineError(ErrorKind.CANCELLED, "annulé par l'utilisateur", tail)
        if (code == 137 || code == 9 || tail.contains("bad_alloc") || tail.contains("out of memory", true))
            throw EngineError(ErrorKind.OUT_OF_MEMORY, "mémoire insuffisante (code $code)", tail)
        if (code != 0) throw EngineError(ErrorKind.FAILED, "le moteur a échoué (code $code)", tail)
        if (!output.isFile || output.length() == 0L) throw EngineError(ErrorKind.NO_OUTPUT, "aucun fichier produit", tail)
        onEvent(Event(Stage.DONE))
        return Result(output, seconds, peakKb / 1024, log.toString(), cmd.drop(1))
    }

    companion object {
        val SHELL: String = if (File("/system/bin/sh").exists()) "/system/bin/sh" else "/bin/sh"

        fun isPng(f: File): Boolean = f.inputStream().use { s ->
            val h = ByteArray(4); s.read(h) == 4 && h[0] == 0x89.toByte() && h[1] == 'P'.code.toByte()
        }

        fun readVmHwmKb(pid: Int): Long = runCatching {
            File("/proc/$pid/status").readLines().firstOrNull { it.startsWith("VmHWM:") }
                ?.split(Regex("\\s+"))?.getOrNull(1)?.toLong() ?: 0L
        }.getOrDefault(0L)
    }
}

/** Traduit les lignes du moteur en étapes observables (pas de pourcentage inventé). */
class LogParser(private val totalSteps: Int) {
    private val stepRe = Regex("""\|\s*(\d+)/(\d+)\s*-""")

    fun parse(line: String): LocalEngine.Event? {
        val l = line.lowercase()
        stepRe.find(line)?.let { m ->
            val step = m.groupValues[1].toInt()
            val total = m.groupValues[2].toInt()
            return LocalEngine.Event(LocalEngine.Stage.SAMPLING, step, total, line)
        }
        return when {
            "save result" in l -> LocalEngine.Event(LocalEngine.Stage.SAVING, line = line)
            "decoding" in l || "decode_first_stage" in l -> LocalEngine.Event(LocalEngine.Stage.DECODING, line = line)
            "generating image" in l || "sampling" in l -> LocalEngine.Event(LocalEngine.Stage.SAMPLING, 0, totalSteps, line)
            "photomaker" in l || "get_learned_condition" in l -> LocalEngine.Event(LocalEngine.Stage.PREPARING, line = line)
            "loading" in l || "load " in l || "loaded" in l -> LocalEngine.Event(LocalEngine.Stage.LOADING, line = line)
            else -> null
        }
    }
}
