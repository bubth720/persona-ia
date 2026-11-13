package ia.persona.app

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ia.persona.app.engine.LocalEngine
import ia.persona.app.engine.LocalJobs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Q02/Q05 sur émulateur : le VRAI moteur natif embarqué (libsdcli.so, compilé pour l'ABI de l'émulateur)
 * s'exécute depuis l'APK, sans Termux ; une erreur de modèle remonte comme erreur typée.
 * L'inférence complète SDXL n'est PAS lancée ici (modèle de 4 Go) : elle est prouvée par la CI CPU
 * et doit être qualifiée sur le POCO physique.
 */
@RunWith(AndroidJUnit4::class)
class NativeEngineTest {
    private val ctx = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun embeddedEngineExecutes() {
        val bin = LocalJobs.binary(ctx)
        assertTrue("libsdcli.so absent de nativeLibraryDir : ${bin.path}", bin.isFile)
        val first = LocalJobs.newEngine(ctx).selfTest()
        assertTrue("sortie inattendue: $first", first.isNotBlank())
    }

    @Test fun corruptModelGivesTypedError() {
        val dir = File(ctx.cacheDir, "badmodel").apply { mkdirs() }
        val bad = File(dir, "bad.gguf").apply { writeBytes(ByteArray(4096) { 7 }) }
        val out = File(dir, "o.png")
        val req = LocalEngine.Request("a photo", "", 64, 64, 1, 1f, 1, emptyList(), threads = 2)
        try {
            LocalJobs.newEngine(ctx).generate(req, LocalEngine.Models(bad, null, null), out) {}
            fail("un modèle corrompu ne doit pas produire d'image")
        } catch (e: LocalEngine.EngineError) {
            assertTrue(e.kind == LocalEngine.ErrorKind.FAILED || e.kind == LocalEngine.ErrorKind.NO_OUTPUT)
        }
        assertEquals(false, out.isFile && out.length() > 0)
    }
}
