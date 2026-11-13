package ia.persona.app.engine

import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.io.RandomAccessFile
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Paquet de modèles locaux (installation initiale), séparé de l'APK à cause de sa taille.
 *
 * Seul trafic réseau de l'application en mode local : téléchargement de ces fichiers publics, à des
 * révisions IMMUABLES, vérifiés par SHA-256. Aucune référence ni résultat n'est jamais envoyé.
 * Alternative sans réseau : import des mêmes fichiers depuis le stockage (même vérification).
 */
class ModelStore(val dir: File, private val specs: List<Spec> = SPECS) {

    data class Spec(
        val role: String, val repo: String, val revision: String, val file: String,
        val size: Long, val sha256: String, val license: String,
    ) {
        val url: String get() = "https://huggingface.co/$repo/resolve/$revision/$file"
    }

    enum class State { ABSENT, PARTIAL, PRESENT_UNVERIFIED, VERIFIED, CORRUPT }

    class StoreException(message: String) : Exception(message)

    init { dir.mkdirs() }

    fun target(s: Spec) = File(dir, s.file)
    private fun part(s: Spec) = File(dir, s.file + ".part")
    private fun stamp(s: Spec) = File(dir, s.file + ".verified")
    val quantized: File get() = File(dir, QUANT_FILE)
    private val quantStamp: File get() = File(dir, "$QUANT_FILE.json")

    fun state(s: Spec): State {
        val f = target(s)
        if (f.isFile) {
            if (stamp(s).isFile && stamp(s).readText().trim() == "${s.sha256} ${f.length()}") return State.VERIFIED
            return if (f.length() == s.size) State.PRESENT_UNVERIFIED else State.CORRUPT
        }
        return if (part(s).isFile) State.PARTIAL else State.ABSENT
    }

    fun freeBytes(): Long = dir.usableSpace

    /** Espace encore nécessaire pour finir l'installation, y compris la quantification. */
    fun bytesNeeded(): Long {
        var n = 0L
        for (s in specs) if (!(s === SDXL && quantReady()) && state(s) != State.VERIFIED) n += s.size - (part(s).takeIf { it.isFile }?.length() ?: 0L)
        if (!quantReady()) n += QUANT_SIZE_ESTIMATE
        return n
    }

    fun verify(s: Spec, onProgress: (Long, Long) -> Unit = { _, _ -> }): Boolean {
        val f = target(s)
        if (!f.isFile || f.length() != s.size) return false
        val ok = sha256(f.inputStream(), f.length(), onProgress) == s.sha256
        if (ok) stamp(s).writeText("${s.sha256} ${f.length()}") else stamp(s).delete()
        return ok
    }

    /** Téléchargement avec reprise (HTTP Range), écriture dans .part, vérification puis renommage. */
    fun download(s: Spec, cancelled: () -> Boolean, onProgress: (Long, Long) -> Unit, urlOverride: String? = null) {
        if (state(s) == State.VERIFIED) return
        val p = part(s)
        val need = s.size - (if (p.isFile) p.length() else 0L)
        if (freeBytes() < need + MARGIN) throw StoreException("espace insuffisant : ${need / MB} Mo nécessaires")
        var have = if (p.isFile) p.length() else 0L
        if (have > s.size) { p.delete(); have = 0 }
        var conn: HttpURLConnection? = null
        try {
            conn = (URL(urlOverride ?: s.url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 30_000; readTimeout = 60_000; instanceFollowRedirects = true
                if (have > 0) setRequestProperty("Range", "bytes=$have-")
            }
            val code = conn.responseCode
            if (code == 200 && have > 0) { have = 0; p.delete() }           // serveur sans reprise
            else if (code != 200 && code != 206) throw StoreException("téléchargement refusé (HTTP $code)")
            RandomAccessFile(p, "rw").use { raf ->
                raf.seek(have)
                conn.inputStream.use { input ->
                    val buf = ByteArray(1 shl 20)
                    while (true) {
                        if (cancelled()) throw StoreException("téléchargement interrompu (reprise possible)")
                        val n = input.read(buf)
                        if (n < 0) break
                        raf.write(buf, 0, n); have += n
                        onProgress(have, s.size)
                    }
                }
                raf.fd.sync()
            }
        } finally { conn?.disconnect() }
        if (p.length() != s.size) throw StoreException("fichier incomplet (${p.length()}/${s.size}), relancer pour reprendre")
        if (sha256(p.inputStream(), p.length()) { _, _ -> } != s.sha256) {
            p.delete(); throw StoreException("empreinte SHA-256 invalide : fichier supprimé, recommencer")
        }
        if (!p.renameTo(target(s))) throw StoreException("renommage impossible")
        stamp(s).writeText("${s.sha256} ${s.size}")
    }

    /** Import local (sans réseau) : copie puis vérification SHA-256 stricte. */
    fun import(s: Spec, input: InputStream, onProgress: (Long, Long) -> Unit) {
        if (freeBytes() < s.size + MARGIN) throw StoreException("espace insuffisant")
        val p = part(s)
        p.delete()
        var n = 0L
        FileOutputStream(p).use { out ->
            input.use { inp ->
                val buf = ByteArray(1 shl 20)
                while (true) { val r = inp.read(buf); if (r < 0) break; out.write(buf, 0, r); n += r; onProgress(n, s.size) }
            }
            out.fd.sync()
        }
        if (n != s.size || sha256(p.inputStream(), n) { _, _ -> } != s.sha256) {
            p.delete(); throw StoreException("ce fichier n'est pas ${s.file} (taille ou empreinte différente)")
        }
        if (!p.renameTo(target(s))) throw StoreException("renommage impossible")
        stamp(s).writeText("${s.sha256} ${s.size}")
    }

    fun quantReady(): Boolean = quantized.isFile && quantStamp.isFile &&
        runCatching { JSONObject(quantStamp.readText()).getLong("size") == quantized.length() }.getOrDefault(false)

    /** Quantification q8_0 sur l'appareil, avec le moteur embarqué ; l'original peut ensuite être supprimé. */
    fun quantize(engine: LocalEngine, onEvent: (LocalEngine.Event) -> Unit): JSONObject {
        val src = target(SDXL)
        if (state(SDXL) != State.VERIFIED) throw StoreException("modèle SDXL non vérifié")
        if (freeBytes() < QUANT_SIZE_ESTIMATE + MARGIN) throw StoreException("espace insuffisant pour la quantification")
        val tmp = File(dir, "$QUANT_FILE.tmp")
        val r = engine.convert(src, tmp, "q8_0", onEvent)
        val sha = sha256(tmp.inputStream(), tmp.length()) { _, _ -> }
        if (!tmp.renameTo(quantized)) throw StoreException("renommage impossible")
        val info = JSONObject().put("size", quantized.length()).put("sha256", sha)
            .put("matches_ci_reference", sha == QUANT_SHA256_CI).put("seconds", r.seconds).put("peak_rss_mb", r.peakRssMb)
        quantStamp.writeText(info.toString(2))
        return info
    }

    fun quantInfo(): JSONObject? = runCatching { JSONObject(quantStamp.readText()) }.getOrNull()

    fun deleteOriginalSdxl() { if (quantReady()) { target(SDXL).delete(); stamp(SDXL).delete() } }

    fun ready(): Boolean = quantReady() && state(VAE) == State.VERIFIED && state(PHOTOMAKER) == State.VERIFIED

    fun models(): LocalEngine.Models = LocalEngine.Models(quantized, target(VAE), target(PHOTOMAKER))

    fun wipe() { dir.listFiles()?.forEach { it.delete() } }

    companion object {
        const val MB = 1_048_576L
        const val MARGIN = 512 * MB
        const val QUANT_FILE = "sdxl_realvisxl4_lightning_q8_0.gguf"
        const val QUANT_SIZE_ESTIMATE = 4_180_813_792L
        /** Empreinte obtenue par la CI (x86, même commit sd.cpp) ; une différence sur ARM est signalée, pas bloquante. */
        const val QUANT_SHA256_CI = "46272d34a83e09ae4c497119afc673bbbf5bf33eaab46d7e8b9a1a68065e4bb2"

        val SDXL = Spec("sdxl", "SG161222/RealVisXL_V4.0_Lightning", "39b41eff57c9d10c62119590901d6771863b426d",
            "RealVisXL_V4.0_Lightning.safetensors", 6_939_220_250L,
            "d6a48d3e2025448f011c27f4667145286910696d744c50c8ba3c2fb31dc98ea1", "CreativeML OpenRAIL++-M")
        val VAE = Spec("vae", "madebyollin/sdxl-vae-fp16-fix", "207b116dae70ace3637169f1ddd2434b91b3a8cd",
            "sdxl_vae.safetensors", 334_641_162L,
            "235745af8d86bf4a4c1b5b4f529868b37019a10f7c0b2e79ad0abca3a22bc6e1", "MIT")
        val PHOTOMAKER = Spec("photomaker", "bssrdf/PhotoMaker", "1d7e19f85ce03bc409b77a874998e5defd50346f",
            "photomaker-v1.safetensors", 933_571_072L,
            "21b907eed072fa9fdbe7418384b50f448856d497f702114f4a43bd7d7ac7ee19", "Apache-2.0")
        val SPECS = listOf(SDXL, VAE, PHOTOMAKER)

        fun sha256(input: InputStream, total: Long, onProgress: (Long, Long) -> Unit): String = input.use {
            val md = MessageDigest.getInstance("SHA-256")
            val buf = ByteArray(1 shl 20)
            var done = 0L
            while (true) { val n = it.read(buf); if (n < 0) break; md.update(buf, 0, n); done += n; onProgress(done, total) }
            md.digest().joinToString("") { b -> "%02x".format(b) }
        }
    }
}
