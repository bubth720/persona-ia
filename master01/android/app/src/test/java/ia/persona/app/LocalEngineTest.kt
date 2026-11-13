package ia.persona.app

import ia.persona.app.engine.LocalEngine
import ia.persona.app.engine.LogParser
import ia.persona.app.engine.ModelStore
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.File
import java.net.ServerSocket
import java.nio.file.Files
import java.security.MessageDigest
import kotlin.concurrent.thread

class LocalEngineTest {
    private fun tmp() = Files.createTempDirectory("le").toFile()

    /** Faux moteur : imprime des lignes au format de sd.cpp, écrit -o, ou échoue selon FAKE_MODE dans le prompt. */
    private fun fakeBinary(dir: File): File = File(dir, "libsdcli.so").apply {
        writeText("""#!/bin/sh
out=""; prompt=""
while [ ${'$'}# -gt 0 ]; do case "${'$'}1" in -o) out="${'$'}2"; shift;; -p) prompt="${'$'}2"; shift;; esac; shift; done
echo "[INFO ] loading model from 'x'"
echo "[INFO ] Photomaker ID Stacking, taking 1s"
case "${'$'}prompt" in *SLOW*) exec sleep 30;; *OOM*) exit 137;; *FAIL*) echo "error: boom"; exit 2;; esac
printf '  |=====>    | 3/6 - 1.0s/it\r  |==========| 6/6 - 1.0s/it\n'
echo "[INFO ] decoding 1 latents"
case "${'$'}prompt" in *NOOUT*) exit 0;; esac
printf '\211PNGfake' > "${'$'}out"
echo "[INFO ] save result image 0 to '${'$'}out'"
""")
        setExecutable(true)
    }

    private fun req(prompt: String, refs: List<File>) = LocalEngine.Request(prompt, "neg", 512, 512, 6, 1.8f, 7, refs, threads = 2)

    private fun models(dir: File): LocalEngine.Models {
        val m = File(dir, "m.gguf").apply { writeText("x") }
        val pm = File(dir, "pm.safetensors").apply { writeText("x") }
        return LocalEngine.Models(m, null, pm)
    }

    @Test fun stagesStepsAndResult() {
        val d = tmp()
        val ref = File(d, "r.jpg").apply { writeBytes(byteArrayOf(-1, -40, 0, 0)) }
        val eng = LocalEngine(fakeBinary(d), d)
        val events = mutableListOf<LocalEngine.Event>()
        val r = eng.generate(req("a woman img, ok", listOf(ref)), models(d), File(d, "out/res.png")) { events += it }
        assertTrue(r.output.isFile)
        val stages = events.map { it.stage }.distinct()
        assertEquals(listOf(LocalEngine.Stage.STARTING, LocalEngine.Stage.LOADING, LocalEngine.Stage.PREPARING,
            LocalEngine.Stage.SAMPLING, LocalEngine.Stage.DECODING, LocalEngine.Stage.SAVING, LocalEngine.Stage.DONE), stages)
        assertEquals(6, events.last { it.stage == LocalEngine.Stage.SAMPLING }.step)
        assertTrue(r.args.contains("--photo-maker") && r.args.contains("--pm-id-images-dir"))
        assertFalse(d.listFiles()!!.any { it.name.startsWith("ids-") })      // copies temporaires supprimées
    }

    @Test fun typedErrors() {
        val d = tmp()
        val ref = File(d, "r.jpg").apply { writeBytes(byteArrayOf(-1, -40, 0, 0)) }
        val eng = LocalEngine(fakeBinary(d), d)
        for ((p, k) in listOf("OOM" to LocalEngine.ErrorKind.OUT_OF_MEMORY, "FAIL" to LocalEngine.ErrorKind.FAILED,
                "NOOUT" to LocalEngine.ErrorKind.NO_OUTPUT)) {
            try { eng.generate(req(p, listOf(ref)), models(d), File(d, "o.png")) {}; fail(p) }
            catch (e: LocalEngine.EngineError) { assertEquals(p, k, e.kind) }
        }
        try { eng.generate(req("x", listOf(ref)), LocalEngine.Models(File(d, "absent"), null, null), File(d, "o.png")) {}; fail() }
        catch (e: LocalEngine.EngineError) { assertEquals(LocalEngine.ErrorKind.MODEL_MISSING, e.kind) }
        try { LocalEngine(File(d, "nope.so"), d).selfTest(); fail() }
        catch (e: LocalEngine.EngineError) { assertEquals(LocalEngine.ErrorKind.ENGINE_MISSING, e.kind) }
    }

    @Test fun cancelKillsProcess() {
        val d = tmp()
        val ref = File(d, "r.jpg").apply { writeBytes(byteArrayOf(-1, -40, 0, 0)) }
        val eng = LocalEngine(fakeBinary(d), d)
        thread { Thread.sleep(800); eng.cancel() }
        val t0 = System.currentTimeMillis()
        try { eng.generate(req("SLOW", listOf(ref)), models(d), File(d, "o.png")) {}; fail() }
        catch (e: LocalEngine.EngineError) { assertEquals(LocalEngine.ErrorKind.CANCELLED, e.kind) }
        assertTrue("annulation effective", System.currentTimeMillis() - t0 < 10_000)
    }

    @Test fun logParserIgnoresNoise() {
        val p = LogParser(6)
        assertEquals(null, p.parse("random noise"))
        assertEquals(4, p.parse("  |====    | 4/6 - 2.31s/it")!!.step)
    }

    private fun sha(b: ByteArray) = MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }

    @Test fun downloadResumeVerifyAndCorruption() {
        val data = ByteArray(3_000_000) { (it * 31).toByte() }
        // Mini serveur HTTP (ServerSocket) : 1re réponse coupée après 1 Mo, 2e réponse en reprise (206).
        val server = ServerSocket(0)
        thread(isDaemon = true) {
            var first = true
            while (!server.isClosed) {
                val sock = runCatching { server.accept() }.getOrNull() ?: break
                sock.use { c ->
                    val reader = c.getInputStream().bufferedReader()
                    var start = 0
                    while (true) {
                        val l = reader.readLine() ?: break
                        if (l.isEmpty()) break
                        if (l.startsWith("Range:", true)) start = l.substringAfter("bytes=").substringBefore("-").trim().toInt()
                    }
                    val body = data.copyOfRange(start, data.size)
                    val status = if (start > 0) "206 Partial Content" else "200 OK"
                    val out = c.getOutputStream()
                    out.write("HTTP/1.1 $status\r\nContent-Length: ${body.size}\r\nConnection: close\r\n\r\n".toByteArray())
                    if (first) { first = false; out.write(body, 0, 1_000_000); out.flush() } else { out.write(body); out.flush() }
                }
            }
        }
        try {
            val port = server.localPort
            val spec = ModelStore.Spec("t", "x", "rev", "f.bin", data.size.toLong(), sha(data), "MIT")
            val d = tmp()
            val store = ModelStore(d, listOf(spec))
            val local = TestSpec.withUrl(spec, "http://127.0.0.1:$port/f.bin")
            try { TestSpec.download(store, local); } catch (_: Exception) { }   // coupure au 1er Mo
            assertEquals(ModelStore.State.PARTIAL, store.state(spec))
            TestSpec.download(store, local)                                       // reprise via Range
            assertEquals(ModelStore.State.VERIFIED, store.state(spec))
            // fichier corrompu à l'import : refusé
            try { store.import(spec, ByteArrayInputStream(data.copyOf().also { it[5] = 0 })) { _, _ -> }; fail() }
            catch (_: ModelStore.StoreException) { }
        } finally { server.close() }
    }
}
