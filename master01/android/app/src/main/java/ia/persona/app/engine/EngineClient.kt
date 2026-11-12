package ia.persona.app.engine

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL

/**
 * Client du contrat moteur (voir master01/engine/persona_engine/contract.py).
 * Aucun écran ne dépend du backend : PC local ou GPU temporaire derrière la même API.
 */
class EngineClient(baseUrl: String, private val token: String, private val timeoutMs: Int = 20_000) {
    val base: String = baseUrl.trimEnd('/')

    class EngineException(val code: Int, msg: String) : IOException(msg)

    init {
        validateUrl(base)
        require(token.isNotBlank()) { "jeton du moteur requis" }
    }

    private fun open(method: String, path: String): HttpURLConnection {
        val c = URL(base + path).openConnection() as HttpURLConnection
        c.requestMethod = method
        c.connectTimeout = timeoutMs
        c.readTimeout = timeoutMs * 3
        c.setRequestProperty("Authorization", "Bearer $token")
        return c
    }

    private fun exec(method: String, path: String, body: ByteArray? = null,
                     headers: Map<String, String> = emptyMap()): ByteArray {
        val c = open(method, path)
        try {
            headers.forEach { (k, v) -> c.setRequestProperty(k, v) }
            if (body != null) {
                c.doOutput = true
                c.setFixedLengthStreamingMode(body.size)
                c.outputStream.use { it.write(body) }
            }
            val code = c.responseCode
            val stream = if (code in 200..299) c.inputStream else c.errorStream
            val bytes = stream?.use { it.readBytes() } ?: ByteArray(0)
            if (code !in 200..299) {
                val msg = try { JSONObject(String(bytes)).optString("error", "HTTP $code") } catch (_: Exception) { "HTTP $code" }
                throw EngineException(code, msg)
            }
            return bytes
        } finally {
            c.disconnect()
        }
    }

    private fun json(method: String, path: String, body: JSONObject? = null): JSONObject =
        JSONObject(String(exec(method, path, body?.toString()?.toByteArray(),
            if (body != null) mapOf("Content-Type" to "application/json") else emptyMap())))

    fun health(): JSONObject = json("GET", "/v1/health")

    fun createJob(kind: String, seed: Long?, params: JSONObject, profile: String): JSONObject {
        val spec = JSONObject().put("kind", kind).put("consent_declared", true).put("params", params).put("profile", profile)
        if (seed != null) spec.put("seed", seed)
        return json("POST", "/v1/jobs", spec)
    }

    fun uploadAuthorizedReference(jobId: String, sha256: String, bytes: ByteArray): JSONObject =
        JSONObject(String(exec("PUT", "/v1/jobs/$jobId/references/$sha256", bytes,
            mapOf("X-Consent" to "granted", "Content-Type" to "application/octet-stream"))))

    fun start(jobId: String) = json("POST", "/v1/jobs/$jobId/start")
    fun getStatus(jobId: String) = json("GET", "/v1/jobs/$jobId")
    fun cancelJob(jobId: String) = json("POST", "/v1/jobs/$jobId/cancel")
    fun fetchOutput(jobId: String, view: String): ByteArray = exec("GET", "/v1/jobs/$jobId/outputs/$view")
    fun fetchBoard(jobId: String): ByteArray = exec("GET", "/v1/jobs/$jobId/board.png")
    fun fetchManifest(jobId: String) = json("GET", "/v1/jobs/$jobId/manifest")
    fun rebuildBoard(jobId: String) = json("POST", "/v1/jobs/$jobId/board")
    fun review(jobId: String, view: String, accepted: Boolean, note: String) =
        json("POST", "/v1/jobs/$jobId/views/$view/review", JSONObject().put("accepted", accepted).put("note", note))
    fun regenerate(jobId: String, view: String) = json("POST", "/v1/jobs/$jobId/views/$view/regenerate", JSONObject())
    fun deleteJob(jobId: String) = json("DELETE", "/v1/jobs/$jobId")

    companion object {
        /** https:// partout ; http:// seulement vers localhost / émulateur / adresses privées littérales. */
        fun validateUrl(url: String) {
            val u = URL(url)
            require(u.protocol == "https" || u.protocol == "http") { "protocole non pris en charge" }
            if (u.protocol == "http") require(isPrivateHost(u.host)) {
                "HTTP non chiffré refusé vers ${u.host} : utilisez https ou une adresse de réseau local privé"
            }
        }

        fun isPrivateHost(host: String): Boolean {
            if (host == "localhost") return true
            val literal = Regex("^\\d{1,3}(\\.\\d{1,3}){3}$")
            if (!literal.matches(host)) return false          // pas de résolution DNS : nom => https exigé
            val a = InetAddress.getByName(host)
            return a.isLoopbackAddress || a.isSiteLocalAddress || a.isLinkLocalAddress
        }
    }
}
