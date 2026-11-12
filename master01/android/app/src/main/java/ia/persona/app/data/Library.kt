package ia.persona.app.data

import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.security.MessageDigest

/**
 * Bibliothèque de références (Phase C) en stockage privé de l'application.
 *
 * - copie octet par octet, jamais de modification de l'original ;
 * - doublons exacts détectés par SHA-256 et signalés ;
 * - journal append-only (fsync) => reprise après interruption, orphelins récupérés ;
 * - aucun import sans autorisation déclarée ; classement manuel ("non_classe" par défaut).
 *
 * Le chiffrement repose sur le chiffrement de fichiers d'Android (FBE) du stockage privé ;
 * allowBackup=false : aucune sauvegarde cloud implicite.
 */
class Library(val root: File) {
    data class Ref(
        val sha256: String,
        val ext: String,
        val size: Long,
        val sourceName: String,
        val importedAt: Long,
        var authorized: Boolean,
        var view: String = "non_classe",
        var validated: Boolean = false,
    )

    enum class Outcome { IMPORTED, DUPLICATE, ERROR }
    data class ImportResult(val outcome: Outcome, val sha256: String?, val message: String = "")

    class ConsentException(msg: String) : SecurityException(msg)

    private val originals = File(root, "originals")
    private val journal = File(root, "journal.jsonl")
    private val records = LinkedHashMap<String, Ref>()
    val recovered = mutableListOf<String>()

    init {
        originals.mkdirs()
        replay()
        recoverOrphans()
    }

    @Synchronized fun all(): List<Ref> = records.values.toList()
    @Synchronized fun get(sha: String): Ref? = records[sha]
    fun fileFor(ref: Ref): File = File(File(originals, ref.sha256.substring(0, 2)), ref.sha256 + ref.ext)

    private fun append(obj: JSONObject) {
        FileOutputStream(journal, true).use { out ->
            out.write((obj.toString() + "\n").toByteArray(Charsets.UTF_8))
            out.flush()
            out.fd.sync()
        }
    }

    private fun replay() {
        if (!journal.exists()) return
        journal.forEachLine { line ->
            if (line.isBlank()) return@forEachLine
            val e = try { JSONObject(line) } catch (_: Exception) { return@forEachLine } // ligne tronquée
            when (e.optString("op")) {
                "import" -> {
                    val r = e.getJSONObject("record")
                    records[r.getString("sha256")] = Ref(
                        r.getString("sha256"), r.getString("ext"), r.getLong("size"), r.getString("sourceName"),
                        r.getLong("importedAt"), r.getBoolean("authorized"))
                }
                "annotate" -> records[e.getString("sha256")]?.let { ref ->
                    if (e.has("view")) ref.view = e.getString("view")
                    if (e.has("validated")) ref.validated = e.getBoolean("validated")
                    if (e.has("authorized")) ref.authorized = e.getBoolean("authorized")
                }
                "remove" -> records.remove(e.getString("sha256"))
            }
        }
    }

    private fun recoverOrphans() {
        originals.listFiles()?.forEach { dir ->
            if (dir.isFile) { if (dir.name.startsWith(".tmp-")) dir.delete(); return@forEach }  // copie partielle
            dir.listFiles()?.forEach { f ->
                if (f.name.startsWith(".tmp-")) { f.delete(); return@forEach }
                val sha = f.nameWithoutExtension
                if (records.containsKey(sha)) return@forEach
                if (sha256(f.inputStream()) != sha) { f.delete(); return@forEach }
                val ref = Ref(sha, "." + f.extension, f.length(), "(récupéré après interruption)",
                    System.currentTimeMillis(), authorized = false)
                append(importEntry(ref))
                records[sha] = ref
                recovered.add(sha)
            }
        }
    }

    private fun importEntry(ref: Ref) = JSONObject().put("op", "import").put("record", JSONObject()
        .put("sha256", ref.sha256).put("ext", ref.ext).put("size", ref.size).put("sourceName", ref.sourceName)
        .put("importedAt", ref.importedAt).put("authorized", ref.authorized))

    /** Importe un flux (SAF ou fichier). [authorized] doit refléter la déclaration de l'utilisateur. */
    @Synchronized
    fun importStream(name: String, input: InputStream, authorized: Boolean): ImportResult {
        if (!authorized) throw ConsentException("Import refusé : usage des photographies non déclaré comme autorisé.")
        val ext = ("." + name.substringAfterLast('.', "")).lowercase()
        if (ext !in SUPPORTED) return ImportResult(Outcome.ERROR, null, "format non pris en charge: $name")
        val tmp = File(originals, ".tmp-" + System.nanoTime() + ext)
        try {
            val md = MessageDigest.getInstance("SHA-256")
            var size = 0L
            FileOutputStream(tmp).use { out ->
                val buf = ByteArray(1 shl 16)
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    md.update(buf, 0, n); out.write(buf, 0, n); size += n
                }
                out.flush(); out.fd.sync()
            }
            val sha = md.digest().joinToString("") { "%02x".format(it) }
            if (!looksLikeImage(tmp)) { tmp.delete(); return ImportResult(Outcome.ERROR, null, "fichier non image: $name") }
            if (records.containsKey(sha)) { tmp.delete(); return ImportResult(Outcome.DUPLICATE, sha, records[sha]!!.sourceName) }
            val dest = File(File(originals, sha.substring(0, 2)).apply { mkdirs() }, sha + ext)
            if (!tmp.renameTo(dest)) { tmp.delete(); return ImportResult(Outcome.ERROR, null, "écriture impossible") }
            val ref = Ref(sha, ext, size, File(name).name, System.currentTimeMillis(), authorized = true)
            append(importEntry(ref))
            records[sha] = ref
            return ImportResult(Outcome.IMPORTED, sha)
        } catch (e: Exception) {
            tmp.delete()
            return ImportResult(Outcome.ERROR, null, e.message ?: e.javaClass.simpleName)
        }
    }

    @Synchronized
    fun annotate(sha: String, view: String? = null, validated: Boolean? = null) {
        val ref = records[sha] ?: return
        require(view == null || view in REFERENCE_VIEWS) { "vue inconnue $view" }
        val e = JSONObject().put("op", "annotate").put("sha256", sha)
        view?.let { e.put("view", it); ref.view = it }
        validated?.let { e.put("validated", it); ref.validated = it }
        append(e)
    }

    @Synchronized
    fun confirmConsent(sha: String) {
        val ref = records[sha] ?: return
        ref.authorized = true
        append(JSONObject().put("op", "annotate").put("sha256", sha).put("authorized", true))
    }

    /** Effacement volontaire (Réglages) : supprime copies privées et journal. Les originaux externes restent. */
    @Synchronized
    fun wipe() {
        originals.deleteRecursively(); journal.delete(); records.clear(); originals.mkdirs()
    }

    /** Diagnostic de couverture à partir des seuls libellés validés par l'humain. */
    @Synchronized
    fun coverage(): Map<String, Int> {
        val counts = REFERENCE_VIEWS.associateWith { 0 }.toMutableMap()
        records.values.filter { it.validated }.forEach { counts[it.view] = counts.getValue(it.view) + 1 }
        return counts
    }

    fun missingViews(): List<String> =
        coverage().filter { (k, v) -> k in NEEDED && v == 0 }.keys.toList()

    /** Références envoyables au moteur : autorisées, de préférence validées et pertinentes. */
    @Synchronized
    fun selectForEngine(kind: String, max: Int = 6): List<Ref> {
        val ok = records.values.filter { it.authorized }
        val wanted = if (kind == "face") FACE_REF_VIEWS else BODY_REF_VIEWS
        val preferred = ok.filter { it.validated && it.view in wanted }
        val pool = preferred.ifEmpty { ok.filter { it.validated }.ifEmpty { ok } }
        return pool.sortedBy { it.view }.take(max)
    }

    companion object {
        val SUPPORTED = setOf(".jpg", ".jpeg", ".png", ".webp")
        val REFERENCE_VIEWS = listOf("face", "profil_gauche", "profil_droit", "trois_quarts_gauche",
            "trois_quarts_droit", "dos", "plan_americain", "plein_pied", "non_classe")
        val FACE_REF_VIEWS = setOf("face", "profil_gauche", "profil_droit", "trois_quarts_gauche", "trois_quarts_droit")
        val BODY_REF_VIEWS = setOf("plein_pied", "plan_americain", "dos", "face")
        val NEEDED = listOf("face", "profil_gauche", "profil_droit", "trois_quarts_gauche", "trois_quarts_droit",
            "plein_pied", "dos")

        fun sha256(input: InputStream): String = input.use {
            val md = MessageDigest.getInstance("SHA-256")
            val buf = ByteArray(1 shl 16)
            while (true) { val n = it.read(buf); if (n < 0) break; md.update(buf, 0, n) }
            md.digest().joinToString("") { b -> "%02x".format(b) }
        }

        fun looksLikeImage(f: File): Boolean {
            val h = ByteArray(12)
            val n = f.inputStream().use { it.read(h) }
            if (n < 4) return false
            val jpeg = h[0] == 0xFF.toByte() && h[1] == 0xD8.toByte()
            val png = h[0] == 0x89.toByte() && h[1] == 'P'.code.toByte() && h[2] == 'N'.code.toByte()
            val webp = n >= 12 && String(h, 0, 4, Charsets.US_ASCII) == "RIFF" && String(h, 8, 4, Charsets.US_ASCII) == "WEBP"
            return jpeg || png || webp
        }
    }
}
